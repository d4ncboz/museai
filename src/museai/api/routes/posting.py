"""Posting queue: finished videos in ``post_dir`` (the Desktop) waiting to go to social media.

muse-video delivers each final video to the Desktop. The dashboard lists them with a caption
per platform (``captions``, written by the social-captions skill; ``caption`` is the fallback for a
platform without one) and one button per platform that opens its upload page; the user marks each platform as
posted, and once every platform is done the video moves to the Trash.

A video missing a platform's caption gets one written in the background (services/captions.py).

deliver.sh puts the thumbnails (thumbnail skill) next to the video as ``<stem> - thumbnail 9x16.jpg`` /
``16x9``; the dashboard shows them to drag into the upload pages, and they go to the Trash with the video.

Each video belongs to a channel (``CHANNELS``: separate accounts, guessed from the file name, changeable
on the card) and gets a posting slot in that channel: two a day, handed out in delivery order, with a
time per platform (``TIMES``, in the channel's audience clock ``AUDIENCE``) to set in each platform's
scheduler. Times are returned in GMT+7, the user's clock.

With ``post_folders`` on, each delivered video (one with its 9x16 thumbnail, settled for ``SETTLE`` s)
moves into a folder of its own, ``"Travel 01 · Fri 30-10 11h30 · <stem>"``: the video, its thumbnails
and ``captions.txt`` (the caption and time per platform). Each channel numbers its folders from 01 in
posting order, renumbered as videos go; deleting a folder takes its video out of the queue. Only folders holding a
``FOLDER_MARK`` file are touched, and videos without a thumbnail stay where they are.
"""

from __future__ import annotations

import ipaddress
import json
import logging
import re
import shutil
import subprocess
import threading
import time
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse

from ...errors import InvalidRequest, NotFound
from ...services.container import Services
from ..deps import get_services
from .dashboard import _local_or_admin

log = logging.getLogger(__name__)
router = APIRouter(tags=["dashboard"], dependencies=[Depends(_local_or_admin)])

# Upload pages. None of them takes a file in the link, so the dashboard also shows the file
# in Finder to drag in. Facebook's reel composer can cross-post to a linked Instagram account.
# The caption limit is the description's (YouTube's caption is "title\n\ndescription", title <= 100);
# X counts weighted characters (emoji, CJK and Vietnamese letters count 2). The social-captions
# skill's check_captions.py enforces the same limits before delivery.
PLATFORMS = {
    "youtube": ("YouTube Shorts", "https://www.youtube.com/upload", 5000),
    "tiktok": ("TikTok", "https://www.tiktok.com/tiktokstudio/upload", 4000),
    "facebook": ("Facebook Reels", "https://www.facebook.com/reels/create", 2200),
    "instagram": ("Instagram Reels", "https://www.instagram.com/", 2200),
    "x": ("X", "https://x.com/compose/post", 280),
    "threads": ("Threads", "https://www.threads.com/", 500),
}
VIDEO_EXT = {".mp4", ".mov", ".m4v"}
# Thumbnail kinds and where each is uploaded (the thumbnail skill's research, 2026-10).
THUMBS = {"9x16": "YouTube Shorts, TikTok, Facebook / Instagram Reels cover",
          "16x9": "YouTube video, Facebook feed"}

TZ = ZoneInfo("Asia/Ho_Chi_Minh")  # GMT+7: the user's clock; calendar days and shown times use it
# Channels post from separate accounts, so each has its own two slots a day: (name, focus per slot).
CHANNELS = {
    "chinese": ("Chinese", {1: "Late afternoon / lunch break: bite-sized (stroke order, word of the day)",
                            2: "Study hour after dinner: conversations, common mistakes, quizzes"}),
    "travel": ("Travel", {1: "UK / Europe evening: a quick view",
                          2: "US East evening: full reels and zoom-ins"}),
    # a new account (dream-life skill): two reels a day from 2026-11-02, 10+ hours apart, so each still gets
    # its own seed-audience test and the account fills the 90-day Shorts-views window faster
    "dream": ("Dream life", {1: "US evening wind-down: the strongest dream of the day",
                             2: "US morning commute: the lighter, quicker dream"}),
    # its own account too (user rule 2026-11-02): kitchen and home clips lose travel viewers
    "healing": ("Healing", {1: "US evening wind-down: one healing video a day"}),
}
# Short name of an audience clock, shown beside the GMT+7 time so the user sees whose evening a slot is.
CLOCKS = {"Europe/London": "London", "America/New_York": "New York"}
# Whose clock each slot's times follow. Chinese lessons have Vietnamese captions for Vietnamese
# learners: both slots in GMT+7. Travel (and the other English formats) speak to English viewers, who
# are asleep at Vietnam's peaks: slot 1 at the UK evening, slot 2 at the US East evening. Their audience
# day is the day before the calendar day, and every travel time is 18:00 or later, so both land on the
# calendar day in GMT+7 (about 01-03 h and 06-09 h); schedule them in each platform's scheduler.
AUDIENCE = {"chinese": (ZoneInfo("Asia/Ho_Chi_Minh"), ZoneInfo("Asia/Ho_Chi_Minh")),
            "travel": (ZoneInfo("Europe/London"), ZoneInfo("America/New_York")),
            "dream": (ZoneInfo("America/New_York"), ZoneInfo("America/New_York")),
            "healing": (ZoneInfo("America/New_York"),)}
