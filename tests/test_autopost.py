"""Auto-post: rules plan new queued videos, the publisher posts them through the mock driver."""

from __future__ import annotations

import asyncio
import json
import os
import time
import types
from datetime import datetime, timedelta

import httpx
import pytest

from museai.api.routes import autopost, posting
from museai.services.publishers import Job, PublishError
from museai.services.publishers.meta import FacebookPublisher, InstagramPublisher
from museai.services.publishers.mock import MockCrash, MockPublisher
from museai.services.publishers.tiktok import TikTokPublisher, chunks
from museai.services.publishers.youtube import YouTubePublisher

CHINESE = "Tiếng Trung mỗi ngày 44 - Đi chợ.mp4"
RULE = {"id": "chinese", "name": "Chinese lessons", "source": "everyday-chinese",
        "platforms": ["tiktok", "youtube"], "captions": {"tiktok": "{caption} #học_tiếng_trung"}}


def drop(settings, name: str, captions: dict | None = None, age: float = 3600) -> None:
    """Deliver a video to the posting folder, ``age`` seconds old (past the copy-in settle time)."""
    settings.post_dir.mkdir(exist_ok=True)
    path = settings.post_dir / name
    path.write_bytes(b"video")
    os.utime(path, (time.time() - age, time.time() - age))
    if captions:
        state = json.loads(settings.posts_file.read_text()) if settings.posts_file.exists() else {}
        state.setdefault(name, {})["captions"] = captions
        settings.posts_file.write_text(json.dumps(state, ensure_ascii=False))


def plan_of(client, admin, name: str) -> dict:
    rows = client.get("/dashboard/autopost", headers=admin).json()["plan"]
    return next(r for r in rows if r["name"] == name)


def run(svc, at: datetime):
    return asyncio.run(autopost.tick(svc, at))


def due(row: dict) -> datetime:
    """Just after the last job of the plan row is due."""
    return max(datetime.fromisoformat(j["time"]) for j in row["jobs"]) + timedelta(minutes=1)


@pytest.fixture
def svc(client):
    return client.app.state.services


@pytest.fixture
def no_trash(monkeypatch):
    monkeypatch.setattr(posting, "_trash", lambda p: p.unlink())


def test_rules_validate_and_save(client, admin):
    assert client.put("/dashboard/autopost/rules", headers=admin,
                      json={"rules": [{**RULE, "platforms": ["myspace"]}]}).status_code == 400
    assert client.put("/dashboard/autopost/rules", headers=admin,
                      json={"rules": [{**RULE, "schedule": "fixed", "times": ["25:00"]}]}).status_code == 400
    assert client.put("/dashboard/autopost/rules", headers=admin,
                      json={"rules": [RULE, RULE]}).status_code == 400
    assert client.put("/dashboard/autopost/rules", headers=admin, json={"rules": [RULE]}).status_code == 200
    d = client.get("/dashboard/autopost", headers=admin).json()
    assert [r["id"] for r in d["rules"]] == ["chinese"]
    assert {s["id"] for s in d["sources"]} >= {"scenic-drop-reel", "everyday-chinese", "teaching-video"}
    assert d["redirect_uri"].endswith("/dashboard/autopost/oauth/callback")


def test_new_video_is_planned_on_its_slot(client, admin, settings):
    client.put("/dashboard/autopost/rules", headers=admin, json={"rules": [
        RULE, {"id": "travel", "source": "scenic-drop-reel", "channel": "travel", "platforms": ["youtube"]}]})
    drop(settings, CHINESE, {"tiktok": "Học đi chợ", "youtube": "Đi chợ\n\nBài 44"})
    drop(settings, "reel-norway.mp4")
    drop(settings, "random clip.mp4")
    d = client.get("/dashboard/autopost", headers=admin).json()
    assert d["unplanned"] == ["random clip.mp4"]
    row = plan_of(client, admin, CHINESE)
    assert row["rule"] == "chinese" and row["channel"] == "chinese"
    jobs = {j["platform"]: j for j in row["jobs"]}
    assert set(jobs) == {"tiktok", "youtube"}
    card = next(v for v in client.get("/dashboard/posts", headers=admin).json()["videos"] if v["name"] == CHINESE)
    assert jobs["youtube"]["time"] == card["schedule"]["youtube"]  # the queue's own slot time
    assert jobs["tiktok"]["time"] == card["schedule"]["tiktok"]
    assert jobs["tiktok"]["caption"] == "Học đi chợ #học_tiếng_trung"
    assert jobs["youtube"]["caption"] == "Đi chợ\n\nBài 44"
    assert plan_of(client, admin, "reel-norway.mp4")["channel"] == "travel"


