# TODO

This file lists every reserved module and all outstanding work. It is the single source of truth for task assignment.

**How to claim a task**: open an issue titled `[Claim] <ID> <task name>` (for example `[Claim] B1 Direct HTTP protocol driver`), put your GitHub ID in the "Owner" column below, and submit a PR, so that nobody duplicates the work. See [CONTRIBUTING.md](CONTRIBUTING.md) for conventions and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the design.

Priorities: **P0** must be done first · **P1** core feature · **P2** better experience · **P3** nice to have

---

## Overview

| ID | Task | Priority | Location | Owner | Status |
|---|---|---|---|---|---|
| A1 | Install dependencies, get tests and lint passing | P0 | `tests/` | | Not started |
| A2 | Test the browser driver with real accounts | P0 | `drivers/browser/` | | Not started |
| A3 | Verify how image/video generation is triggered | P0 | `drivers/browser/driver.py` | | Not started |
| A4 | Verify session renewal | P0 | `upstream/muse.py` | | Not started |
| A5 | Verify the Docker image builds and runs | P1 | `Dockerfile` | | Not started |
| A6 | Enable GitHub Actions CI | P1 | `.github/workflows/ci.yml` | | Not started |
| B1 | Direct HTTP protocol driver | P1 | `drivers/http/` | | Not started |
| B2 | Reuse conversation threads to cut first-token latency | P2 | `drivers/browser/` | | Done |
| B3 | Quota lookup | P2 | `MuseDriver.quota` | | Not started |
| C1 | `/v1/responses` endpoint | P1 | `api/routes/responses.py` | | Not started |
| C2 | `/v1/images/edits` endpoint | P1 | `api/routes/images.py` | | Not started |
| C3 | Emulated tool calling | P2 | `core/prompt.py` | | Not started |
| C4 | Streaming heartbeats to avoid client timeouts | P2 | `api/routes/chat.py` | | Not started |
| D1 | Support more cookie import formats | P1 | `api/routes/admin.py` | | Not started |
| D2 | Cookie import browser extension | P2 | `extension/` (new) | | Not started |
| D3 | Web admin console | P2 | `web/` (new) | | Not started |
| D4 | SQLite / Redis storage backends | P3 | `accounts/store.py` | | Not started |
| E1 | Automatic media cleanup | P2 | `core/media.py` | | Not started |
| E2 | Multiple API keys and rate limiting | P3 | `api/deps.py` | | Not started |
| E3 | Observability (metrics, logs) | P3 | `observability/` (new) | | Not started |

---

## A. Verification and live testing

All v0.1 code is written but has never been run. This group must be done first; otherwise later work has no reliable foundation.

### A1 Install dependencies, get tests and lint passing · P0
- Run `pip install -e '.[dev]'`, `pytest` and `ruff check .`, and fix every failure.
- All tests use the mock driver and make no network calls.
- **Done when**: `pytest` and `ruff check .` both pass locally.

### A2 Test the browser driver with real accounts · P0
- Import cookies from a real muse.ai account, set `MUSE2API_DRIVER=browser`, and verify each of the following:
  - the page reaches the "ready" state (`dom.PAGE_STATE`);
  - writing into the input box and clicking the send button work (`dom.fill_input`, `dom.CLICK_SEND`);
  - assistant replies are read correctly, with no duplicated or missing characters in the stream (`dom.CHAT_STATE`);
  - end-of-reply detection is accurate: it neither cuts replies short nor waits too long;
  - an expired cookie raises `UpstreamAuthError`, and running out of quota raises `UpstreamQuotaError`.
- The DOM selectors have not been checked against the real page yet and may be wrong or outdated; update `drivers/browser/dom.py` to match the actual page.
- Verify that multi-account isolation via `Target.createBrowserContext` works.
- **Done when**: two or more accounts reliably complete streaming and non-streaming chats, and the findings are written up under `docs/`.

### A3 Verify how image/video generation is triggered · P0
- Generation is currently triggered by prefixing the prompt with "Generate an image / a video" (`BrowserDriver._media_prompt`). Confirm that muse.ai reliably generates media when asked this way.
- If the web app has a dedicated image/video entry point (a button, a mode switch, ...), use that instead.
- Confirm that aspect ratio (`16:9`, ...) and video duration are actually honoured.
- Confirm the attachment selector for results (`dom.ATTACHMENT`) and the download logic (`dom.fetch_as_base64`).
- **Done when**: text-to-image and text-to-video with a first frame both reliably produce files.

### A4 Verify session renewal · P0
- Verify that calling `/api/session` really returns fresh cookies and extends the lifetime of `hatch_vml`.
- Verify the parameters and effect of `/api/hatch/vm/wake`.
- Determine a sensible renewal interval and update the default of `MUSE2API_KEEPALIVE_INTERVAL`.
- **Done when**: with keepalive enabled, an account stays usable for three days or more.

### A5 Verify the Docker image builds and runs · P1
- `docker compose up -d --build` succeeds, and the browser driver can start Chromium inside the container.
- Check whether Chromium's sandbox flags need adjusting when the container runs as a non-root user.