# The format skills name their files <prefix>-<slug> (muse-video SKILL.md "Format skills"); a renamed file
# that still names its format ("Kelingking Beach - zoominview.mp4") is travel too. The English formats
# (nostalgia, gown, ...) post on the Travel accounts: their viewers share its clock. Dream-life and healing
# videos post on accounts of their own (user rules 2026-11-02), at the US evening.
DREAM_NAME = re.compile(r"^dream[-_ ]|\bdream-life\b", re.IGNORECASE)
HEALING_NAME = re.compile(r"^healing[-_ ]|\bhealing-video\b", re.IGNORECASE)
# YouTube playlists for Dream life, picked from the file's theme slug (dream-<slug>, dream-life
# themes.py): the first rule that matches wins, the rest are cozy everyday jobs. Playlists keep a viewer watching the
# next video and give the channel page shelves; Instagram and Facebook Reels have none.
DREAM_PLAYLISTS = (
    ("Soft Dream Worlds 🧸", r"plush|made-of|everyday|pets|sweets|crystal|giant-flowers|animal|upside-down|-in-things"
                            r"|doors|rooms-of|seasons-house|musical-garden|giants|rides"),
    ("Dream Places I'd Live 🏡", r"(town|city|island|village|suburb|market|lake|carnival|castle|rooftops|(?<!light)house"
                                r"|cottage|fjord|forest)(-|$)|sea-of-clouds"),
    ("Night Sky Dream Jobs 🌙", r"moon|star|comet|firefly|lantern|lighthouse|sunset|sky|night"),
    ("Weather & Season Dream Jobs ☁️", r"cloud|rain|snow|fog|weather|tide|sunrise|sunlight|autumn|season|umbrella|bubble"),
)
DREAM_CRAFTS = "Cozy Dream Jobs ☕"
TRAVEL_NAME = re.compile(r"^(zoom|reel|scenic|scenery|drop|travel|nostalgia|gown|product)[-_ ]"
                         r"|\b(zoominview|scenic-drop-reel)\b", re.IGNORECASE)