def test_publisher_posts_when_due_and_ticks_the_queue(client, admin, settings, svc):
    client.put("/dashboard/autopost/rules", headers=admin, json={"rules": [RULE]})
    drop(settings, CHINESE, {"tiktok": "Học đi chợ", "youtube": "Đi chợ\n\nBài 44"})
    row = plan_of(client, admin, CHINESE)
    early = min(datetime.fromisoformat(j["time"]) for j in row["jobs"]) - timedelta(minutes=5)
    assert run(svc, early) == []
    ran = [r for at in sorted({datetime.fromisoformat(j["time"]) for j in row["jobs"]})
           for r in run(svc, at + timedelta(minutes=1))]  # each platform at its own time
    assert sorted(ran) == [(CHINESE, "tiktok", "posted"), (CHINESE, "youtube", "posted")]
    assert run(svc, due(row)) == []  # nothing twice
    for p in ("tiktok", "youtube"):
        assert len(svc.publishers[p].posts) == 1
    assert svc.publishers["tiktok"].posts[0]["caption"] == "Học đi chợ #học_tiếng_trung"
    jobs = {j["platform"]: j for j in plan_of(client, admin, CHINESE)["jobs"]}
    assert jobs["youtube"]["state"] == "posted" and jobs["youtube"]["url"].startswith("mock://youtube/")
    card = next(v for v in client.get("/dashboard/posts", headers=admin).json()["videos"] if v["name"] == CHINESE)
    assert set(card["posted"]) == {"tiktok", "youtube"}  # the queue's own posted ticks
    assert card["auto"] == {"tiktok": "posted", "youtube": "posted"}


def test_all_platforms_posted_trashes_through_done_flow(client, admin, settings, svc, no_trash):
    client.put("/dashboard/autopost/rules", headers=admin, json={"rules": [{**RULE, "platforms": list(autopost.AUTO_PLATFORMS)}]})
    drop(settings, CHINESE, {"tiktok": "a", "youtube": "a", "facebook": "a", "instagram": "a"})
    for p in ("x", "threads"):  # posted by hand
        client.post(f"/dashboard/posts/{CHINESE}", headers=admin, json={"platform": p})
    for at in sorted({datetime.fromisoformat(j["time"]) for j in plan_of(client, admin, CHINESE)["jobs"]}):
        run(svc, at + timedelta(minutes=1))  # the publisher ticks all day: each platform at its own time
    assert not (settings.post_dir / CHINESE).exists()
    state = json.loads(settings.posts_file.read_text())
    assert state[CHINESE]["done"]  # the slot stays booked, like a manual post


def test_restart_mid_post_never_posts_twice(client, admin, settings, svc):
    from museai.app import create_app
    from museai.drivers.mock import MockDriver

    client.put("/dashboard/autopost/rules", headers=admin, json={"rules": [{**RULE, "platforms": ["youtube"]}]})
    drop(settings, CHINESE, {"youtube": "Đi chợ"})
    row = plan_of(client, admin, CHINESE)
    remote = settings.data_dir / "autopost-mock.json"
    svc.publishers["youtube"] = MockPublisher("youtube", remote, crash_after_publish=True)
    with pytest.raises(MockCrash):  # the process dies after the platform published
        run(svc, due(row))
    assert json.loads(settings.posts_file.read_text())[CHINESE]["auto"]["jobs"]["youtube"]["state"] == "posting"

    fresh = create_app(settings, MockDriver(delay=0)).state.services  # the server comes back
    assert run(fresh, due(row)) == [(CHINESE, "youtube", "posted")]
    assert len(fresh.publishers["youtube"].posts) == 1


def test_failed_post_retries_then_stops(client, admin, settings, svc):
    client.put("/dashboard/autopost/rules", headers=admin, json={"rules": [{**RULE, "platforms": ["tiktok"]}]})
    drop(settings, CHINESE, {"tiktok": "Học"})
    at = due(plan_of(client, admin, CHINESE))
    svc.publishers["tiktok"].fail = 1
    assert run(svc, at) == [(CHINESE, "tiktok", "retry")]
    job = plan_of(client, admin, CHINESE)["jobs"][0]
    assert job["state"] == "retry" and "unavailable" in job["error"] and job["next_try"] > at.timestamp()
    assert run(svc, at) == []  # waits for the back-off
    assert run(svc, at + timedelta(minutes=2)) == [(CHINESE, "tiktok", "posted")]

    class Rejects(MockPublisher):
        async def publish(self, job, checkpoint, save):
            raise PublishError("bad file", retry=False)

    drop(settings, "Tiếng Trung mỗi ngày 45 - Hỏi đường.mp4", {"tiktok": "x"})
    svc.publishers["tiktok"] = Rejects("tiktok", settings.data_dir / "m.json")
    row = plan_of(client, admin, "Tiếng Trung mỗi ngày 45 - Hỏi đường.mp4")
    assert run(svc, due(row)) == [("Tiếng Trung mỗi ngày 45 - Hỏi đường.mp4", "tiktok", "error")]


