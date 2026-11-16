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
    # two a day (user rule 2026-11-05): 12:00 and 18:30 GMT+7 on every platform; conversations (Everyday
    # Chinese) and vocabulary quizzes alternate (``_assign_slots`` never puts the same kind in two slots in a row)
    "chinese": ("Chinese", {1: "12 PM: lunch break, bite-sized lesson",
                            2: "6:30 PM: after work, before dinner"}),
    # Travel, Dream life and Healing share one plan (user rule 2026-11-05): 07:00 and 19:00 GMT+7 (00 and 12 UTC)
    # on every platform, 12 hours apart, so each slot reaches its own half of the world. Kept for 3-4 weeks,
    # then tuned from each account's own audience data (YouTube's "When your viewers are on YouTube").
    "travel": ("Travel", {1: "7 AM: Americas afternoon / evening, East Asia morning",
                          2: "7 PM: Europe lunch / afternoon, South and East Asia evening"}),
    "dream": ("Dream life", {1: "7 AM: Americas afternoon / evening, East Asia morning",
                             2: "7 PM: Europe lunch / afternoon, South and East Asia evening"}),
    "healing": ("Healing", {1: "7 AM: Americas afternoon / evening, East Asia morning",
                            2: "7 PM: Europe lunch / afternoon, South and East Asia evening"}),
    # English drama (movies-english, me-NNNN files) posts on accounts of its own (user rule 2026-11-05),
    # on the Travel plan: its viewers are English speakers around the world too.
    "english": ("English drama", {1: "7 AM: Americas afternoon / evening, East Asia morning",
                                  2: "7 PM: Europe lunch / afternoon, South and East Asia evening"}),
}
# Short name of an audience clock, shown beside the GMT+7 time so the user sees whose evening a slot is.
CLOCKS = {"Europe/London": "London", "America/New_York": "New York"}
# Whose clock each slot's times follow: every channel's times are set in GMT+7. Chinese lessons have
# Vietnamese captions for Vietnamese learners; Travel, Dream life and Healing post at 07:00 and 19:00 GMT+7
# (00 and 12 UTC), two windows that cover the world between them (TIMES["travel"]).
AUDIENCE = {"chinese": (ZoneInfo("Asia/Ho_Chi_Minh"),) * 2,
            "travel": (ZoneInfo("Asia/Ho_Chi_Minh"),) * 2,
            "dream": (ZoneInfo("Asia/Ho_Chi_Minh"),) * 2,
            "healing": (ZoneInfo("Asia/Ho_Chi_Minh"),) * 2,
            "english": (ZoneInfo("Asia/Ho_Chi_Minh"),) * 2}
# The format skills name their files <prefix>-<slug> (muse-video SKILL.md "Format skills"); a renamed file
# that still names its format ("Kelingking Beach - zoominview.mp4") is travel too. The English formats
# (nostalgia, gown, ...) post on the Travel accounts: their viewers share its clock. Dream-life and healing
# videos post on accounts of their own (user rules 2026-11-02).
DREAM_NAME = re.compile(r"^dream[-_ ]|\bdream-life\b", re.IGNORECASE)
HEALING_NAME = re.compile(r"^healing[-_ ]|\bhealing-video\b", re.IGNORECASE)
ENGLISH_NAME = re.compile(r"^me-\d|\bmovies-english\b", re.IGNORECASE)  # movies-english: me-NNNN
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
# Healing playlists, same rule from the healing-<slug> file name; the rest are slow cooking and home days.
# Titles carry the words viewers search ("rain", "tea", "slow living").
HEALING_PLAYLISTS = (
    ("Rain, Snow & Misty Days 🌧️", r"rain|snow|mist|fog|storm|wind|autumn|winter"),
    ("Tea & Quiet Mornings 🍵", r"tea|cocoa|coffee|lemonade|elderflower|morning"),
    ("Nature Walks & Birdsong 🌿", r"ode|bird|river|forest|meadow|walk|garden|herb|sun"),
)
HEALING_HOME = "Slow Living Kitchen & Home 🍞"
TRAVEL_NAME = re.compile(r"^(zoom|reel|scenic|scenery|drop|travel|nostalgia|gown|product)[-_ ]"
                         r"|\b(zoominview|scenic-drop-reel)\b", re.IGNORECASE)
