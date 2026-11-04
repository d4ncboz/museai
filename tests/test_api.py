from __future__ import annotations

import json
import time
import unicodedata

import pytest


def test_health(client):
    assert client.get("/healthz").json()["ok"] is True
    assert client.get("/readyz").json()["ready"] is True


def test_auth_required(client):
    r = client.get("/v1/models")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_api_key"


def test_models(client, auth):
    ids = {m["id"] for m in client.get("/v1/models", headers=auth).json()["data"]}
    assert {"muse-chat", "muse-image", "muse-video", "gpt-4o"} <= ids


def test_chat_non_stream(client, auth):
    r = client.post("/v1/chat/completions", headers=auth, json={
        "model": "gpt-4o", "messages": [{"role": "user", "content": "hello"}]})
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "chat.completion"
    assert body["model"] == "gpt-4o"
    assert "hello" in body["choices"][0]["message"]["content"]


def test_chat_stream(client, auth):
    with client.stream("POST", "/v1/chat/completions", headers=auth, json={
        "messages": [{"role": "user", "content": "stream me"}], "stream": True,
        "stream_options": {"include_usage": True},
    }) as r:
        assert r.status_code == 200
        lines = [ln[6:] for ln in r.iter_lines() if ln.startswith("data: ")]
    assert lines[-1] == "[DONE]"
    chunks = [json.loads(x) for x in lines[:-1]]
    text = "".join(c["choices"][0]["delta"].get("content", "") for c in chunks if c["choices"])
    assert "stream me" in text
    assert chunks[-1]["usage"]["total_tokens"] > 0


def test_chat_wrong_model_kind(client, auth):
    r = client.post("/v1/chat/completions", headers=auth, json={
        "model": "muse-video", "messages": [{"role": "user", "content": "x"}]})
    assert r.status_code == 400