def test_pause_override_and_post_now(client, admin, settings, svc):
    client.put("/dashboard/autopost/rules", headers=admin, json={"rules": [{**RULE, "platforms": ["tiktok"]}]})
    drop(settings, CHINESE, {"tiktok": "Học"})
    at = due(plan_of(client, admin, CHINESE))
    client.post("/dashboard/autopost/pause", headers=admin, json={"paused": True})
    assert run(svc, at) == []
    client.post("/dashboard/autopost/pause", headers=admin, json={"paused": False})
    client.post(f"/dashboard/autopost/plan/{CHINESE}", headers=admin, json={"paused": True})
    assert run(svc, at) == []
    client.post(f"/dashboard/autopost/plan/{CHINESE}", headers=admin, json={"paused": False})

    later = (at + timedelta(days=2)).replace(microsecond=0)
    client.post(f"/dashboard/autopost/plan/{CHINESE}", headers=admin, json={"times": {"tiktok": later.isoformat()}})
    job = plan_of(client, admin, CHINESE)["jobs"][0]
    assert job["override"] and datetime.fromisoformat(job["time"]) == later
    assert run(svc, at) == []
    client.post(f"/dashboard/autopost/plan/{CHINESE}", headers=admin, json={"retry": "tiktok"})  # Post now
    assert run(svc, datetime.now(posting.TZ) + timedelta(seconds=5)) == [(CHINESE, "tiktok", "posted")]

    drop(settings, "Tiếng Trung mỗi ngày 46 - Mua vé.mp4", {"tiktok": "x"})
    client.post("/dashboard/autopost/plan/Tiếng Trung mỗi ngày 46 - Mua vé.mp4", headers=admin, json={"off": True})
    assert "Tiếng Trung mỗi ngày 46 - Mua vé.mp4" not in [r["name"] for r in client.get(
        "/dashboard/autopost", headers=admin).json()["plan"]]


def test_unconnected_account_and_missed_time(client, admin, settings, svc):
    svc.settings.autopost_mock = False  # real tokens needed: none connected
    client.put("/dashboard/autopost/rules", headers=admin, json={"rules": [{**RULE, "platforms": ["tiktok"]}]})
    drop(settings, CHINESE, {"tiktok": "Học"})
    at = due(plan_of(client, admin, CHINESE))
    assert run(svc, at) == [(CHINESE, "tiktok", "needs_account")]
    assert "connect a TikTok account" in plan_of(client, admin, CHINESE)["jobs"][0]["error"]
    run(svc, at + timedelta(hours=3))  # never connected: no burst of late posts later
    assert plan_of(client, admin, CHINESE)["jobs"][0]["state"] == "missed"


def test_fixed_times_book_the_next_free_one(client, admin, settings):
    client.put("/dashboard/autopost/rules", headers=admin, json={"rules": [
        {**RULE, "schedule": "fixed", "times": ["09:00"]}]})
    drop(settings, CHINESE, {"tiktok": "a"}, age=7200)
    drop(settings, "Tiếng Trung mỗi ngày 45 - Hỏi đường.mp4", {"tiktok": "b"}, age=3600)
    a = plan_of(client, admin, CHINESE)["jobs"][0]["time"]
    b = plan_of(client, admin, "Tiếng Trung mỗi ngày 45 - Hỏi đường.mp4")["jobs"][0]["time"]
    assert a.endswith("T09:00:00+07:00") and b.endswith("T09:00:00+07:00") and a != b


def test_oauth_connect_stores_tokens_server_side(client, admin, settings, svc):
    assert client.get("/dashboard/autopost/oauth/tiktok/start?channel=chinese", headers=admin,
                      follow_redirects=False).status_code == 400  # no developer app yet
    settings.tiktok_client_key, settings.tiktok_client_secret = "ck", "cs"
    r = client.get("/dashboard/autopost/oauth/tiktok/start?channel=chinese", headers=admin, follow_redirects=False)
    assert r.status_code == 307 and r.headers["location"].startswith("https://www.tiktok.com/v2/auth/authorize/")
    state = httpx.URL(r.headers["location"]).params["state"]

    def tiktok(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/v2/oauth/token/":
            return httpx.Response(200, json={"access_token": "SECRET-AT", "refresh_token": "SECRET-RT",
                                             "expires_in": 86400, "open_id": "o"})
        return httpx.Response(200, json={"data": {"user": {"display_name": "Tiếng Trung", "username": "ttmn"}}})

    svc.oauth.http = httpx.AsyncClient(transport=httpx.MockTransport(tiktok))
    assert client.get("/dashboard/autopost/oauth/callback?state=bad&code=c", follow_redirects=False) \
        .headers["location"].startswith("/dashboard#autopost&msg=sign-in%20expired")
    r = client.get(f"/dashboard/autopost/oauth/callback?state={state}&code=c", follow_redirects=False)
    assert "connected" in r.headers["location"]
    page = client.get("/dashboard/autopost", headers=admin).text
    assert "Tiếng Trung" in page and "SECRET" not in page
    assert oct(settings.data_dir.joinpath("oauth.json").stat().st_mode & 0o777) == "0o600"
    tok = asyncio.run(svc.oauth.token("chinese", "tiktok"))
    assert tok["access_token"] == "SECRET-AT" and tok["username"] == "ttmn"


# --- real drivers against a fake platform (request shapes, resume after a restart) ---

class Fake:
    def __init__(self, handler):
        self.calls: list[httpx.Request] = []
        self.handler = handler

    def __call__(self, req: httpx.Request) -> httpx.Response:
        self.calls.append(req)
        return self.handler(req)

    @property
    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(self))