# Two videos a day per channel (user rule 2026-10-29). Each kind of content is watched at its own
# moment and each platform peaks at its own hours, so each channel has its own table: per platform,
# Monday first, "slot 1 slot 2" in that slot's audience clock (AUDIENCE). Revised 2026-11-02; sources
# and reasoning: .claude/skills/social-captions/references/posting-times.md. In short: YouTube Shorts
# do worst posted 12-17 h (Friday aside) and best 18-21 h, so no Shorts go out at noon; learners study
# in short breaks (lunch, commute) and after dinner, weekends in the morning; TikTok gets 15 minutes'
# head start on its peak; travel is watched as an evening wind-down and planned Sunday evening.
TIMES = {
    "chinese": {
        "youtube":   ["17:00 20:00", "19:00 21:00", "19:00 21:00", "19:00 21:00", "16:00 19:00", "11:00 19:00", "17:00 20:00"],
        "tiktok":    ["11:45 20:45", "11:45 20:45", "11:45 20:45", "11:45 18:45", "11:45 20:45", "08:45 19:45", "08:45 19:45"],
        "facebook":  ["11:30 20:30", "11:30 20:30", "11:30 20:30", "11:30 20:30", "11:30 20:30", "09:00 20:30", "09:00 20:30"],
        "instagram": ["09:00 21:00", "09:00 21:00", "12:00 21:00", "09:00 20:00", "12:00 21:00", "09:00 20:00", "09:00 20:00"],
        "x":         ["08:00 12:00", "08:00 12:00", "08:00 12:00", "08:00 12:00", "08:00 12:00", "09:00 12:00", "09:00 12:00"],
        "threads":   ["08:00 12:00", "08:00 12:00", "08:00 12:00", "08:00 12:00", "08:00 12:00", "09:00 12:00", "09:00 12:00"],
    },
    "travel": {
        "youtube":   ["20:00 20:00", "20:00 20:00", "19:00 19:00", "19:00 19:00", "18:00 18:00", "19:00 19:00", "19:00 19:00"],
        "tiktok":    ["19:45 19:45", "19:45 19:45", "19:45 19:45", "18:45 18:45", "18:45 18:45", "18:45 18:45", "18:45 18:45"],
        "facebook":  ["20:00 20:00", "20:00 20:00", "20:00 20:00", "20:00 20:00", "19:00 19:00", "20:00 20:00", "19:00 19:00"],
        "instagram": ["19:00 19:00", "19:00 19:00", "18:00 18:00", "20:00 20:00", "18:00 18:00", "19:00 19:00", "19:00 19:00"],
        "x":         ["18:00 18:00", "18:00 18:00", "18:00 18:00", "18:00 18:00", "18:00 18:00", "18:00 18:00", "18:00 18:00"],
        "threads":   ["18:00 18:00", "18:00 18:00", "18:00 18:00", "18:00 18:00", "18:00 18:00", "18:00 18:00", "18:00 18:00"],
    },
}  # fmt: skip
# New York clock, "evening morning". Slot 1, from the dream-life skill's scripts/post_time.py: the hour whose first two hours
# fall in the evening peak of most US viewers (Eastern to Pacific, weighted by population); it lands at
# 08-09 h in GMT+7. Slot 2: the weekday morning commute (Instagram's Thursday 8-9 h peak, X / Threads
# mornings), later on weekends; it lands at 19-22 h the same day in GMT+7, an easy hour to post by hand.
TIMES["dream"] = {
    "youtube":   ["20:00 08:00", "20:00 08:00", "21:00 08:00", "21:00 08:00", "21:00 08:00", "21:00 10:00", "21:00 10:00"],
    "tiktok":    ["20:45 07:45", "20:45 07:45", "20:45 07:45", "20:45 07:45", "20:45 07:45", "20:45 09:45", "20:45 09:45"],
    "facebook":  ["20:00 08:00", "20:00 08:00", "20:00 08:00", "20:00 08:00", "21:00 08:00", "20:00 10:00", "21:00 10:00"],
    "instagram": ["21:00 08:00", "21:00 08:00", "21:00 08:00", "20:00 08:00", "21:00 08:00", "21:00 10:00", "21:00 10:00"],
    "x":         ["21:00 08:00", "21:00 08:00", "21:00 08:00", "21:00 08:00", "21:00 08:00", "21:00 10:00", "21:00 10:00"],
    "threads":   ["21:00 08:00", "21:00 08:00", "21:00 08:00", "21:00 08:00", "21:00 08:00", "21:00 10:00", "21:00 10:00"],
}  # fmt: skip
# Healing is watched as the same US evening wind-down: slot 1 of the dream table fits it.
TIMES["healing"] = TIMES["dream"]
SLOT_KEY = re.compile(r"^(\d{4}-\d{2}-\d{2})/([12])$")
FOLDER_MARK = ".museai-post"  # marks a folder this module made for one video
SETTLE = 30  # seconds a video must sit unchanged before it moves (deliver.sh may still be copying it)
# Requests (in threads) and the caption writer all read-modify-write posts.json.
_state_lock = threading.Lock()


def _key(name: str) -> str:
    """State key of a file name. macOS lists some names decomposed (NFD) while deliver.sh posts them
    composed, so "Tiếng" could land under two keys and the video lose its caption."""
    return unicodedata.normalize("NFC", name)


def _load(svc: Services) -> dict:
    try:
        raw = json.loads(svc.settings.posts_file.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    state: dict = {}
    for name, entry in raw.items():  # merge entries saved under a decomposed name
        merged = state.setdefault(_key(name), {})
        merged.update({k: v for k, v in entry.items() if v or k not in merged})
    return state


def _save(svc: Services, state: dict) -> None:
    path = svc.settings.posts_file
    with path.with_name("post-history.jsonl").open("a") as log:  # every posted / deleted video, kept for good
        for name, e in state.items():
            if e.get("done") and not e.get("logged"):
                e["logged"] = True
                log.write(json.dumps({"name": name, **{k: v for k, v in e.items() if k != "logged"}},
                                     ensure_ascii=False) + "\n")
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False))
    tmp.replace(path)


def _exists(svc: Services, key: str) -> bool:
    return any(_key(p.name) == key for p in queued(svc))


def _video(svc: Services, name: str) -> Path:
    if Path(name).name == name and Path(name).suffix.lower() in VIDEO_EXT:
        for path in queued(svc):
            if _key(path.name) == _key(name):
                return path
    raise NotFound(f"video '{name}' not found")


