# Hybrid Inference Chat

A **mobile-first Progressive Web App (PWA)** for LLM inference that streams AI responses token-by-token. It implements a **hybrid inference pattern**: routing requests to a **local Ollama model** (on-device, zero latency, zero cost) in development, and to **Google Gemini 2.5 Flash** (cloud-hosted, scalable) in production — all through a secure FastAPI proxy so API keys never reach the browser.

The architecture is built around one core idea: **the client never talks to an AI provider directly**. Every token flows through the backend proxy, which normalises the wire format, enforces CORS, validates input, and decides which upstream to call based on a single environment variable.

---

## LLM Inference Use Cases

### Why hybrid inference?

Most applications need two things that are in tension:
- **Fast, free iteration** during development (local model, no API cost, works offline)
- **High-quality, scalable inference** in production (cloud model, managed capacity)

This project solves that by making the inference provider a **runtime config switch**, not a code branch.

```
INFERENCE_PROVIDER=ollama  →  gemma4:e4b runs on your machine    (dev / air-gapped)
INFERENCE_PROVIDER=gemini  →  Gemini 2.5 Flash runs on Google    (production / cloud)
```

No code changes. No rebuild. Same API contract for the frontend.

### Who is this for?

| Persona | Problem solved |
|---|---|
| **ML / AI developer** | Prompt-engineer and iterate locally against `gemma4:e4b` at zero cost, then validate the same prompts against Gemini in one command |
| **Backend engineer** | Add LLM streaming to an existing product without exposing API keys to the browser or building a streaming proxy from scratch |
| **DevOps / platform team** | Ship the full stack as a single `docker compose up` — Nginx, FastAPI proxy, and model routing included |
| **Privacy-first deployment** | Run entirely on-device with Ollama; no data ever leaves the host |
| **Prototyping / hackathon** | Working streaming chat UI + secure proxy in minutes; swap the model by editing one line |

### Inference scenarios covered

| Scenario | Config | Model |
|---|---|---|
| Local development | `INFERENCE_PROVIDER=ollama` | `gemma4:e4b` via Ollama |
| Air-gapped / offline | `INFERENCE_PROVIDER=ollama` | Any `ollama pull`-ed model |
| Cloud production | `INFERENCE_PROVIDER=gemini` | `gemini-2.5-flash` |
| Experimenting with other Gemini models | `GEMINI_MODEL=gemini-2.5-pro` | Any `/v1beta/models` model |
| Custom local model | `OLLAMA_MODEL=llama3.1:8b` | Any Ollama model tag |

---

## High-Level Design (HLD)

```mermaid
flowchart TD
    subgraph Browser["Browser / Mobile (PWA)"]
        UI["React 19 Chat UI\n(streaming token bubbles)"]
        SW["Service Worker\n(Workbox — offline shell)"]
    end

    subgraph Docker["Docker Host — docker compose up"]
        subgraph FE["frontend  :80"]
            Nginx["Nginx\n• serves React SPA\n• rate-limit /api/ 20 rpm/IP\n• security headers\n• proxy_buffering off for SSE"]
        end
        subgraph BE["backend  :8000 (internal)"]
            GW["FastAPI + Gunicorn\nPOST /api/chat\n• Pydantic validation\n• CORS exact-match allowlist\n• startup health check"]
        end
        FE -- "reverse-proxy /api/*" --> BE
    end

    subgraph Upstream["AI Upstream (one active at a time)"]
        OL["Ollama\ngemma4:e4b\n(host machine)"]
        GM["Google Gemini 2.5 Flash\ngenerativelanguage.googleapis.com"]
    end

    UI -- "POST /api/chat  SSE stream" --> Nginx
    GW -- "INFERENCE_PROVIDER=ollama" --> OL
    GW -- "INFERENCE_PROVIDER=gemini" --> GM
```

### Component map

| Layer | Technology | Responsibility |
|---|---|---|
| **React PWA** | React 19, Vite, Tailwind CSS v4 | Streaming chat UI; Workbox service worker for offline shell |
| **Nginx** | nginx 1.27-alpine | Static SPA serving, `/api/*` reverse-proxy, rate-limiting, security headers, gzip |
| **FastAPI proxy** | Python 3.12, Gunicorn + uvicorn workers | Request validation, upstream fan-out, SSE normalisation |
| **Ollama** | Host-side process | Runs `gemma4:e4b` on-device; zero external traffic |
| **Google Gemini** | Google Cloud | `gemini-2.5-flash` via REST; API key kept server-side only |

---

## How It Works

### Unified SSE protocol

The backend presents one endpoint regardless of which model answers:

```
POST /api/chat
Content-Type: application/json

{ "messages": [{ "role": "user", "content": "Hello" }] }
```