# Two videos a day per channel (user rule 2026-10-29). Each kind of content is watched at its own
# moment and each platform peaks at its own hours, so each channel has its own table: per platform,
# Monday first, "slot 1 slot 2" in that slot's audience clock (AUDIENCE). Revised 2026-11-04 from the
# 2026 Buffer / Sprout / Metricool studies and the Vietnamese golden-hour tables; sources and reasoning:
# .claude/skills/social-captions/references/posting-times.md. In short: the video platforms (YouTube
# Shorts, TikTok, Facebook and Instagram Reels) peak 18-23 h, each on its own hour per weekday; X and
# Threads are daytime platforms (mornings and noon best, evenings worst), so they never mirror the
# evening reel slots; TikTok gets 15 minutes' head start on its peak (its first test audience arrives
# with the peak). Chinese posts two a day at its own times, 12:00 and 18:30 GMT+7 on every platform
# (user rule 2026-11-05).
TIMES = {
    "chinese": {p: ["12:00 18:30"] * 7 for p in ("youtube", "tiktok", "facebook", "instagram", "x", "threads")},
    # GMT+7 (user rule 2026-11-05), one plan for Travel, Dream life and Healing. Slot 1, 07:00 (00 UTC):
    # New York 19 h, Los Angeles 16 h, São Paulo 21 h, Tokyo 09 h, Vietnam 07 h. Slot 2, 19:00 (12 UTC):
    # London 12 h, Berlin 13 h, India 17:30, Vietnam 19 h, Tokyo 21 h. Every platform at the same time.
    # Start point to test for 3-4 weeks, then tune from each account's own audience report; compare
    # videos at the same age (e.g. 7 days), not by early views. YouTube says posting time does not
    # change a Short's long-term reach: the opening shot and retention matter more.
    "travel": {p: ["07:00 19:00"] * 7 for p in ("youtube", "tiktok", "facebook", "instagram", "x", "threads")},
}  # fmt: skip
TIMES["dream"] = TIMES["english"] = TIMES["travel"]
# Healing posts only to YouTube, Facebook and Instagram (user rule 2026-11-16): no X, TikTok or Threads.
TIMES["healing"] = {p: t for p, t in TIMES["travel"].items() if p in ("youtube", "facebook", "instagram")}
SLOT_KEY = re.compile(r"^(\d{4}-\d{2}-\d{2})/([1-4])$")
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
    _log_schedule(path, state)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False))
    tmp.replace(path)


def _log_schedule(path: Path, state: dict) -> None:
    """Append the queued schedule (channel -> slot -> video) to schedule-history.jsonl whenever it
    differs from the last one logged."""
    now: dict[str, dict[str, str]] = {}
    for n, e in state.items():
        if e.get("slot") and not e.get("done") and not n.startswith("("):
            now.setdefault(_channel(n, e), {})[e["slot"]] = n
    log = path.with_name("schedule-history.jsonl")
    try:
        last = json.loads(log.read_text().splitlines()[-1])["schedule"]
    except (FileNotFoundError, IndexError, KeyError, json.JSONDecodeError):
        last = None
    if now and now != last:
        with log.open("a") as f:
            f.write(json.dumps({"at": datetime.now(TZ).isoformat(timespec="seconds"), "schedule": now},
                               ensure_ascii=False) + "\n")


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
    if ENGLISH_NAME.search(name):
        return "english"
    return "travel" if TRAVEL_NAME.search(name) else "chinese"


def _playlist(name: str, entry: dict) -> str | None:
    """The YouTube playlist a video goes in (Dream life and Healing)."""
    channel = _channel(name, entry)
    if channel not in ("dream", "healing"):
        return None
    lists, rest = (DREAM_PLAYLISTS, DREAM_CRAFTS) if channel == "dream" else (HEALING_PLAYLISTS, HEALING_HOME)
    slug = re.sub(r"^(dream|healing)[-_ ]+((life|video)[-_ ]+)?", "", Path(name).stem.lower())
    return next((title for title, rule in lists if re.search(rule, slug)), rest)


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
    """Posting time per platform (in GMT+7) for a slot key "YYYY-MM-DD/<n>" of ``channel``."""
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
    """Slot keys of ``channel`` from today on whose YouTube time is still ahead of ``now``; Dream life's
    list also counts today's first slot, so it starts at slot 1 of today even once its time has passed."""
    d = today = now.astimezone(TZ).date()
    first = min(CHANNELS[channel][1])
    while True:
        for n in CHANNELS[channel][1]:
            key = f"{d.isoformat()}/{n}"
            if (channel == "dream" and d == today and n == first) or _slot_times(key, channel)["youtube"] > now:
                yield key
        d += timedelta(days=1)


