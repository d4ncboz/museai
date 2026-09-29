"""Minimal asyncio Chrome DevTools Protocol client."""

from __future__ import annotations

import asyncio
import contextlib
import itertools
import json
import logging
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from websockets.asyncio.client import ClientConnection, connect

log = logging.getLogger(__name__)


class CDPError(RuntimeError):
    pass


class CDPSession:
    def __init__(self, ws: ClientConnection) -> None:
        self._ws = ws
        self._ids = itertools.count(1)
        self._pending: dict[int, asyncio.Future] = {}
        self._listeners: dict[str, list[Callable[[dict], None]]] = defaultdict(list)
        self._reader = asyncio.create_task(self._read_loop())

    @classmethod
    async def connect(cls, ws_url: str) -> CDPSession:
        ws = await connect(ws_url, max_size=None, ping_interval=None, open_timeout=15)
        return cls(ws)

    @property
    def closed(self) -> bool:
        return self._reader.done()

    async def _read_loop(self) -> None:
        try:
            async for raw in self._ws:
                msg = json.loads(raw)
                if "id" in msg:
                    fut = self._pending.pop(msg["id"], None)
                    if fut and not fut.done():
                        if "error" in msg:
                            fut.set_exception(CDPError(msg["error"].get("message", "cdp error")))
                        else:
                            fut.set_result(msg.get("result", {}))
                elif method := msg.get("method"):
                    for cb in self._listeners.get(method, ()):
                        try:
                            cb(msg.get("params", {}))
                        except Exception:  # noqa: BLE001
                            log.exception("cdp listener for %s failed", method)
        except Exception as exc:  # noqa: BLE001
            log.debug("cdp reader stopped: %s", exc)
        finally:
            for fut in self._pending.values():
                if not fut.done():
                    fut.set_exception(CDPError("cdp connection closed"))
            self._pending.clear()

    def on(self, method: str, callback: Callable[[dict], None]) -> None:
        self._listeners[method].append(callback)

    async def send(self, method: str, params: dict | None = None, timeout: float = 30.0) -> dict:
        if self.closed:
            raise CDPError("cdp connection closed")
        msg_id = next(self._ids)
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        self._pending[msg_id] = fut
        await self._ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
        try:
            return await asyncio.wait_for(fut, timeout)
        finally:
            self._pending.pop(msg_id, None)

    async def evaluate(self, expression: str, *, await_promise: bool = False,
                       timeout: float = 30.0) -> Any:
        res = await self.send(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": await_promise},
            timeout=timeout,
        )
        if exc := res.get("exceptionDetails"):
            text = exc.get("exception", {}).get("description") or exc.get("text", "js error")
            raise CDPError(text)
        return res.get("result", {}).get("value")

    async def close(self) -> None:
        with contextlib.suppress(Exception):
            await self._ws.close()
        self._reader.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await self._reader
