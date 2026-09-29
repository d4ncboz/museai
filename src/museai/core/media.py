"""Local media storage for generated images/videos and helpers for image inputs."""

from __future__ import annotations

import base64
import mimetypes
import re
import uuid
from pathlib import Path

import httpx

from ..errors import InvalidRequest, NotFound

_EXT_BY_MIME = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
}
_SAFE_NAME = re.compile(r"^[A-Za-z0-9_\-]+\.[A-Za-z0-9]+$")


class MediaStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, data: bytes, mime: str, prefix: str = "m") -> str:
        ext = _EXT_BY_MIME.get(mime.split(";")[0].strip().lower(), ".bin")
        name = f"{prefix}_{uuid.uuid4().hex[:16]}{ext}"
        (self.root / name).write_bytes(data)
        return name

    def path_of(self, name: str) -> Path:
        if not _SAFE_NAME.match(name):
            raise NotFound("media not found")
        p = self.root / name
        if not p.is_file():
            raise NotFound("media not found")
        return p

    @staticmethod
    def mime_of(name: str) -> str:
        return mimetypes.guess_type(name)[0] or "application/octet-stream"


async def load_image_ref(ref: str, *, timeout: float = 20.0) -> tuple[bytes, str]:
    """Decode a data URL or download an http(s) URL. Returns ``(bytes, mime)``."""
    ref = ref.strip()
    if ref.startswith("data:"):
        header, _, payload = ref.partition(",")
        mime = header[5:].split(";")[0] or "image/png"
        try:
            return base64.b64decode(payload), mime
        except ValueError as exc:
            raise InvalidRequest("invalid base64 image data") from exc
    if ref.startswith(("http://", "https://")):
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(ref)
            resp.raise_for_status()
            mime = resp.headers.get("content-type", "image/png").split(";")[0]
            return resp.content, mime
    try:
        return base64.b64decode(ref, validate=True), "image/png"
    except ValueError as exc:
        raise InvalidRequest("image must be a data URL, http(s) URL or base64 string") from exc
