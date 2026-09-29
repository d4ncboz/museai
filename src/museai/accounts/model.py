from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AccountStatus(str, Enum):
    ACTIVE = "active"
    COOLING = "cooling"
    """Temporarily unavailable (quota exhausted or transient errors); returns after cooldown."""
    INVALID = "invalid"
    """Session rejected by upstream; needs fresh cookies."""


def _now() -> float:
    return time.time()


class Account(BaseModel):
    id: str = Field(default_factory=lambda: "acc_" + uuid.uuid4().hex[:10])
    label: str = ""
    enabled: bool = True
    status: AccountStatus = AccountStatus.ACTIVE

    cookies: dict[str, str] = Field(default_factory=dict)
    cookie_expires: dict[str, int] = Field(
        default_factory=dict, description="cookie name -> unix expiry seconds"
    )

    created_at: float = Field(default_factory=_now)
    last_used_at: float = 0.0
    cooldown_until: float = 0.0
    last_error: str | None = None
    success_count: int = 0
    fail_count: int = 0

    meta: dict[str, Any] = Field(
        default_factory=dict, description="Driver-specific data such as quota snapshots or vm ids"
    )

    def is_available(self, now: float | None = None) -> bool:
        if not self.enabled or self.status == AccountStatus.INVALID:
            return False
        if self.status == AccountStatus.COOLING:
            return (now or _now()) >= self.cooldown_until
        return True

    def public(self) -> dict[str, Any]:
        """Serialisable view with cookie values masked."""
        data = self.model_dump(mode="json")
        data["cookies"] = {k: _mask(v) for k, v in self.cookies.items()}
        return data


def _mask(value: str) -> str:
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"
