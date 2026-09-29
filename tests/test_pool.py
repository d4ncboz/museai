from __future__ import annotations

import asyncio

import pytest

from museai.accounts import Account, AccountPool, AccountStatus, JsonAccountStore
from museai.drivers.base import ChatRequest
from museai.drivers.mock import MockDriver
from museai.errors import NoAccountAvailable, UpstreamAuthError, UpstreamError
from museai.services.gateway import Gateway


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
