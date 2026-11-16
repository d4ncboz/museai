"""Account pool: scheduling, per-account concurrency limits, health state and failover.

Usage::

    async with pool.lease(exclude={...}, hint=conversation_key) as lease:
        ... use lease.account ...
        lease.fail(exc)   # optional; success is recorded automatically otherwise
"""

from __future__ import annotations

import asyncio
import itertools
import logging
import math
import time
from collections import defaultdict
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from typing import Protocol

from ..errors import NoAccountAvailable, UpstreamAuthError, UpstreamQuotaError, VideoLimitReached
from .model import Account, AccountStatus
from .store import AccountStore

QUOTA_HISTORY = 20

log = logging.getLogger(__name__)


# ---------------------------------------------------------------- strategies
class Strategy(Protocol):
    def choose(self, candidates: list[Account], hint: str | None) -> Account: ...


class RoundRobinStrategy:
    def __init__(self) -> None:
        self._counter = itertools.count()

    def choose(self, candidates: list[Account], hint: str | None) -> Account:
        ordered = sorted(candidates, key=lambda a: a.id)
        return ordered[next(self._counter) % len(ordered)]


class LRUStrategy:
    def choose(self, candidates: list[Account], hint: str | None) -> Account:
        return min(candidates, key=lambda a: a.last_used_at)


class AffinityStrategy:
    """Sticks a hint (e.g. conversation id / user id) to the account that served it last,
    so a driver can reuse warm browser tabs or upstream threads. Falls back to LRU."""

    def __init__(self, max_entries: int = 4096) -> None:
        self._map: dict[str, str] = {}
        self._max = max_entries
        self._fallback = LRUStrategy()

    def choose(self, candidates: list[Account], hint: str | None) -> Account:
        if hint and (acc_id := self._map.get(hint)):
            for acc in candidates:
                if acc.id == acc_id:
                    return acc
        acc = self._fallback.choose(candidates, hint)
        if hint:
            if len(self._map) >= self._max:
                self._map.pop(next(iter(self._map)))
            self._map[hint] = acc.id
        return acc


STRATEGIES: dict[str, type] = {
    "round_robin": RoundRobinStrategy,
    "lru": LRUStrategy,
    "affinity": AffinityStrategy,
}


# ---------------------------------------------------------------- lease
class Lease:
    def __init__(self, account: Account, owner: str | None = None) -> None:
        self.account = account
        self.owner = owner
        self.error: BaseException | None = None

    def fail(self, exc: BaseException) -> None:
        self.error = exc