def job(tmp_path, platform: str, token: dict, caption: str = "Title\n\nBody") -> Job:
    video = tmp_path / "v.mp4"
    video.write_bytes(b"0123456789")
    return Job(video=video, platform=platform, caption=caption, token=token)


def saver():
    saved: list[dict] = []

    async def save(cp: dict) -> None:
        saved.append(dict(cp))

    return saved, save


async def test_youtube_uploads_and_resumes_a_finished_session(tmp_path):
    def yt(req):
        if req.method == "POST":
            assert json.loads(req.content)["snippet"] == {"title": "Title", "description": "Body", "categoryId": "22"}
            return httpx.Response(200, headers={"Location": "https://upload.example/s1"})
        if req.headers.get("content-range") == "bytes */10":
            return httpx.Response(200, json={"id": "done1"})
        return httpx.Response(201, json={"id": "vid1"})

    fake = Fake(yt)
    saved, save = saver()
    res = await YouTubePublisher(fake.client).publish(job(tmp_path, "youtube", {"access_token": "t"}), {}, save)
    assert res.url == "https://youtube.com/shorts/vid1" and saved[0] == {"session": "https://upload.example/s1"}
    fake.calls.clear()
    res = await YouTubePublisher(fake.client).publish(
        job(tmp_path, "youtube", {"access_token": "t"}), {"session": "https://upload.example/s1"}, save)
    assert res.id == "done1" and len(fake.calls) == 1  # asked the session, uploaded nothing


async def test_tiktok_direct_post_and_resume(tmp_path):
    def tt(req):
        path = req.url.path
        if path.endswith("creator_info/query/"):
            return httpx.Response(200, json={"data": {"privacy_level_options": ["SELF_ONLY"]}, "error": {"code": "ok"}})
        if path.endswith("video/init/"):
            body = json.loads(req.content)
            assert body["post_info"]["privacy_level"] == "SELF_ONLY"  # unaudited app
            assert body["source_info"] == {"source": "FILE_UPLOAD", "video_size": 10, "chunk_size": 10,
                                           "total_chunk_count": 1}
            return httpx.Response(200, json={"data": {"publish_id": "p1", "upload_url": "https://up.example/u"},
                                             "error": {"code": "ok"}})
        if path.endswith("status/fetch/"):
            return httpx.Response(200, json={"data": {"status": "PUBLISH_COMPLETE",
                                                      "publicaly_available_post_id": [777]}, "error": {"code": "ok"}})
        assert req.headers["content-range"] == "bytes 0-9/10"
        return httpx.Response(201)

    fake = Fake(tt)
    saved, save = saver()
    tok = {"access_token": "t", "username": "ttmn"}
    res = await TikTokPublisher(fake.client).publish(job(tmp_path, "tiktok", tok), {}, save)
    assert res.url == "https://www.tiktok.com/@ttmn/video/777" and saved == [{"publish_id": "p1"}]
    fake.calls.clear()
    await TikTokPublisher(fake.client).publish(job(tmp_path, "tiktok", tok), {"publish_id": "p1"}, save)
    assert [c.url.path for c in fake.calls] == ["/v2/post/publish/status/fetch/"]
    assert chunks(150 * 2**20)[-1] == (14 * 10 * 2**20, 150 * 2**20 - 1)  # remainder joins the last chunk


async def test_facebook_reel_and_resume_after_publish(tmp_path):
    def fb(req):
        if req.url.host == "rupload.facebook.com":
            assert req.headers["authorization"] == "OAuth pt" and req.headers["file_size"] == "10"
            return httpx.Response(200, json={"success": True})
        if req.method == "GET":
            return httpx.Response(200, json={"status": {"publishing_phase": {"status": "complete"}}})
        form = dict(httpx.QueryParams(req.content.decode()))
        if form["upload_phase"] == "start":
            return httpx.Response(200, json={"video_id": "v9"})
        assert form["video_state"] == "PUBLISHED" and form["description"] == "Hi"
        return httpx.Response(200, json={"success": True})

    fake = Fake(fb)
    saved, save = saver()
    tok = {"page_id": "pg", "access_token": "pt"}
    res = await FacebookPublisher(fake.client).publish(job(tmp_path, "facebook", tok, "Hi"), {}, save)
    assert res.url == "https://www.facebook.com/reel/v9" and saved[-1]["finishing"]
    fake.calls.clear()
    await FacebookPublisher(fake.client).publish(job(tmp_path, "facebook", tok, "Hi"), saved[-1], save)
    assert [c.method for c in fake.calls] == ["GET"]  # already up: not finished again


