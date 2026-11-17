"""postq's dashboard sync: every open dashboard video gets a queue item, nothing else does."""
import argparse
from datetime import datetime, timedelta, timezone
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

postq = SourceFileLoader("postq_cli", str(Path(__file__).parent.parent / "tools" / "postq" / "postq")).load_module()


def _feed(tmp_path, videos):
    return lambda: {"folder": str(tmp_path), "videos": videos}


def _video(tmp_path, name, **kw):
    d = tmp_path / f"Healing 01 · Mon 16-11 18h30 · {name}"
    d.mkdir()
    (d / ".museai-post").write_text("")
    (d / name).write_bytes(b"x")
    return {"name": name, "folder": str(d), "slot": "2026-11-16T18:30", "channel": "healing", "posted": {},
            "open": ["youtube", "facebook", "instagram"], "schedule": {}, **kw}


def _run(monkeypatch, tmp_path, videos):
    calls = []
    monkeypatch.setattr(postq, "cmd_episode", lambda a: calls.append(a))
    postq.sync_dashboard(now=datetime(2026, 11, 16, tzinfo=timezone.utc), fetch=_feed(tmp_path, videos))
    return calls


def test_queues_only_the_dashboard_open_list(monkeypatch, tmp_path):
    # The dashboard's `open` list decides: postq keeps no second copy of the channel's platforms.
    v = _video(tmp_path, "a.mp4", posted={"youtube": True}, open=["facebook", "instagram"])
    (call,) = _run(monkeypatch, tmp_path, [v])
    assert call.platforms == ["meta"]


def test_threads_has_no_queue(monkeypatch, tmp_path):
    v = _video(tmp_path, "a.mp4", open=["tiktok", "instagram", "threads"])
    (call,) = _run(monkeypatch, tmp_path, [v])
    assert call.platforms == ["tiktok", "meta"]


def test_meta_waits_until_inside_28_days(monkeypatch, tmp_path):
    far = (datetime(2026, 11, 16) + timedelta(days=40)).isoformat()
    v = _video(tmp_path, "a.mp4", schedule={"facebook": far + "+00:00"})
    (call,) = _run(monkeypatch, tmp_path, [v])
    assert call.platforms == ["youtube"]


def test_fully_posted_or_unknown_video_queues_nothing(monkeypatch, tmp_path):
    v = _video(tmp_path, "a.mp4", posted={"youtube": True, "facebook": True, "instagram": True}, open=[])
    lone = {**_video(tmp_path, "b.mp4"), "name": "ghost.mp4", "folder": None}
    assert _run(monkeypatch, tmp_path, [v, lone]) == []


def _queued(root, iid, source, platform="youtube", **kw):
    item = {"id": iid, "platform": platform, "account": "A", "source": str(source),
            "video": {"file": f"{iid}-video.mp4"}, "cover": None, **kw}
    (root / f"{iid}.json").write_text(postq.json.dumps(item))
    (root / f"{iid}-video.mp4").write_bytes(b"x")


def test_renamed_folder_retires_the_old_item(monkeypatch, tmp_path):
    root = tmp_path / "queue"
    root.mkdir()
    monkeypatch.setattr(postq, "ROOT", root)
    monkeypatch.setattr(postq, "DONE", root / "done")
    new = tmp_path / "Chinese 06 · Tue 24-11 12h00 · Ep 3" / "Ep 3.mp4"
    new.parent.mkdir()
    new.write_bytes(b"x")
    kept = tmp_path / "Chinese 07 · other" / "Ep 3.mp4"  # still on disk: a different folder, not a rename
    kept.parent.mkdir()
    kept.write_bytes(b"x")
    gone = tmp_path / "Chinese 10 · Thu 26-11 12h00 · Ep 3" / "Ep 3.mp4"
    _queued(root, "old", gone)
    _queued(root, "meta", gone, platform="meta")
    _queued(root, "uploading", gone, video_id="v1")
    _queued(root, "other", kept)
    assert postq.retire_renamed(str(new), "youtube", "A") == ["old"]
    done = postq.json.loads((root / "done" / "old.json").read_text())
    assert done["status"] == "superseded" and done["superseded_by"] == str(new)
    assert (root / "done" / "old-video.mp4").is_file()
    assert sorted(p.stem for p in root.glob("*.json")) == ["meta", "other", "uploading"]


def test_second_sync_skips_while_one_runs(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(postq, "ROOT", tmp_path)
    calls = []
    monkeypatch.setattr(postq, "sync_dashboard", lambda: calls.append(1) or [])
    with postq.sync_lock() as first:
        assert first
        postq.cmd_sync(None)
    assert calls == []
    assert "skipped" in capsys.readouterr().out
    postq.cmd_sync(None)
    assert calls == [1]


def test_one_queue_item_per_video(monkeypatch, tmp_path):
    """Same platform, account and file name = one video: the popup must never show it twice."""
    root = tmp_path / "queue"
    root.mkdir()
    monkeypatch.setattr(postq, "ROOT", root)
    monkeypatch.setattr(postq, "DONE", root / "done")
    a = tmp_path / "Chinese 01 · Fri 20-11 12h00 · Ep 1" / "Ep 1.mp4"
    b = tmp_path / "Chinese 04 · Tue 24-11 12h00 · Ep 1" / "Ep 1.mp4"
    _queued(root, "1-old", a, platform="meta")
    _queued(root, "2-approved", b, platform="meta", auto=True)
    _queued(root, "3-again", a, platform="meta")
    _queued(root, "4-yt", a)  # another platform: its own card
    assert sorted(postq.retire_duplicates()) == ["1-old", "3-again"]
    assert sorted(p.stem for p in root.glob("*.json")) == ["2-approved", "4-yt"]
    done = postq.json.loads((root / "done" / "3-again.json").read_text())
    assert done["status"] == "duplicate" and done["duplicate_of"] == "2-approved"
    assert postq.retire_duplicates() == []
    # enqueue (under its lock) refuses the same video from another folder
    with pytest.raises(SystemExit, match="already queued"):
        postq._enqueue(argparse.Namespace(platform="meta", account="A"), "", [], None, str(tmp_path / "x" / "Ep 1.mp4"))


def test_test_apps_never_sync_the_live_postq_queue(settings, monkeypatch):
    """A test app must not start `postq sync`: it writes the real queue, from whatever checkout runs the tests."""
    from fastapi.testclient import TestClient

    from museai.api.routes import hands
    from museai.app import create_app
    from museai.drivers.mock import MockDriver

    started = []

    async def loop(*a, **kw):
        started.append(1)

    monkeypatch.setattr(hands, "postq_sync_loop", loop)
    with TestClient(create_app(settings, MockDriver(delay=0))):
        pass
    assert not started
    settings.postq_sync = True
    with TestClient(create_app(settings, MockDriver(delay=0))):
        pass
    assert started == [1] or not hands.POSTQ.is_file()
