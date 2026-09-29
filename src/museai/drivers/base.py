"""Driver interface: the only layer that knows how to talk to muse.ai.

A driver turns normalised requests into upstream actions for one account at a
time. Scheduling, retries, persistence and the OpenAI wire format all live
above this layer, so a new transport (browser automation, direct HTTP/WebSocket
protocol, ...) only needs to implement this class.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from ..accounts.model import Account
from ..errors import FeatureNotImplemented

ProgressCallback = Callable[[int], None]
"""Receives a 0-100 progress estimate."""


@dataclass
class InputImage:
    data: bytes
    mime: str = "image/png"


@dataclass
class ChatRequest:
    prompt: str
    model: str
    images: list[InputImage] = field(default_factory=list)
    timeout: float = 300.0
    first_token_timeout: float = 45.0
    conversation_hint: str | None = None
    turns: list[tuple[str, str]] = field(default_factory=list)
    """Role/text pairs of the request, used to continue a hot page instead of resending history."""
    cancel: asyncio.Event | None = None


@dataclass
class ImageRequest:
    prompt: str
    model: str
    size: str | None = None
    """Aspect ratio such as ``1:1`` / ``16:9`` or an OpenAI size like ``1024x1024``."""
    n: int = 1
    reference_images: list[InputImage] = field(default_factory=list)
    timeout: float = 240.0
    on_progress: ProgressCallback | None = None
    cancel: asyncio.Event | None = None


@dataclass
class VideoRequest:
    prompt: str
    model: str
    size: str | None = None
    duration: int | None = None
    first_frame: InputImage | None = None
    timeout: float = 600.0
    on_progress: ProgressCallback | None = None
    cancel: asyncio.Event | None = None


@dataclass
class MediaResult:
    data: bytes
    mime: str
    kind: Literal["image", "video"]
    width: int | None = None
    height: int | None = None
    revised_prompt: str | None = None


@dataclass
class SessionInfo:
    ok: bool
    cookies: dict[str, str] = field(default_factory=dict)
    cookie_expires: dict[str, int] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DriverCapabilities:
    chat: bool = False
    chat_images: bool = False
    image: bool = False
    image_edit: bool = False
    video: bool = False
    renew_session: bool = False
    quota: bool = False


class MuseDriver(ABC):
    name: str = "base"
    requires_account: bool = True
    capabilities: DriverCapabilities = DriverCapabilities()

    async def startup(self) -> None:  # noqa: B027
        """Acquire long-lived resources (browser process, HTTP client, ...)."""

    async def shutdown(self) -> None:  # noqa: B027
        """Release resources acquired in ``startup``."""

    async def health(self) -> dict[str, Any]:
        return {"driver": self.name, "ok": True}

    @abstractmethod
    def chat_stream(self, account: Account, req: ChatRequest) -> AsyncIterator[str]:
        """Yield assistant text deltas. Implementations are async generators."""

    async def generate_image(self, account: Account, req: ImageRequest) -> list[MediaResult]:
        raise FeatureNotImplemented(f"driver '{self.name}' does not support image generation")

    async def generate_video(self, account: Account, req: VideoRequest) -> MediaResult:
        raise FeatureNotImplemented(f"driver '{self.name}' does not support video generation")

    async def renew_session(self, account: Account) -> SessionInfo:
        raise FeatureNotImplemented(f"driver '{self.name}' does not support session renewal")

    async def quota(self, account: Account) -> dict[str, Any]:
        raise FeatureNotImplemented(f"driver '{self.name}' does not support quota lookup")
