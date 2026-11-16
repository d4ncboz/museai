"""Muse Hands: every queued video with its per-platform posting state, one tap to post it now.

Two front ends share ``overview`` / ``trigger``:

- ``/dashboard/hands``: a phone-sized page (the dashboard key goes in ``#key=``).
- the Telegram bot "Muse Hands": the server long-polls Telegram (outbound only, no tunnel), so the
  phone can trigger a post from anywhere while the laptop stays awake. ``/posts`` lists the videos,
  a button per platform presses "Post now"; the auto-post loop (autopost.py) does the posting.

Only chats listed in ``MUSE2API_TELEGRAM_CHAT_IDS`` are served; any other chat (all of them while the list
is empty) just gets its chat id back, to copy into that list.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import logging
import mimetypes
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from ...errors import InvalidRequest
from ...services.chatbots import ChatBots
from ...services.container import Services
from ...services.publishers import AUTO_PLATFORMS
from ..deps import get_services
from . import autopost, handsboard, posting
from .dashboard import _local_or_admin

log = logging.getLogger(__name__)

router = APIRouter(tags=["dashboard"])

_PAGE = Path(__file__).resolve().parent.parent / "static" / "hands.html"
_API = "https://api.telegram.org"
_ICON = {"posted": "✅", "posting": "⏳", "scheduled": "🕒", "retry": "🔁", "waiting": "✍️",
         "needs_account": "🔌", "missed": "⚠️", "error": "❌", "manual": "✋", "paused": "⏸"}


# --- shared ---

def overview(svc: Services) -> dict:
    """Every queued video, soonest slot first, with one entry per auto-post platform."""
    now = datetime.now(posting.TZ)
    videos, state = posting.refresh(svc, now)
    rules = {r.id: r for r in autopost.load_config(svc)["rules"]}
    paused_all = autopost.load_config(svc)["paused"]
    rows = []
    for path in videos:
        key = posting._key(path.name)
        entry = state.get(key, {})
        auto = entry.get("auto")
        planned = isinstance(auto, dict) and not auto.get("off")
        by_platform = {}
        if planned:
            by_platform = {j["platform"]: j for j in autopost._plan_view(path.name, entry, rules)["jobs"]}
        title = ((entry.get("captions") or {}).get("youtube") or entry.get("caption") or "").strip()
        platforms = []
        for p in AUTO_PLATFORMS:
            job = by_platform.get(p)
            if p in entry.get("posted", {}) or (job and job["state"] == "posted"):
                state_name, at, url, error = "posted", job and job["time"], job["url"] if job else "", ""
            elif job:
                state_name = "paused" if auto.get("paused") or paused_all else job["state"]
                at, url, error = job["time"], job["url"], job["error"]
            else:
                state_name, at, url, error = "manual", None, "", ""
            platforms.append({"id": p, "name": posting.PLATFORMS[p][0], "state": state_name, "time": at,
                              "url": url, "error": error, "can_post": state_name != "posted"})
        rows.append({"name": path.name, "id": _short(path.name), "title": title.split("\n")[0],
                     "channel_id": posting._channel(path.name, entry),
                     "channel": posting.CHANNELS[posting._channel(path.name, entry)][0],
                     "slot": entry.get("slot"), "planned": planned, "platforms": platforms,
                     "posted": sorted(entry.get("posted", {})),
                     "folder": str(path.parent) if (path.parent / posting.FOLDER_MARK).is_file() else ""})
    rows.sort(key=lambda r: r["slot"] or "~")
    return {"paused": paused_all, "folder": str(svc.settings.post_dir), "videos": rows}


def _short(name: str) -> str:
    """Telegram button data is capped at 64 bytes: a short stable id stands in for the file name."""
    return hashlib.sha1(posting._key(name).encode()).hexdigest()[:10]


def trigger(svc: Services, name: str, platform: str) -> str:
    """Press "Post now" for ``platform`` of ``name``; returns a one-line result."""
    if platform not in AUTO_PLATFORMS:
        raise InvalidRequest(f"platform must be one of {', '.join(AUTO_PLATFORMS)}")
    path = posting._video(svc, name)
    key = posting._key(path.name)
    with posting._state_lock:
        state = posting._load(svc)
        entry = state.setdefault(key, {})
        auto = entry.get("auto")
        if not isinstance(auto, dict) or auto.get("off"):
            raise InvalidRequest(f"'{name}' has no auto-post plan: plan it on the dashboard first")
        auto.pop("paused", None)
        if not autopost.post_now(auto, platform):
            return f"{platform} already posted"
        posting._save(svc, state)
    if autopost.load_config(svc)["paused"]:
        return f"{platform} queued, but auto-posting is paused (Pause all): resume it first"
    return f"{platform} posting within {int(svc.settings.autopost_interval)} s"


POSTQ = Path(__file__).resolve().parents[4] / "tools" / "postq" / "postq"


def postq_episode(folder: str, platform: str) -> str:
    """Queue one platform of an episode folder in the postq Chrome extension and post it without a click
    right away, not at its captions.txt slot (``postq episode DIR --platforms P --auto --now``);
    returns a one-line result for the phone."""
    if not folder:
        return "not an episode folder: post it from the dashboard"
    # Queued before (e.g. by `postq episodes` without --auto): the tap approves that item instead,
    # so the extension posts it now; postq never queues a second copy.
    if queued := postq_pending(folder, platform):
        cmd, ok = [str(POSTQ), "approve", "--now", *queued], f"{platform}: approved, the extension posts it now"
    else:
        cmd, ok = ([str(POSTQ), "episode", folder, "--platforms", platform, "--auto", "--now"],
                   f"{platform}: queued, the extension posts it now")
    try:
        run = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        return f"{platform}: postq timed out"
    out = (run.stdout.strip() or run.stderr.strip() or f"exit {run.returncode}").splitlines()
    if run.returncode == 0 and run.stdout.strip() and not out[-1].startswith("skipped"):
        return ok
    return f"{platform}: {out[-1][:150]}"


def postq_pending(folder: str, platform: str) -> list[str]:
    """Ids of postq items still waiting for ``platform`` whose video comes from ``folder``."""
    root = Path(os.environ.get("POSTQ_DIR", Path.home() / ".local" / "state" / "postq" / "queue"))
    ids = []
    for p in root.glob("*.json"):
        with contextlib.suppress(OSError, ValueError):
            item = json.loads(p.read_text())
            if item.get("platform") == platform and Path(item.get("source") or "/").parent == Path(folder):
                ids.append(item["id"])
    return sorted(ids)


@router.get("/dashboard/hands", include_in_schema=False)
async def page() -> FileResponse:
    return FileResponse(_PAGE, media_type="text/html", headers={"Cache-Control": "no-cache"})


@router.get("/dashboard/hands/data", include_in_schema=False, dependencies=[Depends(_local_or_admin)])
async def data(svc: Services = Depends(get_services)) -> dict:
    return await asyncio.to_thread(overview, svc)


@router.post("/dashboard/hands/post", include_in_schema=False, dependencies=[Depends(_local_or_admin)])
async def post(body: dict, svc: Services = Depends(get_services)) -> dict:
    message = await asyncio.to_thread(trigger, svc, str(body.get("name", "")), str(body.get("platform", "")))
    return {"ok": True, "message": message}


# --- Telegram ---

def chat_ids(raw: str) -> set[int]:
    return {int(x) for x in raw.replace(";", ",").split(",") if x.strip().lstrip("-").isdigit()}


def render(data: dict) -> tuple[str, dict]:
    """The /posts message and its inline keyboard. Phone first: how many videos are left, then per
    video what still has to be posted (and when) and what is done; one button row per video."""
    videos = data["videos"]
    if not videos:
        return (f"📭 0 videos left.\nWatching: {data.get('folder', '')}\n"
                "New videos land there when a video skill delivers them."), \
            {"inline_keyboard": [[{"text": "🔄 Refresh", "callback_data": "list"}]]}
    todo = sum(any(p["can_post"] and p["state"] != "manual" for p in v["platforms"]) for v in videos)
    lines = [f"🗂 {len(videos)} video{'s' * (len(videos) != 1)} left · {todo} to post"]
    if data["paused"]:
        lines.append("⏸ Auto-posting is paused (Pause all)")
    keyboard = []
    for i, v in enumerate(videos, 1):
        lines.append(f"\n{i}. {v['title'] or v['name']} · {v['channel']}")
        for p in v["platforms"]:
            if p["state"] == "manual" and not p["time"]:
                continue
            when = datetime.fromisoformat(p["time"]).astimezone(posting.TZ).strftime("%a %H:%M") if p["time"] else ""
            lines.append(f"  {_ICON.get(p['state'], '•')} {p['name']} · {p['state'].replace('_', ' ')} {when}".rstrip()
                         + (f" — {p['error'][:80]}" if p["error"] else ""))
        row = [{"text": f"{i} ▸ {p['name']}", "callback_data": f"post:{v['id']}:{p['id']}"}
               for p in v["platforms"] if p["can_post"] and v["planned"]]
        if row:
            keyboard.append(row)
        elif not v["planned"]:
            lines.append("  ✋ not auto-planned: plan it on the dashboard")
    keyboard.append([{"text": "🔄 Refresh", "callback_data": "list"}])
    return "\n".join(lines), {"inline_keyboard": keyboard}


HELP = ("/status dashboard: channels x platforms, tap to drill in + approve\n"
        "/approve <channel|all> [platform]  post queued videos now\n"
        "/posts  every video\n/postq  auto-post status\n/tasks  last 8 renders · /job [id] · /cancel [id]\n"
        "/model  pick the AI · /new  reset chat · or just write to the AI")


def _task_line(t) -> str:
    icon = {"queued": "🕒", "running": "⏳", "succeeded": "✅", "failed": "❌", "cancelled": "✖"}[t.status.value]
    prompt = str(t.request.get("prompt", ""))[:50].replace("\n", " ")
    return f"{icon} {t.id[-6:]} {t.kind} {t.progress}% {prompt}".rstrip()


def tasks_text(svc: Services) -> str:
    tasks = svc.tasks.list(8)
    return "\n".join(_task_line(t) for t in tasks) or "No renders yet."


def _find_task(svc: Services, ref: str | None):
    tasks = svc.tasks.list(500)
    if not ref:
        return tasks[0] if tasks else None
    return next((t for t in tasks if t.id.endswith(ref)), None)


def job_text(svc: Services, ref: str | None) -> str:
    t = _find_task(svc, ref)
    if not t:
        return "No such render."
    err = (t.error or {}).get("message", "") if t.error else ""
    return "\n".join(filter(None, [_task_line(t), f"account: {t.account_label}" if t.account_label else "",
                                    f"error: {err[:300]}" if err else ""]))


async def cancel_task(svc: Services, ref: str | None) -> str:
    t = _find_task(svc, ref)
    if not t or t.finished:
        return "No running render to cancel."
    return "Cancelled." if await svc.tasks.cancel(t.id) else "Could not cancel."


def delete_post(svc: Services, name: str) -> str:
    """Trash the video's whole folder (video, thumbnails, captions.txt), as the dashboard's delete does;
    a video lying loose in the posting folder goes with its thumbnails."""
    posting.update_post(name, {"done": True}, svc)
    return "folder deleted (in Trash)"


def alert_text(name: str, platform: str, result: str, svc: Services) -> tuple[str, list] | None:
    """Message for one finished job, plus its buttons. None = nothing to tell."""
    key = posting._key(name)
    entry = posting._load(svc).get(key, {})
    job = ((entry.get("auto") or {}).get("jobs") or {}).get(platform, {})
    title = ((entry.get("captions") or {}).get("youtube") or entry.get("caption") or name).strip().split("\n")[0]
    label = posting.PLATFORMS[platform][0]
    if result == "posted":
        return f"✅ {title}\n{label} posted {job.get('url', '')}".strip(), []
    if result not in ("retry", "error", "missed", "needs_account"):
        return None
    head = {"retry": f"🔁 {label} failed (try {job.get('attempts', 1)}), it retries by itself",
            "error": f"❌ {label} gave up", "missed": f"⚠️ {label} missed its time",
            "needs_account": f"🔌 {label} has no account connected"}[result]
    vid = _short(name)
    buttons = [[{"text": "🔁 Retry", "callback_data": f"retry:{vid}:{platform}"},
                {"text": "🗑 Delete post", "callback_data": f"delete:{vid}"}]]
    return f"{head}\n{title}\n{(job.get('error') or '')[:300]}".strip(), buttons


def _size(path: Path) -> int:
    return path.stat().st_size if path.is_file() else 0


class Bot:
    def __init__(self, svc: Services, client: httpx.AsyncClient | None = None) -> None:
        self.svc = svc
        s = svc.settings
        self.allowed = chat_ids(s.telegram_chat_ids)
        self.base = f"{_API}/bot{s.telegram_bot_token}"
        self.http = client or httpx.AsyncClient(timeout=70)
        self.offset = 0
        self.ai = ChatBots(s, svc.gateway, self.http)
        self.history: dict[int, list[tuple[str, str]]] = {}
        self.running: set[asyncio.Task] = set()

    async def call(self, method: str, **params) -> dict:
        r = await self.http.post(f"{self.base}/{method}", json=params)
        r.raise_for_status()
        return r.json().get("result")

    async def show(self, chat: int, message: int | None = None) -> None:
        text, markup = render(await asyncio.to_thread(overview, self.svc))
        if message:
            with contextlib.suppress(httpx.HTTPStatusError):  # "message is not modified"
                await self.call("editMessageText", chat_id=chat, message_id=message, text=text,
                                reply_markup=markup)
        else:
            await self.call("sendMessage", chat_id=chat, text=text, reply_markup=markup)

    async def edit(self, chat: int, message: int | None, text: str, markup: dict) -> None:
        if message:
            with contextlib.suppress(httpx.HTTPStatusError):  # "message is not modified"
                await self.call("editMessageText", chat_id=chat, message_id=message, text=text, reply_markup=markup)
        else:
            await self.call("sendMessage", chat_id=chat, text=text, reply_markup=markup)

    async def dashboard(self, chat: int, message: int | None = None) -> None:
        data = await asyncio.to_thread(overview, self.svc)
        cfg = handsboard.config(self.svc)
        text, markup = handsboard.status(data, cfg)
        await self.edit(chat, message, text, markup)

    async def approve_cmd(self, chat: int, args: list[str]) -> None:
        cid, platform = (args + ["all", "all"])[:2] if args else ("all", "all")
        data = await asyncio.to_thread(overview, self.svc)
        cfg = handsboard.config(self.svc)
        if cid != "all" and cid not in posting.CHANNELS or platform != "all" and platform not in AUTO_PLATFORMS:
            await self.call("sendMessage", chat_id=chat, text="/approve <channel|all> [platform]\n"
                            f"channels: {', '.join(posting.CHANNELS)}\nplatforms: {', '.join(AUTO_PLATFORMS)}")
            return
        count = len(handsboard.targets(data, cid, platform, cfg))
        if not count:
            await self.call("sendMessage", chat_id=chat, text="Nothing to approve.")
            return
        text, markup = handsboard.confirm(count, cid, platform)
        await self.call("sendMessage", chat_id=chat, text=text, reply_markup=markup)

    async def board_tap(self, chat: int, cb: dict, kind: str, rest: str) -> None:
        message = cb["message"]["message_id"]
        answer = ""
        data = await asyncio.to_thread(overview, self.svc)
        cfg = handsboard.config(self.svc)
        cid, _, platform = rest.partition(":")
        if kind == "ch":
            text, markup = handsboard.channel(data, cid, cfg, int(platform) if platform.isdigit() else 0)
            await self.edit(chat, message, text, markup)
        elif kind == "pk":
            vid, cid2, *mask = rest.split(":")
            text, markup = handsboard.picker(data, vid, cid2, cfg, int(mask[0]) if mask else None)
            await self.edit(chat, message, text, markup)
        elif kind == "pp":
            vid, cid2, mask = rest.split(":")
            name, ids = handsboard.picked(data, vid, int(mask), cfg)
            done = failed = 0
            for pid in ids:
                try:
                    await asyncio.to_thread(trigger, self.svc, name, pid)
                    done += 1
                except Exception:  # noqa: BLE001 - count it, go on
                    failed += 1
            answer = (f"{done} queued" + (f", {failed} failed" if failed else "")) if ids else "nothing to post"
            data = await asyncio.to_thread(overview, self.svc)
            text, markup = handsboard.channel(data, cid2, cfg)
            await self.edit(chat, message, text, markup)
        elif kind == "px":
            # postq can take minutes and Telegram drops a tap not answered within ~15 s: answer now,
            # run postq in the background, then report and redraw the channel
            vid, cid2, pid = rest.split(":")
            v = next((v for v in data["videos"] if v["id"] == vid), None)
            if not v:
                answer = "video is gone"
            else:
                icon, label, _ = handsboard.POSTQ_PLATFORMS.get(pid, ("", pid, []))
                await self.call("answerCallbackQuery", callback_query_id=cb["id"], text=f"{icon} {label}: sending to postq…")
                task = asyncio.create_task(self.postq_tap(chat, message, v, cid2, pid))
                self.running.add(task)
                task.add_done_callback(self.running.discard)
                return
        elif kind == "delq":
            text, markup = handsboard.confirm_delete(data, cid, platform)
            await self.edit(chat, message, text, markup)
        elif kind == "delc":
            name = next((v["name"] for v in data["videos"] if v["id"] == cid), None)
            try:
                answer = await asyncio.to_thread(delete_post, self.svc, name) if name else "video is gone"
            except Exception as exc:  # noqa: BLE001 - tell the phone, keep polling
                answer = str(getattr(exc, "message", exc))[:190]
            data = await asyncio.to_thread(overview, self.svc)
            text, markup = handsboard.channel(data, platform, cfg)
            await self.edit(chat, message, text, markup)
        elif kind == "apprq":
            count = len(handsboard.targets(data, cid, platform, cfg))
            text, markup = handsboard.confirm(count, cid, platform) if count else ("Nothing to approve.", {
                "inline_keyboard": [[{"text": "‹ Back", "callback_data": "status"}]]})
            await self.edit(chat, message, text, markup)
        elif kind == "appr":
            done = failed = 0
            for name, pid in handsboard.targets(data, cid, platform, cfg):
                try:
                    await asyncio.to_thread(trigger, self.svc, name, pid)
                    done += 1
                except Exception:  # noqa: BLE001 - count it, go on
                    failed += 1
            answer = f"{done} queued" + (f", {failed} failed" if failed else "")
            if cid == "all":
                await self.dashboard(chat, message)
            else:
                text, markup = handsboard.channel(await asyncio.to_thread(overview, self.svc), cid, cfg)
                await self.edit(chat, message, text, markup)
        else:
            await self.dashboard(chat, message)
        with contextlib.suppress(httpx.HTTPStatusError):  # "query is too old" after a slow step
            await self.call("answerCallbackQuery", callback_query_id=cb["id"], text=answer[:190])

    async def postq_tap(self, chat: int, message: int, video: dict, cid: str, pid: str) -> None:
        try:
            result = await asyncio.to_thread(postq_episode, video["folder"], pid)
        except Exception as exc:  # noqa: BLE001 - tell the phone, keep polling
            result = f"{pid}: {exc}"
        log.info("postq %s %s: %s", pid, video["name"], result)
        await self.call("sendMessage", chat_id=chat, text=f"{(video['title'] or video['name'])[:80]}\n{result}")
        text, markup = handsboard.channel(await asyncio.to_thread(overview, self.svc), cid, handsboard.config(self.svc))
        await self.edit(chat, message, text, markup)

    async def pick_model(self, chat: int, message: int | None = None) -> None:
        now = self.ai.current()
        row = [{"text": ("✅ " if p.id == now.id else "") + p.label, "callback_data": f"model:{p.id}"}
               for p in self.ai.providers()]
        params = {"chat_id": chat, "text": f"AI model: {now.label} ({now.model})\nWrite a message to chat with it.",
                  "reply_markup": {"inline_keyboard": [row]}}
        if message:
            with contextlib.suppress(httpx.HTTPStatusError):
                await self.call("editMessageText", message_id=message, **params)
        else:
            await self.call("sendMessage", **params)

    async def send_media(self, chat: int, answer: str) -> str:
        """Upload every ``MEDIA: <path>`` file the AI named; return the answer without those lines."""
        keep = []
        for line in answer.splitlines():
            m = re.match(r"\s*MEDIA:\s*(.+?)\s*$", line)
            if not m:
                keep.append(line)
                continue
            path = Path(m.group(1))
            size = await asyncio.to_thread(_size, path)
            if not size or size > 50_000_000:
                keep.append(f"(file not sent: {path.name})")
                continue
            kind = {"video": "sendVideo", "image": "sendPhoto"}.get(
                (mimetypes.guess_type(path.name)[0] or "").split("/")[0], "sendDocument")
            field = {"sendVideo": "video", "sendPhoto": "photo"}.get(kind, "document")
            r = await self.http.post(f"{self.base}/{kind}", data={"chat_id": str(chat)},
                                     files={field: (path.name, await asyncio.to_thread(path.read_bytes))}, timeout=300)
            if not r.is_success:
                keep.append(f"(upload failed: {path.name})")
        return "\n".join(keep).strip()

    async def chat(self, chat: int, text: str) -> None:
        turns = self.history.setdefault(chat, [])
        turns.append(("user", text))
        del turns[:-20]
        try:
            provider, answer = await self.ai.reply(turns)
        except Exception as exc:  # noqa: BLE001 - say why on the phone
            turns.pop()
            answer, provider = f"⚠️ {getattr(exc, 'message', exc)}"[:900], None
        else:
            turns.append(("assistant", answer))
            try:
                answer = await self.send_media(chat, answer) or "✅ Done."
            except Exception:  # noqa: BLE001 - the text answer still goes out
                log.exception("telegram media upload failed")
        footer = f"\n\n— {provider.label}" if provider else ""
        for i in range(0, max(len(answer), 1), 3900):  # Telegram caps a message at 4096 characters
            last = i + 3900 >= len(answer)
            await self.call("sendMessage", chat_id=chat, text=answer[i:i + 3900] + (footer if last else ""))

    async def handle(self, update: dict) -> None:
        if msg := update.get("message"):
            chat = msg["chat"]["id"]
            if chat not in self.allowed:
                log.warning("telegram: ignored chat %s", chat)
                await self.call("sendMessage", chat_id=chat,
                                text=f"Not allowed. Chat id {chat}: add it to MUSE2API_TELEGRAM_CHAT_IDS.")
                return
            text = (msg.get("text") or "").strip()
            word = text.split()[0].lower().lstrip("/").split("@")[0] if text else ""
            args = text.split()[1:]
            if word in ("status", "start", "dashboard"):
                await self.dashboard(chat)
            elif word == "approve":
                await self.approve_cmd(chat, args)
            elif word == "postq":
                await self.call("sendMessage", chat_id=chat, text=handsboard.queue(await asyncio.to_thread(overview, self.svc)))
            elif word == "tasks":
                await self.call("sendMessage", chat_id=chat, text=tasks_text(self.svc))
            elif word == "job":
                await self.call("sendMessage", chat_id=chat, text=job_text(self.svc, args[0] if args else None))
            elif word == "cancel":
                await self.call("sendMessage", chat_id=chat, text=await cancel_task(self.svc, args[0] if args else None))
            elif word in ("posts", "list"):
                await self.show(chat)
            elif text.startswith("/model"):
                await self.pick_model(chat)
            elif text.startswith("/new"):
                self.history.pop(chat, None)
                self.ai.new_session()
                await self.call("sendMessage", chat_id=chat, text="New conversation.")
            elif text and not text.startswith("/"):
                now = self.ai.current()
                if now.agent:  # may run for minutes: keep the bot answering meanwhile
                    await self.call("sendMessage", chat_id=chat, text=f"⏳ {now.label} is on it…")
                    task = asyncio.create_task(self.chat(chat, text))
                    self.running.add(task)
                    task.add_done_callback(self.running.discard)
                else:
                    await self.chat(chat, text)
            else:
                await self.call("sendMessage", chat_id=chat,
                                text=HELP)
        elif cb := update.get("callback_query"):
            chat = cb["message"]["chat"]["id"]
            if chat not in self.allowed:
                return
            kind, _, rest = cb["data"].partition(":")
            answer = ""
            if kind == "noop":
                await self.call("answerCallbackQuery", callback_query_id=cb["id"])
                return
            if kind in ("status", "ch", "apprq", "appr", "delq", "delc", "pk", "pp", "px"):
                await self.board_tap(chat, cb, kind, rest)
                return
            if kind == "model":
                try:
                    answer = f"Now: {self.ai.choose(rest).label}"
                except InvalidRequest as exc:
                    answer = exc.message[:190]
                await self.call("answerCallbackQuery", callback_query_id=cb["id"], text=answer)
                await self.pick_model(chat, cb["message"]["message_id"])
                return
            if kind in ("post", "retry", "delete"):
                vid, _, platform = rest.partition(":")
                overview_data = await asyncio.to_thread(overview, self.svc)
                name = next((v["name"] for v in overview_data["videos"] if v["id"] == vid), None)
                try:
                    if not name:
                        raise InvalidRequest("video is gone: refresh the list")
                    if kind == "delete":
                        answer = await asyncio.to_thread(delete_post, self.svc, name)
                    else:
                        answer = await asyncio.to_thread(trigger, self.svc, name, platform)
                except Exception as exc:  # noqa: BLE001 - tell the phone, keep polling
                    answer = str(getattr(exc, "message", exc))[:190]
            await self.call("answerCallbackQuery", callback_query_id=cb["id"], text=answer)
            if kind == "list" or cb["message"].get("text", "").startswith(("🗂", "📭")):
                await self.show(chat, cb["message"]["message_id"])
            else:  # an alert: show what the tap did, drop its buttons
                await self.call("editMessageText", chat_id=chat, message_id=cb["message"]["message_id"],
                                text=f"{cb['message'].get('text', '')}\n\n→ {answer}")

    async def alert(self, svc: Services, done: list[tuple[str, str, str]]) -> None:
        """Tell every allowed chat what the last auto-post pass did. A failure comes with buttons."""
        for name, platform, result in done:
            if (text := alert_text(name, platform, result, svc)) is None:
                continue
            body, buttons = text
            for chat in self.allowed:
                await self.call("sendMessage", chat_id=chat, text=body,
                                reply_markup={"inline_keyboard": buttons} if buttons else {})

    async def poll_once(self) -> None:
        updates = await self.call("getUpdates", offset=self.offset, timeout=50,
                                  allowed_updates=["message", "callback_query"])
        for u in updates:
            self.offset = u["update_id"] + 1
            try:
                await self.handle(u)
            except Exception:  # noqa: BLE001 - one bad update must not stop the bot
                log.exception("telegram update failed")


async def telegram_loop(svc: Services) -> None:
    bot = Bot(svc)
    with contextlib.suppress(Exception):
        await bot.call("setMyCommands", commands=[
            {"command": "status", "description": "Dashboard: what is left to post"},
            {"command": "approve", "description": "Post queued videos now"},
            {"command": "posts", "description": "Every video"},
            {"command": "postq", "description": "Auto-post status"},
            {"command": "tasks", "description": "Last renders"},
            {"command": "model", "description": "Pick the AI that answers (ChatGPT / Claude / Muse)"},
            {"command": "new", "description": "Start a new conversation"}])
    autopost.listeners.append(bot.alert)
    log.info("telegram bot polling for %d chat(s)", len(bot.allowed))
    while True:
        try:
            await bot.poll_once()
        except asyncio.CancelledError:
            autopost.listeners.remove(bot.alert)
            raise
        except Exception as exc:  # noqa: BLE001 - network blips: retry
            log.warning("telegram poll failed: %s", exc)
            await asyncio.sleep(5)


def keep_awake() -> subprocess.Popen | None:
    """macOS: hold off idle and (on power) system sleep for as long as this server runs. The laptop
    must stay awake for Muse Hands to post; the display may sleep."""
    if sys.platform != "darwin":
        return None
    try:
        return subprocess.Popen(["caffeinate", "-i", "-s", "-m", "-w", str(os.getpid())])
    except OSError:
        log.warning("caffeinate not available: the laptop may sleep")
        return None
