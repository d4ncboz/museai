"""Auto-post: rules that pick, for every video landing in the posting queue, the channel, platforms,
time and caption, and a publisher loop that posts it through each platform's API when its time comes.

Rules (``data/autopost.json``, edited on the dashboard) are tried in order; the first enabled rule
whose match fits a new queued video plans it: ``entry["auto"]`` in ``posts.json`` names the rule
and the platforms, and each platform gets a job. Times come from the posting slot the queue already
books (posting.py, per platform offsets), or from the rule's fixed times, or from a per-platform
override set on the dashboard.

Each job is keyed by video and platform. It moves ``waiting → posting → posted`` (or ``retry`` /
``error``); ``posting`` is saved before the driver runs and the driver saves a checkpoint before
every step that must not repeat (publishers/base.py), so a restart resumes the post instead of
posting it twice. A posted job ticks the platform through the queue's own ``posted`` flow, which
moves the video to the Trash once every platform is ticked.
"""

from __future__ import annotations

import asyncio
import fnmatch
import json
import logging
import re
import time
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, ValidationError, field_validator

from ...errors import InvalidRequest, NotFound
from ...services.container import Services
from ...services.oauth import PROVIDERS, OAuthError
from ...services.publishers import AUTO_PLATFORMS, Job, PublishError
from ..deps import get_services
from . import posting
from .dashboard import _local_or_admin

log = logging.getLogger(__name__)

router = APIRouter(tags=["dashboard"], dependencies=[Depends(_local_or_admin)])
# The provider redirects the browser here; the one-time ``state`` stands in for the admin key.
callback_router = APIRouter(tags=["dashboard"])

# Where a video came from, by its file name (muse-video SKILL.md "Format skills": <prefix>-<slug>).
SOURCES = {
    "scenic-drop-reel": ("Scenic drop reel", r"^reel[-_ ]|\bscenic-drop-reel\b"),
    "zoominview": ("Zoom-in view", r"^zoom[-_ ]|\bzoominview\b"),
    "scenery-director": ("Scenery director", r"^scenic[-_ ]"),
    "travel": ("Travel documentary", r"^travel[-_ ]"),
    "product-ad": ("Product ad", r"^ad[-_ ]"),
    "teaching-video": ("Teaching video", r"^lesson[-_ ]"),
    "everyday-chinese": ("EVERYDAY CHINESE", r"^tiếng trung mỗi ngày|everyday chinese"),
}
CAPTION_FIELDS = "{caption} = the platform's caption, {title} = its first line, {name} = file name, {channel}"
# Seconds to wait before retry n (1-based); after the last one the job stops at "error".
BACKOFF = (60, 300, 900, 3600, 3 * 3600)
SETTLE = 30.0  # a file younger than this may still be copying in
# A job whose time passed this long ago without starting (paused, no account) waits for the user
# instead of going up at once, so un-pausing never posts a backlog in one burst.
MISSED = timedelta(hours=2)


