"""Background session keepalive.

muse.ai sessions expire unless refreshed; this loop periodically asks the active
driver to renew each account and merges refreshed cookies back into the pool.
Drivers that do not support renewal simply raise ``FeatureNotImplemented`` and
the loop skips them.
"""

from __future__ import annotations

import asyncio
import logging
import time

from ..drivers.base import MuseDriver
from ..errors import FeatureNotImplemented, UpstreamAuthError
from .model import AccountStatus
from .pool import AccountPool

log = logging.getLogger(__name__)


async def renew_account(pool: AccountPool, driver: MuseDriver, account_id: str) -> dict:
    acc = pool.get(account_id)
    if acc is None:
        return {"ok": False, "error": "not found"}
    try:
        info = await driver.renew_session(acc)
    except FeatureNotImplemented as exc:
        return {"ok": False, "error": exc.message}
    except UpstreamAuthError as exc:
        acc.status = AccountStatus.INVALID
        acc.last_error = exc.message
        await pool.upsert(acc)
        return {"ok": False, "error": exc.message}

    acc.cookies.update(info.cookies)
    acc.cookie_expires.update(info.cookie_expires)
    acc.meta.update(info.meta)
    acc.meta["renewed_at"] = time.time()
    await pool.upsert(acc)
    return {"ok": info.ok, "meta": info.meta}


async def keepalive_loop(pool: AccountPool, driver: MuseDriver, interval: float) -> None:
    log.info("keepalive loop started (interval=%ss)", interval)
    while True:
        await asyncio.sleep(interval)
        for acc in pool.all():
            if not acc.enabled or acc.status == AccountStatus.INVALID:
                continue
            try:
                result = await renew_account(pool, driver, acc.id)
                log.info("keepalive %s -> %s", acc.id, result.get("ok"))
            except Exception:  # noqa: BLE001
                log.exception("keepalive failed for %s", acc.id)
