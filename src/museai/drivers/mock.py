"""Offline driver used for development, tests and front-end work.

It needs no accounts and returns deterministic output, so the whole API surface
can be exercised without touching muse.ai.
"""

from __future__ import annotations

import asyncio
import struct
import zlib
from collections.abc import AsyncIterator

from ..accounts.model import Account
from .base import (
    ChatRequest,
    DriverCapabilities,
    ImageRequest,
    MediaResult,
    MuseDriver,
    SessionInfo,
    VideoRequest,
)


def _solid_png(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    row = b"\x00" + bytes(rgb) * width
    raw = row * height
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


class MockDriver(MuseDriver):
    name = "mock"
    requires_account = False
    capabilities = DriverCapabilities(
        chat=True, chat_images=True, image=True, image_edit=True, video=True, renew_session=True
    )

    def __init__(self, delay: float = 0.01) -> None:
        self.delay = delay

    async def chat_stream(self, account: Account, req: ChatRequest) -> AsyncIterator[str]:
        reply = f"[mock:{req.model}] You said: {req.prompt[-200:]}"
        if req.images:
            reply += f" (with {len(req.images)} image(s))"
        for i in range(0, len(reply), 8):
            if req.cancel and req.cancel.is_set():
                return
            await asyncio.sleep(self.delay)
            yield reply[i : i + 8]

    async def generate_image(self, account: Account, req: ImageRequest) -> list[MediaResult]:
        results = []
        for i in range(max(1, req.n)):
            if req.on_progress:
                req.on_progress(int((i + 1) / max(1, req.n) * 100))
            await asyncio.sleep(self.delay)
            color = (40 + 50 * i % 200, 120, 200)
            results.append(
                MediaResult(
                    data=_solid_png(64, 64, color),
                    mime="image/png",
                    kind="image",
                    width=64,
                    height=64,
                    revised_prompt=req.prompt,
                )
            )
        return results

    async def generate_video(self, account: Account, req: VideoRequest) -> MediaResult:
        for p in (10, 40, 70, 100):
            await asyncio.sleep(self.delay)
            if req.on_progress:
                req.on_progress(p)
        # Not a playable video; placeholder bytes with the right mime for plumbing tests.
        return MediaResult(data=b"\x00\x00\x00\x18ftypmp42mock", mime="video/mp4", kind="video")

    async def renew_session(self, account: Account) -> SessionInfo:
        return SessionInfo(ok=True, meta={"driver": "mock"})