def _channel(name: str, entry: dict) -> str:
    """The video's channel: the one picked on its card, else guessed from the file name."""
    if entry.get("channel") in CHANNELS:
        return entry["channel"]
    if DREAM_NAME.search(name):
        return "dream"
    if HEALING_NAME.search(name):
        return "healing"
    return "travel" if TRAVEL_NAME.search(name) else "chinese"


def _playlist(name: str, entry: dict) -> str | None:
    """The YouTube playlist a video goes in (Dream life only)."""
    if _channel(name, entry) != "dream":
        return None
    slug = re.sub(r"^dream[-_ ]+(life[-_ ]+)?", "", Path(name).stem.lower())
    return next((title for title, rule in DREAM_PLAYLISTS if re.search(rule, slug)), DREAM_CRAFTS)


def _kind(name: str) -> str:
    """What a video is, from its format prefix (healing, gown, nostalgia, ...): a day mixes kinds. Place
    reels (drone drops, scenery) are one kind, zoom-in views another."""
    low = name.lower()
    if "zoominview" in low:
        return "zoom"
    if "scenic-drop-reel" in low:
        return "place"
    word = re.split(r"[-_ ]", Path(low).stem, maxsplit=1)[0]
    return {"reel": "place", "scenic": "place", "scenery": "place", "drop": "place", "travel": "place"}.get(word, word)


def _thumbs(path: Path) -> dict[str, Path]:
    """The video's thumbnails on disk, by kind."""
    found = {k: path.with_name(f"{path.stem} - thumbnail {k}.jpg") for k in THUMBS}
    return {k: p for k, p in found.items() if p.is_file()}


def _slot_times(key: str, channel: str = "chinese") -> dict[str, datetime]:
    """Posting time per platform (in GMT+7) for a slot key "YYYY-MM-DD/1|2" of ``channel``."""
    day, n = SLOT_KEY.match(key).groups()
    d, n = date.fromisoformat(day), int(n)
    if n not in CHANNELS[channel][1]:
        raise ValueError(f"{CHANNELS[channel][0]} has no slot {n}")
    tz = AUDIENCE[channel][n - 1]
    out = {}
    for p, week in TIMES[channel].items():
        # an audience west of GMT+7: its evening of the day before lands on the calendar day, its morning
        # on the same day
        for a in (d, d - timedelta(days=1)):
            hh, mm = map(int, week[a.weekday()].split()[n - 1].split(":"))
            out[p] = datetime(a.year, a.month, a.day, hh, mm, tzinfo=tz).astimezone(TZ)
            if out[p].date() == d:
                break
    return out


def _slots_from(now: datetime, channel: str):
    """Slot keys of ``channel`` from today on whose YouTube time is still ahead of ``now``."""
    d = now.astimezone(TZ).date()
    while True:
        for n in CHANNELS[channel][1]:
            key = f"{d.isoformat()}/{n}"
            if _slot_times(key, channel)["youtube"] > now:
                yield key
        d += timedelta(days=1)


def _assign_slots(state: dict, videos: list[Path], now: datetime) -> bool:
    """Lay each channel's queue out back to back in its free slots. History is the slots of videos
    posted or deleted (records) and of queued videos posted on a platform or planned for auto-posting;
    those never move. Every other queued video takes a free upcoming slot, in queue order: its current
    slot (a slot the user picks sets its place in line), then delivery. Kinds mix (``_kind``): each free
    slot takes the first video in line of a kind not yet posting that day nor in the slot before, else
    one not yet posting that day, else the first. So no upcoming slot stays empty while videos wait, a
    slot that passed unposted moves up, and a day shows e.g. a healing video and a drone reel.
    Returns True when the state changed."""
    entries = [(p.name, state.setdefault(_key(p.name), {})) for p in sorted(videos, key=lambda p: p.stat().st_mtime)]
    changed = False
    for n, e in entries:
        if e.get("done"):  # the same name delivered again: a new video; the old record moves aside, its
            # slot staying in the history
            if e.get("slot"):
                state.setdefault(f"(posted {_channel(n, e)} {e['slot']})", dict(e))
            for k in ("done", "slot", "slot_pinned", "title"):
                e.pop(k, None)
            changed = True
    queued_names = {n for n, _ in entries}
    history: dict[str, dict[str, str]] = {ch: {} for ch in CHANNELS}  # slot -> kind of what posts there
    queue: dict[str, list[tuple[str, dict]]] = {ch: [] for ch in CHANNELS}
    for n, e in state.items():
        if n not in queued_names:
            if e.get("done") and e.get("slot"):
                history[_channel(n, e)][e["slot"]] = _kind(n)
    for n, e in entries:
        auto = e.get("auto") if isinstance(e.get("auto"), dict) else {}
        planned = bool(auto) and not auto.get("off") and not auto.get("paused")  # auto-post keeps its slot
        if e.get("slot") and (any((e.get("posted") or {}).values()) or planned):
            history[_channel(n, e)][e["slot"]] = _kind(n)
        else:
            queue[_channel(n, e)].append((n, e))
    for ch, line in queue.items():
        line.sort(key=lambda ne: ne[1].get("slot") or "~")  # stable: delivery order breaks ties
        taken = history[ch]
        for slot in (k for k in _slots_from(now, ch) if k not in taken):
            if not line:
                break
            day, n = slot.split("/")
            before = f"{day}/{int(n) - 1}" if n != "1" else \
                f"{date.fromisoformat(day) - timedelta(days=1)}/{max(CHANNELS[ch][1])}"
            same_day = {k for s, k in taken.items() if s.startswith(day)}
            name, e = _pick(line, [same_day | {taken.get(before)}, same_day])
            taken[slot] = _kind(name)
            changed |= e.get("slot") != slot
            e["slot"] = slot
    return _episode_order(entries) or changed