# ---------------------------------------------------------------- pool
class AccountPool:
    def __init__(
        self,
        store: AccountStore,
        *,
        strategy: str = "lru",
        max_concurrency: int = 1,
        cooldown: float = 120.0,
        quota_cooldown: float = 3600.0,
        video_limit_cooldown: float = 3600.0,
        acquire_timeout: float = 60.0,
    ) -> None:
        self.store = store
        self.strategy: Strategy = STRATEGIES[strategy]()
        self.max_concurrency = max(1, max_concurrency)
        self.cooldown = cooldown
        self.quota_cooldown = quota_cooldown
        self.video_limit_cooldown = video_limit_cooldown
        self.acquire_timeout = acquire_timeout
        self._accounts: dict[str, Account] = {}
        self._inflight: dict[str, int] = defaultdict(int)
        # Fair share: leases held per owner (client session) and who waits for one.
        self._owner_load: dict[str, int] = defaultdict(int)
        self._waiters: dict[int, tuple[str | None, tuple[str, ...], bool]] = {}
        self._seq = itertools.count()
        self._cond = asyncio.Condition()

    # ---- lifecycle / CRUD ----
    async def load(self) -> None:
        self._accounts = {a.id: a for a in await self.store.load()}
        log.info("loaded %d account(s)", len(self._accounts))

    async def persist(self) -> None:
        await self.store.save(list(self._accounts.values()))

    def all(self) -> list[Account]:
        return list(self._accounts.values())

    def get(self, account_id: str) -> Account | None:
        return self._accounts.get(account_id)

    async def upsert(self, account: Account) -> Account:
        async with self._cond:
            self._accounts[account.id] = account
            self._cond.notify_all()
        await self.persist()
        return account

    async def remove(self, account_id: str) -> bool:
        async with self._cond:
            removed = self._accounts.pop(account_id, None) is not None
        if removed:
            await self.persist()
        return removed

    def stats(self) -> dict[str, int]:
        now = time.time()
        return {
            "total": len(self._accounts),
            "available": sum(1 for a in self._accounts.values() if a.is_available(now)),
            "invalid": sum(1 for a in self._accounts.values() if a.status == AccountStatus.INVALID),
            "inflight": sum(self._inflight.values()),
        }

    # ---- scheduling ----
    def _candidates(
        self, exclude: Iterable[str], video: bool = False
    ) -> tuple[list[Account], bool, float | None]:
        """Returns (free candidates, whether any usable account is merely busy, and the
        earliest time a cooling account comes back, if any). For a video job an account at
        its video limit counts as cooling until ``video_blocked_until``."""
        now = time.time()
        excluded = set(exclude)
        free, busy, next_ready = [], False, None
        for acc in self._accounts.values():
            if acc.id in excluded:
                continue
            if not acc.is_available(now):
                if acc.enabled and acc.status == AccountStatus.COOLING:
                    next_ready = min(next_ready or acc.cooldown_until, acc.cooldown_until)
                continue
            if video and acc.video_blocked(now):
                next_ready = min(next_ready or acc.video_blocked_until, acc.video_blocked_until)
                continue
            if self._inflight[acc.id] >= self.max_concurrency:
                busy = True
                continue
            free.append(acc)
        return free, busy, next_ready

    def _turn_key(self, seq: int) -> tuple[int, int]:
        owner = self._waiters[seq][0]
        return (self._owner_load[owner] if owner else 0, seq)

    def _my_turn(self, seq: int) -> bool:
        """A free account goes to the waiter whose owner holds the fewest leases, oldest
        first, among waiters that can use one. An owner alone takes every free account."""
        mine = self._turn_key(seq)
        return not any(
            self._turn_key(other) < mine and self._candidates(exclude, video)[0]
            for other, (_, exclude, video) in self._waiters.items()
            if other != seq
        )

    async def acquire(
        self,
        *,
        exclude: Iterable[str] = (),
        hint: str | None = None,
        timeout: float | None = None,
        owner: str | None = None,
        avoid: Iterable[str] = (),
        video: bool = False,
    ) -> Account:
        """Wait for a free account. ``timeout`` defaults to ``acquire_timeout``; ``math.inf``
        waits as long as it takes. Busy and cooling accounts are waited for; only a pool
        with nothing that can ever become free fails at once. An ``avoid`` account is taken
        only when no other account is free right now: it never makes the caller wait."""
        exclude = tuple(exclude)
        avoid = frozenset(avoid)
        deadline = time.monotonic() + (self.acquire_timeout if timeout is None else timeout)
        seq = next(self._seq)
        async with self._cond:
            self._waiters[seq] = (owner, exclude, video)
            try:
                return await self._wait_turn(seq, exclude, hint, deadline, owner, avoid, video)
            finally:
                del self._waiters[seq]
                # Waiters this one stood in front of may take a free account now.
                self._cond.notify_all()

    async def _wait_turn(
        self, seq: int, exclude: tuple[str, ...], hint: str | None, deadline: float,
        owner: str | None, avoid: frozenset[str] = frozenset(), video: bool = False,
    ) -> Account:
        while True:
            free, busy, next_ready = self._candidates(exclude, video)
            if free and self._my_turn(seq):
                acc = self.strategy.choose([a for a in free if a.id not in avoid] or free, hint)
                self._inflight[acc.id] += 1
                if owner:
                    self._owner_load[owner] += 1
                acc.last_used_at = time.time()
                return acc
            if free:
                # Another client's job goes first; it wakes us once it has its account.
                busy = True
            if not busy and next_ready is None:
                raise NoAccountAvailable("no usable account in pool")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise NoAccountAvailable(
                    "all accounts are busy, try again later"
                    if busy
                    else "all accounts are cooling down, try again later"
                )
            wait = remaining
            if next_ready is not None:
                wait = min(wait, max(0.05, next_ready - time.time()))
            try:
                await asyncio.wait_for(
                    self._cond.wait(), timeout=None if math.isinf(wait) else wait
                )
            except asyncio.TimeoutError:
                continue

    async def release(
        self, account: Account, error: BaseException | None = None, owner: str | None = None
    ) -> None:
        async with self._cond:
            self._inflight[account.id] = max(0, self._inflight[account.id] - 1)
            if owner:
                self._owner_load[owner] = max(0, self._owner_load[owner] - 1)
            self._apply_result(account, error)
            self._cond.notify_all()
        await self.persist()

    def _apply_result(self, acc: Account, error: BaseException | None) -> None:
        if error is None:
            acc.success_count += 1
            acc.last_error = None
            if acc.status == AccountStatus.COOLING:
                acc.status = AccountStatus.ACTIVE
            return
        acc.fail_count += 1
        acc.last_error = str(error)[:500]
        if isinstance(error, UpstreamAuthError):
            acc.status = AccountStatus.INVALID
            log.warning("account %s marked invalid: %s", acc.id, error)
        elif isinstance(error, VideoLimitReached):
            # Only videos are blocked: the account keeps taking chat and image jobs.
            acc.video_blocked_until = time.time() + self.video_limit_cooldown
            acc.quota_hits = [*acc.quota_hits, time.time()][-QUOTA_HISTORY:]
            log.warning("account %s at its video limit, no video jobs for %.0f s",
                        acc.id, self.video_limit_cooldown)
        elif isinstance(error, UpstreamQuotaError):
            acc.status = AccountStatus.COOLING
            acc.cooldown_until = time.time() + self.quota_cooldown
            acc.quota_hits = [*acc.quota_hits, time.time()][-QUOTA_HISTORY:]
            log.warning("account %s out of quota, cooling down", acc.id)
        elif getattr(error, "retryable", False) and getattr(error, "cools_account", True):
            acc.status = AccountStatus.COOLING
            acc.cooldown_until = time.time() + self.cooldown

    @asynccontextmanager
    async def lease(
        self,
        *,
        exclude: Iterable[str] = (),
        hint: str | None = None,
        timeout: float | None = None,
        owner: str | None = None,
        avoid: Iterable[str] = (),
        video: bool = False,
    ) -> AsyncIterator[Lease]:
        acc = await self.acquire(exclude=exclude, hint=hint, timeout=timeout, owner=owner,
                                 avoid=avoid, video=video)
        lease = Lease(acc, owner)
        try:
            yield lease
        except (asyncio.CancelledError, GeneratorExit):
            # Client went away; not the account's fault.
            raise
        except BaseException as exc:
            lease.error = lease.error or exc
            raise
        finally:
            await self.release(acc, lease.error, owner)