def test_image_url_and_media(client, auth):
    r = client.post("/v1/images/generations", headers=auth,
                    json={"prompt": "a cat", "n": 2, "size": "1:1"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert len(data) == 2
    path = data[0]["url"].split("testserver", 1)[1]
    media = client.get(path)
    assert media.status_code == 200
    assert media.headers["content-type"] == "image/png"


def test_image_b64(client, auth):
    r = client.post("/v1/images/generations", headers=auth,
                    json={"prompt": "a dog", "response_format": "b64_json"})
    assert r.json()["data"][0]["b64_json"]


def test_video_task(client, auth):
    r = client.post("/v1/videos", headers=auth, json={"prompt": "waves", "duration": 5})
    task_id = r.json()["id"]
    for _ in range(50):
        task = client.get(f"/v1/videos/{task_id}", headers=auth).json()
        if task["status"] in ("succeeded", "failed"):
            break
        time.sleep(0.02)
    assert task["status"] == "succeeded", task
    assert task["result"]["url"].endswith(".mp4")


def test_finished_video_is_not_rendered_again(client, auth):
    def render(**headers):
        task_id = client.post("/v1/videos", headers={**auth, **headers},
                              json={"prompt": "same clip"}).json()["id"]
        for _ in range(50):
            if client.get(f"/v1/videos/{task_id}", headers=auth).json()["status"] == "succeeded":
                return task_id
            time.sleep(0.02)
        raise AssertionError("video did not finish")

    first = render()
    assert render() == first
    assert render(**{"X-Muse-Retake": "1"}) != first


def test_video_task_records_account(client, auth, admin):
    acc = client.post("/admin/accounts", headers=admin, json={
        "label": "a1", "cookies": {"hatch_sess": "s", "hatch_native_auth_device": "d"}},
    ).json()["account"]
    task_id = client.post("/v1/videos", headers=auth, json={"prompt": "waves"}).json()["id"]
    for _ in range(50):
        task = client.get(f"/v1/videos/{task_id}", headers=auth).json()
        if task["status"] in ("succeeded", "failed"):
            break
        time.sleep(0.02)
    assert task["account_id"] == acc["id"]
    listed = next(t for t in client.get("/admin/tasks", headers=admin).json()["data"]
                  if t["id"] == task_id)
    assert (listed["account_label"], listed["attempts"]) == ("a1", [acc["id"]])
    assert listed["created_at"] <= listed["started_at"] <= listed["updated_at"]


def test_dashboard_page(client, admin):
    r = client.get("/dashboard")
    assert r.status_code == 200
    assert "Ready to post" in r.text
    # TestClient's peer is "testclient", not loopback, so the admin key is required.
    assert client.get("/dashboard/data").status_code == 401
    data = client.get("/dashboard/data", headers=admin).json()
    assert data["system"]["level"] in {"ok", "busy", "overloaded"}
    assert {k: v for k, v in data.items() if k != "system"} == {
        "accounts": [],
        "usage": {},
        "videos": [],
    }


def test_dashboard_data_open_to_loopback(settings):
    from fastapi.testclient import TestClient

    from museai.app import create_app
    from museai.drivers.mock import MockDriver

    app = create_app(settings, MockDriver(delay=0))
    with TestClient(app, client=("127.0.0.1", 50000)) as c:
        assert c.get("/dashboard/data").status_code == 200


def test_dashboard_cookie_upload(client, admin):
    acc = client.post("/admin/accounts", headers=admin, json={
        "label": "a1", "cookies": {"hatch_sess": "old", "hatch_native_auth_device": "d"},
    }).json()["account"]
    client.patch(f"/admin/accounts/{acc['id']}", headers=admin, json={"enabled": True})
    url = f"/dashboard/accounts/{acc['id']}/cookies"
    export = [
        {"name": "hatch_sess", "value": "new", "domain": ".muse.ai", "expirationDate": 1893456000.5},
        {"name": "hatch_native_auth_device", "value": "d2", "domain": "muse.ai"},
        {"name": "other", "value": "x", "domain": ".example.com"},
    ]
    assert client.post(url, json=export).status_code == 401
    r = client.post(url, headers=admin, json=export)
    assert r.status_code == 200
    assert r.json()["account"]["status"] == "active"
    r = client.post(url, headers=admin, json=[{"name": "datr", "value": "x"}])
    assert r.status_code == 400
    assert "hatch_sess" in r.json()["error"]["message"]


def test_dashboard_rename(client, admin):
    acc = client.post("/admin/accounts", headers=admin, json={
        "label": "a1", "cookies": {"hatch_sess": "s", "hatch_native_auth_device": "d"},
    }).json()["account"]
    url = f"/dashboard/accounts/{acc['id']}/label"
    assert client.post(url, json={"label": "x"}).status_code == 401
    assert client.post(url, headers=admin, json={"label": " "}).status_code == 400
    r = client.post(url, headers=admin, json={"label": " me@example.com "})
    assert r.json()["account"]["label"] == "me@example.com"


def test_parse_cookie_export():
    from museai.upstream.muse import parse_cookie_export

    assert parse_cookie_export({"cookies": {"a": "1", "b": ""}}) == ({"a": "1"}, {})
    assert parse_cookie_export([{"name": "a", "value": "1", "expirationDate": 5.9}]) == (
        {"a": "1"}, {"a": 5})


def test_reserved_endpoints(client, auth):
    assert client.post("/v1/responses", headers=auth, json={}).status_code == 501
    assert client.post("/v1/images/edits", headers=auth).status_code == 501


def test_admin_accounts_crud(client, auth, admin):
    assert client.get("/admin/accounts", headers=auth).status_code == 401

    r = client.post("/admin/accounts", headers=admin,
                    json={"label": "a1", "cookies": {"hatch_sess": "secretvalue123"}})
    assert r.status_code == 200
    acc = r.json()["account"]
    assert acc["cookies"]["hatch_sess"] != "secretvalue123"
    assert "hatch_native_auth_device" in r.json()["missing_cookies"]

    r = client.patch(f"/admin/accounts/{acc['id']}", headers=admin, json={"enabled": False})
    assert r.json()["account"]["enabled"] is False

    assert len(client.get("/admin/accounts", headers=admin).json()["data"]) == 1
    assert client.post(f"/admin/accounts/{acc['id']}/renew", headers=admin).json()["ok"]
    assert client.delete(f"/admin/accounts/{acc['id']}", headers=admin).status_code == 200
    assert client.get("/admin/status", headers=admin).json()["accounts"]["total"] == 0


def test_posting_queue(client, admin, settings, monkeypatch):
    from museai.api.routes import posting

    trashed = []
    monkeypatch.setattr(posting, "_trash", lambda p: (trashed.append(p.name), p.unlink()))
    settings.post_dir.mkdir()
    (settings.post_dir / "ep1.mp4").write_bytes(b"video")
    (settings.post_dir / "notes.txt").write_text("not a video")
    (settings.post_dir / "ep1 - thumbnail 9x16.jpg").write_bytes(b"jpg")

    d = client.get("/dashboard/posts", headers=admin).json()
    assert [v["name"] for v in d["videos"]] == ["ep1.mp4"]
    assert {p["id"] for p in d["platforms"]} == {
        "youtube", "tiktok", "facebook", "instagram", "x", "threads"
    }
    assert client.get("/dashboard/posts/ep1.mp4/file", headers=admin).content == b"video"
    assert client.get("/dashboard/posts/notes.txt/file", headers=admin).status_code == 404
    assert [t["kind"] for t in d["videos"][0]["thumbnails"]] == ["9x16"]
    thumb = client.get("/dashboard/posts/ep1.mp4/thumbnail/9x16", headers=admin)
    assert thumb.content == b"jpg" and thumb.headers["content-disposition"].startswith("inline")  # opens, not downloads
    assert client.get("/dashboard/posts/ep1.mp4/thumbnail/16x9", headers=admin).status_code == 404

    r = client.post("/dashboard/posts/ep1.mp4", headers=admin, json={"caption": "hi #fyp"}).json()
    assert r["video"]["caption"] == "hi #fyp"
    r = client.post("/dashboard/posts/ep1.mp4", headers=admin,
                    json={"captions": {"x": "short #a", "youtube": "Title\n\nDesc"}}).json()
    assert r["video"]["captions"] == {"x": "short #a", "youtube": "Title\n\nDesc"}
    assert r["video"]["caption"] == "hi #fyp"
    r = client.post("/dashboard/posts/ep1.mp4", headers=admin, json={"captions": {"x": ""}}).json()
    assert r["video"]["captions"] == {"youtube": "Title\n\nDesc"}
    assert client.post("/dashboard/posts/ep1.mp4", headers=admin,
                       json={"captions": {"myspace": "x"}}).status_code == 400
    assert {p["id"]: p["limit"] for p in client.get("/dashboard/posts", headers=admin)
            .json()["platforms"]}["x"] == 280
    for p in ("youtube", "tiktok", "facebook"):
        r = client.post("/dashboard/posts/ep1.mp4", headers=admin, json={"platform": p}).json()
        assert not r["trashed"]
    r = client.post("/dashboard/posts/ep1.mp4", headers=admin,
                    json={"platform": "tiktok", "posted": False}).json()
    assert set(r["video"]["posted"]) == {"youtube", "facebook"}
    for p in ("tiktok", "instagram", "x"):
        r = client.post("/dashboard/posts/ep1.mp4", headers=admin, json={"platform": p}).json()
        assert not r["trashed"]
    for p in ("threads",):
        r = client.post("/dashboard/posts/ep1.mp4", headers=admin, json={"platform": p}).json()
    assert r["trashed"] and trashed == ["ep1 - thumbnail 9x16.jpg", "ep1.mp4"]
    d = client.get("/dashboard/posts", headers=admin).json()
    assert d["videos"] == []
    # The posted video's slot stays booked: the next one takes the slot after it, not its slot again.
    gone = [s for day in d["calendar"]["chinese"] for s in day["slots"] if s["gone"]]
    assert [g["gone"] for g in gone] == [{"name": "ep1.mp4", "title": "Title"}]
    (settings.post_dir / "ep2.mp4").write_bytes(b"video")
    keys = [s["key"] for day in d["calendar"]["chinese"] for s in day["slots"] if day["date"] >= gone[0]["key"][:10]]
    ep2 = client.get("/dashboard/posts", headers=admin).json()["videos"][0]
    assert ep2["slot"] == keys[keys.index(gone[0]["key"]) + 1]


def test_posting_folders(client, admin, settings, monkeypatch):
    import os
    import shutil
    import time

    from museai.api.routes import posting

    trashed = []
    monkeypatch.setattr(posting, "_trash", lambda p: (trashed.append(p.name), shutil.rmtree(p) if p.is_dir() else p.unlink()))
    root = settings.post_dir
    root.mkdir()

    def deliver(stem, age=60, thumb=True):
        (root / f"{stem}.mp4").write_bytes(stem.encode())
        if thumb:
            (root / f"{stem} - thumbnail 9x16.jpg").write_bytes(b"jpg")
        old = time.time() - age
        os.utime(root / f"{stem}.mp4", (old, old))

    deliver("zoom-Hoi An")
    deliver("reel-Hue", age=90)
    deliver("lesson-ni hao")
    deliver("fresh", age=0)  # deliver.sh may still be copying it
    deliver("holiday", thumb=False)  # the user's own clip: no thumbnail, never moved
    (root / "lesson-ni hao - thumbnail 16x9.jpg").write_bytes(b"wide")

    def folders():
        return sorted(d.name for d in root.iterdir() if d.is_dir())

    d = client.get("/dashboard/posts", headers=admin).json()
    assert {v["name"] for v in d["videos"]} == {"zoom-Hoi An.mp4", "reel-Hue.mp4", "lesson-ni hao.mp4", "fresh.mp4",
                                                 "holiday.mp4"}
    names = folders()
    # Each channel numbers its own folders from 01, in posting order.
    assert [n[:10] for n in names] == ["Chinese 01", "Travel 01 ", "Travel 02 "]
    assert names[0].endswith(" · lesson-ni hao") and names[1].endswith(" · reel-Hue") and names[2].endswith(" · zoom-Hoi An")
    assert ":" not in "".join(names)
    lesson = next(root / n for n in names if "lesson" in n)
    assert {p.name for p in lesson.iterdir()} == {
        ".museai-post", "lesson-ni hao.mp4", "lesson-ni hao - thumbnail 9x16.jpg", "lesson-ni hao - thumbnail 16x9.jpg"}
    assert (root / "fresh.mp4").is_file() and (root / "holiday.mp4").is_file()

    # Everything still works on the moved video; captions land in captions.txt.
    assert client.get("/dashboard/posts/lesson-ni hao.mp4/file", headers=admin).content == b"lesson-ni hao"
    assert client.get("/dashboard/posts/lesson-ni hao.mp4/thumbnail/16x9", headers=admin).content == b"wide"
    client.post("/dashboard/posts/lesson-ni hao.mp4", headers=admin,
                json={"caption": "Ni hao #chinese", "captions": {"youtube": "Hello in Chinese"}})
    client.get("/dashboard/posts", headers=admin)
    caps = (lesson / "captions.txt").read_text()
    assert "=== YouTube Shorts" in caps and "Hello in Chinese" in caps and "Ni hao #chinese" in caps

    # Posted everywhere: the whole folder goes, the other renumbers to 01.
    for p in posting.PLATFORMS:
        r = client.post("/dashboard/posts/lesson-ni hao.mp4", headers=admin, json={"platform": p}).json()
    assert r["trashed"] and trashed == [lesson.name]
    client.get("/dashboard/posts", headers=admin)
    assert [n[:9] for n in folders()] == ["Travel 01", "Travel 02"]

    # A folder deleted by hand takes its video out of the queue; the next one renumbers to 01.
    hue = folders()[0]
    shutil.rmtree(root / hue)
    d = client.get("/dashboard/posts", headers=admin).json()
    assert len(folders()) == 1 and folders()[0].startswith("Travel 01 ") and folders()[0].endswith("zoom-Hoi An")
    # Its slot is kept as posted: the calendar shows it gone, and the same name delivered again is a new
    # video that gets a slot of its own.
    record = posting._load(client.app.state.services)["reel-Hue.mp4"]
    assert record["done"] and record["channel"] == "travel"
    gone = [s for day in d["calendar"]["travel"] for s in day["slots"] if s["gone"]]
    assert [s["key"] for s in gone] == [record["slot"]]
    deliver("reel-Hue")
    d = client.get("/dashboard/posts", headers=admin).json()
    assert next(v["slot"] for v in d["videos"] if v["name"] == "reel-Hue.mp4") not in (None, record["slot"])
    shutil.rmtree(root / next(f for f in folders() if f.endswith("reel-Hue")))
    client.get("/dashboard/posts", headers=admin)
    shutil.rmtree(root / folders()[0])
    d = client.get("/dashboard/posts", headers=admin).json()
    assert {v["name"] for v in d["videos"]} == {"fresh.mp4", "holiday.mp4"}

    # Delivered again under the same name: the new video replaces the folder.
    deliver("reel-Da Nang")
    client.get("/dashboard/posts", headers=admin)
    first = folders()
    deliver("reel-Da Nang")
    (root / "reel-Da Nang.mp4").write_bytes(b"v2")
    os.utime(root / "reel-Da Nang.mp4", (time.time() - 60,) * 2)
    client.get("/dashboard/posts", headers=admin)
    assert first[0] in trashed and len(folders()) == 1
    assert (root / folders()[0] / "reel-Da Nang.mp4").read_bytes() == b"v2"


def test_posting_queue_fills_free_slots(tmp_path):
    import os
    from datetime import datetime

    from museai.api.routes import posting

    # Sunday 2026-11-08 12:00: EP45 posted at slot 1, EP46 (posted on one platform) holds slot 2, and a
    # video posted early holds Tuesday slot 1. The queue runs on in Sunday's evening slots, then Monday.
    now = datetime(2026, 11, 8, 12, 0, tzinfo=posting.TZ)
    videos = []
    for i, name in enumerate(("ep46.mp4", "ep47.mp4", "ep48.mp4", "ep49.mp4")):
        (p := tmp_path / name).write_bytes(b"v")
        os.utime(p, (1000 + i, 1000 + i))
        videos.append(p)
    state = {"ep45": {"slot": "2026-11-08/1", "channel": "chinese", "done": 1},
             "early": {"slot": "2026-11-10/1", "channel": "chinese", "done": 1},
             "ep46.mp4": {"slot": "2026-11-08/2", "posted": {"youtube": True}},
             "ep47.mp4": {"slot": "2026-11-09/2", "slot_pinned": True},
             "ep48.mp4": {"slot": "2026-11-12/1"}}
    assert posting._assign_slots(state, videos, now)
    assert [state[f"ep{n}.mp4"]["slot"] for n in (46, 47, 48, 49)] == [
        "2026-11-08/2", "2026-11-08/3", "2026-11-08/4", "2026-11-09/1"]
    assert not posting._assign_slots(state, videos, now)


def test_posting_queue_mixes_kinds_per_day(tmp_path):
    import os
    from datetime import datetime

    from museai.api.routes import posting

    # Delivered in a run of one kind, the travel queue still shows two kinds a day: a nostalgia video next
    # to a drone reel or a gown run, never two nostalgia videos the same day.
    now = datetime(2026, 11, 8, 12, 0, tzinfo=posting.TZ)
    names = ("nostalgia-a.mp4", "nostalgia-b.mp4", "nostalgia-c.mp4", "reel-d.mp4", "gown-e.mp4", "zoom-f.mp4")
    videos = []
    for i, name in enumerate(names):
        (p := tmp_path / name).write_bytes(b"v")
        os.utime(p, (1000 + i, 1000 + i))
        videos.append(p)
    state = {"scenic-x (posted)": {"slot": "2026-11-09/1", "channel": "travel", "done": 1}}
    assert posting._assign_slots(state, videos, now)
    days: dict[str, list[str]] = {}
    for n in names:
        days.setdefault(state[n]["slot"][:10], []).append(posting._kind(n))
    assert all(len(set(kinds)) == len(kinds) for kinds in days.values()), days
    assert state["nostalgia-a.mp4"]["slot"] == "2026-11-09/2"  # next to the posted drone reel
    assert not posting._assign_slots(state, videos, now)


def test_chinese_day_alternates_conversations_and_quizzes(tmp_path):
    import os
    from datetime import datetime

    from museai.api.routes import posting

    # Conversations delivered in a run, then quizzes: each day gets four, conversation and quiz in turn.
    now = datetime(2026, 11, 8, 5, 0, tzinfo=posting.TZ)
    names = [f"Tiếng Trung mỗi ngày {n} - x.mp4" for n in (52, 53, 54, 55)] + \
        [f"quiz-{t}.mp4" for t in ("food", "family", "school", "body")]
    videos = []
    for i, name in enumerate(names):
        (p := tmp_path / name).write_bytes(b"v")
        os.utime(p, (1000 + i, 1000 + i))
        videos.append(p)
    state: dict = {}
    assert posting._assign_slots(state, videos, now)
    by_time = sorted(names, key=lambda n: posting._slot_times(state[n]["slot"])["youtube"])
    assert [posting._kind(n) for n in by_time] == ["tiếng", "quiz"] * 4
    assert {state[n]["slot"][:10] for n in names} == {"2026-11-08", "2026-11-09"}
    assert [posting._slot_times(f"2026-11-09/{n}")["youtube"].hour for n in posting.CHANNELS["chinese"][1]] == \
        [7, 11, 20, 22]
    assert not posting._assign_slots(state, videos, now)


def test_posting_slots(tmp_path):
    import os
    from datetime import datetime

    from museai.api.routes import posting

    # Thursday 2026-10-29 19:00 GMT+7: today's morning (7:00) and lunch (11:30) YouTube slots have passed,
    # the evening ones (20:00, 22:00) are ahead.
    now = datetime(2026, 10, 29, 19, 0, tzinfo=posting.TZ)
    times = posting._slot_times("2026-10-31/3")  # Saturday evening, each platform at its own peak
    assert times["youtube"].isoformat() == "2026-10-31T19:00:00+07:00"
    assert times["x"].isoformat() == "2026-10-31T12:00:00+07:00"
    # No YouTube Short goes out at noon (its weakest hours); a learner's Sunday starts in the morning.
    assert all(posting._slot_times(f"2026-11-0{d}/2")["youtube"].hour not in range(12, 16) for d in range(2, 9))
    assert posting._slot_times("2026-11-01/1")["tiktok"].isoformat() == "2026-11-01T08:45:00+07:00"
    # Travel speaks to English viewers: Monday's London evening, then Monday's New York evening,
    # both on Tuesday in GMT+7.
    assert posting._slot_times("2026-11-03/1", "travel")["youtube"].isoformat() == "2026-11-03T02:00:00+07:00"
    assert posting._slot_times("2026-11-03/2", "travel")["tiktok"].isoformat() == "2026-11-03T06:45:00+07:00"
    # X and Threads peak in the morning: London 9:00 and New York 11:00 are Tuesday afternoon and night
    assert posting._slot_times("2026-11-03/1", "travel")["x"].isoformat() == "2026-11-03T16:00:00+07:00"
    assert posting._slot_times("2026-11-03/2", "travel")["threads"].isoformat() == "2026-11-03T23:00:00+07:00"

    videos = []
    for i, name in enumerate(("a.mp4", "b.mp4", "c.mp4")):
        (p := tmp_path / name).write_bytes(b"v")
        os.utime(p, (1000 + i, 1000 + i))
        videos.append(p)
    state = {"b.mp4": {"slot": "2026-10-29/1", "posted": {}}}  # missed, not pinned
    assert posting._assign_slots(state, videos, now)
    assert [state[n]["slot"] for n in ("b.mp4", "a.mp4", "c.mp4")] == [
        "2026-10-29/3", "2026-10-29/4", "2026-10-30/1"]  # missed b keeps its place in line, then delivery order
    assert not posting._assign_slots(state, videos, now)
    cal = posting._calendar(state, {n: n for n in ("a.mp4", "b.mp4", "c.mp4")}, now)["chinese"]
    assert len(cal) == 7 and cal[0]["slots"][2]["video"] == "b.mp4" and cal[0]["slots"][1]["video"] is None

    # Travel posts from other accounts on its own clock: today's 02:00 and 06:00 slots have passed, so
    # it books tomorrow's first one, even though Chinese has that slot taken.
    (p := tmp_path / "zoom-madeira.mp4").write_bytes(b"v")
    os.utime(p, (2000, 2000))
    assert posting._assign_slots(state, [*videos, p], now)
    assert state["zoom-madeira.mp4"]["slot"] == "2026-10-30/1"
    cal = posting._calendar(state, {n: n for n in state}, now)
    assert cal["travel"][1]["slots"][0]["video"] == "zoom-madeira.mp4"
    assert cal["chinese"][0]["slots"][2]["video"] == "b.mp4"

    # A new Chinese video takes the next free Chinese slot, not one only Travel has free.
    (p := tmp_path / "d.mp4").write_bytes(b"v")
    os.utime(p, (3000, 3000))
    assert posting._assign_slots(state, [*videos, p], now)
    chinese = [e["slot"] for n, e in state.items() if posting._channel(n, e) == "chinese"]
    assert state["d.mp4"]["slot"] == "2026-10-30/2" and len(set(chinese)) == len(chinese)

    # Posted / deleted videos keep their slot (records go a year after it); the queue fills the others.
    state["gone.mp4"] = {"slot": "2026-10-30/3", "channel": "chinese", "title": "t", "done": 1}
    state["old.mp4"] = {"slot": "2025-10-01/1", "channel": "chinese", "title": "t", "done": 1}
    (p := tmp_path / "e.mp4").write_bytes(b"v")
    os.utime(p, (4000, 4000))
    assert posting._forget_old(state, now) and "old.mp4" not in state
    assert posting._assign_slots(state, [*videos, tmp_path / "d.mp4", p], now)
    assert [state[n]["slot"] for n in ("b.mp4", "a.mp4", "c.mp4", "d.mp4", "e.mp4")] == [
        "2026-10-29/3", "2026-10-29/4", "2026-10-30/1", "2026-10-30/2", "2026-10-30/4"]
    # The same name delivered again is a new video: the old record moves aside, staying in the history,
    # and the new one joins the end of the queue.
    (tmp_path / "gone.mp4").write_bytes(b"v")
    os.utime(tmp_path / "gone.mp4", (5000, 5000))
    assert posting._assign_slots(state, [*videos, tmp_path / "d.mp4", p, tmp_path / "gone.mp4"], now)
    assert state["gone.mp4"]["slot"] == "2026-10-31/1" and "done" not in state["gone.mp4"]
    assert state["(posted chinese 2026-10-30/3)"]["done"]  # kept for the next passes too


def test_episodes_post_in_number_order(tmp_path):
    import os
    from datetime import datetime

    from museai.api.routes import posting

    now = datetime(2026, 10, 29, 19, 0, tzinfo=posting.TZ)  # Thursday: slot 2 (11:30) passed, slot 3 (20:00) ahead
    videos = []
    names = ("Tiếng Trung mỗi ngày 47 - B.mp4", "lesson-bi-so-sanh.mp4", "Tiếng Trung mỗi ngày 46 - A.mp4")
    for i, name in enumerate(names):
        (p := tmp_path / name).write_bytes(b"v")
        os.utime(p, (1000 + i, 1000 + i))
        videos.append(p)
    state = {}
    assert posting._assign_slots(state, videos[:2], now)  # EP47 arrives first and books the first slot
    assert posting._assign_slots(state, videos, now)  # then EP46: it takes EP47's slot, EP47 its
    assert state["Tiếng Trung mỗi ngày 46 - A.mp4"]["slot"] == "2026-10-29/3"
    assert state["lesson-bi-so-sanh.mp4"]["slot"] == "2026-10-29/4"  # another series keeps its slot
    assert state["Tiếng Trung mỗi ngày 47 - B.mp4"]["slot"] == "2026-10-30/1"
    assert not posting._assign_slots(state, videos, now)

    # A slot the user picked stays.
    state["Tiếng Trung mỗi ngày 47 - B.mp4"].update(slot="2026-10-29/3", slot_pinned=True)
    state["Tiếng Trung mỗi ngày 46 - A.mp4"]["slot"] = "2026-10-30/1"
    assert not posting._assign_slots(state, videos, now)
    assert state["Tiếng Trung mỗi ngày 47 - B.mp4"]["slot"] == "2026-10-29/3"


def test_posting_channel_from_file_name():
    from museai.api.routes import posting

    for name in ("zoom-madeira.mp4", "reel-ilulissat.mp4", "travel-bled.mp4", "Kelingking Beach - zoominview.mp4",
                 "nostalgia-1985.mp4"):
        assert posting._channel(name, {}) == "travel", name
    for name in ("dream-star-fisher.mp4", "Rainbow laundry - dream-life.mp4"):
        assert posting._channel(name, {}) == "dream", name
    for name in ("healing-highland-pear-compote.mp4", "Provence herbs - healing-video.mp4"):
        assert posting._channel(name, {}) == "healing", name
    for name in ("EVERYDAY CHINESE 13 - Finding the subway.mp4", "Tiếng Trung mỗi ngày 16 - Đi cắt tóc.mp4",
                 "lesson-bi-so-sanh_vertical_9x16.mp4", "Zoomed lesson.mp4"):
        assert posting._channel(name, {}) == "chinese", name
    assert posting._channel("reel-x.mp4", {"channel": "chinese"}) == "chinese"

def test_posting_dream_two_slots_a_day(client, admin, settings):
    from museai.api.routes import posting

    # New York 20:00 on Monday is Tuesday 08:00 in GMT+7 (winter time); New York 07:00 Tuesday is 19:00
    assert posting._slot_times("2026-11-03/1", "dream")["instagram"].isoformat() == "2026-11-03T08:00:00+07:00"
    assert posting._slot_times("2026-11-03/2", "dream")["instagram"].isoformat() == "2026-11-03T19:00:00+07:00"
    settings.post_dir.mkdir()
    for name in ("dream-a.mp4", "dream-b.mp4"):
        (settings.post_dir / name).write_bytes(b"v")
    d = client.get("/dashboard/posts", headers=admin).json()
    assert all(len(day["slots"]) == 2 for day in d["calendar"]["dream"])
    # shown in GMT+7, with the audience's own clock beside it
    aud = posting._audience("2026-11-03/1", "dream")
    assert aud["clock"] == "New York" and aud["times"]["instagram"] == "2026-11-02T20:00:00-05:00"
    assert d["calendar"]["dream"][0]["slots"][0]["audience"]["clock"] == "New York"
    assert d["calendar"]["chinese"][0]["slots"][0]["audience"] is None
    assert len({v["slot"] for v in d["videos"]}) == 2


def test_posting_dream_playlists(client, admin, settings):
    from museai.api.routes import posting

    cases = {"dream-star-fisher.mp4": "Night Sky", "dream-rainbow-laundry.mp4": "Weather",
             "dream-butterfly-tailor.mp4": "Cozy Dream Jobs", "dream-giant-sweets.mp4": "Soft Dream Worlds",
             "dream-seasons-house.mp4": "Soft Dream Worlds", "dream-lavender-lake.mp4": "Dream Places",
             "dream-lighthouse-of-wishes.mp4": "Night Sky"}
    for name, playlist in cases.items():
        assert posting._playlist(name, {}).startswith(playlist), name
    assert posting._playlist("reel-kyoto.mp4", {}) is None
    settings.post_dir.mkdir()
    (settings.post_dir / "dream-star-fisher.mp4").write_bytes(b"v")
    (settings.post_dir / "reel-kyoto.mp4").write_bytes(b"v")
    d = client.get("/dashboard/posts", headers=admin).json()
    assert len(d["playlists"]["dream"]) == 5 and any(n.startswith("Night Sky") for n in d["playlists"]["dream"])
    videos = {v["name"]: v for v in d["videos"]}
    assert videos["dream-star-fisher.mp4"]["playlist"].startswith("Night Sky")
    assert videos["reel-kyoto.mp4"]["playlist"] is None
    assert "=== YouTube playlist ===" in posting._captions_text("dream-star-fisher.mp4", {"caption": "hi"})


def test_posting_healing_playlists():
    from museai.api.routes import posting

    cases = {"healing-irish-rain-ode.mp4": "Rain", "healing-danish-first-snow.mp4": "Rain",
             "healing-taiwan-tea-house-ode.mp4": "Tea", "healing-swiss-hot-cocoa.mp4": "Tea",
             "healing-mekong-birds-ode.mp4": "Nature", "healing-provence-herbs.mp4": "Nature",
             "healing-finnish-rye-bread.mp4": "Slow Living", "healing-lakeside-soup.mp4": "Slow Living"}
    for name, playlist in cases.items():
        assert posting._playlist(name, {}).startswith(playlist), name


def test_campaign_progress(client, admin, settings, monkeypatch):
    from datetime import date

    from museai.api.routes import campaign

    assert client.get("/dashboard/campaign/nope", headers=admin).status_code == 400
    monkeypatch.setattr(campaign, "_today", lambda: date(2026, 11, 2))
    r = client.post("/dashboard/campaign/dream", headers=admin,
                    json={"start": "2026-11-02", "youtube": {"subs": 100, "shorts_views_90d": 0, "uploads_90d": 3}})
    assert r.status_code == 200 and r.json()["day"] == 1 and r.json()["phase"]["name"].startswith("Days 1-30")
    monkeypatch.setattr(campaign, "_today", lambda: date(2026, 11, 12))
    d = client.post("/dashboard/campaign/dream", headers=admin,
                    json={"youtube": {"subs": 200, "shorts_views_90d": 100_000}, "instagram": {"followers": 600}}).json()
    fan = next(g for g in d["goals"] if g["id"] == "yt-fan")
    subs = next(p for p in fan["parts"] if p["metric"] == "subs")
    assert subs["have"] == 200 and subs["per_day"] == 10 and subs["pct"] == 40
    # 3M views at 10k a day is the slowest part: 290 more days
    assert fan["eta"] == "2027-08-29" and not fan["done"]
    assert next(g for g in d["goals"] if g["id"] == "ig-gifts")["done"]
    assert len(d["snapshots"]) == 2 and (settings.data_dir / "campaign-dream.json").exists()
    bad = client.post("/dashboard/campaign/dream", headers=admin, json={"youtube": {"subs": "lots"}})
    assert bad.status_code == 400


@pytest.mark.parametrize("clock", ["09:00", "18:00", "20:30", "23:59"])  # GMT+7, Monday 2026-11-02
def test_posting_move_slot(client, admin, settings, monkeypatch, clock):
    from datetime import datetime

    from museai.api.routes import posting

    # Freeze the listing's clock: once a day's Chinese slots have passed, its first free slot is
    # tomorrow's, the same key as Travel's first (London's evening lands after midnight GMT+7).
    now = datetime.fromisoformat(f"2026-11-02T{clock}+07:00")
    monkeypatch.setattr(posting, "datetime", type("Clock", (datetime,), {"now": classmethod(lambda cls, tz=None: now)}))
    settings.post_dir.mkdir()
    for name in ("a.mp4", "b.mp4"):
        (settings.post_dir / name).write_bytes(b"v")
    d = client.get("/dashboard/posts", headers=admin).json()
    slots = {v["name"]: v["slot"] for v in d["videos"]}
    assert len(set(slots.values())) == 2
    assert set(d["videos"][0]["schedule"]) == {"youtube", "tiktok", "facebook", "instagram", "x", "threads"}
    assert sum(s["video"] is not None for day in d["calendar"]["chinese"] for s in day["slots"]) == 2
    assert {c["id"] for c in d["channels"]} == {"chinese", "travel", "dream", "healing"}

    r = client.post("/dashboard/posts/a.mp4", headers=admin, json={"slot": slots["b.mp4"]}).json()
    assert r["video"]["slot"] == slots["b.mp4"]
    moved = {v["name"]: v["slot"] for v in client.get("/dashboard/posts", headers=admin).json()["videos"]}
    assert moved == {"a.mp4": slots["b.mp4"], "b.mp4": slots["a.mp4"]}  # swapped
    assert list(moved) == ["b.mp4", "a.mp4"]  # cards in posting order
    for bad in ("2026-10-30/5", "tomorrow", "2026-13-40/1", 5):
        assert client.post("/dashboard/posts/a.mp4", headers=admin, json={"slot": bad}).status_code == 400

    # Moving a to Travel frees its Chinese slot and books the first free Travel slot.
    client.post("/dashboard/posts/a.mp4", headers=admin, json={"channel": "travel"})
    d = client.get("/dashboard/posts", headers=admin).json()
    a = next(v for v in d["videos"] if v["name"] == "a.mp4")
    assert a["channel"] == "travel"
    assert [s["key"] for day in d["calendar"]["travel"] for s in day["slots"] if s["video"]] == [a["slot"]]
    assert sum(s["video"] is not None for day in d["calendar"]["chinese"] for s in day["slots"]) == 1
    # A slot holding a video of the other channel is not a swap.
    r = client.post("/dashboard/posts/b.mp4", headers=admin, json={"slot": a["slot"]}).json()
    assert r["video"]["slot"] == a["slot"]
    after = {v["name"]: v["slot"] for v in client.get("/dashboard/posts", headers=admin).json()["videos"]}
    assert after["a.mp4"] == a["slot"]
    assert after["b.mp4"] == next(posting._slots_from(now, "chinese"))  # alone in Chinese: first slot, no gap
    assert client.post("/dashboard/posts/a.mp4", headers=admin, json={"channel": "nope"}).status_code == 400


def test_dashboard_cancel_and_retry(settings, auth, admin):
    from fastapi.testclient import TestClient

    from museai.app import create_app
    from museai.drivers.mock import MockDriver

    with TestClient(create_app(settings, MockDriver(delay=0.5))) as c:
        def status(task_id):
            for _ in range(100):
                task = c.get(f"/v1/videos/{task_id}", headers=auth).json()
                if task["status"] not in ("queued", "running"):
                    return task["status"]
                time.sleep(0.02)
            return task["status"]

        task_id = c.post("/v1/videos", headers=auth, json={"prompt": "waves"}).json()["id"]
        url = f"/dashboard/videos/{task_id}"
        assert c.post(url + "/retry", headers=admin).status_code == 400  # still rendering
        assert c.post(url + "/cancel", headers=admin).json() == {"cancelled": True}
        assert status(task_id) == "cancelled"

        again = c.post(url + "/retry", headers=admin).json()["id"]
        assert again != task_id
        # A second click while the retry renders joins it instead of rendering twice.
        assert c.post(url + "/retry", headers=admin).json()["id"] == again
        assert c.post("/dashboard/videos/nope/cancel", headers=admin).status_code == 404


def test_auto_captions_fill_missing_platforms(client, admin, settings):
    from museai.services import captions

    svc = client.app.state.services
    svc.captions.enabled = True
    asked = []

    async def write(path, caption, missing):
        asked.append((path.name, caption, missing))
        return {p: f"{p} text #tag" for p in missing}

    svc.captions.write = write
    settings.post_dir.mkdir()
    name = unicodedata.normalize("NFD", "Tiếng 1.mp4")
    (settings.post_dir / name).write_bytes(b"video")
    # macOS lists the name decomposed; its state is keyed composed
    client.post(f"/dashboard/posts/{name}", headers=admin, json={"captions": {"x": "mine"}})
    client.get("/dashboard/posts", headers=admin)
    for _ in range(50):
        v = client.get("/dashboard/posts", headers=admin).json()["videos"][0]
        if len(v["captions"]) == 6 and not v["auto_captions"]:
            break
        time.sleep(0.05)
    assert v["captions"]["x"] == "mine"
    assert v["captions"]["threads"] == "threads text #tag"
    assert v["caption"] == "tiktok text #tag"
    assert v["auto_captions"] is None
    assert asked == [(name, "", [p for p in captions.PLATFORMS if p != "x"])]


def test_auto_captions_parse_and_prompt():
    from museai.services import captions

    got = captions.parse('Sure!\n```json\n{"x": "hi", "tiktok": "", "myspace": "no"}\n```', ["x", "tiktok"])
    assert got == {"x": "hi"}
    assert captions.parse("no json here", ["x"]) == {}
    text = captions.prompt("a.mp4", "", ["x"], "RULES", ["x: 300 characters, limit 280"])
    assert "RULES" in text and "x: 300 characters" in text and "frames" in text