### A6 Enable GitHub Actions CI · P1
- The repository already contains `.github/workflows/ci.yml` (lint and tests on Python 3.10 / 3.12).
- Pushing this file with a token requires the `workflow` scope; pushing over SSH does not.
- **Done when**: PRs run CI automatically and show the result.

---

## B. Drivers

### B1 Direct HTTP protocol driver · P1
Talk to muse.ai's backend directly, without a browser. This removes Chromium and significantly reduces latency and memory usage.
1. Capture and analyse the web app's traffic when sending a message (endpoints, handshake, framing, auth headers) and document it in `docs/protocol.md`.
2. Implement a transport client under `drivers/http/` that opens a session using the account's cookies.
3. Implement `chat_stream` by converting upstream incremental events into text deltas.
4. Implement image and video generation and attachment download.
5. Use recorded real responses as test fixtures; CI must not contact the real service.
- A more detailed step-by-step breakdown is in the docstring at the top of `drivers/http/driver.py`.
- **Done when**: chat works with `MUSE2API_DRIVER=http` and passes the same API tests as the browser driver.

### B2 Reuse conversation threads to cut first-token latency · P2
Done. A follow-up whose `messages` continue the conversation already on the page stays on that tab and only the new user text is sent. Pass `user` to keep one person on one account (`affinity`, the default). A different history, a different `user`, a stuck page, or a long thread opens a fresh page.

### B3 Quota lookup · P2
- Implement `MuseDriver.quota` to read the account's plan, weekly usage and remaining quota.
- Show quota in `/admin/accounts`, and let scheduling prefer accounts with plenty of quota left.
- Also declare `quota=True` in `DriverCapabilities` and add a fake implementation to `MockDriver`.

---

## C. Protocol

### C1 `/v1/responses` endpoint · P1
- Support the OpenAI Responses API (used by default by newer clients such as Codex).
- Convert `input` and `instructions` and pass them to `flatten_messages`, reusing `Gateway.chat_stream`.
- Streaming must emit Responses API events (`response.created`, `response.output_text.delta`, `response.completed`, ...).
- **Done when**: the official OpenAI SDK's `client.responses.create()` works both streaming and non-streaming.

### C2 `/v1/images/edits` endpoint · P1
- Parse the multipart form (`image` / `image[]`, `prompt`, `size`, `response_format`).
- Put the uploaded images into `ImageRequest.reference_images` and reuse the response shaping from `generate_images`.
- **Done when**: the official SDK's `client.images.edit()` works.

### C3 Emulated tool calling · P2
- muse.ai has no native function calling. The idea is to describe the available tools and an output format in the prompt, parse tool calls out of the reply, and convert them to OpenAI's `tool_calls` format.
- muse.ai may refuse to follow the requested format, so verify feasibility first and ship it behind a config flag that is off by default.

### C4 Streaming heartbeats to avoid client timeouts · P2
- Streaming requests wait for the first chunk before responding, which can take up to 45 seconds (`first_token_timeout`). Some clients and reverse proxies time out in the meantime.
- Approach: optionally return 200 immediately and send SSE comment lines (`: keepalive`) as heartbeats while waiting. The trade-off is that errors can then no longer be reported as HTTP status codes.

---

## D. Accounts and administration

### D1 Support more cookie import formats · P1
- `/admin/accounts` currently only accepts `{"cookies": {"name": "value"}}`.
- Add support for a raw `Cookie: a=1; b=2` request header string and for JSON arrays exported by extensions such as EditThisCookie (which include expiry times).
- Support importing multiple accounts in one request.

### D2 Cookie import browser extension · P2
- Create an `extension/` directory with a Chrome / Edge extension.
- With one click in a browser that is logged in to muse.ai, it reads all cookies (including HttpOnly cookies that page scripts cannot see, with their expiry times) and pushes them to `/admin/accounts`.
- Requires handling CORS on the server side.

### D3 Web admin console · P2
- Create a `web/` directory, built on the existing `/admin/*` endpoints.
- Features: service status, account list (state / cooldown / errors / quota), importing and editing accounts, task list, media library, and an interactive API tester.
- Any tech stack is fine. Prefer a build output that FastAPI can serve as static files, so deployment gains no extra steps.

### D4 SQLite / Redis storage backends · P3
- Implement the `AccountStore` protocol in `accounts/store.py`, selectable through configuration.
- A Redis backend prepares for multi-instance deployments (the per-account concurrency counters would then also need to be shared across processes).

---

## E. Operations

### E1 Automatic media cleanup · P2
- Generated images and videos stay in `data/media/` forever; there is no cleanup.
- Add retention-time or size-limit settings and clean up periodically in the background.

### E2 Multiple API keys and rate limiting · P3
- There is currently a single API key and a single admin key.
- Support multiple keys (each with its own rate limit and usage statistics), managed through the admin API.

### E3 Observability · P3
- Expose Prometheus metrics: request count, latency, first-token latency, per-account success/failure counts, queue wait time.
- Structured request logs with a unique ID per request for troubleshooting.
