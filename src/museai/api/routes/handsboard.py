"""Muse Hands dashboard text: what is left to post, per channel and platform, built for a phone.

Look and content are editable in ``data/hands.json`` under ``"dashboard"`` (all keys optional)::

    {"dashboard": {"title": "Posting",
                   "platforms": ["youtube", "tiktok", "facebook", "instagram"],   # columns, in order
                   "channels": ["chinese", "travel"],                              # only these, in order
                   "icons": {"youtube": "▶️", "tiktok": "🎵", "facebook": "📘", "instagram": "📸"},
                   "hide_empty": false}}                                           # hide channels with 0 left
"""

from __future__ import annotations

import json
from datetime import datetime

from ...services.container import Services
from ...services.publishers import AUTO_PLATFORMS
from . import posting

ICONS = {"youtube": "▶️", "tiktok": "🎵", "facebook": "📘", "instagram": "📸"}
BAD = ("error", "missed", "needs_account")
Keyboard = dict


def config(svc: Services) -> dict:
    try:
        own = json.loads((svc.settings.data_dir / "hands.json").read_text()).get("dashboard") or {}
    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        own = {}
    platforms = [p for p in own.get("platforms") or AUTO_PLATFORMS if p in AUTO_PLATFORMS]
    return {"title": own.get("title") or "Posting", "platforms": platforms or list(AUTO_PLATFORMS),
            "channels": own.get("channels"), "icons": {**ICONS, **(own.get("icons") or {})},
            "hide_empty": bool(own.get("hide_empty"))}


def pending(video: dict, platforms: list[str]) -> list[dict]:
    """The platforms of ``video`` that still have to be posted (shown columns only)."""
    return [p for p in video["platforms"] if p["id"] in platforms and p["can_post"] and p["state"] != "manual"]


def channels(data: dict, cfg: dict, everything: bool = False) -> list[tuple[str, str, list[dict]]]:
    """(id, name, videos) per channel in dashboard order; the videos still to post, or every video
    (posted ones too) with ``everything``."""
    names: dict[str, str] = {}
    groups: dict[str, list[dict]] = {}
    for v in data["videos"]:
        names[v["channel_id"]] = v["channel"]
        groups.setdefault(v["channel_id"], []).append(v)
    order = cfg["channels"] or list(posting.CHANNELS)
    rows = []
    for cid in order:
        if cid not in posting.CHANNELS:
            continue
        videos = [v for v in groups.get(cid, []) if everything or pending(v, cfg["platforms"])]
        if videos or not cfg["hide_empty"]:
            rows.append((cid, posting.CHANNELS[cid][0], videos))
    return rows


def _when(iso: str | None) -> str:
    return datetime.fromisoformat(iso).astimezone(posting.TZ).strftime("%a %H:%M") if iso else ""


STATE = {"posted": "✅", "scheduled": "🕒", "retry": "🔁", "error": "❌", "missed": "⚠️", "needs_account": "🔌",
         "posting": "⏳", "paused": "⏸", "waiting": "✍️", "manual": "⬜"}
# postq platforms (tools/postq): button icon, label, and the dashboard "posted" boxes it ticks
POSTQ_PLATFORMS = {"youtube": ("▶️", "YT", ["youtube"]), "tiktok": ("🎵", "TT", ["tiktok"]),
                   "meta": ("Ⓜ️", "Meta", ["facebook", "instagram"]), "x": ("𝕏", "X", ["x"])}
PER_PAGE = 8  # videos per message: Telegram caps a message at 4096 characters and a keyboard at 100 buttons


