"""Auto-post: rules plan new queued videos, the publisher posts them through the mock driver."""

from __future__ import annotations

import asyncio
import json
import os
import time
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