async def test_instagram_reel_waits_for_processing(tmp_path):
    states = iter(["IN_PROGRESS", "FINISHED"])

    def ig(req):
        if req.url.host == "rupload.facebook.com":
            return httpx.Response(200, json={"success": True})
        if req.url.path.endswith("/media"):
            assert dict(httpx.QueryParams(req.content.decode()))["media_type"] == "REELS"
            return httpx.Response(200, json={"id": "c1", "uri": "https://rupload.facebook.com/ig-api-upload/x/c1"})
        if req.url.path.endswith("/media_publish"):
            return httpx.Response(200, json={"id": "m1"})
        if req.url.path.endswith("/c1"):
            return httpx.Response(200, json={"status_code": next(states)})
        return httpx.Response(200, json={"permalink": "https://www.instagram.com/reel/abc/"})

    pub = InstagramPublisher(Fake(ig).client)
    pub.poll_every = 0
    saved, save = saver()
    res = await pub.publish(job(tmp_path, "instagram", {"ig_user_id": "u", "access_token": "pt"}), {}, save)
    assert res.url == "https://www.instagram.com/reel/abc/" and saved[-1]["publishing"]


# --- Muse Hands ---

def test_hands_lists_and_posts_now(client, admin, settings):
    from museai.api.routes import hands

    drop(settings, CHINESE, captions={"youtube": "Đi chợ\nmore", "tiktok": "x"})
    autopost.save_config(client.app.state.services, False, [autopost.Rule(**RULE)])
    data = client.get("/dashboard/hands/data", headers=admin).json()
    video = next(v for v in data["videos"] if v["name"] == CHINESE)
    assert video["title"] == "Đi chợ" and video["planned"]
    states = {p["id"]: p["state"] for p in video["platforms"]}
    assert states["youtube"] == "scheduled" and states["facebook"] == "manual"

    res = client.post("/dashboard/hands/post", json={"name": CHINESE, "platform": "youtube"}, headers=admin)
    assert res.status_code == 200 and "youtube posting within" in res.json()["message"]
    assert plan_of(client, admin, CHINESE)["jobs"][0]["state"] in ("retry", "scheduled")
    assert client.post("/dashboard/hands/post", json={"name": "nope.mp4", "platform": "youtube"},
                       headers=admin).status_code == 404

    text, markup = hands.render(client.get("/dashboard/hands/data", headers=admin).json())
    buttons = [b["callback_data"] for row in markup["inline_keyboard"] for b in row]
    assert f"post:{video['id']}:youtube" in buttons and "list" in buttons
    assert all(len(b.encode()) <= 64 for b in buttons)


def test_hands_bot_ignores_strangers_and_triggers(client, admin, settings):
    from museai.api.routes import hands

    drop(settings, CHINESE, captions={"youtube": "t", "tiktok": "x"})
    svc = client.app.state.services
    autopost.save_config(svc, False, [autopost.Rule(**RULE)])
    settings.telegram_bot_token, settings.telegram_chat_ids = "T", "42"
    sent = []

    class Http:
        async def post(self, url, json):
            sent.append((url.rsplit("/", 1)[1], json))
            return httpx.Response(200, json={"ok": True, "result": []}, request=httpx.Request("POST", url))

    bot = hands.Bot(svc, Http())
    vid = next(v["id"] for v in client.get("/dashboard/hands/data", headers=admin).json()["videos"])
    asyncio.run(bot.handle({"message": {"chat": {"id": 7}, "text": "/posts"}}))
    assert [m for m, _ in sent] == ["sendMessage"] and "Not allowed" in sent[0][1]["text"]
    sent.clear()
    asyncio.run(bot.handle({"callback_query": {"id": "c", "data": f"post:{vid}:tiktok",
                                               "message": {"chat": {"id": 42}, "message_id": 5}}}))
    assert [m for m, _ in sent] == ["answerCallbackQuery", "editMessageText"]
    assert "tiktok posting within" in sent[0][1]["text"]


def test_hands_alerts_failure_with_buttons(client, admin, settings, monkeypatch):
    from museai.api.routes import hands

    drop(settings, CHINESE, captions={"youtube": "t", "tiktok": "x"})
    svc = client.app.state.services
    autopost.save_config(svc, False, [autopost.Rule(**RULE)])
    settings.telegram_bot_token, settings.telegram_chat_ids = "T", "42"
    sent = []

    class Http:
        async def post(self, url, json):
            sent.append((url.rsplit("/", 1)[1], json))
            return httpx.Response(200, json={"ok": True, "result": []}, request=httpx.Request("POST", url))

    bot = hands.Bot(svc, Http())
    client.get("/dashboard/hands/data", headers=admin)
    autopost._job(svc, posting._key(CHINESE), "youtube", state="error", error="quota exceeded", attempts=6)
    asyncio.run(bot.alert(svc, [(CHINESE, "youtube", "error"), (CHINESE, "tiktok", "waiting")]))
    assert len(sent) == 1 and "quota exceeded" in sent[0][1]["text"]
    data = [b["callback_data"] for row in sent[0][1]["reply_markup"]["inline_keyboard"] for b in row]
    assert [d.split(":")[0] for d in data] == ["retry", "delete"]
    assert all(len(d.encode()) <= 64 for d in data)

    sent.clear()
    def cb(d):
        return {"callback_query": {"id": "c", "data": d,
                                   "message": {"chat": {"id": 42}, "message_id": 5, "text": "❌"}}}

    asyncio.run(bot.handle(cb(data[0])))
    assert "youtube posting within" in sent[0][1]["text"] and sent[1][0] == "editMessageText"
    trashed = []
    monkeypatch.setattr(posting, "_trash", trashed.append)
    asyncio.run(bot.handle(cb(data[1])))
    assert trashed and trashed[-1].name == CHINESE  # loose in the posting folder: just the video

    folder = settings.post_dir / "Episode 45"
    folder.mkdir()
    (folder / "45.mp4").write_bytes(b"v")
    (folder / "notes.txt").write_text("x")
    (folder / posting.FOLDER_MARK).write_text("")
    os.utime(folder / "45.mp4", (time.time() - 3600,) * 2)
    trashed.clear()
    asyncio.run(bot.handle(cb(f"delete:{hands._short('45.mp4')}")))
    assert len(trashed) == 1 and trashed[0].parent == settings.post_dir and trashed[0].name.endswith("· 45")