Response — `text/event-stream`:
```
data: "Hello"

data: ", "

data: "world!"

data: [DONE]
```

The React client iterates an `AsyncGenerator<string>` — it has no knowledge of which provider is active.

### Provider switching (zero code change)

```
INFERENCE_PROVIDER=ollama  →  POST http://ollama:11434/api/chat  (NDJSON → normalised SSE)
INFERENCE_PROVIDER=gemini  →  POST googleapis.com/…:streamGenerateContent?alt=sse  (SSE → SSE)
```

### Streaming pipeline

```
Ollama NDJSON chunks  ──►  FastAPI normaliser  ──►  SSE frames  ──►  Nginx (buffering OFF)  ──►  Browser
Gemini SSE frames     ──►  FastAPI pass-through ──►  SSE frames  ──►  Nginx (buffering OFF)  ──►  Browser
```

---

## Sequence Diagrams

### 1 — Local development (Ollama)

```mermaid
sequenceDiagram
    actor User
    participant PWA  as React PWA<br/>(Vite :5173)
    participant API  as FastAPI Proxy<br/>(:8000)
    participant OL   as Ollama<br/>(:11434 / gemma4:e4b)

    User->>PWA: types message, presses Enter
    activate PWA
    PWA->>API: POST /api/chat {"messages":[...]}
    activate API
    API->>OL: POST /api/chat (NDJSON stream)
    activate OL

    loop each generated token
        OL-->>API: {"message":{"content":"tok"}, "done":false}
        API-->>PWA: data: "tok"\n\n  (SSE)
        PWA-->>User: token appended to chat bubble
    end

    OL-->>API: {"done":true}
    deactivate OL
    API-->>PWA: data: [DONE]\n\n
    deactivate API
    deactivate PWA
```

### 2 — Production (Docker Compose + Gemini)

```mermaid
sequenceDiagram
    actor User
    participant Nginx  as Nginx<br/>(frontend :80)
    participant API    as FastAPI Proxy<br/>(backend :8000)
    participant Gemini as Google Gemini 2.5 Flash<br/>(googleapis.com)

    User->>Nginx: GET / — React SPA (cached by SW on repeat)
    User->>Nginx: POST /api/chat {"messages":[...]}
    activate Nginx
    Nginx->>API: reverse-proxy (X-Forwarded-For, rate-limit checked)
    activate API
    API->>Gemini: POST .../gemini-2.5-flash:streamGenerateContent?alt=sse&key=***
    activate Gemini

    loop SSE token stream
        Gemini-->>API: data: {candidates:[{content:{parts:[{text:"tok"}]}}]}
        API-->>Nginx: data: "tok"\n\n
        Nginx-->>User: forwarded live (proxy_buffering off)
    end

    Gemini-->>API: stream ends
    deactivate Gemini
    API-->>Nginx: data: [DONE]\n\n
    deactivate API
    deactivate Nginx
```

### 3 — Error handling

```mermaid
sequenceDiagram
    participant PWA as React PWA
    participant API as FastAPI Proxy
    participant Up  as Upstream

    PWA->>API: POST /api/chat

    alt Ollama not running
        API--xUp: httpx.ConnectError
        API-->>PWA: 503 "Cannot reach Ollama"
    else GOOGLE_API_KEY not set
        API-->>PWA: 500 "GOOGLE_API_KEY is not configured"
    else Upstream timeout > 120 s
        API--xUp: httpx.TimeoutException
        API-->>PWA: 504 "Request timed out"
    else Upstream 4xx / 5xx
        Up-->>API: error body
        API-->>PWA: 502 "Upstream returned HTTP …"
    else Invalid message payload
        API-->>PWA: 422 Unprocessable Entity
    end

    PWA->>PWA: shows dismissible error banner
```

### 4 — PWA offline / Service Worker caching

```mermaid
sequenceDiagram
    participant Browser
    participant SW  as Service Worker<br/>(Workbox)
    participant Net as Network (Nginx)

    Browser->>SW: GET / (or any shell asset)
    SW->>SW: CacheFirst strategy — hit?
    alt cache hit (offline or repeat visit)
        SW-->>Browser: shell from cache (instant)
    else cache miss
        SW->>Net: fetch from network
        Net-->>SW: HTML + JS + CSS + icons
        SW->>SW: store in Workbox precache
        SW-->>Browser: serve response
    end

    Browser->>SW: POST /api/chat
    SW->>Net: NetworkOnly — SSE streams are never cached
    Net-->>Browser: live token stream
```

