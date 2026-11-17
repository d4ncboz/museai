"""The postq popup's list is the dashboard's "Ready to post" list: one `open` list, computed by the dashboard."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

FOLLOW = Path(__file__).parent.parent / "tools" / "postq" / "ext" / "follow.js"


def test_dashboard_open_list_follows_channel_and_ticks(client, admin, settings):
    settings.post_dir.mkdir()
    (settings.post_dir / "healing-rain.mp4").write_bytes(b"video")
    (settings.post_dir / "travel-story-rome.mp4").write_bytes(b"video")
    videos = {v["name"]: v for v in client.get("/dashboard/posts", headers=admin).json()["videos"]}
    assert set(videos["healing-rain.mp4"]["open"]) == {"youtube", "facebook", "instagram"}
    assert set(videos["travel-story-rome.mp4"]["open"]) == {"youtube", "tiktok", "facebook", "instagram", "x", "threads"}
    v = client.post("/dashboard/posts/healing-rain.mp4", headers=admin, json={"platform": "facebook"}).json()["video"]
    assert set(v["open"]) == {"youtube", "instagram"}


def _follow(items, videos, now):
    js = f"const {{followDashboard}} = require({json.dumps(str(FOLLOW))});" \
         f"console.log(JSON.stringify(followDashboard({json.dumps(items)}, {json.dumps(videos)}, {now})));"
    return json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)


def _item(iid, platform, name, **kw):
    return {"id": iid, "platform": platform, "video": {"name": name}, "schedule_at": "old", **kw}


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_popup_list_equals_the_dashboard_list():
    now = 1_795_000_000_000  # 2026-11-18
    soon = "2026-11-20T07:00:00+07:00"
    far = "2027-01-20T07:00:00+07:00"
    videos = [
        {"name": "a.mp4", "channel": "healing", "slot": "2026-11-20/1", "folder": "/f/a",
         "open": ["youtube", "instagram"], "schedule": {"youtube": soon, "facebook": soon}},
        {"name": "b.mp4", "channel": "healing", "slot": "2026-11-20/2", "folder": "/f/b",
         "open": ["youtube", "facebook", "instagram"], "schedule": {"facebook": soon}},
        {"name": "c.mp4", "channel": "healing", "slot": "2027-01-20/1", "folder": "/f/c",
         "open": ["facebook", "instagram"], "schedule": {"facebook": far}},
    ]
    items = [
        _item("b-meta", "meta", "b.mp4", targets=["facebook", "instagram"]),
        _item("a-meta", "meta", "a.mp4", targets=["facebook", "instagram"]),  # instagram still open
        _item("a-yt", "youtube", "a.mp4"),
        _item("a-yt2", "youtube", "a.mp4", auto=True),  # queued twice: the approved one is the card
        _item("a-x", "x", "a.mp4"),  # Healing has no X: not in its open list
        _item("gone-meta", "meta", "gone.mp4", targets=["facebook", "instagram"]),  # left the dashboard
    ]
    f = _follow(items, videos, now)
    assert [i["id"] for i in f["items"]] == ["a-meta", "a-yt2", "b-meta"]  # dashboard order
    assert f["items"][0]["schedule_at"] == soon  # the dashboard's slot time, not the queued one
    assert sorted(i["id"] for i in f["off"]) == ["a-x", "gone-meta"]
    assert [i["id"] for i in f["dups"]] == ["a-yt"]
    assert [(m["name"], m["platform"]) for m in f["missing"]] == [("b.mp4", "youtube"), ("c.mp4", "meta")]
    assert "28 days" in f["missing"][1]["why"]
    assert f["missing"][1]["wait"] == "2026-12-23" and "wait" not in f["missing"][0]  # panel: one summary line
    twice = _follow([], [videos[2], {**videos[2], "folder": "/f/c2"}], now)["missing"]
    assert len(twice) == 1  # two dashboard videos with one name: one row, not two


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_feed_without_open_lists_what_the_dashboard_shows_unticked():
    # A gateway started before the feed had `open`: the popup listed nothing at all.
    feed = {"platforms": [{"id": p} for p in ("youtube", "tiktok", "facebook", "instagram", "x", "threads")],
            "channels": [{"id": "healing", "platforms": ["youtube", "facebook", "instagram"]}],
            "videos": [{"name": "a.mp4", "channel": "healing", "posted": {"youtube": "2026-11-17"}},
                       {"name": "b.mp4", "channel": "chinese", "posted": {}, "open": ["x"]}]}
    js = f"const {{dashboardVideos}} = require({json.dumps(str(FOLLOW))});" \
         f"console.log(JSON.stringify(dashboardVideos({json.dumps(feed)})));"
    out = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    assert [v["open"] for v in out] == [["facebook", "instagram"], ["x"]]
    items = [_item("a-meta", "meta", "a.mp4", targets=["facebook", "instagram"]), _item("a-yt", "youtube", "a.mp4")]
    assert [i["id"] for i in _follow(items, out, 0)["items"]] == ["a-meta"]