class Rule(BaseModel):
    id: str = Field(min_length=1, max_length=40)
    name: str = ""
    enabled: bool = True
    # Match: every field set must fit (empty = any).
    source: str = ""  # a SOURCES id
    pattern: str = ""  # glob on the file name, case-insensitive ("*Thuê*", "reel-*norway*")
    on_channel: str = ""  # the channel the queue put it on (picked on the card or guessed from the name)
    # What to post.
    channel: str = ""  # move it to this channel ("" = keep)
    platforms: list[str] = Field(default_factory=lambda: list(AUTO_PLATFORMS))
    schedule: Literal["slot", "fixed"] = "slot"
    times: list[str] = Field(default_factory=list)  # "HH:MM" GMT+7, for schedule "fixed"
    captions: dict[str, str] = Field(default_factory=dict)  # template per platform, default "{caption}"
    thumbnail: Literal["9x16", "16x9", "none"] = "9x16"
    privacy: Literal["public", "private"] = "public"

    @field_validator("source")
    @classmethod
    def _source(cls, v: str) -> str:
        if v and v not in SOURCES:
            raise ValueError(f"unknown source '{v}' ({', '.join(SOURCES)})")
        return v

    @field_validator("on_channel", "channel")
    @classmethod
    def _channel(cls, v: str) -> str:
        if v and v not in posting.CHANNELS:
            raise ValueError(f"unknown channel '{v}' ({', '.join(posting.CHANNELS)})")
        return v

    @field_validator("platforms")
    @classmethod
    def _platforms(cls, v: list[str]) -> list[str]:
        if bad := set(v) - set(AUTO_PLATFORMS):
            raise ValueError(f"auto-post supports {', '.join(AUTO_PLATFORMS)}, not {', '.join(sorted(bad))}")
        return [p for p in AUTO_PLATFORMS if p in v]

    @field_validator("times")
    @classmethod
    def _times(cls, v: list[str]) -> list[str]:
        for t in v:
            if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", t):
                raise ValueError(f"time '{t}' is not HH:MM")
        return sorted(set(v))

    @field_validator("captions")
    @classmethod
    def _captions(cls, v: dict[str, str]) -> dict[str, str]:
        if bad := set(v) - set(AUTO_PLATFORMS):
            raise ValueError(f"caption templates for unknown platforms: {', '.join(sorted(bad))}")
        return {p: t for p, t in v.items() if t.strip()}

    def matches(self, name: str, channel: str) -> bool:
        if not self.enabled or not self.platforms:
            return False
        if self.source and not re.search(SOURCES[self.source][1], unicodedata.normalize("NFC", name), re.I):
            return False
        if self.pattern and not fnmatch.fnmatch(name.lower(), self.pattern.lower()):
            return False
        return not self.on_channel or self.on_channel == channel


# --- rules file ---

def _rules_file(svc: Services) -> Path:
    return svc.settings.data_dir / "autopost.json"


def load_config(svc: Services) -> dict:
    try:
        raw = json.loads(_rules_file(svc).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        raw = {}
    rules = []
    for r in raw.get("rules", []):
        try:
            rules.append(Rule(**r))
        except ValidationError as exc:  # a rule broken by hand stays out, the rest still run
            log.warning("auto-post rule %s skipped: %s", r.get("id"), exc)
    return {"paused": bool(raw.get("paused")), "rules": rules}


def save_config(svc: Services, paused: bool, rules: list[Rule]) -> None:
    path = _rules_file(svc)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"paused": paused, "rules": [r.model_dump() for r in rules]},
                              indent=2, ensure_ascii=False))
    tmp.replace(path)


# --- planning (called from posting.refresh under its lock) ---

def plan(state: dict, videos: list[Path], rules: list[Rule]) -> bool:
    """Give each queued video not planned yet the first rule that matches it. Returns True when the
    state changed. Runs before slots are handed out, so a rule's channel books a slot there."""
    changed = False
    for path in videos:
        key = posting._key(path.name)
        entry = state.setdefault(key, {})
        if "auto" in entry or entry.get("done"):
            continue
        rule = next((r for r in rules if r.matches(path.name, posting._channel(key, entry))), None)
        if rule is None:
            continue
        if rule.channel and rule.channel != posting._channel(key, entry):
            entry["channel"] = rule.channel
            entry.pop("slot", None)
            entry.pop("slot_pinned", None)
        entry["auto"] = {"rule": rule.id, "platforms": [p for p in rule.platforms if p not in entry.get("posted", {})],
                         "jobs": {}}
        changed = True
    return changed