def _pick(line: list[tuple[str, dict]], avoid: list[set]) -> tuple[str, dict]:
    """Take the first video in ``line`` whose kind is in none of the first ``avoid`` set, else the
    second, ..., else the first video."""
    for kinds in avoid:
        for i, (name, _) in enumerate(line):
            if _kind(name) not in kinds:
                return line.pop(i)
    return line.pop(0)


def _episode_order(entries: list[tuple[str, dict]]) -> bool:
    """Episodes of one series post in number order: EP47 delivered before EP46 trades slots with it.
    Videos posted on any platform, pinned by the user or planned for auto-posting keep their slot."""
    series: dict[tuple[str, str], list[tuple[int, dict]]] = {}
    for n, e in entries:
        auto = e.get("auto") if isinstance(e.get("auto"), dict) else {}
        if e.get("slot_pinned") or any((e.get("posted") or {}).values()) or (auto and not auto.get("off")):
            continue
        if m := re.match(r"(.*?\D)(\d+)(?!\d)", Path(n).stem):
            series.setdefault((_channel(n, e), m[1].strip().lower()), []).append((int(m[2]), e))
    changed = False
    for eps in series.values():
        slots = sorted(e["slot"] for _, e in eps)
        for (_, e), slot in zip(sorted(eps, key=lambda ep: ep[0]), slots, strict=True):
            changed |= e["slot"] != slot
            e["slot"] = slot
    return changed


def _forget_old(state: dict, now: datetime, keep_days: int = 365) -> bool:
    """Drop records of posted / deleted videos whose slot is more than ``keep_days`` behind."""
    cut = (now.astimezone(TZ).date() - timedelta(days=keep_days)).isoformat()
    old = [n for n, e in state.items() if e.get("done") and e.get("slot", "") < cut]
    for n in old:
        del state[n]
    return bool(old)


def _forget_deleted(state: dict, present: set[str]) -> bool:
    """Turn the entry of a video deleted by hand (its folder deleted once posted) into the record
    ``_record`` keeps, so its slot stays booked until ``_forget_old`` drops it, and the same name
    delivered again is a new video with a slot of its own."""
    gone = [n for n, e in state.items() if not e.get("done") and n not in present]
    for n in gone:
        if state[n].get("slot"):
            state[n] = _record(state[n], n)
        else:  # never booked: nothing to keep
            del state[n]
    return bool(gone)


def _record(entry: dict, name: str) -> dict:
    """What stays of a posted / deleted video: its slot, channel and title, for the calendar."""
    caption = (entry.get("captions", {}).get("youtube") or entry.get("caption") or "").split("\n")[0].strip()
    return {"slot": entry["slot"], "channel": _channel(name, entry), "title": caption, "done": time.time()}


def _view(path: Path, entry: dict, svc: Services) -> dict:
    st = path.stat()
    key = entry.get("slot")
    return {"name": path.name, "size": st.st_size, "mtime": st.st_mtime,
            "caption": entry.get("caption", ""), "captions": entry.get("captions", {}),
            "auto_captions": svc.captions.status(_key(path.name)),
            "posted": entry.get("posted", {}), "slot": key, "channel": _channel(path.name, entry),
            "playlist": _playlist(path.name, entry),
            "thumbnails": [{"kind": k, "use": THUMBS[k]} for k in _thumbs(path)],
            "auto": {p: j.get("state", "") for p, j in (entry.get("auto") or {}).get("jobs", {}).items()},
            "schedule": {p: t.isoformat() for p, t in _slot_times(key, _channel(path.name, entry)).items()} if key else {},
            "audience": _audience(key, _channel(path.name, entry)) if key else None}


