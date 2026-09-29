<h1 align="center">Muse AI</h1>

<p align="center">
  <b>OpenAI-compatible API gateway for <a href="https://muse.ai">muse.ai</a> personal workspaces, featuring native 9Router integration.</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/API-OpenAI%20Compatible-green" alt="OpenAI Compatible" />
  <img src="https://img.shields.io/badge/9Router-Ready-purple" alt="9Router Ready" />
  <img src="https://img.shields.io/badge/License-MIT-lightgrey" alt="License" />
</p>

---

## Architecture

```text
OpenAI SDK / 9Router / Web Client
              │
              ▼ HTTP (Bearer Token)
       ┌──────────────┐
       │   Muse AI    │ FastAPI Proxy (Port 18610)
       └──────┬───────┘
              │ Chrome DevTools Protocol (CDP over WebSocket)
              ▼
       ┌──────────────┐
       │   Chromium   │ Headless Browser (Isolated Context per Account)
       └──────┬───────┘
              │ HTTPS / WSS (hatch_sess + hatch_gw + datr)
              ▼
          muse.ai
```

---

## Technical Highlights

- **OpenAI Wire Compatibility**: Direct drop-in for OpenAI SDKs, LangChain, LobeChat, NextChat, Cherry Studio, and autonomous coding agents.
- **Native 9Router Provider**: Ships with `scripts/connect_9router.py` to auto-register model routes directly into 9Router's SQLite database (`~/.9router/db/data.sqlite`).
- **Resilient Cookie Injection**: Automatically URL-decodes percent-encoded cookie tokens (`%3A` -> `:`) and registers sessions across dual-domain scopes (`.muse.ai` and `muse.ai`) via CDP.
- **Meta Edge Proxy Compliance**: Supports `datr` cookie passing to prevent device-integrity redirects on Meta infrastructure.
- **Account Pooling & Failover**: Multi-account scheduling (`affinity`, `lru`, `round_robin`), concurrency limits, automatic error cooldown, and transparent retries.
- **Deterministic Offline Testing**: 100% offline test suite powered by `MockDriver` (23 passed in < 0.5s).

---

## Quickstart

### 1. Installation

Requires Python 3.10+ and a local Chromium or Google Chrome binary.

```bash
git clone https://github.com/d4ncboz/museai.git
cd museai

python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

### 2. Configuration

Copy the example environment configuration:

```bash
cp .env.example .env
```

Default settings in `.env`:

```ini
MUSEAI_DRIVER=browser
MUSEAI_HOST=127.0.0.1
MUSEAI_PORT=18610
MUSEAI_API_KEY=sk-museai-local-key
MUSEAI_ADMIN_KEY=sk-museai-admin-key
MUSEAI_POOL_STRATEGY=affinity
MUSEAI_KEEPALIVE_ENABLED=true
```

*(Note: Chrome executable is auto-detected on macOS `/Applications/Google Chrome.app` and Linux `/usr/bin/chromium`. Set `MUSEAI_CHROMIUM_PATH` if using a custom path).*

### 3. Run the Service

```bash
python -m museai
```

The server binds to `http://127.0.0.1:18610`.

---

## Authentication & Account Import

Export your session cookies from an active [muse.ai](https://muse.ai) browser session (DevTools `F12` ──> `Application` ──> `Cookies` ──> `https://muse.ai`):

- `hatch_sess`: Session authentication token
- `hatch_gw`: Gateway routing cookie
- `hatch_native_auth_device`: Registered device UUID
- `hatch_vml`: Workspace lease token *(optional/dynamic)*
- `datr`: Meta device verification cookie *(recommended)*

### Import via Admin API

```bash
curl -X POST http://127.0.0.1:18610/admin/accounts \
  -H "Authorization: Bearer sk-museai-admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "label": "primary-account",
    "cookies": {
      "hatch_sess": "...",
      "hatch_gw": "...",
      "hatch_native_auth_device": "...",
      "hatch_vml": "...",
      "datr": "..."
    }
  }'
```

Alternatively, use the helper script to convert raw Netscape / DevTools JSON exports:

```bash
python scripts/extract_cookies.py exported_cookies.txt --label primary-account --out account.json
curl -X POST http://127.0.0.1:18610/admin/accounts \
  -H "Authorization: Bearer sk-museai-admin-key" \
  -H "Content-Type: application/json" \
  -d @account.json
```

---

## 9Router Multi-Model Gateway Hook

To register `museai` into a local [9Router](https://github.com/9router/9router) instance:

```bash
python scripts/connect_9router.py --port 18610 --api-key sk-museai-local-key --prefix muse
```

Call the model through 9Router immediately:

```bash
curl -s -X POST http://127.0.0.1:20128/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "muse/muse-chat",
    "messages": [{"role": "user", "content": "ping"}]
  }'
```

Available model IDs routed by 9Router:
- `muse/muse-chat`: Primary personal agent conversational model
- `muse/gpt-4o`: OpenAI tooling alias
- `muse/gpt-5`: High-reasoning alias
- `muse/claude-sonnet-4`: Sonnet alias
- `muse/muse-video`: Text / first-frame image-to-video

---

## API Usage

### Streaming Chat Completion (`curl`)

```bash
curl -N -X POST http://127.0.0.1:18610/v1/chat/completions \
  -H "Authorization: Bearer sk-museai-local-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "muse-chat",
    "messages": [
      {"role": "system", "content": "You are a concise engineering assistant."},
      {"role": "user", "content": "Explain raft consensus in two sentences."}
    ],
    "stream": true
  }'
```

### Python SDK (`openai`)

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:18610/v1",
    api_key="sk-museai-local-key"
)

response = client.chat.completions.create(
    model="muse-chat",
    messages=[{"role": "user", "content": "Write a thread-safe singleton in Python"}],
    stream=False
)

print(response.choices[0].message.content)
```

---

## Endpoints

| Method | Route | Description |
|---|---|---|
| `GET` | `/healthz` · `/readyz` | Service liveness and driver readiness checks |
| `GET` | `/v1/models` | OpenAI-compliant model catalog and alias mapping |
| `POST` | `/v1/chat/completions` | Multi-turn chat (streaming SSE & buffered JSON) |
| `POST` | `/v1/images/generations` | Text-to-image synthesis |
| `POST` | `/v1/videos` | Asynchronous video generation task dispatch |
| `GET` | `/v1/videos/{id}` | Task status polling |
| `GET/POST` | `/admin/accounts` | Account pool CRUD and session renewal |
| `GET` | `/admin/status` | Real-time driver stats, tabs, and pool health |

---

## Development & Testing

```bash
# Run unit tests (MockDriver, zero external network calls)
pytest

# Code style & linting
ruff check .
ruff format .
```

See [AGENTS.md](AGENTS.md) for machine-readable architecture contracts, protocol framing, and contribution guidelines.

---

## License

[MIT](LICENSE) © 2026 D4NNBOZ
