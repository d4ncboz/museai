from __future__ import annotations

import asyncio
import math
import time

import pytest

from museai.accounts import Account, AccountPool, AccountStatus, JsonAccountStore
from museai.api.routes.dashboard import usage_estimate
from museai.api.routes.videos import video_timeout
from museai.config import Settings
from museai.drivers.base import ChatRequest, VideoRequest
from museai.drivers.mock import MockDriver
from museai.errors import (
    GenerationTimeout,
    NoAccountAvailable,
    UpstreamAuthError,
    UpstreamError,
    UpstreamQuotaError,
    UpstreamRefused,
)
from museai.services.gateway import Gateway
from museai.services.tasks import Task, TaskStatus


async def _pool(tmp_path, n=2, **kw) -> AccountPool:
    pool = AccountPool(JsonAccountStore(tmp_path / "acc.json"), acquire_timeout=0.2, **kw)
    for i in range(n):
        await pool.upsert(Account(id=f"a{i}", cookies={"hatch_sess": "x"}))
    return pool


async def test_empty_pool_raises(tmp_path):
    pool = await _pool(tmp_path, n=0)
    with pytest.raises(NoAccountAvailable):
        await pool.acquire()


async def test_lru_spreads_load(tmp_path):
    pool = await _pool(tmp_path, strategy="lru")
    first = await pool.acquire()
    await pool.release(first)
    second = await pool.acquire()
    assert first.id != second.id


async def test_concurrency_limit_waits_then_times_out(tmp_path):
    pool = await _pool(tmp_path, n=1)
    held = await pool.acquire()
    with pytest.raises(NoAccountAvailable, match="busy"):
        await pool.acquire()
    waiter = asyncio.create_task(pool.acquire())
    await asyncio.sleep(0.05)
    await pool.release(held)
    assert (await waiter).id == held.id


async def test_auth_error_invalidates(tmp_path):
    pool = await _pool(tmp_path, n=1)
    with pytest.raises(UpstreamAuthError):
        async with pool.lease():
            raise UpstreamAuthError("bad cookie")
    assert pool.get("a0").status == AccountStatus.INVALID
    with pytest.raises(NoAccountAvailable):
        await pool.acquire()


async def test_all_cooling_waits_for_cooldown_instead_of_failing(tmp_path):
    pool = await _pool(tmp_path, n=1)
    acc = pool.get("a0")
    acc.status, acc.cooldown_until = AccountStatus.COOLING, time.time() + 0.15
    got = await pool.acquire(timeout=2)
    assert got.id == "a0"


async def test_cooling_past_the_deadline_still_times_out(tmp_path):
    pool = await _pool(tmp_path, n=1)
    acc = pool.get("a0")
    acc.status, acc.cooldown_until = AccountStatus.COOLING, time.time() + 60
    with pytest.raises(NoAccountAvailable, match="cooling"):
        await pool.acquire()


async def test_unlimited_queue_waits_for_busy_account(tmp_path):
    pool = await _pool(tmp_path, n=1)
    held = await pool.acquire()
    waiter = asyncio.create_task(pool.acquire(timeout=math.inf))
    await asyncio.sleep(0.4)  # longer than acquire_timeout: must still be queued
    assert not waiter.done()
    await pool.release(held)
    assert (await asyncio.wait_for(waiter, 1)).id == "a0"


async def test_persistence_roundtrip(tmp_path):
    await _pool(tmp_path, n=2)
    reloaded = AccountPool(JsonAccountStore(tmp_path / "acc.json"))
    await reloaded.load()
    assert {a.id for a in reloaded.all()} == {"a0", "a1"}


class _FlakyDriver(MockDriver):
    requires_account = True

    def __init__(self, bad: set[str]):
        super().__init__(delay=0)
        self.bad = bad

    async def chat_stream(self, account, req):
        if account.id in self.bad:
            raise UpstreamError("boom")
        async for d in super().chat_stream(account, req):
            yield d


