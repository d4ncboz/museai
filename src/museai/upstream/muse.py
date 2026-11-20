"""Facts about the muse.ai web app shared by all drivers.

Everything here was observed from the public web client and may change without
notice. Keep upstream-specific constants in this module so that a site update
is a one-file fix.
"""

from __future__ import annotations

import uuid

import httpx

from ..drivers.base import SessionInfo
from ..errors import UpstreamAuthError, UpstreamError

SITE = "https://muse.ai"
NEW_THREAD_URL = f"{SITE}/thread/new"
SESSION_API = f"{SITE}/api/session"
VM_WAKE_API = f"{SITE}/api/hatch/vm/wake"

# Cookies required to establish a logged-in session.
# hatch_vml is dynamically assigned upon thread creation; datr is recommended for Meta proxy stability.
# hatch_gw is no longer issued by muse.ai (verified against a live 2026-10 session).
SESSION_COOKIES = ("hatch_sess", "hatch_native_auth_device")
RECOMMENDED_COOKIES = ("hatch_vml", "datr")

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/140.0.0.0 Safari/537.36"
)


def cookie_header(cookies: dict[str, str]) -> str:
    return "; ".join(f"{k}={v}" for k, v in cookies.items() if v)


def missing_session_cookies(cookies: dict[str, str]) -> list[str]:
    return [name for name in SESSION_COOKIES if not cookies.get(name)]


def parse_cookie_export(data: object) -> tuple[dict[str, str], dict[str, int]]:
    """Read a browser cookie export into (cookies, expiry epoch per cookie).

    Accepts a Cookie-Editor / DevTools array of ``{name, value, domain, expirationDate}``,
    the same wrapped as ``{"cookies": [...]}``, or a flat ``{name: value}`` object.
    Cookies of other sites in the export are dropped.
    """
    if isinstance(data, dict) and "cookies" in data:
        data = data["cookies"]
    if isinstance(data, dict):
        return {str(k): str(v) for k, v in data.items() if v}, {}
    if not isinstance(data, list):
        raise ValueError("expected a JSON array of cookies or a {name: value} object")
    cookies: dict[str, str] = {}
    expires: dict[str, int] = {}
    for item in data:
        if not isinstance(item, dict) or not item.get("name") or not item.get("value"):
            continue
        if not str(item.get("domain") or "muse.ai").lstrip(".").endswith("muse.ai"):
            continue
        cookies[item["name"]] = str(item["value"])
        exp = item.get("expirationDate") or item.get("expires")
        if isinstance(exp, (int, float)) and exp > 0:
            expires[item["name"]] = int(exp)
    return cookies, expires


def cookie_export(cookies: dict[str, str], expires: dict[str, int]) -> list[dict[str, object]]:
    """Write an account's cookies as a Cookie-Editor JSON export, the inverse of
    ``parse_cookie_export``, to import into a browser or back into the dashboard.

    The store keeps only name, value and expiry; the other fields are muse.ai's usual ones.
    """
    out: list[dict[str, object]] = []
    for name, value in cookies.items():
        host_only = name.startswith("__Host-")
        item: dict[str, object] = {
            "domain": "muse.ai" if host_only else ".muse.ai",
            "hostOnly": host_only,
            "httpOnly": name.startswith("hatch_"),
            "name": name,
            "path": "/",
            "sameSite": "lax",
            "secure": True,
            "session": name not in expires,
            "storeId": "0",
            "value": value,
        }
        if name in expires:
            item["expirationDate"] = expires[name]
        out.append(item)
    return out


async def renew_session(
    cookies: dict[str, str], *, wake_vm: bool = True, timeout: float = 15.0
) -> SessionInfo:
    """Hit the session endpoint, which rotates short-lived cookies via Set-Cookie,
    and optionally wake the account's cloud workspace so the first request is fast."""
    headers = {
        "User-Agent": USER_AGENT,
        "Origin": SITE,
        "Referer": NEW_THREAD_URL,
        "Accept": "application/json",
    }
    jar = dict(cookies)
    expires: dict[str, int] = {}
    async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
        resp = await client.get(SESSION_API, headers={"Cookie": cookie_header(jar)})
        if resp.status_code in (401, 403):
            raise UpstreamAuthError(f"session rejected by upstream (HTTP {resp.status_code})")
        if resp.status_code >= 400:
            raise UpstreamError(f"session endpoint returned HTTP {resp.status_code}")

        for c in resp.cookies.jar:
            if c.value:
                jar[c.name] = c.value
            if c.expires:
                expires[c.name] = int(c.expires)

        body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        meta = {"session_status": body.get("status"), "vm_id": body.get("vm_id"),
                "vm_state": body.get("vm_state")}

        if wake_vm and meta["vm_id"] and meta["vm_state"] != "DISABLED":
            try:
                w = await client.post(
                    VM_WAKE_API,
                    headers={"Cookie": cookie_header(jar)},
                    json={"vm_id": meta["vm_id"], "retry_count": 0,
                          "connect_attempt_id": str(uuid.uuid4())},
                )
                meta["vm_wake_ok"] = w.status_code == 200
            except httpx.HTTPError:
                meta["vm_wake_ok"] = False

    return SessionInfo(ok=meta["session_status"] == "assigned", cookies=jar,
                       cookie_expires=expires, meta=meta)
