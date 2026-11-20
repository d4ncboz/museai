#!/usr/bin/env python3
"""OpenAI-compatible text-to-speech on top of the museai video route.

POST /v1/audio/speech {"input": "...", "voice": "alloy"} -> audio/wav (mono, 24 kHz).

muse.ai has no speech endpoint, so each request renders a short still video in which a narrator
reads the text, then ffmpeg keeps only the audio and trims leading/trailing silence. Results are
cached on disk by (voice, text), so a retried batch costs nothing.

Stdlib only; needs ffmpeg on PATH and a running museai gateway. See tools/tts-shim/README.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

VOICES = {
    "alloy": "a calm British woman",
    "echo": "a calm British man",
    "fable": "a warm British woman",
    "onyx": "a deep British man",
    "nova": "a bright young British woman",
    "shimmer": "a friendly British woman",
}
DONE = ("succeeded", "completed")
FINAL = (*DONE, "failed", "error", "cancelled")
SILENCE = (
    "silenceremove=start_periods=1:start_threshold=-45dB"
    ":stop_periods=1:stop_threshold=-45dB:stop_duration=0.6"
)


def video_seconds(text: str) -> int:
    """Clip length for a script: ~2.3 words/s plus slack, clamped to 5..60 s."""
    return min(60, max(5, int(len(text.split()) / 2.3) + 4))


def build_prompt(text: str, voice: str) -> str:
    speaker = VOICES.get(voice, VOICES["alloy"])
    return (
        f"A plain still scene. {speaker} speaks this script exactly, word for word, at a natural "
        f'pace, with no music, no extra words, no added sentences: "{text}"'
    )


def cache_path(cache_dir: Path, text: str, voice: str) -> Path:
    digest = hashlib.sha256(f"{voice}|{text}".encode()).hexdigest()[:24]
    return cache_dir / f"{digest}.wav"


class Synth:
    def __init__(
        self,
        gateway: str,
        api_key: str,
        cache_dir: Path,
        concurrency: int = 3,
        poll_seconds: float = 5,
        retry_seconds: float = 20,
        attempts: int = 6,
    ):
        self.gateway = gateway.rstrip("/")
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self.cache_dir = cache_dir
        self.sem = threading.Semaphore(concurrency)  # one render per muse account
        self.poll_seconds = poll_seconds
        self.retry_seconds = retry_seconds
        self.attempts = attempts
        cache_dir.mkdir(parents=True, exist_ok=True)

    def _call(self, path: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.gateway + path, data=data, headers=self.headers)
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)

    def speech(self, text: str, voice: str = "alloy") -> bytes:
        path = cache_path(self.cache_dir, text, voice)
        if path.exists():
            return path.read_bytes()
        last: Exception | None = None
        for _ in range(self.attempts):
            try:
                wav = self.render(text, voice)
            except Exception as e:  # noqa: BLE001 - retried, then re-raised
                last = e
                print(f"tts-shim: render failed, retrying: {e!r}", file=sys.stderr, flush=True)
                time.sleep(self.retry_seconds)
                continue
            path.write_bytes(wav)
            return wav
        assert last is not None
        raise last

    def render(self, text: str, voice: str) -> bytes:
        body = {"prompt": build_prompt(text, voice), "duration": video_seconds(text)}
        with self.sem:
            video = None
            for _ in range(3):
                task = self._call("/v1/videos", body)
                for _ in range(180):
                    time.sleep(self.poll_seconds)
                    video = self._call(f"/v1/videos/{task['id']}")
                    if video["status"] in FINAL:
                        break
                if video and video["status"] in DONE:
                    break
            else:
                raise RuntimeError("video render failed 3 times")
            req = urllib.request.Request(video["result"]["url"], headers=self.headers)
            with urllib.request.urlopen(req, timeout=120) as r:
                mp4 = r.read()
        return extract_audio(mp4)


def extract_audio(mp4: bytes) -> bytes:
    with tempfile.TemporaryDirectory() as d:
        src, dst = Path(d, "v.mp4"), Path(d, "a.wav")
        src.write_bytes(mp4)
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-i",
                str(src),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "24000",
                "-af",
                SILENCE,
                str(dst),
            ],
            check=True,
        )
        return dst.read_bytes()


def make_handler(synth: Synth) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.rstrip("/") != "/v1/models":
                self.send_error(404)
                return
            self._json(200, {"object": "list", "data": [{"id": "muse-tts", "object": "model"}]})

        def do_POST(self):
            if self.path.rstrip("/") != "/v1/audio/speech":
                self.send_error(404)
                return
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
                text = body["input"]
            except (ValueError, KeyError, TypeError):
                self._json(400, {"error": {"message": "body needs JSON with 'input'"}})
                return
            try:
                wav = synth.speech(text, body.get("voice", "alloy"))
            except Exception as e:  # noqa: BLE001 - reported to the client
                self._json(502, {"error": {"message": str(e)[:200]}})
                return
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(wav)))
            self.end_headers()
            self.wfile.write(wav)

        def _json(self, code: int, obj: dict) -> None:
            data = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    return Handler


def read_api_key(key_file: Path) -> str:
    key = os.environ.get("MUSE_TTS_API_KEY", "").strip()
    if key:
        return key
    if not key_file.exists():
        sys.exit(f"tts-shim: no API key: set MUSE_TTS_API_KEY or create {key_file}")
    return key_file.read_text().strip()


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--gateway", default=os.environ.get("MUSE_TTS_GATEWAY", "http://127.0.0.1:18610")
    )
    p.add_argument("--key-file", type=Path, default=REPO / "data" / "api_key")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=int(os.environ.get("MUSE_TTS_PORT", "18620")))
    p.add_argument(
        "--concurrency",
        type=int,
        default=int(os.environ.get("MUSE_TTS_CONCURRENCY", "3")),
        help="parallel renders; one per muse account in the pool",
    )
    p.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(os.environ.get("MUSE_TTS_CACHE", Path.home() / ".cache" / "museai-tts")),
    )
    a = p.parse_args(argv)
    synth = Synth(a.gateway, read_api_key(a.key_file), a.cache_dir, a.concurrency)
    print(f"tts-shim: http://{a.host}:{a.port}/v1/audio/speech -> {a.gateway}", flush=True)
    ThreadingHTTPServer((a.host, a.port), make_handler(synth)).serve_forever()


if __name__ == "__main__":
    main()
