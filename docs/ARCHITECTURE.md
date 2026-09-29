# Architecture

## Layers

```
┌─────────────────────────────────────────────────────────────┐
│ api/            OpenAI protocol layer (routes, schemas, auth)│
│   routes/chat.py  images.py  videos.py  media.py  admin.py   │
├─────────────────────────────────────────────────────────────┤
│ services/       Service layer                                │
│   gateway.py    Runs driver calls on pooled accounts,        │
│                 with failover                                │
│   tasks.py      Background long-running tasks (video, ...)   │
│   container.py  Dependency wiring (app.state.services)       │
├──────────────────────────────┬──────────────────────────────┤
│ accounts/  Account pool       │ core/  Upstream-agnostic     │
│   model / store / pool        │   models   registry, aliases │
│   keepalive  session renewal  │   prompt   messages → prompt │
│                               │   media    storage, inputs   │
├──────────────────────────────┴──────────────────────────────┤
│ drivers/        The only layer that talks to muse.ai         │
│   base.py   MuseDriver interface + request/result types      │
│   mock.py   Offline driver                                   │
│   browser/  Chromium + CDP (cdp.py / chromium.py / dom.py)   │
│   http/     Direct protocol (reserved)                       │
├─────────────────────────────────────────────────────────────┤
│ upstream/muse.py  Upstream constants (URLs, cookie names)    │
│                   and HTTP session renewal                   │
└─────────────────────────────────────────────────────────────┘
```

Dependencies flow strictly downward: `api → services → accounts/core → drivers → upstream`. Routes never call a driver directly, and drivers know nothing about the HTTP wire format.

## Lifecycle of a chat request

1. `routes/chat.py` validates the request, `resolve_model` resolves aliases, and `flatten_messages` merges the conversation into a single prompt and extracts images.
2. `Gateway.chat_stream` leases an account through `AccountPool.lease()` (chosen by the configured strategy and subject to the per-account concurrency limit).
3. It calls `driver.chat_stream(account, ChatRequest)` and receives text deltas.
4. On failure:
   - `UpstreamAuthError`: the account is marked `invalid`;
   - `UpstreamQuotaError`: the account cools down for at least one hour;
   - any other retryable error: the account cools down for `account_cooldown` seconds;
   - if nothing has been sent to the client yet, the request is retried on another account (up to `max_failover` times).
5. For streaming, the route pulls the first delta before returning 200, so errors such as "no account available" or "upstream authentication failed" come back with the right HTTP status code.

## Driver contract

```python
class MuseDriver(ABC):
    name: str
    requires_account: bool
    capabilities: DriverCapabilities

    async def startup(self) / shutdown(self)
    async def health(self) -> dict
    def chat_stream(self, account, ChatRequest) -> AsyncIterator[str]   # required
    async def generate_image(self, account, ImageRequest) -> list[MediaResult]
    async def generate_video(self, account, VideoRequest) -> MediaResult
    async def renew_session(self, account) -> SessionInfo
    async def quota(self, account) -> dict
```

- Unimplemented capabilities raise `FeatureNotImplemented` (HTTP 501) so the upper layers can degrade gracefully.
- Errors must be mapped to the `Upstream*` types in `errors.py`; the account pool relies on them to decide an account's state.
- Drivers are not responsible for retries, persistence or building URLs.

## Browser driver notes

- One Chromium process. Each account gets its own isolated context via `Target.createBrowserContext` plus one reused tab, so switching accounts never requires clearing cookies.
- Follow-up chat from the same owner stays on that conversation and only the new user text is sent. The thread URL is stored on the account, so a later request reopens that muse chat instead of `/thread/new`. A different history or a different `user` opens a fresh page. The default pool strategy is `affinity`.
- All DOM selectors and in-page scripts live in `drivers/browser/dom.py`. When muse.ai changes its UI, this is usually the only file that needs updating.
- Text is written into the textarea through the native value setter plus an `input` event, so React picks it up and long prompts stay fast. If the send button cannot be found, it falls back to pressing Enter.
- Output detection polls the text of the last assistant bubble and emits the new part. The reply is considered finished once the Stop button is gone and the text has stopped changing.
- Media: wait for a new attachment node, then `fetch()` its `blob:` URL inside the page and return the bytes as base64.

## Roadmap

Reserved modules and outstanding work are tracked in [TODO.md](../TODO.md) at the repository root.