def _audience(key: str, channel: str) -> dict | None:
    """The audience's own clock for a slot whose audience lives outside GMT+7: its name and the time
    per platform there (the user schedules in GMT+7; this says whose evening it is)."""
    tz = AUDIENCE[channel][int(key[-1]) - 1]
    if tz == TZ:
        return None
    return {"clock": CLOCKS.get(tz.key, tz.key), "times": {p: t.astimezone(tz).isoformat()
                                                           for p, t in _slot_times(key, channel).items()}}


def _calendar(state: dict, names: dict[str, str], now: datetime, days: int = 7) -> dict[str, list[dict]]:
    """Per channel, the next ``days`` days of slots with the video (file name, by state key in
    ``names``) booked in each (or None), and ``gone`` (name, title) for a video already posted or
    deleted from that slot."""
    booked = {(_channel(n, e), e["slot"]): names[n] for n, e in state.items() if n in names and e.get("slot")}
    gone = {(_channel(n, e), e["slot"]): {"name": n, "title": e.get("title", "")}
            for n, e in state.items() if n not in names and e.get("slot")}
    start = now.astimezone(TZ).date()
    out: dict[str, list[dict]] = {}
    for ch, (_, focus) in CHANNELS.items():
        out[ch] = []
        for i in range(days):
            d = start + timedelta(days=i)
            slots = []
            for n in focus:
                key = f"{d.isoformat()}/{n}"
                aud = _audience(key, ch)
                slots.append({"key": key, "n": n, "time": _slot_times(key, ch)["youtube"].isoformat(),
                              "audience": aud and {"clock": aud["clock"], "time": aud["times"]["youtube"]},
                              "focus": focus[n], "video": booked.get((ch, key)),
                              "gone": None if (ch, key) in booked else gone.get((ch, key))})
            out[ch].append({"date": d.isoformat(), "slots": slots})
    return out


def _trash(path: Path) -> None:
    if shutil.which("trash"):
        subprocess.run(["trash", str(path)], check=True)
    else:
        bin_ = Path.home() / ".Trash"
        bin_.mkdir(exist_ok=True)
        name = f"{path.name}-{int(time.time())}" if path.is_dir() else f"{path.stem}-{int(time.time())}{path.suffix}"
        shutil.move(str(path), bin_ / name)


def _save_captions(svc: Services, key: str, captions: dict[str, str]) -> None:
    """Store auto-written captions in the platforms still empty (the user may have typed one since)."""
    with _state_lock:
        state = _load(svc)
        entry = state.setdefault(key, {})
        own = entry.setdefault("captions", {})
        for platform, text in captions.items():
            own.setdefault(platform, text)
        if not entry.get("caption") and own.get("tiktok"):
            entry["caption"] = own["tiktok"]  # push notifications and the "All" tab show it
        _save(svc, state)


def _is_video(p: Path) -> bool:
    return p.is_file() and p.suffix.lower() in VIDEO_EXT and not p.name.startswith(".")


def _folders(root: Path) -> list[Path]:
    """The per-video folders this module made in ``root``."""
    return [d for d in root.iterdir() if d.is_dir() and (d / FOLDER_MARK).is_file()]


def queued(svc: Services) -> list[Path]:
    """Videos in the posting folder and in its per-video folders, newest first."""
    root = svc.settings.post_dir
    if not root.is_dir():
        return []
    found = [p for p in root.iterdir() if _is_video(p)] + [p for d in _folders(root) for p in d.iterdir() if _is_video(p)]
    return sorted(found, key=lambda p: p.stat().st_mtime, reverse=True)


def _folder_name(n: int, name: str, entry: dict) -> str:
    """"Travel 01 · Fri 30-10 11h30 · <stem>": channel and its own number (so Finder groups each
    channel), YouTube slot time, file name (no colon or dot, which Finder shows oddly or reads as an
    extension)."""
    parts = [f"{CHANNELS[_channel(name, entry)][0]} {n:02d}"]
    if key := entry.get("slot"):
        parts.append(_slot_times(key, _channel(name, entry))["youtube"].strftime("%a %d-%m %Hh%M"))
    return " · ".join(parts + [Path(name).stem[:100]])


