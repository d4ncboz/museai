"""Admin dashboard: which account rendered which video.

Requests from the machine running museai need no key; anyone else needs the admin
key, passed to the page as ``/dashboard#key=<admin key>``.
"""

from __future__ import annotations

import asyncio
import ipaddress
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse

from ...accounts.keepalive import renew_account
from ...accounts.model import Account, AccountStatus
from ...core.system import cpu_load
from ...errors import InvalidRequest, NotFound
from ...services.container import Services
from ...services.tasks import Task, TaskStatus
from ...upstream import muse
from ..deps import get_services, public_base, require_admin_key
from .videos import submit_video

router = APIRouter(tags=["dashboard"])

_PAGE = Path(__file__).resolve().parent.parent / "static" / "dashboard.html"


def usage_estimate(acc: Account, videos: list[Task]) -> dict[str, Any]:
    """Estimate videos left before muse.ai says "Out of usage" again.

    muse.ai exposes no balance, so the cap is learned: the most videos the account
    finished between two "Out of usage" hits (the first window starts when tracking
    started). ``used`` counts videos finished since the last hit.
    """
    mine = [t for t in videos if t.account_id == acc.id]
    done = sorted(t.updated_at for t in mine if t.status == TaskStatus.SUCCEEDED)
    start = min((t.created_at for t in mine), default=None)
    caps = []
    for hit in sorted(acc.quota_hits):
        if start is not None and start < hit:
            caps.append(sum(start < t <= hit for t in done))
        start = hit
    since = start if acc.quota_hits else None
    used = sum(since is None or t > since for t in done)
    cap = max(caps) if caps else None
    return {
        "cap": cap,
        "used": used,
        "left": None if cap is None else max(cap - used, 0),
        "windows": len(caps),
    }


def _local_or_admin(request: Request) -> None:
    host = request.client.host if request.client else ""
    try:
        if ipaddress.ip_address(host).is_loopback:
            return
    except ValueError:
        pass
    require_admin_key(request)


@router.post("/dashboard/accounts", include_in_schema=False,
             dependencies=[Depends(_local_or_admin)])
async def add_account(request: Request, label: str = "muse",
                      svc: Services = Depends(get_services)) -> dict:
    """Add an account from a browser cookie export, then check the cookies upstream."""
    try:
        cookies, expires = muse.parse_cookie_export(await request.json())
    except ValueError as exc:
        raise InvalidRequest(f"not a cookie export: {exc}") from exc
    if missing := muse.missing_session_cookies(cookies):
        raise InvalidRequest(f"export is missing session cookies: {', '.join(missing)}")
    acc = Account(label=label.strip()[:100] or "muse", cookies=cookies, cookie_expires=expires)
    await svc.pool.upsert(acc)
    check = await renew_account(svc.pool, svc.driver, acc.id)
    return {"account": svc.pool.get(acc.id).public(), "check": check}


@router.post("/dashboard/accounts/{account_id}/cookies", include_in_schema=False,
             dependencies=[Depends(_local_or_admin)])
async def upload_cookies(account_id: str, request: Request,
                         svc: Services = Depends(get_services)) -> dict:
    """Replace an account's cookies with a browser export, then check them upstream."""
    acc = svc.pool.get(account_id)
    if acc is None:
        raise NotFound(f"account '{account_id}' not found")
    try:
        cookies, expires = muse.parse_cookie_export(await request.json())
    except ValueError as exc:
        raise InvalidRequest(f"not a cookie export: {exc}") from exc
    if missing := muse.missing_session_cookies(cookies):
        raise InvalidRequest(f"export is missing session cookies: {', '.join(missing)}")
    acc.cookies, acc.cookie_expires = cookies, expires
    acc.status, acc.cooldown_until, acc.last_error = AccountStatus.ACTIVE, 0.0, None
    acc.video_blocked_until = 0.0
    await svc.pool.upsert(acc)
    # Also drops the account's open tab, so the next job uses the new cookies.
    check = await renew_account(svc.pool, svc.driver, account_id)
    return {"account": svc.pool.get(account_id).public(), "check": check}


@router.post("/dashboard/accounts/{account_id}/label", include_in_schema=False,
             dependencies=[Depends(_local_or_admin)])
async def rename_account(account_id: str, body: dict, svc: Services = Depends(get_services)) -> dict:
    """Rename an account, e.g. to the muse.ai login email (muse.ai never tells us)."""
    acc = svc.pool.get(account_id)
    if acc is None:
        raise NotFound(f"account '{account_id}' not found")
    label = str(body.get("label") or "").strip()
    if not label:
        raise InvalidRequest("label must not be empty")
    acc.label = label[:100]
    await svc.pool.upsert(acc)
    return {"account": acc.public()}