async def test_gateway_fails_over(tmp_path):
    pool = await _pool(tmp_path, n=2, strategy="round_robin")
    gw = Gateway(pool, _FlakyDriver({"a0"}), max_failover=2)
    text = "".join([d async for d in gw.chat_stream(ChatRequest(prompt="hi", model="m"))])
    assert "hi" in text
    assert pool.get("a0").status == AccountStatus.COOLING
    assert pool.get("a1").success_count == 1


class _SlowVideoDriver(MockDriver):
    requires_account = True

    def __init__(self):
        super().__init__(delay=0)
        self.calls = 0

    async def generate_video(self, account, req):
        self.calls += 1
        raise GenerationTimeout("video generation timed out")


async def test_generation_timeout_keeps_account_and_raises_with_no_other_account(tmp_path):
    pool = await _pool(tmp_path, n=1)
    driver = _SlowVideoDriver()
    gw = Gateway(pool, driver, max_failover=2)
    with pytest.raises(GenerationTimeout):
        await gw.generate_video(VideoRequest(prompt="p", model="m"))
    assert driver.calls == 1
    assert pool.get("a0").status == AccountStatus.ACTIVE
    assert (await pool.acquire()).id == "a0"


class _OneBadVideoDriver(MockDriver):
    requires_account = True

    def __init__(self, exc: Exception):
        super().__init__(delay=0)
        self.exc, self.accounts = exc, []

    async def generate_video(self, account, req):
        self.accounts.append(account.id)
        if len(self.accounts) == 1:
            raise self.exc
        return await super().generate_video(account, req)


@pytest.mark.parametrize(
    "exc", [GenerationTimeout("timed out"), UpstreamRefused("text only: Done, attached below")]
)
async def test_stuck_or_refused_video_moves_to_another_account_without_cooldown(tmp_path, exc):
    pool = await _pool(tmp_path, n=2, strategy="round_robin")
    driver = _OneBadVideoDriver(exc)
    gw = Gateway(pool, driver, max_failover=2)
    result = await gw.generate_video(VideoRequest(prompt="p", model="m"))
    assert result.data
    assert len(set(driver.accounts)) == 2
    assert all(a.status == AccountStatus.ACTIVE for a in pool.all())


class _StuckOnDriver(MockDriver):
    """Times out on the given accounts, renders on the rest; records each attempt's timeout."""

    requires_account = True

    def __init__(self, stuck: set[str]):
        super().__init__(delay=0)
        self.stuck, self.calls = stuck, []

    async def generate_video(self, account, req):
        self.calls.append((account.id, req.timeout))
        if account.id in self.stuck:
            raise GenerationTimeout("video generation timed out")
        return await super().generate_video(account, req)


async def test_new_video_job_skips_account_whose_render_timed_out(tmp_path):
    pool = await _pool(tmp_path, n=2, strategy="round_robin")
    driver = _StuckOnDriver({"a0"})
    gw = Gateway(pool, driver, max_failover=2, stuck_video_cooldown=1800)
    for _ in range(3):
        assert (await gw.generate_video(VideoRequest(prompt="p", model="m"))).data
    # a0 timed out once; every later job went straight to a1.
    assert [acc for acc, _ in driver.calls] == ["a0", "a1", "a1", "a1"]


async def test_stuck_account_still_takes_jobs_when_it_is_the_only_one(tmp_path):
    pool = await _pool(tmp_path, n=1)
    driver = _StuckOnDriver({"a0"})
    gw = Gateway(pool, driver, max_failover=2, stuck_video_cooldown=1800)
    for _ in range(2):
        with pytest.raises(GenerationTimeout):
            await gw.generate_video(VideoRequest(prompt="p", model="m"))
    assert [acc for acc, _ in driver.calls] == ["a0", "a0"]


