"""Growth campaign of a channel's accounts: progress toward each platform's monetization eligibility.

The user types each platform's numbers from its own analytics (YouTube Studio, Meta Business Suite) into
the dashboard now and then; each save is a dated snapshot in ``data/campaign-<channel>.json``. From the
first and last snapshot the dashboard shows the growth per day, when each goal will be reached at that
pace, and what is needed per day to reach it by the campaign's target day.

Thresholds were checked on 2026-11-02 (YouTube's YPP pages; Meta's Stars page; Instagram's from a
secondary source). Facebook's Content Monetization is invite-only with no public threshold, and Vietnam
was not on its country list, so the Facebook goal is Stars.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends

from ...errors import InvalidRequest
from ...services.container import Services
from ..deps import get_services
from .dashboard import _local_or_admin
from .posting import CHANNELS, TZ

router = APIRouter(tags=["dashboard"], dependencies=[Depends(_local_or_admin)])

# Numbers typed in per platform: (key, label, where to read it).
METRICS = {
    "youtube": [
        ("subs", "Subscribers", "Studio > Analytics > Audience"),
        ("shorts_views_90d", "Shorts views, last 90 days", "Studio > Analytics > Content > Shorts, 90 days"),
        ("uploads_90d", "Public uploads, last 90 days", "Studio > Content"),
    ],
    "facebook": [("followers", "Followers", "Professional dashboard > Insights")],
    "instagram": [("followers", "Followers", "Profile > Professional dashboard")],
}
# Goals in order; each needs every metric it names to reach its number.
GOALS = [
    {"id": "yt-fan", "platform": "youtube", "name": "YouTube Partner Program: fan funding",
     "unlocks": "Memberships, Supers, Shopping",
     "need": {"subs": 500, "uploads_90d": 3, "shorts_views_90d": 3_000_000}},
    {"id": "yt-ads", "platform": "youtube", "name": "YouTube Partner Program: ad revenue",
     "unlocks": "Shorts ad revenue share (from 2027-02-01 the 10M views must hold every 90 days)",
     "need": {"subs": 1000, "shorts_views_90d": 10_000_000}},
    {"id": "fb-stars", "platform": "facebook", "name": "Facebook Stars",
     "unlocks": "Stars from viewers; hold 500 followers for 30 days (Vietnam: check the eligibility page)",
     "need": {"followers": 500}},
    {"id": "ig-gifts", "platform": "instagram", "name": "Instagram Gifts on Reels",
     "unlocks": "Gifts from viewers (Vietnam: check the eligibility page)", "need": {"followers": 500}},
    {"id": "ig-market", "platform": "instagram", "name": "Instagram Creator Marketplace",
     "unlocks": "Brand deals", "need": {"followers": 1000}},
    {"id": "ig-subs", "platform": "instagram", "name": "Instagram Subscriptions",
     "unlocks": "Paid subscribers", "need": {"followers": 10_000}},
]  # fmt: skip
TARGET_DAYS = 180  # the campaign aims to qualify for every goal but Instagram Subscriptions in six months
# What to do in each phase of the campaign (days since start), and every week.
PHASES = [
    (0, "Days 1-30: find the hook", [
        "Post 2 reels a day on every platform, at the slot times; never skip a day",
        "Try a different kind of dream in each reel: the views tell which kinds hook",
        "Instagram: post some as Trial Reels so non-followers test the hook first",
        "Reply to every comment in the first hour",
    ]),
    (30, "Days 31-90: double down", [
        "Make more of the kinds whose reels kept viewers past 70% (Studio > Shorts > retention)",
        "Number the series (\"Dream job #31\") so viewers follow to see the next one",
        "Pin a comment asking which dream job comes next, and make the top answer",
        "Keep the templates varied: YouTube rejects mass-produced, repetitive channels",
    ]),
    (90, "Days 91-180: qualify", [
        "Apply to the YouTube Partner Program the day a goal turns green (review takes about a month)",
        "Turn on 2-Step Verification and link AdSense before applying",
        "Keep posting 2 a day: Shorts views count only the last 90 days",
        "Facebook / Instagram: open the monetization page weekly; invites come without notice",
    ]),
]  # fmt: skip
WEEKLY = [
    "Update the numbers below from each platform's analytics",
    "Read which 3 reels did best and why (hook, dream kind, hour)",
    "Check every post is public and has its caption and cover",
]


def _file(svc: Services, channel: str):
    if channel not in CHANNELS:
        raise InvalidRequest(f"unknown channel {channel!r}")
    return svc.settings.data_dir / f"campaign-{channel}.json"


def _load(svc: Services, channel: str) -> dict:
    path = _file(svc, channel)
    return json.loads(path.read_text()) if path.exists() else {}


def _today() -> date:
    return datetime.now(TZ).date()


def _rate(snaps: list[dict], platform: str, metric: str) -> float | None:
    """Growth per day between the first and last snapshot holding ``metric``."""
    points = [(date.fromisoformat(s["date"]), s[platform][metric])
              for s in snaps if isinstance((s.get(platform) or {}).get(metric), (int, float))]
    if len(points) < 2 or points[-1][0] == points[0][0]:
        return None
    return (points[-1][1] - points[0][1]) / (points[-1][0] - points[0][0]).days


def _view(data: dict) -> dict:
    today = _today()
    start = date.fromisoformat(data["start"]) if data.get("start") else today
    snaps = sorted(data.get("snapshots") or [], key=lambda s: s["date"])
    day = (today - start).days
    target = start + timedelta(days=TARGET_DAYS)
    current = {p: {} for p in METRICS}
    for s in snaps:  # the latest value of each metric
        for p in METRICS:
            current[p].update({k: v for k, v in (s.get(p) or {}).items() if v is not None})
    goals = []
    for g in GOALS:
        parts, etas = [], []
        for m, need in g["need"].items():
            have = current[g["platform"]].get(m)
            rate = _rate(snaps, g["platform"], m)
            left = max(0, need - (have or 0))
            eta = today if not left else \
                today + timedelta(days=-(-left // rate)) if rate and rate > 0 else None
            etas.append(eta)
            parts.append({"metric": m, "label": dict((k, lb) for k, lb, _ in METRICS[g["platform"]])[m],
                          "have": have, "need": need, "pct": min(100, round(100 * (have or 0) / need)),
                          "per_day": round(rate, 1) if rate is not None else None,
                          "need_per_day": round(left / max(1, (target - today).days), 1) if left else 0})
        done = all(p["have"] is not None and p["have"] >= p["need"] for p in parts)
        goals.append({**{k: g[k] for k in ("id", "platform", "name", "unlocks")}, "parts": parts,
                      "pct": min(p["pct"] for p in parts), "done": done,
                      "eta": None if None in etas else max(etas).isoformat()})
    phase = next(ph for ph in reversed(PHASES) if day >= ph[0])
    return {"start": start.isoformat(), "day": day + 1, "target": target.isoformat(),
            "phase": {"name": phase[1], "todo": phase[2]}, "weekly": WEEKLY,
            "metrics": {p: [{"id": k, "label": lb, "where": w} for k, lb, w in ms] for p, ms in METRICS.items()},
            "current": current, "goals": goals,
            "snapshots": [{"date": s["date"]} | {p: s.get(p) for p in METRICS} for s in snaps]}


@router.get("/dashboard/campaign/{channel}", include_in_schema=False)
def get_campaign(channel: str, svc: Services = Depends(get_services)) -> dict:
    return _view(_load(svc, channel))


@router.post("/dashboard/campaign/{channel}", include_in_schema=False)
def update_campaign(channel: str, body: dict, svc: Services = Depends(get_services)) -> dict:
    """Save today's numbers (``{"youtube": {"subs": 120}, ...}``, merged into today's snapshot) and,
    with ``start`` (YYYY-MM-DD), the campaign's first day."""
    data = _load(svc, channel)
    if "start" in body:
        try:
            data["start"] = date.fromisoformat(body["start"]).isoformat()
        except (TypeError, ValueError):
            raise InvalidRequest("start must be YYYY-MM-DD") from None
    data.setdefault("start", _today().isoformat())
    today = _today().isoformat()
    snaps = data.setdefault("snapshots", [])
    snap = next((s for s in snaps if s["date"] == today), None)
    for p, ms in METRICS.items():
        given = body.get(p) or {}
        for k, _, _ in ms:
            v = given.get(k)
            if v is None or v == "":
                continue
            if not isinstance(v, (int, float)) or isinstance(v, bool) or v < 0:
                raise InvalidRequest(f"{p} {k} must be a number >= 0")
            if snap is None:
                snap = {"date": today}
                snaps.append(snap)
            snap.setdefault(p, {})[k] = v
    path = _file(svc, channel)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1))
    return _view(data)