def book_fixed(state: dict, rules: list[Rule], now: datetime) -> bool:
    """Book the next free fixed time in its channel for each video planned by a "fixed" rule."""
    by_id = {r.id: r for r in rules}
    taken = {(posting._channel(n, e), e["auto"]["at"]) for n, e in state.items()
             if isinstance(e.get("auto"), dict) and e["auto"].get("at")}
    changed = False
    for name, entry in state.items():
        auto = entry.get("auto")
        rule = by_id.get(auto.get("rule")) if isinstance(auto, dict) else None
        if not rule or rule.schedule != "fixed" or not rule.times or auto.get("at") or entry.get("done"):
            continue
        ch = posting._channel(name, entry)
        d = now.astimezone(posting.TZ).date()
        for _ in range(366):
            free = [at for t in rule.times if (at := _at(d, t)) > now and (ch, at.isoformat()) not in taken]
            if free:
                auto["at"] = free[0].isoformat()
                taken.add((ch, auto["at"]))
                changed = True
                break
            d += timedelta(days=1)
    return changed


def _at(d: date, hhmm: str) -> datetime:
    hh, mm = map(int, hhmm.split(":"))
    return datetime(d.year, d.month, d.day, hh, mm, tzinfo=posting.TZ)


def time_for(name: str, entry: dict, platform: str) -> datetime | None:
    """When ``platform`` posts: the dashboard override, else the rule's fixed time, else the slot's."""
    auto = entry.get("auto") or {}
    if at := (auto.get("times") or {}).get(platform) or auto.get("at"):
        return datetime.fromisoformat(at)
    if entry.get("slot"):
        return posting._slot_times(entry["slot"], posting._channel(name, entry)).get(platform)
    return None


def caption_for(name: str, entry: dict, platform: str, rule: Rule | None) -> str:
    own = (entry.get("captions") or {}).get(platform) or entry.get("caption") or ""
    template = (rule.captions.get(platform) if rule else None) or "{caption}"
    fields = defaultdict(str, caption=own, title=own.strip().split("\n")[0], name=Path(name).stem,
                         channel=posting.CHANNELS[posting._channel(name, entry)][0])
    try:
        return template.format_map(fields).strip()
    except (ValueError, IndexError):  # a stray "{" in a template: post it as written
        return template.replace("{caption}", own).strip()


# --- publisher ---

def _job(svc: Services, key: str, platform: str, **changes) -> dict:
    """Update one job in posts.json (under the queue's lock); returns the job."""
    with posting._state_lock:
        state = posting._load(svc)
        auto = state.get(key, {}).get("auto")
        if not isinstance(auto, dict):
            return {}
        job = auto.setdefault("jobs", {}).setdefault(platform, {})
        job.update(changes)
        posting._save(svc, state)
        return job


def _mark_posted(svc: Services, path: Path, platform: str) -> None:
    """Tick the platform the same way the dashboard checkbox does (Trash once all are ticked)."""
    with posting._state_lock:
        if path.is_file():
            posting._update(svc, path, {"platform": platform})


async def tick(svc: Services, now: datetime | None = None) -> list[tuple[str, str, str]]:
    """Plan new videos and post every job whose time has come. Returns (video, platform, state)."""
    now = now or datetime.now(posting.TZ)
    config = load_config(svc)
    videos, state = await asyncio.to_thread(posting.refresh, svc, now)
    if config["paused"]:
        return []
    rules = {r.id: r for r in config["rules"]}
    done = []
    for path in sorted(videos, key=lambda p: p.stat().st_mtime):
        key = posting._key(path.name)
        entry = state.get(key, {})
        auto = entry.get("auto")
        if not isinstance(auto, dict) or auto.get("paused") or auto.get("off"):
            continue
        if time.time() - path.stat().st_mtime < SETTLE:
            continue
        for platform in auto.get("platforms", []):
            job = (auto.get("jobs") or {}).get(platform, {})
            if job.get("state") == "posted":
                if platform not in entry.get("posted", {}):  # crashed between the two saves
                    await asyncio.to_thread(_mark_posted, svc, path, platform)
                continue
            if platform in entry.get("posted", {}) or job.get("state") == "error":
                continue
            at = time_for(path.name, entry, platform)
            if at is None or at > now or job.get("next_try", 0) > now.timestamp() or job.get("state") == "missed":
                continue
            if at < now - MISSED and job.get("state") in (None, "waiting", "needs_account"):
                _job(svc, key, platform, state="missed",
                     error="its time passed while it could not post; press Post now or pick a new time")
                continue
            result = await post(svc, path, entry, platform, rules.get(auto.get("rule")), job, now)
            done.append((path.name, platform, result))
            if not path.is_file():  # trashed after the last platform
                break
            entry = posting._load(svc).get(key, entry)
    return done


