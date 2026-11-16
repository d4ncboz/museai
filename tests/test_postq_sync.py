"""postq's dashboard sync: every open dashboard video gets a queue item, nothing else does."""
from datetime import datetime, timedelta, timezone
from importlib.machinery import SourceFileLoader
from pathlib import Path

postq = SourceFileLoader("postq_cli", str(Path(__file__).parent.parent / "tools" / "postq" / "postq")).load_module()


def _feed(tmp_path, videos, platforms):
    return lambda: {"folder": str(tmp_path), "channels": [{"id": "healing", "platforms": platforms}], "videos": videos}


def _video(tmp_path, name, **kw):
    d = tmp_path / f"Healing 01 · Mon 16-11 18h30 · {name}"
    d.mkdir()
    (d / ".museai-post").write_text("")
    (d / name).write_bytes(b"x")
    return {"name": name, "folder": str(d), "slot": "2026-11-16T18:30", "channel": "healing", "posted": {}, "schedule": {}, **kw}


def _run(monkeypatch, tmp_path, videos, platforms):
    calls = []
    monkeypatch.setattr(postq, "cmd_episode", lambda a: calls.append(a))
    postq.sync_dashboard(now=datetime(2026, 11, 16, tzinfo=timezone.utc), fetch=_feed(tmp_path, videos, platforms))
    return calls


def test_queues_open_platforms_only_for_channel(monkeypatch, tmp_path):
    v = _video(tmp_path, "a.mp4", posted={"youtube": True})
    (call,) = _run(monkeypatch, tmp_path, [v], ["youtube", "facebook", "instagram"])
    assert call.platforms == ["meta"]

def test_healing_never_queues_x_tiktok(monkeypatch, tmp_path):
    (call,) = _run(monkeypatch, tmp_path, [_video(tmp_path, "a.mp4")], ["youtube", "facebook", "instagram"])
    assert call.platforms == ["youtube", "meta"]


def test_meta_waits_until_inside_28_days(monkeypatch, tmp_path):
    far = (datetime(2026, 11, 16) + timedelta(days=40)).isoformat()
    v = _video(tmp_path, "a.mp4", schedule={"facebook": far + "+00:00"})
    (call,) = _run(monkeypatch, tmp_path, [v], ["youtube", "facebook", "instagram"])
    assert call.platforms == ["youtube"]


def test_fully_posted_or_unknown_video_queues_nothing(monkeypatch, tmp_path):
    v = _video(tmp_path, "a.mp4", posted={"youtube": True, "facebook": True, "instagram": True})
    lone = {**_video(tmp_path, "b.mp4"), "name": "ghost.mp4", "folder": None}
    assert _run(monkeypatch, tmp_path, [v, lone], ["youtube", "facebook", "instagram"]) == []