def test_hands_chat_models(client, settings):
    from museai.api.routes import hands

    settings.telegram_bot_token, settings.telegram_chat_ids = "T", "42"
    settings.openai_api_key, settings.anthropic_api_key = "ok", "ak"
    settings.codex_bin = settings.claude_bin = "no-such-cli"
    svc = client.app.state.services
    sent, calls = [], []

    class Http:
        async def post(self, url, json=None, headers=None):
            calls.append((url, json))
            if "api.telegram.org" in url:
                sent.append((url.rsplit("/", 1)[1], json))
                return httpx.Response(200, json={"ok": True, "result": []}, request=httpx.Request("POST", url))
            body = ({"choices": [{"message": {"content": "from gpt"}}]} if "openai" in url
                    else {"content": [{"type": "text", "text": "from claude"}]})
            return httpx.Response(200, json=body, request=httpx.Request("POST", url))

    bot = hands.Bot(svc, Http())
    say = lambda t: asyncio.run(bot.handle({"message": {"chat": {"id": 42}, "text": t}}))  # noqa: E731
    tap = lambda d: asyncio.run(bot.handle({"callback_query": {  # noqa: E731
        "id": "c", "data": d, "message": {"chat": {"id": 42}, "message_id": 9, "text": "m"}}}))

    say("/model")
    labels = [b["text"] for b in sent[-1][1]["reply_markup"]["inline_keyboard"][0]]
    assert labels == ["✅ ChatGPT", "Claude", "Muse"]  # nothing chosen yet: the first available is current
    tap("model:claude")
    say("hello")
    assert sent[-1][1]["text"] == "from claude\n\n— Claude"
    ai = [c for c in calls if "telegram" not in c[0]]
    assert ai[-1][0].startswith("https://api.anthropic.com") and ai[-1][1]["messages"][-1]["content"] == "hello"
    tap("model:chatgpt")
    say("again")
    assert sent[-1][1]["text"].startswith("from gpt")
    ai = [c for c in calls if "telegram" not in c[0]]
    assert [m["role"] for m in ai[-1][1]["messages"]] == ["system", "user", "assistant", "user"]
    assert hands.ChatBots(settings, svc.gateway).current().id == "chatgpt"  # survives a restart
    settings.openai_api_key = ""
    tap("model:chatgpt")  # key gone: refused, not switched
    assert bot.ai.current().id == "claude"