def status(data: dict, cfg: dict) -> tuple[str, Keyboard]:
    """/status: one button per channel, nothing else."""
    rows = channels(data, cfg, everything=True)
    left = sum(1 for _, _, vs in rows for v in vs if pending(v, cfg["platforms"]))
    lines = [f"📊 {cfg['title']} · {left} video{'s' * (left != 1)} to post"]
    if data["paused"]:
        lines.append("⏸ Auto-posting paused")
    nxt = min((p["time"] for _, _, vs in rows for v in vs for p in pending(v, cfg["platforms"]) if p["time"]), default=None)
    if nxt:
        lines.append(f"Next: {_when(nxt)}")
    lines.append("Pick a channel:")
    keyboard = []
    for cid, name, videos in rows:
        todo = sum(bool(pending(v, cfg["platforms"])) for v in videos)
        keyboard.append([{"text": f"{name} · {len(videos)} video{'s' * (len(videos) != 1)}" + (f" · {todo} to post" if todo else ""),
                          "callback_data": f"ch:{cid}"}])
    if not rows or not any(vs for _, _, vs in rows):
        lines.append("\n📭 No videos." + (f"\nWatching: {data['folder']}" if data.get("folder") else ""))
    keyboard.append([{"text": "🔄 Refresh", "callback_data": "status"}])
    return "\n".join(lines), {"inline_keyboard": keyboard}


