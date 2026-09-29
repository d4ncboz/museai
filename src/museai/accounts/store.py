"""Account persistence. ``AccountStore`` is the interface; ``JsonAccountStore`` is the default.

A SQLite/Redis store can be added by implementing the same protocol.
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Protocol

from .model import Account


class AccountStore(Protocol):
    async def load(self) -> list[Account]: ...
    async def save(self, accounts: list[Account]) -> None: ...


class JsonAccountStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = asyncio.Lock()

    async def load(self) -> list[Account]:
        if not self.path.is_file():
            return []
        raw = await asyncio.to_thread(self.path.read_text, encoding="utf-8")
        if not raw.strip():
            return []
        return [Account.model_validate(item) for item in json.loads(raw)]

    async def save(self, accounts: list[Account]) -> None:
        payload = json.dumps(
            [a.model_dump(mode="json") for a in accounts], ensure_ascii=False, indent=2
        )
        async with self._lock:
            await asyncio.to_thread(self._atomic_write, payload)

    def _atomic_write(self, payload: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".accounts.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
            os.chmod(tmp, 0o600)
            os.replace(tmp, self.path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
