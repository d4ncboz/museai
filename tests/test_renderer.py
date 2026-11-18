import json
import time

import pytest
from fastapi.testclient import TestClient

from museai.app import create_app
from museai.core.renderer import renderer_status
from museai.drivers.mock import MockDriver


def beat(root, age=0.0, runtime="up", **extra):
    (root / "server.json").write_text(json.dumps({
        "host": "box", "pid": 1, "ts": time.time() - age, "runtime": runtime,
        "session": "muse", "colab_url": "https://colab.example/x", "job": None, **extra}))


def job(root, state, jid, **result):
    d = root / state / jid
    d.mkdir(parents=True)
    (d / "job.json").write_text(json.dumps({"cmd": "x", "inputs": {"in.mp4": 1}}))
    (d / "in.mp4").write_bytes(b"in")
    if result:
        (d / "result.json").write_text(json.dumps(result))
    return d


@pytest.fixture
def drive(tmp_path):
    root = tmp_path / "drive"
    for s in ("queue", "running", "done", "failed"):
        (root / s).mkdir(parents=True)
    return root


def test_status_online_counts_and_jobs(drive):
    beat(drive)
    job(drive, "queue", "20260101-000000-a")
    (drive / "queue" / "20260101-000001-b.part").mkdir()
    out = job(drive, "done", "20260101-000002-c", rc=0, seconds=12, host="box")
    (out / "out.mp4").write_bytes(b"x")
    bad = job(drive, "failed", "20260101-000003-d", rc=1, seconds=3)
    (bad / "log.txt").write_text("x" * 3000 + "boom")
    st = renderer_status(str(drive))
    assert st["state"] == "online" and st["online"] and st["host"] == "box"
    assert st["counts"] == {"queue": 1, "running": 0, "done": 1, "failed": 1}
    assert [j["id"][-1] for j in st["jobs"]] == ["d", "c", "a"]
    failed, done = st["jobs"][0], st["jobs"][1]
    assert failed["log"].endswith("boom") and len(failed["log"]) <= 1500 and failed["rc"] == 1
    assert done["files"] == ["out.mp4"] and done["seconds"] == 12


def test_status_idle_and_stale(drive):
    beat(drive, runtime="stopped")
    assert renderer_status(str(drive))["state"] == "idle"
    beat(drive, age=120)
    st = renderer_status(str(drive))
    assert st["state"] == "offline" and not st["online"]


def test_status_broken_json_and_missing_folder(drive, tmp_path):
    (drive / "server.json").write_text("{nope")
    st = renderer_status(str(drive))
    assert st["state"] == "offline" and "error" in st
    st = renderer_status(str(tmp_path / "nowhere"))
    assert st["configured"] is True and "error" in st


@pytest.fixture
def rclient(settings, drive):
    with_drive = settings.model_copy(update={"render_drive": str(drive)})
    with TestClient(create_app(with_drive, MockDriver(delay=0))) as c:
        yield c


def test_dashboard_data_renderer(client, rclient, drive, admin):
    assert client.get("/dashboard/data", headers=admin).json()["renderer"] is None
    beat(drive)
    assert rclient.get("/dashboard/data", headers=admin).json()["renderer"]["state"] == "online"


def test_file_route(rclient, drive, admin, tmp_path):
    out = job(drive, "done", "20260101-000002-c", rc=0, seconds=1)
    (out / "out.mp4").write_bytes(b"video")
    (drive / "secret.txt").write_text("secret")
    ok = rclient.get("/dashboard/renderer/20260101-000002-c/out.mp4", headers=admin)
    assert ok.status_code == 200 and ok.content == b"video"
    for url in (
        "/dashboard/renderer/..%2F/out.mp4",
        "/dashboard/renderer/%2e%2e/secret.txt",
        "/dashboard/renderer/20260101-000002-c/%2e%2e%2Fsecret.txt",
        "/dashboard/renderer/20260101-000002-c/..%2f..%2fsecret.txt",
        "/dashboard/renderer/20260101-000002-c/missing.mp4",
    ):
        assert rclient.get(url, headers=admin).status_code == 404, url


def test_file_route_off(client, admin):
    assert client.get("/dashboard/renderer/a/b.mp4", headers=admin).status_code == 404
