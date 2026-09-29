"""HTTP/WebSocket protocol driver (reserved).

Goal: talk to muse.ai's backend directly, without a browser. This removes the
Chromium dependency and cuts latency and memory by an order of magnitude.

Work breakdown (open for contributors, see CONTRIBUTING.md):

1. Capture the web client's traffic after sending a message and document the
   transport (endpoint(s), handshake, framing, auth headers) in
   ``docs/protocol.md``.
2. Implement a transport client under ``drivers/http/`` that opens a session for
   an ``Account`` using its cookies.
3. Implement ``chat_stream`` by mapping upstream incremental events to text
   deltas.
4. Implement media generation and attachment download.
5. Add recorded-fixture tests (no live traffic in CI).

Until then every capability raises ``FeatureNotImplemented`` (HTTP 501), except
session renewal, which already works over plain HTTP.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from ...accounts.model import Account
from ...config import Settings
from ...errors import FeatureNotImplemented
from ...upstream import muse
from ..base import ChatRequest, DriverCapabilities, MuseDriver, SessionInfo


class HttpDriver(MuseDriver):
    name = "http"
    capabilities = DriverCapabilities(renew_session=True)

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def chat_stream(self, account: Account, req: ChatRequest) -> AsyncIterator[str]:
        raise FeatureNotImplemented("http driver chat is not implemented yet; use driver=browser")
        yield ""  # pragma: no cover  (makes this an async generator)

    async def renew_session(self, account: Account) -> SessionInfo:
        return await muse.renew_session(account.cookies)
