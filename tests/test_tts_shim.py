"""tools/tts-shim: request handling, caching and retries against a fake gateway (no network, no ffmpeg)."""

from __future__ import annotations

import importlib.util
import json
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "tts_shim", Path(__file__).resolve().parents[1] / "tools" / "tts-shim" / "tts_shim.py"
)
tts_shim = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tts_shim)


def serve(handler_cls):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


@pytest.fixture
def gateway():
    """Fake museai: POST /v1/videos queues a task, GET returns it done with a media URL."""
    state = {"prompts": [], "fail_first": 0, "auth": []}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            state["auth"].append(self.headers.get("Authorization"))
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state["prompts"].append(body)
            self._json({"id": f"t{len(state['prompts'])}", "status": "queued"})

        def do_GET(self):
            if self.path.startswith("/media/"):
                data = b"MP4"
                self.send_response(200)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            if state["fail_first"]:
                state["fail_first"] -= 1
                self._json({"status": "failed"})
                return
            self._json({"status": "succeeded", "result": {"url": f"{base}/media/v.mp4"}})

        def _json(self, obj):
            data = json.dumps(obj).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    server, base = serve(Handler)
    yield base, state
    server.shutdown()


@pytest.fixture
def no_ffmpeg(monkeypatch):
    monkeypatch.setattr(tts_shim, "extract_audio", lambda mp4: b"WAV:" + mp4)


def make_synth(base, tmp_path, **kw):
    return tts_shim.Synth(base, "k-test", tmp_path / "cache", poll_seconds=0, retry_seconds=0, **kw)


def test_video_seconds_clamps():
    assert tts_shim.video_seconds("word") == 5
    assert tts_shim.video_seconds("w " * 1000) == 60
    assert tts_shim.video_seconds("w " * 23) == 14


def test_unknown_voice_falls_back_to_alloy():
    assert "a calm British woman" in tts_shim.build_prompt("hi", "nope")
    assert "a deep British man" in tts_shim.build_prompt("hi", "onyx")


def test_speech_renders_once_then_serves_cache(gateway, tmp_path, no_ffmpeg):
    base, state = gateway
    synth = make_synth(base, tmp_path)
    assert synth.speech("Hello there.", "nova") == b"WAV:MP4"
    assert synth.speech("Hello there.", "nova") == b"WAV:MP4"
    assert len(state["prompts"]) == 1
    assert state["prompts"][0]["duration"] == 5
    assert '"Hello there."' in state["prompts"][0]["prompt"]
    assert state["auth"] == ["Bearer k-test"]


def test_failed_render_is_resubmitted(gateway, tmp_path, no_ffmpeg):
    base, state = gateway
    state["fail_first"] = 2
    assert make_synth(base, tmp_path).speech("Again.") == b"WAV:MP4"
    assert len(state["prompts"]) == 3


def test_http_speech_and_errors(gateway, tmp_path, no_ffmpeg):
    base, _ = gateway
    server, url = serve(tts_shim.make_handler(make_synth(base, tmp_path)))
    try:
        req = urllib.request.Request(
            f"{url}/v1/audio/speech",
            data=json.dumps({"input": "Hi.", "voice": "echo"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as r:
            assert r.headers["Content-Type"] == "audio/wav"
            assert r.read() == b"WAV:MP4"

        with urllib.request.urlopen(f"{url}/v1/models") as r:
            assert json.load(r)["data"][0]["id"] == "muse-tts"

        bad = urllib.request.Request(f"{url}/v1/audio/speech", data=b"{}")
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(bad)
        assert e.value.code == 400
    finally:
        server.shutdown()


def test_api_key_from_env_wins(monkeypatch, tmp_path):
    key_file = tmp_path / "api_key"
    key_file.write_text("from-file\n")
    monkeypatch.delenv("MUSE_TTS_API_KEY", raising=False)
    assert tts_shim.read_api_key(key_file) == "from-file"
    monkeypatch.setenv("MUSE_TTS_API_KEY", "from-env")
    assert tts_shim.read_api_key(key_file) == "from-env"
