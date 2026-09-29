<h1 align="center">museai</h1>

<p align="center">
  <b>High-performance, async OpenAI-compatible API gateway and bridge for <a href="https://muse.ai">muse.ai</a> personal AI agents.</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/API-OpenAI%20Compatible-green" alt="OpenAI Compatible" />
  <img src="https://img.shields.io/badge/9Router-Ready-purple" alt="9Router Ready" />
  <img src="https://img.shields.io/badge/License-MIT-lightgrey" alt="License" />
</p>

---

## Overview

`museai` transforms your [muse.ai](https://muse.ai) browser session and tokens into standard, production-ready **OpenAI API endpoints** (`/v1/chat/completions`, `/v1/images/generations`, `/v1/videos`, `/v1/models`).

Connect your muse.ai account balance (including high-token tier accounts) directly to:
- **9Router Multi-Model Gateway** (call `muse/muse-chat`, `muse/gpt-4o`, `muse/gpt-5`)
- Chat clients: NextChat, LobeChat, Cherry Studio, LibreChat
- Developer tools: Cursor, Claude Code, Codex, Hermes Agent, LangChain, OpenAI Python/TS SDKs

---

## Key Features

- **Standard OpenAI Endpoints**: Streaming SSE (`stream: true`), non-streaming completions, image generation, and video generation.
- **9Router Integration**: Includes one-click script (`scripts/connect_9router.py`) to register the provider directly into your local 9Router cluster.
- **Resilient Headless Driver**: Automated Chrome DevTools Protocol (CDP) driver with automatic URL-decoding, dual-domain cookie scoping (`.muse.ai` and `muse.ai`), and locale-agnostic DOM detection.
- **Account Pooling & Failover**: Automatic multi-account scheduling (`lru`, `round_robin`, `affinity`), concurrency throttling, failure cooldown, and instant retry.
- **AI Agent Friendly**: Ships with a machine-readable `AGENTS.md` specification file for autonomous AI coding agents.

---

## Quick Start

### 1. Installation

```bash
git clone https://github.com/d4ncboz/museai.git
cd museai

python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

### 2. Configuration

Create your `.env` configuration file:

```bash
cp .env.example .env
```

Example configuration (`.env`):
```ini
MUSEAI_DRIVER=browser
MUSEAI_HOST=127.0.0.1
MUSEAI_PORT=18610
MUSEAI_API_KEY=sk-museai-local-key
MUSEAI_ADMIN_KEY=sk-museai-admin-key
MUSEAI_POOL_STRATEGY=affinity
MUSEAI_KEEPALIVE_ENABLED=true
```

### 3. Start the Server

```bash
python -m museai
```

The gateway listens at `http://127.0.0.1:18610`.

---

## Importing Accounts & Session Cookies

To connect your muse.ai account, export your session cookies from Chrome DevTools (`F12` ──> `Application` ──> `Cookies` ──> `https://muse.ai`):

- `hatch_sess` (Session token)
- `hatch_gw` (Gateway cluster token)
- `hatch_native_auth_device` (Device UUID)
- `hatch_vml` (Workspace lease token)
- `datr` (Meta device integrity cookie)

Register the account via the Admin API:

```bash
curl -X POST http://127.0.0.1:18610/admin/accounts \
  -H "Authorization: Bearer sk-museai-admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "label": "my-muse-account",
    "cookies": {
      "hatch_sess": "...",
      "hatch_gw": "...",
      "hatch_native_auth_device": "...",
      "hatch_vml": "...",
      "datr": "..."
    }
  }'
```

---

## Connecting to 9Router

Connect your `museai` instance to [9Router](https://github.com/9router/9router) with a single command:

```bash
python scripts/connect_9router.py --port 18610 --api-key sk-museai-local-key --prefix muse
```

Test inference directly through 9Router:

```bash
curl -s -X POST http://127.0.0.1:20128/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "muse/muse-chat",
    "messages": [{"role": "user", "content": "Hello via 9Router!"}]
  }'
```

---

## API Examples

### Chat Completion (Streaming)

```bash
curl -N http://127.0.0.1:18610/v1/chat/completions \
  -H "Authorization: Bearer sk-museai-local-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "muse-chat",
    "messages": [{"role": "user", "content": "Tell me a haiku about code"}],
    "stream": true
  }'
```

### Python OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:18610/v1", api_key="sk-museai-local-key")

response = client.chat.completions.create(
    model="muse-chat",
    messages=[{"role": "user", "content": "Write a Python one-liner"}],
)
print(response.choices[0].message.content)
```

---

## Supported Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/healthz` · `/readyz` | Liveness & readiness probes |
| `GET` | `/v1/models` | List of models and aliases (`gpt-4o`, `gpt-5`, etc.) |
| `POST` | `/v1/chat/completions` | Chat completions (streaming SSE & non-streaming) |
| `POST` | `/v1/images/generations` | Text-to-image generation |
| `POST` | `/v1/videos` | Async video generation task creation |
| `GET` | `/v1/videos/{id}` | Poll background video task progress |
| `GET/POST` | `/admin/accounts` | Account management & cookie renewal |
| `GET` | `/admin/status` | Account pool statistics & driver health |

---

## Architecture & Contributions

See [AGENTS.md](AGENTS.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed technical specifications and code conventions.

## License

[MIT](LICENSE) © 2026 D4NNBOZ