def test_hands_status_dashboard_and_approve(client, admin, settings, monkeypatch):
    from museai.api.routes import hands

    drop(settings, CHINESE, captions={"youtube": "t", "tiktok": "x"})
    svc = client.app.state.services
    autopost.save_config(svc, False, [autopost.Rule(**RULE)])
    settings.telegram_bot_token, settings.telegram_chat_ids = "T", "42"
    sent = []

    class Http:
        async def post(self, url, json):
            sent.append((url.rsplit("/", 1)[1], json))
            return httpx.Response(200, json={"ok": True, "result": []}, request=httpx.Request("POST", url))

    bot = hands.Bot(svc, Http())

    def msg(text):
        asyncio.run(bot.handle({"message": {"chat": {"id": 42}, "text": text}}))

    def tap(data):
        asyncio.run(bot.handle({"callback_query": {"id": "c", "data": data,
                                                   "message": {"chat": {"id": 42}, "message_id": 5}}}))

    def last_edit():
        return [j for m, j in sent if m == "editMessageText"][-1]

    def btns(j):
        return [b["callback_data"] for row in j["reply_markup"]["inline_keyboard"] for b in row]

    msg("/status")  # one message: a button per channel, nothing else
    assert [m for m, _ in sent] == ["sendMessage"]
    buttons = btns(sent[-1][1])
    assert "1 video to post" in sent[-1][1]["text"] and "ch:chinese" in buttons and "apprq:all:all" not in buttons
    tap("ch:chinese")  # the posts: Post + Delete per video, post-all across platforms below
    chan = last_edit()
    chan_buttons = btns(chan)
    vid = next(b.split(":")[1] for b in chan_buttons if b.startswith("px:"))
    assert chan_buttons[:6] == ["noop"] + [f"px:{vid}:chinese:{p}" for p in ("youtube", "tiktok", "meta", "x")] + [f"delq:{vid}:chinese"]
    queued = []
    monkeypatch.setattr(hands, "postq_episode", lambda folder, p: queued.append(p) or f"{p} queued in postq")
    async def tap_and_wait(data):  # px answers at once and runs postq in the background
        await bot.handle({"callback_query": {"id": "c", "data": data, "message": {"chat": {"id": 42}, "message_id": 5}}})
        await asyncio.gather(*bot.running)

    asyncio.run(tap_and_wait(f"px:{vid}:chinese:meta"))  # one tap: postq posts it through the extension
    answers = [j.get("text", "") for m, j in sent if m == "answerCallbackQuery"]
    assert queued == ["meta"] and "sending to postq" in answers[-1]
    assert any("meta queued in postq" in j.get("text", "") for m, j in sent if m == "sendMessage")
    assert "apprq:chinese:all" in chan_buttons and "apprq:chinese:youtube" in chan_buttons
    assert all(len(b.encode()) <= 64 for b in chan_buttons)
    tap(f"pk:{vid}:chinese")  # platform picker (still reachable): every platform left is selected
    pick = btns(last_edit())
    assert pick[0].startswith(f"pk:{vid}:chinese:") and pick[-2].startswith(f"pp:{vid}:chinese:")
    tap(pick[0])  # untick the first platform
    assert btns(last_edit())[-2] != pick[-2]
    tap(pick[-2])  # post the rest
    assert any("queued" in j.get("text", "") for m, j in sent if m == "answerCallbackQuery")
    assert last_edit()["text"].startswith("Chinese ·")
    tap("apprq:all:youtube")
    assert "Post 1 job" in last_edit()["text"]
    tap("appr:all:youtube")
    assert any("1 queued" in j.get("text", "") for m, j in sent if m == "answerCallbackQuery")
    msg("/postq")
    assert "Auto-posting" in sent[-1][1]["text"]
    msg("/tasks")
    assert sent[-1][0] == "sendMessage"
    msg("/approve bogus")
    assert "channels:" in sent[-1][1]["text"]

    delq = f"delq:{vid}:chinese"
    tap(delq)
    assert "Yes, delete" in str([j for m, j in sent if m == "editMessageText"][-1]["reply_markup"])
    trashed = []
    monkeypatch.setattr(posting, "_trash", trashed.append)
    tap(delq.replace("delq:", "delc:", 1))
    assert trashed and trashed[-1].name == CHINESE
    assert sent[-2][0] == "editMessageText" and sent[-2][1]["text"].startswith("Chinese ·")  # back on the list


FAKE_APP_SERVER = """#!/usr/bin/env python3
import json, sys
log = open(sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != "app-server" else "/dev/null", "a")
ANSWER = __ANSWER__
for line in sys.stdin:
    m = json.loads(line)
    log.write(m.get("method", "") + "\\n"); log.flush()
    if "id" not in m:
        continue
    out = {"initialize": {}, "thread/start": {"thread": {"id": "t-1"}}, "thread/resume": {}, "thread/name/set": {},
           "turn/start": {}}[m["method"]]
    print(json.dumps({"id": m["id"], "result": out}), flush=True)
    if m["method"] == "turn/start":
        item = {"type": "agentMessage", "text": ANSWER}
        print(json.dumps({"method": "item/completed", "params": {"item": item}}), flush=True)
        print(json.dumps({"method": "turn/completed", "params": {"turn": {"status": "completed"}}}), flush=True)
"""


def fake_codex(tmp_path, answer):
    log = tmp_path / "calls.log"
    fake = tmp_path / "codex"
    fake.write_text(FAKE_APP_SERVER.replace("__ANSWER__", repr(answer)).replace(
        'sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != "app-server" else "/dev/null"', repr(str(log))))
    fake.chmod(0o755)
    return fake, log


def test_hands_codex_thread_is_kept_and_resumed(client, settings, tmp_path):
    from museai.api.routes import hands

    fake, log = fake_codex(tmp_path, "from codex")
    settings.codex_bin, settings.claude_bin = str(fake), "no-such-cli"
    settings.openai_api_key = settings.anthropic_api_key = ""
    bots = hands.ChatBots(settings, client.app.state.services.gateway)
    assert [p.id for p in bots.providers()] == ["codex", "muse"]
    bots.choose("codex")
    provider, text = asyncio.run(bots.reply([("user", "one")]))
    assert provider.id == "codex" and text == "from codex"
    asyncio.run(bots.reply([("user", "one"), ("assistant", "x"), ("user", "two")]))
    calls = log.read_text().split()
    assert calls.count("thread/start") == 1 and calls.count("thread/resume") == 1 and "thread/name/set" in calls
    bots.new_session()
    asyncio.run(bots.reply([("user", "three")]))
    assert log.read_text().split().count("thread/start") == 2


FAKE_CLAUDE = """#!/usr/bin/env python3
import json, sys
open(__LOG__, "a").write(json.dumps(sys.argv[1:]) + "\\n")
print("from claude code")
"""


