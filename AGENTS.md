# AGENTS.md — MUSEAI ENGINEERING & ARCHITECTURE SPECIFICATION
# Machine-readable technical contract for AI Coding Agents (Hermes, Claude Code, Cursor, Codex)
---

## 1. PROJECT IDENTITY & PURPOSE

`museai` is an asynchronous gateway proxy that exposes the [muse.ai](https://muse.ai) personal AI agent and workspace as a production-ready, **OpenAI-compatible REST API** (`/v1/chat/completions`, `/v1/images/generations`, `/v1/videos`, `/v1/models`).

It bridges browser-only web sessions into standard LLM client interfaces (NextChat, LobeChat, Cherry Studio, LangChain, OpenAI SDKs) and multi-model gateways (specifically **9Router**).

---

## 2. REPOSITORY ARCHITECTURE

```
museai/
├── src/museai/
│   ├── app.py                 # FastAPI application factory, lifecycle, middleware
│   ├── config.py              # Pydantic Settings (env vars prefix MUSE2API_)
│   ├── errors.py              # Custom Exception hierarchy -> HTTP & OpenAI JSON error bodies
│   ├── api/
│   │   ├── deps.py            # Dependency injection, bearer authentication
│   │   ├── schemas.py         # OpenAI-compliant Pydantic request/response schemas
│   │   └── routes/            # chat.py, images.py, videos.py, media.py, models.py, admin.py
│   ├── services/
│   │   ├── container.py       # Dependency container wiring
│   │   ├── gateway.py         # Account lease, failover retry loop, streaming orchestration
│   │   ├── tasks.py           # Long-running async background tasks (video generation)
│   │   ├── oauth.py           # OAuth connect + token refresh for auto-posting (docs/auto-post.md)
│   │   └── publishers/        # Auto-post drivers: YouTube, TikTok, Facebook, Instagram, mock
│   ├── accounts/
│   │   ├── model.py           # Account dataclass, status lifecycle (active, cooling, disabled)
│   │   ├── pool.py            # AccountPool: scheduling (lru, round_robin, affinity), concurrency
│   │   ├── store.py           # JSON file persistence for accounts
│   │   └── keepalive.py       # Periodic session renewal loop
│   ├── core/
│   │   ├── media.py           # Media disk storage & URL generation
│   │   ├── models.py          # Public model catalog & alias resolution (gpt-4o, gpt-5 -> muse-chat)
│   │   └── prompt.py          # Multi-turn message flattening & system prompt formatting
│   ├── drivers/
│   │   ├── base.py            # MuseDriver ABC interface & standardized request/response types
│   │   ├── mock.py            # Offline mock driver for zero-network testing
│   │   ├── browser/           # Headless Chromium driver via Chrome DevTools Protocol (CDP)
│   │   │   ├── cdp.py         # Lightweight async WebSocket CDP client
│   │   │   ├── chromium.py    # Subprocess lifecycle & automatic binary discovery
│   │   │   ├── dom.py         # In-page JS scripts & robust DOM selectors
│   │   │   └── driver.py      # BrowserDriver: per-account tab management & cookie injection
│   │   └── http/              # Direct-protocol HTTP driver (future expansion)
│   └── upstream/
│       └── muse.py            # Upstream constants, cookie validation, and session renewal
├── scripts/
│   ├── connect_9router.py     # Auto-register node & models to 9Router SQLite database
│   └── extract_cookies.py     # Cookie parser & import generator
├── tests/                     # Comprehensive test suite (100% offline via MockDriver)
├── Dockerfile                 # Container image with Chromium & Python runtime
├── docker-compose.yml         # Container deployment configuration
├── pyproject.toml             # Package metadata, dependencies, build settings
└── .env.example               # Environment variable templates
```

---

## 3. CORE PROTOCOL & DRIVER SPECIFICATIONS

### A. Upstream Authentication Contract
Upstream `muse.ai` authenticates via browser cookies. The engine manages:
1. **`hatch_sess`** *(Mandatory)*: User session authorization token.
2. **`hatch_native_auth_device`** *(Mandatory)*: Unique device fingerprint UUID.
3. **`hatch_vml`** *(Recommended)*: Virtual Machine workspace lease token (automatically minted upon thread creation).
4. **`datr`** *(Recommended)*: Meta infrastructure device integrity cookie (prevents login landing page redirects).

`hatch_gw` was formerly required for gateway routing but is no longer issued by muse.ai
(verified against a live 2026-10 session); requiring it caused valid exports to be rejected.

**Critical Implementation Rule:** Cookies passed through CDP `Network.setCookie` MUST be URL-decoded (`urllib.parse.unquote`) and applied across both `.muse.ai` and `muse.ai` domains to guarantee edge proxy compatibility.

### B. Driver Layer Abstraction
- The application NEVER couples HTTP route handlers directly to browser automation.
- All upstream interactions flow through `MuseDriver` (`src/museai/drivers/base.py`):
  - `chat_stream(account, request)` -> `AsyncIterator[str]`
  - `generate_image(account, request)` -> `MediaResult`
  - `generate_video(account, request, progress_cb)` -> `MediaResult`
  - `renew_session(account)` -> `SessionInfo`

---

## 4. AGENT RUNBOOK & CLI COMMANDS

### Environment Setup
```bash
# Install the package with dev dependencies (Python 3.10+, uv)
uv sync --extra dev
```

### Running Tests
```bash
# Run complete test suite (Runs 100% offline using MockDriver)
pytest

# Code formatting and linting
ruff check .
ruff format .
```

### Starting the Service
```bash
# Local development start (default: http://127.0.0.1:18610)
python -m museai
```

### Connecting to 9Router Gateway
```bash
# Auto-inject provider node and models into 9Router SQLite database
python scripts/connect_9router.py --port 18610 --prefix muse
```

### Offloading Renders to a Colab GPU (muse-renderer)
Heavy steps after the muse clips come back (stitch/compose, Real-ESRGAN upscale, music) can run on a free Colab
runtime instead of this machine, through the private companion repo `lvluu/muse-renderer`. Its server is a
login service on the muse machine (systemd on Linux, launchd on macOS) that starts a Colab runtime per job and
stops it when idle; the runtime clones this repo, so job commands call the skill scripts through `$MUSEAI`.
```bash
# setup once per machine: muse-renderer README "Setup" (agent checklist in its AGENTS.md)
export MUSE_RENDER_DRIVE=...          # queue folder on Google Drive
muse-renderer submit -n ep1 seg1.mp4 seg2.mp4 -- 'bash "$MUSEAI/.claude/skills/muse-video/scripts/stitch.sh" out.mp4 seg1.mp4 seg2.mp4'
muse-renderer wait <id> -o work/      # new files come back here
```
Measured 2026-11-17: 3 muse segments stitched in about 100 s on Colab (upload + stitch + download). Only
committed scripts run there: push a skill-script change before queueing a job that needs it.

---

## 5. REVISION LOG & BUG MITIGATION HISTORY

When modifying the codebase, preserve these verified fixes:
1. **Cookie Decoding Bug**: Cookie strings containing URL-encoded colons (`v1%3A...`) must be unquoted before sending via CDP `Network.setCookie`. Raw percent-encoded tokens cause upstream 401s.
2. **Dual-Domain Cookie Scope**: Always register cookies for both `domain: ".muse.ai"` and `domain: "muse.ai"`.
3. **Multi-Language DOM Readiness**: Upstream renders in user locales (English, Indonesian, Chinese, etc.). Readiness selectors in `dom.py` rely on input presence and hydration state, avoiding locale-specific string matching.
4. **Clean Concurrency Model**: Headless Chromium runs 1 persistent process with isolated `BrowserContext` per account to prevent session bleeding.

## 6. VIDEO GENERATION SKILL

Every video made through museai follows `.claude/skills/muse-video/SKILL.md`. `scripts/muse-video` there appends `prompt/quality.txt` (motion, continuity, lip sync, steady pace, composition rules) to every prompt, and `scripts/qa.py` is the quality gate before delivery. Change the rules in those files, not in individual prompts.

## 7. DELIVERY WORKFLOW

When a change is finished: branch from the latest `main`, commit, push the branch, open a PR, wait for the `CI` workflow
(`.github/workflows/ci.yml`: secrets scan, `ruff check .`, `pytest -q` on Python 3.10 and 3.12), then squash-merge.
Run `ruff check .` and `pytest -q` locally first. Any failing check: fix it, do not merge.