async def test_video_job_render_time_is_capped_across_failovers(tmp_path, monkeypatch):
    pool = await _pool(tmp_path, n=3, strategy="round_robin")
    clock = [0.0]
    monkeypatch.setattr("museai.services.gateway.time.monotonic", lambda: clock[0])

    class Slow(_StuckOnDriver):
        async def generate_video(self, account, req):
            clock[0] += req.timeout  # renders until its deadline
            return await super().generate_video(account, req)

    driver = Slow({"a0", "a1", "a2"})
    gw = Gateway(pool, driver, max_failover=2, video_deadline=1800)
    with pytest.raises(GenerationTimeout):
        await gw.generate_video(VideoRequest(prompt="p", model="m", timeout=1500))
    # 1500 s on the first account leaves 300 s for the second; then too little for a third.
    assert [t for _, t in driver.calls] == [1500, 300]
    assert clock[0] <= 1800


def test_video_timeout_scales_with_clip_length():
    s = Settings(video_timeout=1500, video_timeout_base=360, video_timeout_per_second=60)
    assert video_timeout(s, 6) == 720
    assert video_timeout(s, 10) == 960
    assert video_timeout(s, 30) == 1500
    assert video_timeout(s, None) == 1500


class _HeldVideoDriver(MockDriver):
    """Each video runs until its test releases it; records the account it ran on."""

    def __init__(self) -> None:
        super().__init__(delay=0)
        self.running: dict[str, str] = {}  # prompt -> account id
        self.release: dict[str, asyncio.Event] = {}

    async def generate_video(self, account, req):
        self.running[req.prompt] = account.id
        self.release[req.prompt] = done = asyncio.Event()
        await done.wait()
        return await super().generate_video(account, req)


async def test_videos_run_in_parallel_one_per_account_and_queue_for_the_next_free(tmp_path):
    pool = await _pool(tmp_path, n=4)
    driver = _HeldVideoDriver()
    # Waits far longer than the pool's own 0.2 s acquire timeout.
    gw = Gateway(pool, driver, media_queue_timeout=5)

    def submit(name):
        return asyncio.create_task(gw.generate_video(VideoRequest(prompt=name, model="muse-video")))

    async def settle():
        for _ in range(20):
            await asyncio.sleep(0.01)

    jobs = {f"v{i}": submit(f"v{i}") for i in range(1, 5)}
    await settle()
    assert sorted(driver.running.values()) == ["a0", "a1", "a2", "a3"]

    jobs["v5"] = submit("v5")
    await asyncio.sleep(0.4)
    assert "v5" not in driver.running

    driver.release["v4"].set()
    await jobs["v4"]
    await settle()
    assert driver.running["v5"] == driver.running["v4"]

    jobs["v6"] = submit("v6")
    driver.release["v2"].set()
    await jobs["v2"]
    await settle()
    assert driver.running["v6"] == driver.running["v2"]

    for name in ("v1", "v3", "v5", "v6"):
        driver.release[name].set()
    await asyncio.gather(*jobs.values())


async def test_quota_error_records_hit(tmp_path):
    pool = await _pool(tmp_path, n=1)
    with pytest.raises(UpstreamQuotaError):
        async with pool.lease():
            raise UpstreamQuotaError("Out of usage")
    assert len(pool.get("a0").quota_hits) == 1


def test_usage_estimate_learns_cap_from_quota_hits():
    acc = Account(id="a0", quota_hits=[100.0, 200.0])

    def video(created, done, status=TaskStatus.SUCCEEDED, account="a0"):
        t = Task(kind="video", request={}, status=status, account_id=account, created_at=created)
        t.updated_at = done
        return t

    videos = [
        video(10, 20),
        video(20, 50),
        video(50, 90),  # window 1: 3 before first hit
        video(110, 150),
        video(150, 190),  # window 2: 2
        video(210, 250),
        video(250, 260, status=TaskStatus.FAILED),  # since last hit: 1 used
        video(210, 250, account="other"),
    ]
    assert usage_estimate(acc, videos) == {"cap": 3, "used": 1, "left": 2, "windows": 2}
    assert usage_estimate(Account(id="a0"), videos)["left"] is None