def _video(svc: Services, task_id: str) -> Task:
    task = svc.tasks.get(task_id)
    if task is None or task.kind != "video":
        raise NotFound(f"video task '{task_id}' not found")
    return task


@router.post("/dashboard/videos/{task_id}/cancel", include_in_schema=False,
             dependencies=[Depends(_local_or_admin)])
async def cancel_video(task_id: str, svc: Services = Depends(get_services)) -> dict:
    """Stop a waiting or rendering video; its account is free for the next job."""
    _video(svc, task_id)
    return {"cancelled": await svc.tasks.cancel(task_id)}


@router.post("/dashboard/videos/{task_id}/retry", include_in_schema=False,
             dependencies=[Depends(_local_or_admin)])
async def retry_video(task_id: str, request: Request, svc: Services = Depends(get_services)) -> dict:
    """Render a failed or cancelled video again with the same request.

    The same request still in flight is joined instead, so a double click never renders twice.
    """
    old = _video(svc, task_id)
    if not old.finished or old.status == TaskStatus.SUCCEEDED:
        raise InvalidRequest("only a failed or cancelled video can be retried")
    if old.request.get("has_first_frame"):
        raise InvalidRequest("this video started from an image that is not stored; resend it from the client")
    task = submit_video(svc, public_base(request), old.request, None, old.session)
    return {"id": task.id}


# Phone app (PWA): the page, its service worker, manifest and icons, plus web push.
_STATIC = {"sw.js": "text/javascript", "manifest.webmanifest": "application/manifest+json",
           "icon-180.png": "image/png", "icon-192.png": "image/png", "icon-512.png": "image/png"}


@router.get("/dashboard/static/{name}", include_in_schema=False)
async def dashboard_static(name: str) -> FileResponse:
    if name not in _STATIC:
        raise NotFound(f"'{name}' not found")
    # The worker lives under /dashboard/static/ but controls the page at /dashboard.
    headers = {"Service-Worker-Allowed": "/dashboard", "Cache-Control": "no-cache"}
    return FileResponse(_PAGE.parent / name, media_type=_STATIC[name], headers=headers)


@router.get("/dashboard/push", include_in_schema=False, dependencies=[Depends(_local_or_admin)])
async def push_info(svc: Services = Depends(get_services)) -> dict:
    return {"key": svc.push.public_key, "devices": len(svc.push.subscriptions)}


@router.post("/dashboard/push/subscribe", include_in_schema=False,
             dependencies=[Depends(_local_or_admin)])
async def push_subscribe(body: dict, svc: Services = Depends(get_services)) -> dict:
    """Store a browser PushSubscription (``{endpoint, keys: {p256dh, auth}}``)."""
    keys = body.get("keys") or {}
    if not str(body.get("endpoint", "")).startswith("https://") or not keys.get("p256dh") \
            or not keys.get("auth"):
        raise InvalidRequest("not a push subscription")
    return {"devices": svc.push.subscribe(body)}


@router.post("/dashboard/push/unsubscribe", include_in_schema=False,
             dependencies=[Depends(_local_or_admin)])
async def push_unsubscribe(body: dict, svc: Services = Depends(get_services)) -> dict:
    svc.push.unsubscribe(str(body.get("endpoint", "")))
    return {"devices": len(svc.push.subscriptions)}


@router.post("/dashboard/push/test", include_in_schema=False,
             dependencies=[Depends(_local_or_admin)])
async def push_test(svc: Services = Depends(get_services)) -> dict:
    sent = await svc.push.notify("museai notifications are on",
                                 "You'll get one like this when a video is ready to post.")
    return {"sent": sent}


@router.get("/dashboard", include_in_schema=False)
async def dashboard() -> FileResponse:
    return FileResponse(_PAGE, media_type="text/html", headers={"Cache-Control": "no-cache"})


@router.get("/dashboard/data", include_in_schema=False, dependencies=[Depends(_local_or_admin)])
async def dashboard_data(limit: int = 1000, svc: Services = Depends(get_services)) -> dict:
    videos = [t for t in svc.tasks.list(limit) if t.kind == "video"]
    accounts = svc.pool.all()
    return {
        "accounts": [{**a.public(), "jobs": svc.gateway.jobs.get(a.id, [])} for a in accounts],
        "usage": {a.id: usage_estimate(a, videos) for a in accounts},
        "videos": [t.model_dump(mode="json") for t in videos],
        "system": await asyncio.to_thread(cpu_load),
    }