async def post(svc: Services, path: Path, entry: dict, platform: str, rule: Rule | None, job: dict,
               now: datetime) -> str:
    """Run one job; returns its new state."""
    key = posting._key(path.name)
    channel = posting._channel(key, entry)
    token = await svc.oauth.token(channel, platform) if not svc.settings.autopost_mock else {"access_token": "mock"}
    if not token:
        _job(svc, key, platform, state="needs_account",
             error=f"connect a {posting.PLATFORMS[platform][0]} account to the {posting.CHANNELS[channel][0]} channel")
        return "needs_account"
    caption = caption_for(path.name, entry, platform, rule)
    if not caption:
        _job(svc, key, platform, state="waiting", error="waiting for the caption")
        return "waiting"
    thumb = None
    if rule is None or rule.thumbnail != "none":
        thumb = posting._thumbs(path).get(rule.thumbnail if rule else "9x16")
    attempts = job.get("attempts", 0) + 1
    _job(svc, key, platform, state="posting", attempts=attempts, started=time.time(), error="")

    async def save(checkpoint: dict) -> None:
        await asyncio.to_thread(_job, svc, key, platform, checkpoint=checkpoint)

    try:
        result = await svc.publishers[platform].publish(
            Job(video=path, platform=platform, caption=caption, token=token, thumbnail=thumb,
                privacy=rule.privacy if rule else "public"),
            job.get("checkpoint") or {}, save)
    except PublishError as exc:
        return _failed(svc, key, platform, attempts, str(exc), exc.retry, now)
    except Exception as exc:  # noqa: BLE001 - a network or driver bug is retried like a platform error
        log.exception("auto-post %s to %s failed", path.name, platform)
        return _failed(svc, key, platform, attempts, f"{type(exc).__name__}: {exc}", True, now)
    _job(svc, key, platform, state="posted", url=result.url, id=result.id, posted_at=time.time(),
         error="", checkpoint={})
    await asyncio.to_thread(_mark_posted, svc, path, platform)
    log.info("auto-posted %s to %s: %s", path.name, platform, result.url)
    return "posted"


def _failed(svc: Services, key: str, platform: str, attempts: int, error: str, retry: bool,
            now: datetime) -> str:
    if retry and attempts <= len(BACKOFF):
        _job(svc, key, platform, state="retry", error=error, next_try=now.timestamp() + BACKOFF[attempts - 1])
        return "retry"
    _job(svc, key, platform, state="error", error=error)
    return "error"


async def loop(svc: Services) -> None:
    while True:
        try:
            await tick(svc)
        except Exception:  # noqa: BLE001 - one bad pass must not stop auto-posting
            log.exception("auto-post pass failed")
        await asyncio.sleep(svc.settings.autopost_interval)


# --- dashboard ---

def _plan_view(name: str, entry: dict, rules: dict[str, Rule]) -> dict:
    auto = entry["auto"]
    rule = rules.get(auto.get("rule"))
    jobs = []
    for p in auto.get("platforms", []):
        job = (auto.get("jobs") or {}).get(p, {})
        at = time_for(name, entry, p)
        state = job.get("state") or ("posted" if p in entry.get("posted", {}) else "scheduled")
        jobs.append({"platform": p, "time": at.isoformat() if at else None, "state": state,
                     "url": job.get("url", ""), "error": job.get("error", ""), "attempts": job.get("attempts", 0),
                     "next_try": job.get("next_try"), "override": bool((auto.get("times") or {}).get(p)),
                     "caption": caption_for(name, entry, p, rule)})
    return {"name": name, "channel": posting._channel(name, entry), "rule": auto.get("rule"),
            "rule_name": rule.name if rule else "", "paused": bool(auto.get("paused")), "jobs": jobs}


