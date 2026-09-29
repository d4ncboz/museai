from __future__ import annotations

import hmac

from fastapi import Request

from ..errors import Unauthorized
from ..services.container import Services


def get_services(request: Request) -> Services:
    return request.app.state.services


def _bearer(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.headers.get("x-api-key", "").strip()


def _check(provided: str, expected: str) -> None:
    if not expected or not hmac.compare_digest(provided.encode(), expected.encode()):
        raise Unauthorized("invalid or missing API key")


def require_api_key(request: Request) -> None:
    s = get_services(request).settings
    provided = _bearer(request)
    # The admin key is a superset of the API key.
    if s.admin_key and provided and hmac.compare_digest(provided.encode(), s.admin_key.encode()):
        return
    _check(provided, s.api_key)


def require_admin_key(request: Request) -> None:
    _check(_bearer(request), get_services(request).settings.effective_admin_key)


def public_base(request: Request) -> str:
    base = get_services(request).settings.public_base
    return base.rstrip("/") if base else str(request.base_url).rstrip("/")
