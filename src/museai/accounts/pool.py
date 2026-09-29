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
import time
from collections import defaultdict
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from typing import Protocol

from ..errors import NoAccountAvailable, UpstreamAuthError, UpstreamQuotaError
from .model import Account, AccountStatus
from .store import AccountStore

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
    def __init__(self, account: Account) -> None:
        self.account = account
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
        acquire_timeout: float = 60.0,
    ) -> None:
        self.store = store
        self.strategy: Strategy = STRATEGIES[strategy]()
        self.max_concurrency = max(1, max_concurrency)
        self.cooldown = cooldown
        self.acquire_timeout = acquire_timeout
        self._accounts: dict[str, Account] = {}
        self._inflight: dict[str, int] = defaultdict(int)
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
    def _candidates(self, exclude: Iterable[str]) -> tuple[list[Account], bool]:
        """Returns (free candidates, whether any usable account is merely busy)."""
        now = time.time()
        excluded = set(exclude)
        free, busy = [], False
        for acc in self._accounts.values():
            if acc.id in excluded or not acc.is_available(now):
                continue
            if self._inflight[acc.id] >= self.max_concurrency:
                busy = True
                continue
            free.append(acc)
        return free, busy

    async def acquire(self, *, exclude: Iterable[str] = (), hint: str | None = None) -> Account:
        exclude = tuple(exclude)
        deadline = time.monotonic() + self.acquire_timeout
        async with self._cond:
            while True:
                free, busy = self._candidates(exclude)
                if free:
                    acc = self.strategy.choose(free, hint)
                    self._inflight[acc.id] += 1
                    acc.last_used_at = time.time()
                    return acc
                if not busy:
                    raise NoAccountAvailable("no usable account in pool")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise NoAccountAvailable("all accounts are busy, try again later")
                try:
                    await asyncio.wait_for(self._cond.wait(), timeout=remaining)
                except asyncio.TimeoutError:
                    continue

    async def release(self, account: Account, error: BaseException | None = None) -> None:
        async with self._cond:
            self._inflight[account.id] = max(0, self._inflight[account.id] - 1)
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
        elif isinstance(error, UpstreamQuotaError):
            acc.status = AccountStatus.COOLING
            acc.cooldown_until = time.time() + max(self.cooldown, 3600)
            log.warning("account %s out of quota, cooling down", acc.id)
        elif getattr(error, "retryable", False):
            acc.status = AccountStatus.COOLING
            acc.cooldown_until = time.time() + self.cooldown

    @asynccontextmanager
    async def lease(
        self, *, exclude: Iterable[str] = (), hint: str | None = None
    ) -> AsyncIterator[Lease]:
        acc = await self.acquire(exclude=exclude, hint=hint)
        lease = Lease(acc)
        try:
            yield lease
        except (asyncio.CancelledError, GeneratorExit):
            # Client went away; not the account's fault.
            raise
        except BaseException as exc:
            lease.error = lease.error or exc
            raise
        finally:
            await self.release(acc, lease.error)