@router.get("/dashboard/autopost", include_in_schema=False)
async def overview(request: Request, svc: Services = Depends(get_services)) -> dict:
    config = load_config(svc)
    videos, state = await asyncio.to_thread(posting.refresh, svc, datetime.now(posting.TZ))
    rules = {r.id: r for r in config["rules"]}
    names = {posting._key(p.name): p.name for p in videos}
    plan_rows = [_plan_view(names[k], e, rules) for k, e in state.items()
                 if k in names and isinstance(e.get("auto"), dict) and not e["auto"].get("off")]
    plan_rows.sort(key=lambda r: min((j["time"] or "~") for j in r["jobs"]) if r["jobs"] else "~")
    return {
        "enabled": svc.settings.autopost_enabled, "mock": svc.settings.autopost_mock,
        "paused": config["paused"], "rules": [r.model_dump() for r in config["rules"]],
        "sources": [{"id": k, "name": n} for k, (n, _) in SOURCES.items()],
        "platforms": [{"id": p, "name": posting.PLATFORMS[p][0]} for p in AUTO_PLATFORMS],
        "channels": [{"id": k, "name": n} for k, (n, _) in posting.CHANNELS.items()],
        "caption_fields": CAPTION_FIELDS,
        "connections": svc.oauth.view(), "redirect_uri": _redirect(request, svc),
        "plan": plan_rows,
        "unplanned": [names[k] for k, e in state.items() if k in names and not isinstance(e.get("auto"), dict)],
    }


@router.put("/dashboard/autopost/rules", include_in_schema=False)
def put_rules(body: dict, svc: Services = Depends(get_services)) -> dict:
    try:
        rules = [Rule(**r) for r in body.get("rules", [])]
    except (ValidationError, TypeError) as exc:
        raise InvalidRequest(f"bad rule: {exc}") from None
    if len({r.id for r in rules}) != len(rules):
        raise InvalidRequest("rule ids must be unique")
    save_config(svc, load_config(svc)["paused"], rules)
    return {"rules": [r.model_dump() for r in rules]}


@router.post("/dashboard/autopost/pause", include_in_schema=False)
def pause_all(body: dict, svc: Services = Depends(get_services)) -> dict:
    config = load_config(svc)
    save_config(svc, bool(body.get("paused", True)), config["rules"])
    return {"paused": bool(body.get("paused", True))}


