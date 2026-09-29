"""Chromium process management."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import shutil
from pathlib import Path

import httpx

log = logging.getLogger(__name__)

_CANDIDATES = (
    "chromium",
    "chromium-browser",
    "google-chrome",
    "google-chrome-stable",
    "/usr/bin/chromium",
    "/snap/bin/chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)


def find_chromium(configured: str = "") -> str:
    for c in ((configured,) if configured else ()) + _CANDIDATES:
        if c and (os.path.isfile(c) or shutil.which(c)):
            return c
    raise FileNotFoundError(
        "Chromium/Chrome not found; install it or set MUSE2API_CHROMIUM_PATH"
    )


class ChromiumProcess:
    def __init__(self, executable: str, port: int, profile_dir: Path, headless: bool = True,
                 proxy: str = ""):
        self.executable = executable
        self.port = port
        self.profile_dir = profile_dir
        self.headless = headless
        self.proxy = proxy
        self.proc: asyncio.subprocess.Process | None = None

    @property
    def http_base(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    async def browser_ws_url(self) -> str | None:
        try:
            # Local DevTools port must not follow http_proxy/https_proxy.
            async with httpx.AsyncClient(timeout=2, trust_env=False) as client:
                r = await client.get(f"{self.http_base}/json/version")
                return r.json().get("webSocketDebuggerUrl")
        except (httpx.HTTPError, ValueError):
            return None

    async def start(self) -> str:
        """Start (or attach to an already running) Chromium; return the browser ws URL."""
        if url := await self.browser_ws_url():
            log.info("attached to existing Chromium on port %s", self.port)
            return url

        self.profile_dir.mkdir(parents=True, exist_ok=True)
        for lock in ("SingletonLock", "SingletonSocket", "SingletonCookie"):
            with contextlib.suppress(FileNotFoundError):
                (self.profile_dir / lock).unlink()

        args = [
            self.executable,
            f"--remote-debugging-port={self.port}",
            "--remote-allow-origins=*",
            f"--user-data-dir={self.profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-dev-shm-usage",
            "--disable-background-networking",
            "--autoplay-policy=no-user-gesture-required",
            "--window-size=1440,2200",
            "about:blank",
        ]
        if self.proxy:
            args.insert(1, f"--proxy-server={self.proxy}")
        if self.headless:
            args[1:1] = ["--headless=new", "--disable-gpu"]
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            args.insert(1, "--no-sandbox")

        log.info("launching Chromium: %s", self.executable)
        self.proc = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
        )
        for _ in range(60):
            if url := await self.browser_ws_url():
                return url
            if self.proc.returncode is not None:
                break
            await asyncio.sleep(0.5)
        raise RuntimeError("Chromium did not expose a DevTools endpoint")

    async def stop(self) -> None:
        if self.proc and self.proc.returncode is None:
            self.proc.terminate()
            try:
                await asyncio.wait_for(self.proc.wait(), 10)
            except asyncio.TimeoutError:
                self.proc.kill()
        self.proc = None