def test_hands_claude_code_session_is_named_and_resumed(client, settings, tmp_path):
    from museai.api.routes import hands

    log = tmp_path / "claude.log"
    fake = tmp_path / "claude"
    fake.write_text(FAKE_CLAUDE.replace("__LOG__", repr(str(log))))
    fake.chmod(0o755)
    settings.claude_bin, settings.codex_bin = str(fake), "no-such-codex"
    settings.openai_api_key = settings.anthropic_api_key = ""
    bots = hands.ChatBots(settings, client.app.state.services.gateway)
    assert [(p.id, p.agent) for p in bots.providers()] == [("claude-code", True), ("muse", False)]
    bots.choose("claude-code")
    provider, text = asyncio.run(bots.reply([("user", "one")]))
    assert provider.agent and text == "from claude code"
    asyncio.run(bots.reply([("user", "one"), ("assistant", "x"), ("user", "two")]))
    first, second = (json.loads(line) for line in log.read_text().splitlines())
    sid = bots._read()["claude_session"]
    assert first[:2] == ["-p", "one"] and first[first.index("--session-id") + 1] == sid
    assert first[first.index("--name") + 1] == "Muse Hands · Telegram"
    assert second[second.index("--resume") + 1] == sid and "--session-id" not in second
    bots.new_session()
    assert "claude_session" not in bots._read()
    asyncio.run(bots.reply([("user", "three")]))
    assert bots._read()["claude_session"] != sid


def test_hands_codex_delegates_and_sends_media(client, settings, tmp_path):
    from museai.api.routes import hands

    video = tmp_path / "clip.mp4"
    video.write_bytes(b"x")
    fake, _ = fake_codex(tmp_path, f"rendered\nMEDIA: {video}")
    settings.codex_bin = str(fake)
    settings.telegram_bot_token, settings.telegram_chat_ids = "T", "42"
    settings.openai_api_key = settings.anthropic_api_key = ""
    sent = []

    class Http:
        async def post(self, url, json=None, data=None, files=None, timeout=None):
            sent.append((url.rsplit("/", 1)[1], json or data, files))
            return httpx.Response(200, json={"ok": True, "result": []}, request=httpx.Request("POST", url))

    async def run():
        bot = hands.Bot(client.app.state.services, Http())
        bot.ai.choose("codex")
        await bot.handle({"message": {"chat": {"id": 42}, "text": "make a video of a cat"}})
        await asyncio.gather(*bot.running)

    asyncio.run(run())
    assert [m for m, *_ in sent] == ["sendMessage", "sendVideo", "sendMessage"]
    assert sent[1][2]["video"][0] == "clip.mp4" and sent[2][1]["text"].startswith("rendered")
    assert "MEDIA" not in sent[2][1]["text"]


def test_postq_tap_approves_an_already_queued_item(tmp_path, monkeypatch):
    from museai.api.routes import hands

    folder = tmp_path / "Healing 01 · ep"
    folder.mkdir()
    queue = tmp_path / "queue"
    queue.mkdir()
    (queue / "a1.json").write_text(json.dumps({"id": "a1", "platform": "meta", "source": str(folder / "v.mp4")}))
    (queue / "b2.json").write_text(json.dumps({"id": "b2", "platform": "x", "source": str(folder / "v.mp4")}))
    monkeypatch.setenv("POSTQ_DIR", str(queue))
    runs = []
    monkeypatch.setattr(hands.subprocess, "run", lambda cmd, **_: runs.append(cmd[1:]) or
                        types.SimpleNamespace(returncode=0, stdout="approved a1\n", stderr=""))
    assert hands.postq_episode(str(folder), "meta") == "meta: approved, the extension posts it now"
    assert hands.postq_episode(str(folder), "tiktok") == "tiktok: queued, the extension posts it now"
    assert runs == [["approve", "--now", "a1"], ["episode", str(folder), "--platforms", "tiktok", "--auto", "--now"]]


def test_hands_claude_code_hands_over_to_codex_only_at_its_usage_limit(client, settings, tmp_path):
    from museai.api.routes import hands

    fake_cx, _ = fake_codex(tmp_path, "from codex")
    claude = tmp_path / "claude"
    claude.write_text("#!/bin/sh\necho \"$MODE\"\n[ \"$MODE\" = ok ] || exit 1\n")
    claude.chmod(0o755)
    settings.claude_bin, settings.codex_bin = str(claude), str(fake_cx)
    settings.openai_api_key = settings.anthropic_api_key = ""
    bots = hands.ChatBots(settings, client.app.state.services.gateway)
    assert bots.current().id == "claude-code"  # the default agent
    os.environ["MODE"] = "ok"
    try:
        assert asyncio.run(bots.reply([("user", "hi")])) [0].id == "claude-code"
        os.environ["MODE"] = "Claude AI usage limit reached|1763290800"
        provider, text = asyncio.run(bots.reply([("user", "hi")]))
        assert provider.id == "codex" and text.endswith("from codex")
        os.environ["MODE"] = "some other failure"
        with pytest.raises(hands.InvalidRequest):
            asyncio.run(bots.reply([("user", "hi")]))
    finally:
        os.environ.pop("MODE", None)