@router.post("/dashboard/autopost/plan/{name}", include_in_schema=False)
def update_plan(name: str, body: dict, svc: Services = Depends(get_services)) -> dict:
    """Override one video's plan: ``paused``; ``off`` (post it by hand; ``off: false`` lets the rules
    plan it again); ``platforms``; ``times`` {platform: ISO time, "" = back to the slot}; ``retry``
    (post that platform now, also after an error or a missed time); ``rule`` (plan it with that rule
    again)."""
    path = posting._video(svc, name)
    key = posting._key(path.name)
    rules = {r.id: r for r in load_config(svc)["rules"]}
    with posting._state_lock:
        state = posting._load(svc)
        entry = state.setdefault(key, {})
        if "off" in body:
            if body["off"]:
                entry["auto"] = {"off": True}
            else:
                entry.pop("auto", None)
        if "rule" in body:
            rule = rules.get(body["rule"])
            if not rule:
                raise InvalidRequest(f"unknown rule '{body['rule']}'")
            entry.pop("auto", None)
            plan(state, [path], [rule.model_copy(update={"enabled": True, "source": "", "pattern": "",
                                                         "on_channel": ""})])
        auto = entry.get("auto")
        if isinstance(auto, dict) and not auto.get("off"):
            if "paused" in body:
                auto["paused"] = bool(body["paused"])
            if "platforms" in body:
                if not isinstance(body["platforms"], list) or set(body["platforms"]) - set(AUTO_PLATFORMS):
                    raise InvalidRequest(f"platforms must be a list of {', '.join(AUTO_PLATFORMS)}")
                auto["platforms"] = [p for p in AUTO_PLATFORMS if p in body["platforms"]]
            for platform, at in (body.get("times") or {}).items():
                if platform not in AUTO_PLATFORMS:
                    raise InvalidRequest(f"unknown platform '{platform}'")
                if at:
                    try:
                        parsed = datetime.fromisoformat(at)
                    except ValueError:
                        raise InvalidRequest(f"time '{at}' is not ISO 8601") from None
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=posting.TZ)
                    auto.setdefault("times", {})[platform] = parsed.isoformat()
                else:
                    auto.get("times", {}).pop(platform, None)
            if (platform := body.get("retry")) in AUTO_PLATFORMS:  # "Post now"
                job = auto.setdefault("jobs", {}).setdefault(platform, {})
                if job.get("state") != "posted":
                    job.update(state="retry", attempts=0, next_try=0, error="")
                    auto.setdefault("times", {})[platform] = datetime.now(posting.TZ).isoformat()
                    if platform not in auto.get("platforms", []):
                        auto.setdefault("platforms", []).append(platform)
        elif any(k in body for k in ("paused", "platforms", "times", "retry")):
            raise InvalidRequest(f"'{name}' has no auto-post plan")
        posting._save(svc, state)
    return {"ok": True}


def _redirect(request: Request, svc: Services) -> str:
    base = svc.settings.public_base.rstrip("/") or str(request.base_url).rstrip("/")
    return f"{base}/dashboard/autopost/oauth/callback"


@router.get("/dashboard/autopost/oauth/{provider}/start", include_in_schema=False)
def oauth_start(provider: str, channel: str, request: Request, svc: Services = Depends(get_services)):
    if channel not in posting.CHANNELS:
        raise InvalidRequest(f"unknown channel '{channel}'")
    if provider not in PROVIDERS:
        raise NotFound(f"unknown provider '{provider}'")
    try:
        return RedirectResponse(svc.oauth.start(provider, channel, _redirect(request, svc)))
    except OAuthError as exc:
        raise InvalidRequest(str(exc)) from None


@callback_router.get("/dashboard/autopost/oauth/callback", include_in_schema=False)
async def oauth_callback(state: str = "", code: str = "", error: str = "",
                         svc: Services = Depends(get_services)) -> RedirectResponse:
    if error or not code:
        msg = error or "no code"
    else:
        try:
            provider, channel = await svc.oauth.finish(state, code)
            msg = f"connected {PROVIDERS[provider].name} to {posting.CHANNELS[channel][0]}"
        except OAuthError as exc:
            msg = str(exc)
        except Exception as exc:  # noqa: BLE001 - show it on the dashboard instead of a 500 page
            log.warning("oauth callback failed: %s", type(exc).__name__)
            msg = f"sign-in failed ({type(exc).__name__})"
    return RedirectResponse(f"/dashboard#autopost&msg={quote(msg)}", status_code=303)


@router.post("/dashboard/autopost/accounts/{channel}/{platform}", include_in_schema=False)
def account_update(channel: str, platform: str, body: dict, svc: Services = Depends(get_services)) -> dict:
    """``{"choice": id}`` picks another Page / Instagram account; ``{"disconnect": true}`` forgets it."""
    if channel not in posting.CHANNELS or platform not in AUTO_PLATFORMS:
        raise InvalidRequest("unknown channel or platform")
    try:
        if body.get("disconnect"):
            svc.oauth.disconnect(channel, platform)
        elif choice := body.get("choice"):
            svc.oauth.choose(channel, platform, str(choice))
    except OAuthError as exc:
        raise InvalidRequest(str(exc)) from None
    return svc.oauth.view()