def _captions_text(name: str, entry: dict) -> str:
    """captions.txt: per platform its posting time and caption, ready to paste."""
    shared = entry.get("caption", "")
    times = _slot_times(entry["slot"], _channel(name, entry)) if entry.get("slot") else {}
    blocks = []
    for p, (label, _, _) in PLATFORMS.items():
        text = entry.get("captions", {}).get(p) or shared
        if text:
            when = times[p].strftime("%a %d-%m %H:%M") if p in times else ""
            blocks.append(f"=== {label}{'  ' + when if when else ''} ===\n{text.strip()}\n")
    if playlist := _playlist(name, entry):
        blocks.append(f"=== YouTube playlist ===\n{playlist}\n")
    return "\n".join(blocks)


def _organize(root: Path, videos: list[Path], state: dict, now: datetime) -> list[Path]:
    """Move each ready video into its own folder, number the folders in posting order and refresh
    their captions.txt; returns ``videos`` at their new paths."""
    arrived = [p for p in videos if p.parent == root and p.with_name(f"{p.stem} - thumbnail 9x16.jpg").is_file()
               and now.timestamp() - p.stat().st_mtime >= SETTLE]
    again = {_key(p.name) for p in arrived}
    for p in videos:
        if p.parent != root and _key(p.name) in again:  # delivered again under the same name: the new one wins
            _trash(p.parent)
    out = {p: p for p in videos if p.parent == root or _key(p.name) not in again}
    ready = [p for p in out if p.parent != root] + arrived
    ready.sort(key=lambda p: (state.get(_key(p.name), {}).get("slot") or "~", p.stat().st_mtime))
    want, count = {}, {}  # each channel numbers its own videos from 01
    for p in ready:
        entry = state.get(_key(p.name), {})
        n = count[_channel(p.name, entry)] = count.get(_channel(p.name, entry), 0) + 1
        want[p] = root / _folder_name(n, p.name, entry)
    # Renumbering can swap two names: park the folders that move under hidden names first.
    parked = {}
    for p in ready:
        if p.parent != root and p.parent != want[p]:
            tmp = root / f".museai-renaming-{len(parked)}-{int(time.time())}"
            p.parent.rename(tmp)
            parked[p] = tmp / p.name
    for p in ready:
        folder = want[p]
        if p in parked:
            parked[p].parent.rename(folder)
        elif p.parent == root:
            folder.mkdir(exist_ok=True)
            (folder / FOLDER_MARK).touch()
            shutil.move(str(p), folder / p.name)
        new = out[p] = folder / p.name
        for kind in THUMBS:  # thumbnails delivered next to the video, also after it moved
            thumb = root / f"{new.stem} - thumbnail {kind}.jpg"
            if thumb.is_file():
                thumb.replace(folder / thumb.name)
        text = _captions_text(p.name, state.get(_key(p.name), {}))
        caps = folder / "captions.txt"
        if text and (not caps.is_file() or caps.read_text() != text):
            caps.write_text(text)
    return [out[p] for p in videos if p in out]


def refresh(svc: Services, now: datetime, videos: list[Path] | None = None) -> tuple[list[Path], dict]:
    """Book slots for new videos and plan their auto-posting (routes/autopost.py); returns the queued
    videos and the saved state."""
    from . import autopost  # it builds on this module

    videos = queued(svc) if videos is None else videos
    rules = autopost.load_config(svc)["rules"]
    with _state_lock:
        state = _load(svc)
        changed = _forget_old(state, now) | autopost.plan(state, videos, rules)
        if svc.settings.post_dir.is_dir():  # listed again under the lock: a video moving to its folder is not gone
            changed |= _forget_deleted(state, {_key(p.name) for p in queued(svc)})
        changed |= _assign_slots(state, videos, now) | autopost.book_fixed(state, rules, now)
        if changed:
            _save(svc, state)
        if svc.settings.post_folders:
            try:
                videos = _organize(svc.settings.post_dir, videos, state, now)
            except OSError as exc:  # a file in use or a name clash: the queue still lists, next pass retries
                log.warning("posting folders: %s", exc)
    return videos, state


@router.get("/dashboard/posts", include_in_schema=False)
async def list_posts(svc: Services = Depends(get_services)) -> dict:
    folder = svc.settings.post_dir
    videos = queued(svc)
    now = datetime.now(TZ)
    videos, state = refresh(svc, now, videos)
    for p in videos:
        svc.captions.schedule(_key(p.name), p, state.get(_key(p.name), {}),
                              lambda key, caps: _save_captions(svc, key, caps))
    return {
        "folder": str(folder),
        "timezone": "GMT+7",
        "channels": [{"id": k, "name": n, "focus": f} for k, (n, f) in CHANNELS.items()],
        "platforms": [{"id": k, "name": n, "url": u, "limit": lim}
                      for k, (n, u, lim) in PLATFORMS.items()],
        # Cards in posting order: the next slot first.
        "videos": sorted((_view(p, state.get(_key(p.name), {}), svc) for p in videos),
                         key=lambda v: v["slot"] or "~"),
        "calendar": _calendar(state, {_key(p.name): p.name for p in videos}, now),
        "playlists": {"dream": [title for title, _ in DREAM_PLAYLISTS] + [DREAM_CRAFTS]},
    }