---

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Python | ≥ 3.11 | Backend proxy |
| Node.js | ≥ 20 | Frontend build |
| [Ollama](https://ollama.com) | latest | Local inference (dev only) |
| Docker + Compose plugin | ≥ 24 | Production deployment |

---

## Quick Start — Local Development (Ollama)

### 1. Pull the model

```bash
ollama pull gemma4:e4b   # ~3 GB, one-time download
ollama serve             # starts on http://localhost:11434
```

### 2. Start the backend

```bash
cd backend

python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# backend/.env is pre-configured: INFERENCE_PROVIDER=ollama, OLLAMA_MODEL=gemma4:e4b
uvicorn main:app --reload --port 8000
```

Verify: `curl http://localhost:8000/health`
→ `{"status":"ok","provider":"ollama"}`

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

Header shows **Local · Gemma4 E4B via Ollama**. Type a message and watch tokens stream in.

---

## Production — Docker Compose (Gemini)

### 1. Get a Gemini API key

[aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) → Create API key.

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env`:

```dotenv
INFERENCE_PROVIDER=gemini
GOOGLE_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
FRONTEND_ORIGIN=http://localhost    # or https://yourdomain.com in production
PORT=80
```

### 3. Build and run

```bash
docker compose up --build
```

Open [http://localhost](http://localhost) — header shows **Cloud · Gemini 2.5 Flash**.

### 4. Stop

```bash
docker compose down
```

---

## Switching Provider (no rebuild required)

The provider is resolved at **runtime**, so you can switch a running stack without rebuilding images:

```bash
# Switch to Gemini
INFERENCE_PROVIDER=gemini GOOGLE_API_KEY=… docker compose up -d

# Switch back to Ollama (via host machine's Ollama daemon)
INFERENCE_PROVIDER=ollama docker compose up -d
```

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Default | Description |
|---|---|---|
| `INFERENCE_PROVIDER` | `ollama` | `ollama` or `gemini` |
| `GOOGLE_API_KEY` | — | Required when provider is `gemini` |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Any model listed at `/v1beta/models` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `gemma4:e4b` | Any `ollama pull`-ed model tag |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | CORS-allowed origin (exact match, no trailing slash) |

### Frontend (`frontend/.env`)

| Variable | Default | Description |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | Backend URL. Leave empty in Docker — Nginx handles routing |

### Docker Compose (root `.env`)

All backend vars above, plus:

| Variable | Default | Description |
|---|---|---|
| `PORT` | `80` | Host port exposed by the frontend Nginx container |

---

## Project Structure

```
hybrid-inference-app/
├── backend/
│   ├── main.py              # FastAPI app — CORS, lifespan startup check, structured logging
│   ├── routers/
│   │   └── inference.py     # POST /api/chat — Pydantic models, Ollama + Gemini stream helpers
│   ├── requirements.txt     # fastapi, uvicorn[standard], gunicorn, httpx, python-dotenv
│   ├── Dockerfile           # python:3.12-slim → non-root user → gunicorn 2 workers
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx           # Root layout: header, error banner, chat area, input bar
│   │   ├── components/
│   │   │   ├── ChatThread.tsx # Message list, auto-scroll, streaming cursor animation
│   │   │   └── InputBar.tsx   # Auto-grow textarea, Enter-to-send, loading spinner
│   │   ├── hooks/
│   │   │   └── useChat.ts    # Optimistic UI, token accumulation, error recovery
│   │   └── services/
│   │       └── api.ts        # AsyncGenerator SSE client (fetch + ReadableStream)
│   ├── nginx.conf            # SPA fallback, /api/ reverse-proxy, rate-limit, gzip
│   ├── Dockerfile            # node:22 build stage → nginx:1.27-alpine serve stage
│   ├── vite.config.ts        # Vite + Tailwind CSS v4 + vite-plugin-pwa (Workbox)
│   └── .env.example
│
├── docker-compose.yml        # Two services: backend (internal) + frontend (port 80)
├── .env.example              # Root template for docker-compose
└── README.md
```

---

## Security

| Control | Implementation |
|---|---|
| **API key isolation** | Key lives only in the backend process env — never sent to browser |
| **CORS strict allowlist** | Exact origin match; `*` is never used |
| **Docs disabled in production** | `/docs` and `/openapi.json` return 404 when `INFERENCE_PROVIDER=gemini` |
| **Rate limiting** | Nginx `limit_req_zone`: 20 req/min per IP, burst 5 |
| **Non-root container** | Backend runs as `appuser` (not root) inside Docker |
| **Input validation** | Pydantic rejects blank content, unknown roles, and empty message lists before any upstream call |
| **No key in logs** | Structured logs never print `GOOGLE_API_KEY` |
| **SSE not cached** | Workbox `NetworkOnly` strategy for `/api/*` — no token leakage via cache |