async def test_identical_in_flight_submission_joins_existing_task(tmp_path):
    from museai.services.tasks import TaskManager

    tasks = TaskManager(tmp_path / "tasks.json")
    release = asyncio.Event()
    renders = 0

    async def runner(task, progress):
        nonlocal renders
        renders += 1
        await release.wait()
        return {"url": "x"}

    first = tasks.submit("video", {"prompt": "p"}, runner, dedupe_key="k")
    again = tasks.submit("video", {"prompt": "p"}, runner, dedupe_key="k")
    other = tasks.submit("video", {"prompt": "q"}, runner, dedupe_key="k2")
    assert again.id == first.id and other.id != first.id
    release.set()
    await asyncio.sleep(0.05)
    assert renders == 2 and first.status == TaskStatus.SUCCEEDED
    # Finished tasks no longer absorb new submissions: a retake renders again.
    retake = tasks.submit("video", {"prompt": "p"}, runner, dedupe_key="k")
    assert retake.id != first.id


async def test_one_client_uses_every_free_account(tmp_path):
    pool = await _pool(tmp_path, n=2)
    first = await pool.acquire(owner="A")
    second = await pool.acquire(owner="A")
    assert {first.id, second.id} == {"a0", "a1"}


async def test_free_account_goes_to_the_client_holding_fewest(tmp_path):
    pool = await _pool(tmp_path, n=2)
    a1 = await pool.acquire(owner="A")
    await pool.acquire(owner="B")
    a2 = asyncio.create_task(pool.acquire(owner="A", timeout=math.inf))
    await asyncio.sleep(0.01)
    b2 = asyncio.create_task(pool.acquire(owner="B", timeout=math.inf))
    await asyncio.sleep(0.01)
    # Both wait. A frees its account: A and B hold one each, so A's earlier request wins.
    await pool.release(a1, owner="A")
    await asyncio.sleep(0.01)
    assert a2.done() and not b2.done()
    b2.cancel()


async def test_waiting_client_goes_before_a_busy_one(tmp_path):
    pool = await _pool(tmp_path, n=2)
    a1 = await pool.acquire(owner="A")
    a2 = await pool.acquire(owner="A")
    a3 = asyncio.create_task(pool.acquire(owner="A", timeout=math.inf))
    await asyncio.sleep(0.01)
    b1 = asyncio.create_task(pool.acquire(owner="B", timeout=math.inf))
    await asyncio.sleep(0.01)
    # A holds two, B none: the next free account goes to B although A asked first.
    await pool.release(a1, owner="A")
    await asyncio.sleep(0.01)
    assert b1.done() and not a3.done()
    await pool.release(a2, owner="A")
    await asyncio.sleep(0.01)
    assert a3.done()


async def test_shutdown_marks_running_jobs_interrupted(tmp_path):
    from museai.services.tasks import TaskManager

    tasks = TaskManager(tmp_path / "tasks.json")

    async def runner(task, progress):
        await asyncio.Event().wait()

    running = tasks.submit("video", {"prompt": "p"}, runner)
    await asyncio.sleep(0.01)
    await tasks.shutdown()
    # Clients retry "interrupted"; a "cancelled" job would be dropped on a restart.
    assert running.status == TaskStatus.FAILED and running.error["code"] == "interrupted"


async def test_gateway_lists_image_jobs_per_account(tmp_path):
    """An account busy with an image shows it: the dashboard used to call it Ready."""
    from museai.drivers.base import ImageRequest
    from museai.drivers.mock import MockDriver
    from museai.services.gateway import Gateway

    pool = await _pool(tmp_path, n=1)
    gw = Gateway(pool, MockDriver(delay=0))
    seen = []

    async def generate_image(account, req):
        seen.append(gw.jobs[account.id][:])
        return []

    gw.driver.generate_image = generate_image
    await gw.generate_image(ImageRequest(prompt="a red bike", model="muse-image"))
    assert [[(j["kind"], j["prompt"]) for j in jobs] for jobs in seen] == [[("image", "a red bike")]]
    assert all(not jobs for jobs in gw.jobs.values())