@router.get("/dashboard/posts/{name}/file", include_in_schema=False)
async def post_file(name: str, svc: Services = Depends(get_services)) -> FileResponse:
    return FileResponse(_video(svc, name))


@router.get("/dashboard/posts/{name}/thumbnail/{kind}", include_in_schema=False)
async def post_thumbnail(name: str, kind: str, svc: Services = Depends(get_services)) -> FileResponse:
    thumb = _thumbs(_video(svc, name)).get(kind)
    if not thumb:
        raise NotFound(f"no {kind} thumbnail for '{name}'")
    return FileResponse(thumb, filename=thumb.name, content_disposition_type="inline")  # view; save from there


# Plain def (not async): trashing and Finder run subprocesses, so FastAPI runs these in a thread.
@router.post("/dashboard/posts/{name}", include_in_schema=False)
def update_post(name: str, body: dict, svc: Services = Depends(get_services)) -> dict:
    """Set the caption, per-platform ``captions`` (merged in; an empty text drops that platform's
    own caption), the ``channel`` (moving it drops its slot; the next listing books one there), the
    posting ``slot`` ("YYYY-MM-DD/1|2"; a video of the same channel already there swaps into this
    one's old slot), mark a platform posted (or not), or ``{"done": true}`` to trash it now.

    Marking the last platform posted moves the video to the Trash.
    """
    path = _video(svc, name)
    with _state_lock:
        return _update(svc, path, body)


def _update(svc: Services, path: Path, body: dict) -> dict:
    name = _key(path.name)
    state = _load(svc)
    entry = state.setdefault(name, {})
    if "caption" in body:
        entry["caption"] = str(body["caption"] or "")[:5000]
    if captions := body.get("captions"):
        if not isinstance(captions, dict) or set(captions) - set(PLATFORMS):
            raise InvalidRequest(f"captions must map platforms ({', '.join(PLATFORMS)}) to text")
        own = entry.setdefault("captions", {})
        for platform, text in captions.items():
            if text := str(text or "")[:5200]:  # YouTube: title + blank line + description
                own[platform] = text
            else:
                own.pop(platform, None)
    if (channel := body.get("channel")) and channel != _channel(name, entry):
        if channel not in CHANNELS:
            raise InvalidRequest(f"unknown channel '{channel}'")
        entry["channel"] = channel
        entry.pop("slot", None)
        entry.pop("slot_pinned", None)
    if slot := body.get("slot"):
        try:
            _slot_times(slot, _channel(name, entry))
        except (TypeError, AttributeError, ValueError):
            raise InvalidRequest("slot must be 'YYYY-MM-DD/n', n one of the channel's slots") from None
        for other, e in state.items():
            if other != name and e.get("slot") == slot and _channel(other, e) == _channel(name, entry) \
                    and _exists(svc, other):
                if old := entry.get("slot"):
                    e["slot"], e["slot_pinned"] = old, True
                else:
                    e.pop("slot", None)
        entry["slot"], entry["slot_pinned"] = slot, True
    if platform := body.get("platform"):
        if platform not in PLATFORMS:
            raise InvalidRequest(f"unknown platform '{platform}'")
        posted = entry.setdefault("posted", {})
        if body.get("posted", True):
            posted[platform] = time.time()
        else:
            posted.pop(platform, None)
    done = body.get("done") or set(entry.get("posted", {})) >= set(PLATFORMS)
    if done:
        if (path.parent / FOLDER_MARK).is_file():
            _trash(path.parent)
        else:
            for thumb in _thumbs(path).values():
                _trash(thumb)
            _trash(path)
        if entry.get("slot"):
            state[name] = _record(entry, name)  # keeps the slot booked: the next video takes the one after
        else:
            state.pop(name, None)
    _save(svc, state)
    return {"trashed": bool(done), "video": None if done else _view(path, entry, svc)}


@router.post("/dashboard/posts/{name}/reveal", include_in_schema=False)
def reveal_post(name: str, request: Request, svc: Services = Depends(get_services)) -> dict:
    """Show the video in Finder, to drag into an upload page. Only on the machine itself."""
    path = _video(svc, name)
    host = request.client.host if request.client else ""
    try:
        local = ipaddress.ip_address(host).is_loopback
    except ValueError:
        local = False
    if local and shutil.which("open"):
        subprocess.run(["open", "-R", str(path)], check=False)
    return {"revealed": local}