def channel(data: dict, cid: str, cfg: dict, page: int = 0) -> tuple[str, Keyboard]:
    """Every video of one channel, posted ones too: per video a Post and a Delete button; at the bottom
    post-everything buttons across platforms."""
    name, videos = next(((n, v) for c, n, v in channels(data, cfg, everything=True) if c == cid),
                        (posting.CHANNELS.get(cid, (cid,))[0], []))
    pages = max(1, -(-len(videos) // PER_PAGE))
    page = min(max(page, 0), pages - 1)
    lines = [f"{name} · {len(videos)} video{'s' * (len(videos) != 1)}" + (f" · page {page + 1}/{pages}" if pages > 1 else ""),
             "Tap a platform to post it there (postq extension) · posted ones disappear"]
    keyboard = []
    for i, v in enumerate(videos[page * PER_PAGE:(page + 1) * PER_PAGE], page * PER_PAGE + 1):
        row = [{"text": f"{icon} {i}", "callback_data": f"px:{v['id']}:{cid}:{pid}"}
               for pid, (icon, _, boxes) in POSTQ_PLATFORMS.items() if not set(boxes) <= set(v.get("posted", []))]
        if row:  # title row, then its platform buttons right below it (a message can't hold buttons in its text)
            keyboard.append([{"text": f"{i}. {(v['title'] or v['name'])[:60]}", "callback_data": "noop"}])
            row.append({"text": f"🗑 {i}", "callback_data": f"delq:{v['id']}:{cid}"})
            keyboard.append(row)
    if not videos:
        lines.append("\n📭 No videos.")
    if pages > 1:
        keyboard.append([{"text": "‹ Prev", "callback_data": f"ch:{cid}:{page - 1}"}] * (page > 0)
                        + [{"text": "Next ›", "callback_data": f"ch:{cid}:{page + 1}"}] * (page < pages - 1))
    across = [pid for pid in cfg["platforms"] if any(p["id"] == pid for v in videos if v["planned"] for p in pending(v, [pid]))]
    if across:
        keyboard.append([{"text": "✅ Post all", "callback_data": f"apprq:{cid}:all"}]
                        + [{"text": f"{cfg['icons'][pid]} all", "callback_data": f"apprq:{cid}:{pid}"} for pid in across])
    keyboard.append([{"text": "🔄 Refresh", "callback_data": f"ch:{cid}:{page}"},
                     {"text": "‹ Channels", "callback_data": "status"}])
    return "\n".join(lines), {"inline_keyboard": keyboard}


def picker(data: dict, vid: str, cid: str, cfg: dict, mask: int | None = None) -> tuple[str, Keyboard]:
    """Choose the platforms to post one video to (bit i of ``mask`` = cfg platform i; default: all that are left)."""
    v = next((v for v in data["videos"] if v["id"] == vid), None)
    back = [{"text": "‹ Back", "callback_data": f"ch:{cid}"}]
    if not v:
        return "Video is gone.", {"inline_keyboard": [back]}
    todo = {p["id"] for p in pending(v, cfg["platforms"])}
    full = sum(1 << i for i, pid in enumerate(cfg["platforms"]) if pid in todo)
    mask = full if mask is None else mask & full
    keyboard = [[{"text": ("✅ " if mask >> i & 1 else "⬜ ") + f"{cfg['icons'][pid]} {posting.PLATFORMS[pid][0]}",
                  "callback_data": f"pk:{vid}:{cid}:{mask ^ (1 << i)}"}]
                for i, pid in enumerate(cfg["platforms"]) if pid in todo]
    go = ({"text": "▶ Post selected", "callback_data": f"pp:{vid}:{cid}:{mask}"} if mask
          else {"text": "Pick a platform", "callback_data": f"pk:{vid}:{cid}:{mask}"})
    keyboard.append([go, back[0]])
    return f"Post \"{(v['title'] or v['name'])[:80]}\" to:", {"inline_keyboard": keyboard}


def picked(data: dict, vid: str, mask: int, cfg: dict) -> tuple[str, list[str]]:
    """(video name, platform ids) a ``pp`` tap posts."""
    v = next((v for v in data["videos"] if v["id"] == vid), None)
    if not v:
        return "", []
    todo = {p["id"] for p in v["platforms"] if p["state"] not in ("posted", "posting")}
    return v["name"], [pid for i, pid in enumerate(cfg["platforms"]) if mask >> i & 1 and pid in todo]


def confirm_delete(data: dict, vid: str, cid: str) -> tuple[str, Keyboard]:
    v = next((v for v in data["videos"] if v["id"] == vid), None)
    if not v:
        return "Video is gone.", {"inline_keyboard": [[{"text": "‹ Back", "callback_data": f"ch:{cid}"}]]}
    return (f"Delete \"{(v['title'] or v['name'])[:80]}\"?\nIts folder (video, thumbnails, captions) goes to Trash.",
            {"inline_keyboard": [[{"text": "🗑 Yes, delete", "callback_data": f"delc:{vid}:{cid}"},
                                  {"text": "✖ No", "callback_data": f"ch:{cid}"}]]})


def targets(data: dict, cid: str, platform: str, cfg: dict) -> list[tuple[str, str]]:
    """(video name, platform) pairs an approve of ``cid`` (or "all") x ``platform`` ("all") would post."""
    out = []
    for c, _, videos in channels(data, cfg):
        if cid in ("all", c):
            for v in videos:
                if v["planned"]:
                    out += [(v["name"], p["id"]) for p in pending(v, cfg["platforms"])
                            if platform in ("all", p["id"]) and p["state"] != "posting"]
    return out


def confirm(count: int, cid: str, platform: str) -> tuple[str, Keyboard]:
    what = "everything" if cid == "all" else cid
    where = "" if platform == "all" else f" on {platform}"
    return (f"Post {count} job{'s' * (count != 1)} now ({what}{where})?",
            {"inline_keyboard": [[{"text": f"✅ Yes, post {count}", "callback_data": f"appr:{cid}:{platform}"},
                                  {"text": "✖ No", "callback_data": "status"}]]})


def queue(data: dict) -> str:
    """/postq: the auto-poster at a glance."""
    counts: dict[str, int] = {}
    for v in data["videos"]:
        for p in v["platforms"]:
            if p["state"] != "manual":
                counts[p["state"]] = counts.get(p["state"], 0) + 1
    icons = {"scheduled": "🕒", "posting": "⏳", "retry": "🔁", "waiting": "✍️", "needs_account": "🔌",
             "missed": "⚠️", "error": "❌", "posted": "✅", "paused": "⏸"}
    lines = ["⏸ Auto-posting paused" if data["paused"] else "▶️ Auto-posting running"]
    lines += [f"{icons.get(k, '•')} {k.replace('_', ' ')}: {n}" for k, n in sorted(counts.items())]
    return "\n".join(lines + ([] if counts else ["Queue empty."]))