def _assign_slots(state: dict, videos: list[Path], now: datetime) -> bool:
    """Lay each channel's queue out back to back in its free slots. History is the slots of videos
    posted or deleted (records), manually pinned, or queued videos posted on a platform or planned for
    auto-posting; those never move. Every other queued video takes a free upcoming slot, the gaps left before a video
    ticked out of order included, in queue order: its current
    slot (a slot the user picks sets its place in line), then delivery. Kinds mix (``_kind``): each free
    slot takes the first video in line of a kind not yet posting that day nor in the slot before, else
    one not in the slot before (Chinese: conversation, quiz in turn), else one not
    yet posting that day, else the first. So no slot after the history stays empty while videos wait, a
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
    last_post: dict[str, str] = {}  # channel -> slot of its latest posted / deleted video
    for n, e in state.items():
        if n not in queued_names:
            if e.get("done") and e.get("slot"):
                ch = _channel(n, e)
                history[ch][e["slot"]] = _kind(n)
                last_post[ch] = max(last_post.get(ch, ""), e["slot"])
    for n, e in entries:
        auto = e.get("auto") if isinstance(e.get("auto"), dict) else {}
        planned = bool(auto) and not auto.get("off") and not auto.get("paused")  # auto-post keeps its slot
        if e.get("long"):  # 16:9 long clip: posts the same day as the shorts, takes none of their slots
            continue
        if e.get("slot") and (e.get("slot_pinned") or any((e.get("posted") or {}).values()) or planned):
            history[_channel(n, e)][e["slot"]] = _kind(n)
        else:
            queue[_channel(n, e)].append((n, e))
    for ch, line in queue.items():
        line.sort(key=lambda ne: ne[1].get("slot") or "~")  # stable: delivery order breaks ties
        taken = history[ch]
        for slot in (k for k in _slots_from(now, ch) if k not in taken and k > last_post.get(ch, "")):  # gaps between posted slots too
            if not line:
                break
            day, n = slot.split("/")
            before = f"{day}/{int(n) - 1}" if n != "1" else \
                f"{date.fromisoformat(day) - timedelta(days=1)}/{max(CHANNELS[ch][1])}"
            same_day = {k for s, k in taken.items() if s.startswith(day)}
            prev = {taken.get(before)}
            name, e = _pick(line, [same_day | prev, prev, same_day])
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
            "thumbnails": [{"kind": k, "use": THUMBS[k], "v": int(t.stat().st_mtime)}  # v: new URL when replaced
                           for k, t in _thumbs(path).items()],
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
        "channels": [{"id": k, "name": n, "focus": f, "platforms": list(TIMES[k])} for k, (n, f) in CHANNELS.items()],
        "platforms": [{"id": k, "name": n, "url": u, "limit": lim}
                      for k, (n, u, lim) in PLATFORMS.items()],
        # Cards in posting order: the next slot first.
        "videos": sorted((_view(p, state.get(_key(p.name), {}), svc) for p in videos),
                         key=lambda v: v["slot"] or "~"),
        "calendar": _calendar(state, {_key(p.name): p.name for p in videos}, now),
        "playlists": {"dream": [title for title, _ in DREAM_PLAYLISTS] + [DREAM_CRAFTS],
                      "healing": [title for title, _ in HEALING_PLAYLISTS] + [HEALING_HOME]},
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
    posting ``slot`` ("YYYY-MM-DD/<n>"; a video of the same channel already there swaps into this
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
    done = body.get("done") or set(entry.get("posted", {})) >= set(TIMES[_channel(name, entry)])
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
