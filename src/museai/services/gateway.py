"""Gateway: runs driver calls on pooled accounts with automatic failover."""

from __future__ import annotations

import logging
import math
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import replace
from typing import TypeVar

from ..accounts.model import Account, AccountStatus
from ..accounts.pool import AccountPool, Lease
from ..drivers.base import ChatRequest, ImageRequest, MediaResult, MuseDriver, VideoRequest
from ..errors import GenerationTimeout, UpstreamError

log = logging.getLogger(__name__)
T = TypeVar("T")

# A failover with less render time left than this is not started.
MIN_VIDEO_ATTEMPT = 120.0

_ANONYMOUS = Account(id="anonymous", label="driver without accounts")


class Gateway:
    def __init__(
        self,
        pool: AccountPool,
        driver: MuseDriver,
        *,
        max_failover: int = 2,
        media_queue_timeout: float | None = None,
        video_deadline: float = math.inf,
        stuck_video_cooldown: float = 0.0,
    ) -> None:
        self.pool = pool
        self.driver = driver
        self.max_failover = max_failover
        # Image/video jobs run in the background, so they wait for the next free account
        # (one job per account) instead of failing after the chat acquire timeout.
        self.media_queue_timeout = media_queue_timeout
        # One video job never renders longer than this in all, failovers included.
        self.video_deadline = video_deadline
        # An account whose render timed out gets no new video job for this long while another
        # account can take it: one stuck account once timed out five clips in a row, 12 min each.
        self.stuck_video_cooldown = stuck_video_cooldown
        self._stuck_until: dict[str, float] = {}
        # What each account is doing right now (chat, image, video), for the dashboard cards:
        # tasks only record videos, so an account busy with an image used to look idle.
        self.jobs: dict[str, list[dict]] = {}

    @asynccontextmanager
    async def _lease(
        self, exclude: list[str], hint: str | None, timeout: float | None = None,
        owner: str | None = None, kind: str = "chat", prompt: str = "",
    ) -> AsyncIterator[Lease]:
        if not self.driver.requires_account and not self.pool.all():
            yield Lease(_ANONYMOUS)
            return
        async with self.pool.lease(exclude=exclude, hint=hint, timeout=timeout,
                                   owner=owner) as lease:
            job = {"kind": kind, "prompt": prompt[:200], "since": time.time()}
            jobs = self.jobs.setdefault(lease.account.id, [])
            jobs.append(job)
            try:
                yield lease
            finally:
                jobs.remove(job)

    def _should_retry(self, exc: UpstreamError, attempt: int, tried: list[str]) -> bool:
        """Fail over only to an account not tried yet; with none left the caller gets
        the upstream error instead of "no usable account"."""
        if not exc.retryable or attempt >= self.max_failover:
            return False
        accounts = self.pool.all()
        return not accounts or any(
            a.enabled and a.status != AccountStatus.INVALID and a.id not in tried
            for a in accounts
        )

    def _stuck_accounts(self, tried: list[str]) -> list[str]:
        """Accounts whose last render timed out, skipped only while another usable one is left."""
        now = time.monotonic()
        usable = [a.id for a in self.pool.all()
                  if a.enabled and a.status != AccountStatus.INVALID and a.id not in tried]
        stuck = [i for i in usable if self._stuck_until.get(i, 0) > now]
        return stuck if len(stuck) < len(usable) else []

    async def chat_stream(self, req: ChatRequest) -> AsyncIterator[str]:
        tried: list[str] = []
        for attempt in range(self.max_failover + 1):
            async with self._lease(tried, req.conversation_hint) as lease:
                emitted = False
                try:
                    async for delta in self.driver.chat_stream(lease.account, req):
                        emitted = True
                        yield delta
                    return
                except UpstreamError as exc:
                    lease.fail(exc)
                    tried.append(lease.account.id)
                    # Once text reached the client we cannot transparently switch accounts.
                    if emitted or not self._should_retry(exc, attempt, tried):
                        raise
                    log.warning("chat failed on %s (%s), failing over", lease.account.id, exc)

    async def chat_complete(self, req: ChatRequest) -> str:
        return await self._run(
            lambda acc: self.driver.chat_complete(acc, req), req.conversation_hint
        )

    async def _run(
        self,
        fn: Callable[[Account], Awaitable[T]],
        hint: str | None = None,
        queue_timeout: float | None = None,
        on_account: Callable[[Account], None] | None = None,
        owner: str | None = None,
        kind: str = "chat",
        prompt: str = "",
        time_left: Callable[[], float] = lambda: math.inf,
    ) -> T:
        tried: list[str] = []
        for attempt in range(self.max_failover + 1):
            avoid = self._stuck_accounts(tried) if kind == "video" else []
            async with self._lease(tried + avoid, hint, queue_timeout, owner, kind,
                                   prompt) as lease:
                if on_account:
                    on_account(lease.account)
                try:
                    return await fn(lease.account)
                except UpstreamError as exc:
                    lease.fail(exc)
                    tried.append(lease.account.id)
                    if kind == "video" and isinstance(exc, GenerationTimeout):
                        self._stuck_until[lease.account.id] = (
                            time.monotonic() + self.stuck_video_cooldown)
                    if not self._should_retry(exc, attempt, tried):
                        raise
                    if time_left() < MIN_VIDEO_ATTEMPT:
                        log.warning("%s failed on %s (%s), no time left to fail over",
                                    kind, lease.account.id, exc)
                        raise
                    log.warning("call failed on %s (%s), failing over", lease.account.id, exc)
        raise AssertionError("unreachable")

    async def generate_image(self, req: ImageRequest) -> list[MediaResult]:
        return await self._run(
            lambda acc: self.driver.generate_image(acc, req), queue_timeout=self.media_queue_timeout,
            kind="image", prompt=req.prompt,
        )

    async def generate_video(
        self, req: VideoRequest, on_account: Callable[[Account], None] | None = None,
        owner: str | None = None,
    ) -> MediaResult:
        # The budget counts render time on accounts only; waiting in the queue is not a stuck tab.
        spent = 0.0

        def time_left() -> float:
            return self.video_deadline - spent

        async def render(acc: Account) -> MediaResult:
            nonlocal spent
            start = time.monotonic()
            try:
                return await self.driver.generate_video(
                    acc, replace(req, timeout=min(req.timeout, time_left())))
            finally:
                spent += time.monotonic() - start

        return await self._run(
            render,
            queue_timeout=self.media_queue_timeout,
            time_left=time_left,
            on_account=on_account,
            owner=owner,
            kind="video",
            prompt=req.prompt,
        )
