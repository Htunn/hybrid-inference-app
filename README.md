# InferMesh

**A learning-focused demonstration of AI inference and RAG (Retrieval Augmented Generation) pipelines.**

This project shows the complete end-to-end flow of how modern AI applications work behind the scenes — from uploading documents and generating embeddings, to semantic search, streaming inference, and response generation. Perfect for developers who want to understand how these systems work by seeing a complete, working implementation.

## Project Objective

This is a **demonstration project** designed to help you **understand the end-to-end flow** of how inference and RAG work behind the scenes. Not intended for large-scale production or enterprise deployments.

**Learning Focus:**
- 🔍 **See how RAG works** — Upload documents, watch them get chunked and embedded, query with semantic search
- 🔄 **Understand streaming inference** — Follow token-by-token generation from LLM to browser via Server-Sent Events (SSE)
- 🔌 **Multi-provider abstraction** — Switch between local (Ollama) and cloud (Gemini/OpenAI) models without code changes
- 📊 **Observability** — See request latency, token throughput, cache performance via Prometheus metrics
- 🏗️ **Architecture patterns** — Learn production-like patterns (Docker orchestration, health checks, caching, streaming)

**What this is NOT:**
- ❌ Large-scale production system
- ❌ Enterprise-grade deployment
- ❌ Mission-critical application platform

---

## Platform Support

### ✅ Supported Platforms
- **macOS (Intel & Apple Silicon M1/M2/M3)** — Optimized with CPU-only PyTorch for fast builds (~5 min vs. 20+ min)
- **Linux (x86_64 & ARM64)** — Works on cloud VMs, local machines, Kubernetes clusters
- **Docker Desktop** — Cross-platform containerized deployment

### ⚠️ Current Limitations
- **Windows with NVIDIA GPU** — Not currently supported. The RAG pipeline uses CPU-only PyTorch to avoid CUDA dependencies. Windows users can run via Docker Desktop, but NVIDIA GPU acceleration for embeddings is not configured.
- **vLLM provider** — Requires NVIDIA GPU + CUDA drivers (Linux only). Not compatible with Mac or CPU-only builds.

> **Why CPU-only PyTorch?** The RAG embedding model (`sentence-transformers`) depends on PyTorch. The default PyTorch installation downloads 444 MB of CUDA/cuDNN libraries that Mac users don't need. The CPU-only build reduces Docker image size and build time significantly.

### Future Roadmap
- [ ] Windows CUDA support for RAG embeddings
- [ ] Apple Metal GPU acceleration for Mac (via PyTorch MPS)
- [ ] AMD ROCm support for vLLM on Linux

---

## What Makes This Different From Basic Tutorials?

### Typical Tutorial Approach
```
📖 Code snippets showing API calls
📖 Conceptual explanations
❌ No complete, runnable system
❌ No observability or debugging tools
❌ Single provider only
```

### This Project
```
✅ Full working implementation with Docker
✅ Complete RAG pipeline with pgvector
✅ Multiple inference backends (4 providers)
✅ Metrics and monitoring with Grafana
✅ Production-like architecture patterns
✅ You can inspect every step of the flow
```

**Architecture Overview:**
```
┌─────────────┐
│  Client     │
│  (browser)  │
└──────┬──────┘
       │ API key exposed
       │ streaming not standardized
       ▼
┌─────────────┐
│  LLM API    │
│  (vendor)   │
└─────────────┘
```
🚫 **Limitations of basic setups:**
- API keys in browser = security risk
- No RAG / document retrieval
- No monitoring or observability
- No caching layer
- Single provider (vendor lock-in)
- No production deployment infrastructure

### This Platform (Complete Learning Environment)
```
┌──────────────┐     ┌────────────────────────┐     ┌──────────────┐
│  React PWA   │ ──▶ │  FastAPI Proxy         │ ──▶ │ Ollama       │
│  (offline)   │     │  • RAG pipeline        │     │ Gemini       │
│              │ ◀── │  • Prefix cache        │ ◀── │ OpenAI       │
│              │     │  • Batch processor     │     │ vLLM (GPU)   │
└──────────────┘     │  • Rate limiting       │     └──────────────┘
                     │  • Prometheus metrics  │
                     └──────┬─────────────────┘
                            │
                     ┌──────▼─────────┐
                     │  PostgreSQL    │
                     │  + pgvector    │
                     │  (embeddings)  │
                     └────────────────┘
```

**📚 What you can learn:**
✅ **RAG with pgvector** — Upload documents (.pdf/.md/.txt), see automatic chunking, semantic search with HNSW index  
✅ **Prefix caching** — Understand how to reuse system prompt tokens (observe 40-60% savings in metrics)  
✅ **Batch processing** — See how to queue multiple inference jobs and process asynchronously  
✅ **Multi-provider** — Switch between Ollama (local), Gemini (cloud), OpenAI (GPT-4o), vLLM (Linux GPU)  
✅ **Observability** — Explore Prometheus metrics + Grafana dashboards (latency, throughput, cache hits)  
✅ **Security patterns** — See rate limiting (20 req/min), CORS configuration, input validation  
✅ **Deployment** — Learn Docker Compose orchestration, health checks, multi-stage builds  
✅ **PWA patterns** — Service worker caching, offline-first design, installable web app  

---

## Use Cases: When to Use This Project

| Scenario | Recommended Approach | This Project |
|---|---|---|
| **Learning how RAG works** | Read tutorials | ✅ **See it in action** — Upload docs, query, inspect chunks |
| **Understanding inference streaming** | Read API docs | ✅ **Watch tokens flow** — SSE stream from LLM → backend → browser |
| **Prototyping RAG apps** | Start from scratch | ✅ **Reference implementation** — Full pipeline with pgvector |
| **Comparing LLM providers** | Write separate clients | ✅ **Switch with 1 env var** — Ollama, Gemini, OpenAI, vLLM |
| **Quick single-user prototype** | Ollama CLI | ❌ Overkill — Too many components |
| **Large-scale production** | Use managed services | ❌ Not designed for enterprise scale |

### Example Learning Scenarios

**1. Understanding RAG Pipeline**
- Upload a PDF document (`.pdf`, `.md`, or `.txt`)
- Watch it get chunked into semantic sections
- See embeddings generated with `all-MiniLM-L6-v2`
- Query: "What is X?" and inspect retrieved chunks
- Observe how chunks are injected into LLM context
- See source citations in the response

**2. Exploring Inference Backends**
- Start with Ollama (free, runs locally)
- Switch to Gemini (cloud, faster responses)
- Compare latency and token throughput in Grafana
- No code changes required — just environment variable

**3. Observing System Behavior**
- Open Grafana dashboard at `http://localhost:3000`
- Send multiple queries and watch metrics update
- See cache hit rate improve with repeated prompts
- Monitor vector search latency for RAG queries

---

## InferMesh Pattern

### Why "hybrid"?

This project demonstrates a flexible architecture where you can:
- **Develop locally** with free on-device models (Ollama) — no API costs, works offline
- **Test with cloud APIs** (Gemini, OpenAI) — higher quality responses, managed infrastructure
- **Switch between them** with a single environment variable — no code changes, same API contract

```bash
INFERENCE_PROVIDER=ollama  →  gemma4:e4b runs on your machine    (free, offline)
INFERENCE_PROVIDER=gemini  →  Gemini 2.5 Flash runs on Google    (cloud, fast)
INFERENCE_PROVIDER=openai  →  GPT-4o runs on OpenAI             (cloud, alternative)
INFERENCE_PROVIDER=vllm    →  Llama 3.1 runs on your GPU        (Linux + NVIDIA GPU only)
```

This pattern helps you understand how to build provider-agnostic inference systems.

### Architecture Principle

**The client never talks to an AI provider directly.** Every token flows through the backend proxy, which demonstrates:
- How to normalize different API formats (NDJSON → SSE, SSE → SSE)
- How to implement rate limiting and CORS
- How to validate input with Pydantic
- How RAG retrieval and context injection works
- How prefix caching improves performance
- How to collect metrics for observability
- How to route to different providers at runtime

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
| **Claude** | Native or OpenAI-compatible | Direct Anthropic API or custom proxies (auto-detects) |

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
INFERENCE_PROVIDER=claude  →  POST {base_url}/v1/messages (Anthropic) OR /chat/completions (OpenAI-compatible)
INFERENCE_PROVIDER=openai  →  POST api.openai.com/v1/chat/completions  (OpenAI SSE → SSE)
INFERENCE_PROVIDER=vllm    →  POST {vllm_url}/v1/chat/completions  (OpenAI SSE → SSE)
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

### 5 — RAG ingestion pipeline

```mermaid
sequenceDiagram
    actor User
    participant UI     as React PWA<br/>(RAG tab)
    participant Nginx  as Nginx<br/>(:80)
    participant API    as FastAPI Proxy<br/>(:8000)
    participant EMB    as LocalEmbedder<br/>(all-MiniLM-L6-v2)
    participant PG     as PostgreSQL<br/>(pgvector)

    User->>UI: drag & drop / browse → selects .md / .txt / .pdf
    activate UI
    UI->>Nginx: POST /api/rag/ingest  multipart/form-data
    activate Nginx
    Nginx->>API: reverse-proxy
    activate API

    API->>API: load_upload() — read bytes, SHA-256 hash,\nextract text (pypdf for .pdf)
    API->>PG: upsert document row by file_path
    note over API,PG: if hash unchanged → return status:"skipped"

    API->>API: split_document() — heading-aware\nmarkdown chunks (max 400 tokens, 50-token overlap)
    API->>EMB: embed(chunk_texts)  [batch of 32]
    activate EMB
    EMB-->>API: list[list[float]]  (384-dim vectors)
    deactivate EMB

    loop each chunk
        API->>PG: INSERT INTO chunks (content, embedding, …)
    end
    API->>PG: COMMIT
    deactivate API

    Nginx-->>UI: {"status":"ok","chunks_created":N}
    deactivate Nginx
    UI-->>User: "filename.md ingested successfully"
    UI->>Nginx: GET /api/rag/documents
    Nginx->>API: fetch document list
    API->>PG: SELECT id, file_path, title, ingested_at FROM documents
    PG-->>API: rows
    API-->>UI: JSON document list
    UI-->>User: document appears in Knowledge Base panel
    deactivate UI
```

### 6 — RAG query pipeline

```mermaid
sequenceDiagram
    actor User
    participant UI     as React PWA<br/>(RAG tab)
    participant Nginx  as Nginx<br/>(:80)
    participant API    as FastAPI Proxy<br/>(:8000)
    participant EMB    as LocalEmbedder<br/>(all-MiniLM-L6-v2)
    participant PG     as PostgreSQL<br/>(pgvector HNSW)
    participant LLM    as LLM Upstream<br/>(Ollama or Gemini)

    User->>UI: types question, presses Enter
    activate UI
    UI->>Nginx: POST /api/rag/query\n{"question":"…","top_k":5,"min_similarity":0.3}
    activate Nginx
    Nginx->>API: reverse-proxy
    activate API

    API->>EMB: embed_one(question)
    activate EMB
    EMB-->>API: query_vector[384]  (~5 ms on CPU)
    deactivate EMB

    API->>PG: SELECT … FROM chunks c JOIN documents d\nWHERE 1-(c.embedding <=> query_vector) ≥ 0.3\nORDER BY cosine distance LIMIT 5
    note over API,PG: HNSW index — approximate nearest-neighbour
    PG-->>API: top-k RetrievedChunk rows (content, file_path, heading, similarity)

    alt no chunks above threshold
        API-->>UI: SSE: "No relevant content found"\nSSE: {"type":"sources","sources":[]}\nSSE: [DONE]
    else chunks found
        API->>API: build_prompt() — inject numbered\nContext [1]…[k] sections + question

        API->>LLM: POST /api/chat or Gemini API\n(system prompt + grounded user message, stream:true)
        activate LLM

        loop each generated token
            LLM-->>API: token
            API-->>Nginx: data: "tok"\n\n  (SSE)
            Nginx-->>UI: forwarded live (proxy_buffering off)
            UI-->>User: token appended to assistant bubble
        end

        LLM-->>API: stream ends
        deactivate LLM
        API-->>Nginx: data: {"type":"sources","sources":["file.md",…]}\n\n
        API-->>Nginx: data: [DONE]\n\n
        deactivate API
        Nginx-->>UI: final SSE events
        deactivate Nginx
        UI-->>User: source badges rendered below answer
    end
    deactivate UI
```

### 7 — RAG document deletion

```mermaid
sequenceDiagram
    actor User
    participant UI    as React PWA<br/>(RAG tab)
    participant Nginx as Nginx<br/>(:80)
    participant API   as FastAPI Proxy<br/>(:8000)
    participant PG    as PostgreSQL<br/>(pgvector)

    User->>UI: clicks ✕ on a document row
    UI->>Nginx: DELETE /api/rag/documents/{id}
    Nginx->>API: reverse-proxy
    API->>PG: DELETE FROM documents WHERE id=…\n(CASCADE → chunks deleted automatically)
    PG-->>API: OK
    API-->>UI: {"status":"deleted","document_id":…}
    UI->>Nginx: GET /api/rag/documents
    Nginx->>API: refresh list
    API->>PG: SELECT … FROM documents
    PG-->>API: updated rows
    API-->>UI: JSON document list
    UI-->>User: document disappears from Knowledge Base panel
```

---

## Technical Features

### Advanced Capabilities (Inspired by vLLM)

This project demonstrates several advanced techniques inspired by [vLLM](https://github.com/vllm-project/vllm) (83k+ stars, PagedAttention pioneer):

#### 1. Multi-Backend Abstraction
Support for **5 inference backends** with a unified interface:
- **Ollama** — Local on-device inference (dev/air-gapped)
- **Google Gemini** — Cloud API (production recommended)
- **vLLM** — Self-hosted high-performance server (OpenAI-compatible)
- **OpenAI** — GPT-4o / GPT-4o-mini via official API
- **Claude** — Native Anthropic API or OpenAI-compatible endpoints (auto-detects)

Switch providers with one environment variable — no code changes required:
```bash
INFERENCE_PROVIDER=vllm    # → vLLM server
INFERENCE_PROVIDER=openai  # → OpenAI API
INFERENCE_PROVIDER=gemini  # → Google Gemini
INFERENCE_PROVIDER=ollama  # → Local Ollama
INFERENCE_PROVIDER=claude  # → Claude (auto-detects native or compatible API)
```

#### 2. Prefix Caching
Automatic LRU caching of prompt prefixes to reduce redundant computation:
- Caches repeated system messages, RAG context, chat history
- SHA-256 hashing for cache key generation
- Configurable cache size and minimum prefix length
- Tracks cache hits/misses via Prometheus metrics

**Example:** In RAG workflows with fixed system prompts, cache hit rate can exceed 70%.

```bash
PREFIX_CACHE_SIZE=100        # Max entries
PREFIX_MIN_LENGTH=3          # Min messages to cache
```

#### 3. Continuous Batching
Inspired by vLLM's continuous batching algorithm for throughput optimization:
- Groups multiple requests into batches
- Configurable batch size and wait time
- Priority queue for request scheduling
- Queue length monitoring

```bash
BATCH_ENABLED=true
BATCH_SIZE=8                 # Max requests per batch
BATCH_WAIT_MS=50             # Wait time before executing batch
```

**Note:** Current implementation is a framework for true continuous batching. Full vLLM-style batching requires model-level integration.

#### 4. Comprehensive Metrics (Prometheus)
Observability with 15+ metrics to help you understand system behavior:

**Latency & Performance:**
- `inference_latency_seconds` — Time to first token (TTFT) histogram
- `inference_throughput_tokens_per_second` — Generation speed

**Throughput:**
- `inference_requests_total` — Counter by backend and status
- `inference_tokens_total` — Total tokens generated

**Caching:**
- `prefix_cache_hits_total` / `prefix_cache_misses_total`
- Cache hit rate calculation

**Batching:**
- `batch_size` — Histogram of batch sizes
- `batch_wait_time_seconds` — Batching wait time
- `queue_length` — Current queue depth

**RAG:**
- `rag_retrieval_latency_seconds` — Vector search performance
- `rag_documents_retrieved_total` — Retrieved chunks counter

Access metrics endpoint:
```bash
curl http://localhost/metrics
```

#### 5. Prometheus + Grafana Integration
Pre-configured monitoring stack (optional):

```bash
# Start with monitoring
docker compose --profile monitoring up

# Access Grafana: http://localhost:3000
# Default credentials: admin / admin
```

**Included Dashboard Panels:**
- Requests per second (by backend)
- Token throughput
- Latency percentiles (P50, P95, P99)
- Cache hit rate
- Queue length
- Average batch size

Grafana datasource and dashboard are auto-provisioned.

#### 6. vLLM Backend Support
Optional vLLM service in docker-compose.yml for exploring GPU-accelerated inference:

```bash
# Start with vLLM (requires NVIDIA GPU)
docker compose --profile vllm up

# Backend auto-connects to vLLM
INFERENCE_PROVIDER=vllm
VLLM_MODEL=meta-llama/Llama-3.1-8B-Instruct
```

**vLLM Features Enabled:**
- PagedAttention (via vLLM native implementation)
- Prefix caching (`--enable-prefix-caching`)
- Chunked prefill (`--enable-chunked-prefill`)
- FP8 quantization (configurable: `VLLM_QUANTIZATION=fp8|awq|gptq`)
- KV cache FP8 optimization

#### 7. Quantization Configuration
Comprehensive quantization settings in `config.toml`:

**vLLM:**
- FP8, AWQ, GPTQ support
- KV cache dtype optimization
- Speculative decoding configuration

**Ollama:**
- Model tags for quantization (`:q4_0`, `:q8_0`, `:e4b`, `:f16`)
- GPU offloading control

**Configuration Example:**
```toml
[vllm]
model = "meta-llama/Llama-3.1-8B-Instruct"
quantization = "fp8"
kv_cache_dtype = "fp8"
enable_prefix_caching = true
gpu_memory_utilization = 0.9

[ollama]
model = "gemma4:e4b"  # 4-bit quantized
quantization = "q4_0"
num_gpu = 1
```

### Architecture Highlights

**Error Handling:**
- Graceful SSE error events (prevents connection hangs)
- Request ID tracking for debugging
- Startup validation checks

**Performance Techniques:**
- Gunicorn + Uvicorn workers for concurrency
- Nginx reverse proxy with rate limiting (20 req/min per IP)
- Zero-copy SSE streaming (`proxy_buffering off`)
- CORS configuration

**Observability:**
- Structured logging with request/response correlation
- Health check endpoint with cache stats
- Prometheus metrics endpoint
- Grafana dashboards for visualization

**Configuration:**
- Environment-based configuration
- TOML config file for advanced settings
- Docker Compose profiles (dev/monitoring/vllm)

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

## RAG Knowledge Base — Quick Start

The **RAG tab** lets you upload documents and ask questions grounded in their content. It requires PostgreSQL with the pgvector extension, which is included in the Docker Compose stack.

### Local development with Docker Compose

```bash
# Start all three services (postgres + backend + frontend)
docker compose up --build

# Open http://localhost — click the "RAG" tab
# Upload a .md / .txt / .pdf file, then ask a question about it
```

The `pgvector/pgvector:pg16` image ships with the extension pre-installed — no manual setup needed. The backend initialises the schema on first startup.

### Without Docker (RAG + Ollama dev setup)

```bash
# 1. Start PostgreSQL with pgvector (Docker is easiest)
docker run -d \
  --name pgvector \
  -e POSTGRES_USER=rag \
  -e POSTGRES_PASSWORD=ragpassword \
  -e POSTGRES_DB=rag_db \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# 2. Add RAG env vars to backend/.env
echo "DATABASE_URL=postgresql+asyncpg://rag:ragpassword@localhost:5432/rag_db" >> backend/.env
echo "EMBEDDER_PROVIDER=local" >> backend/.env

# 3. Install new dependencies (sentence-transformers downloads ~23 MB model on first embed)
cd backend
pip install -r requirements.txt

# 4. Start the backend (tables + pgvector extension created automatically)
uvicorn main:app --reload --port 8000
```

The first embed call downloads `all-MiniLM-L6-v2` to the Hugging Face cache (`~/.cache/huggingface`).

### RAG architecture overview

```mermaid
flowchart LR
    subgraph Ingestion["Ingestion pipeline (upload time)"]
        direction TB
        F["File upload\n.md / .txt / .pdf"] --> L["loader.py\nextract text + SHA-256 hash"]
        L --> C["chunker.py\nheading-aware split\n≤ 400 tokens, 50-token overlap"]
        C --> E["LocalEmbedder\nall-MiniLM-L6-v2\n384-dim vectors"]
        E --> DB[("PostgreSQL\n+ pgvector\ndocuments + chunks")]
    end

    subgraph Query["Query pipeline (per request)"]
        direction TB
        Q["User question"] --> EQ["LocalEmbedder\nembed question"]
        EQ --> VS["vector_search()\ncosine similarity ≥ 0.3\nHNSW index — top-k chunks"]
        VS --> PB["prompt_builder.py\ninject context sections"]
        PB --> LLM["LLM upstream\n(Ollama or Gemini)\nstreamed answer"]
        LLM --> R["SSE tokens\n+ source badges"]
    end

    DB --> VS
```

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
| `INFERENCE_PROVIDER` | `ollama` | `ollama`, `gemini`, `vllm`, `openai`, or `claude` |
| `GOOGLE_API_KEY` | — | Required when provider is `gemini` |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Any model listed at `/v1beta/models` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `gemma4:e4b` | Any `ollama pull`-ed model tag |
| `CLAUDE_BASE_URL` | — | Claude endpoint URL (native: `https://api.anthropic.com`, custom: `https://api.example.com/v1`) |
| `CLAUDE_API_KEY` | — | API key (Bearer token for native, x-api-key for custom) |
| `CLAUDE_MODEL` | — | Model identifier (e.g. `claude-3-5-sonnet-20241022`) |
| `CLAUDE_API_TYPE` | (auto-detect) | Optional: `anthropic` (native) or `openai` (compatible) - auto-detects from URL if not set |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | CORS-allowed origin (exact match, no trailing slash) |
| `DATABASE_URL` | — | asyncpg connection string for RAG (e.g. `postgresql+asyncpg://rag:pw@localhost:5432/rag_db`); RAG disabled if unset |
| `EMBEDDER_PROVIDER` | `local` | `local` (sentence-transformers) — `openai`/`gemini` stubs available |

### Frontend (`frontend/.env`)

| Variable | Default | Description |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | Backend URL. Leave empty in Docker — Nginx handles routing |

### Docker Compose (root `.env`)

All backend vars above, plus:

| Variable | Default | Description |
|---|---|---|
| `PORT` | `80` | Host port exposed by the frontend Nginx container |
| `POSTGRES_PASSWORD` | `ragpassword` | PostgreSQL superuser password for the `rag` user |

---

## Project Structure

```
InferMesh/
├── backend/
│   ├── main.py              # FastAPI app — CORS, lifespan (init_db + embedder), routing
│   ├── routers/
│   │   ├── inference.py     # POST /api/chat — Ollama + Gemini stream helpers
│   │   └── rag.py           # POST /api/rag/ingest|query, GET|DELETE /api/rag/documents
│   ├── db/
│   │   ├── base.py          # Async SQLAlchemy engine, get_session(), init_db()
│   │   └── models.py        # Document + Chunk tables; HNSW index on embedding vector(384)
│   ├── rag/
│   │   ├── embedder.py      # EmbeddingProvider ABC, LocalEmbedder (all-MiniLM-L6-v2), factory
│   │   ├── loader.py        # Bytes → RawDocument (.md/.txt UTF-8, .pdf via pypdf)
│   │   ├── chunker.py       # Heading-aware markdown split + sentence-boundary overlap
│   │   ├── vector_store.py  # upsert_document, insert_chunk, vector_search, list/delete
│   │   └── prompt_builder.py# SYSTEM_PROMPT + build_prompt() — numbered context injection
│   ├── requirements.txt     # + sqlalchemy, asyncpg, pgvector, sentence-transformers, pypdf
│   ├── Dockerfile           # python:3.12-slim → non-root user → gunicorn 2 workers
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx           # Root layout: Chat / RAG tab switcher in header
│   │   ├── pages/
│   │   │   └── RagPage.tsx   # Two-panel RAG UI (document panel + RAG chat)
│   │   ├── components/
│   │   │   ├── ChatThread.tsx  # Message list, auto-scroll, streaming cursor animation
│   │   │   ├── InputBar.tsx    # Auto-grow textarea, Enter-to-send, loading spinner
│   │   │   ├── DocumentUpload.tsx # Drag-and-drop / browse zone, ingest progress
│   │   │   ├── DocumentList.tsx   # Ingested file rows with delete button
│   │   │   └── SourceBadges.tsx   # Indigo pill badges for RAG source citations
│   │   ├── hooks/
│   │   │   ├── useChat.ts    # Optimistic UI, token accumulation, error recovery
│   │   │   └── useRag.ts     # RAG messages, upload, delete, document list state
│   │   └── services/
│   │       ├── api.ts        # AsyncGenerator SSE client for /api/chat
│   │       └── ragApi.ts     # ingestDocument, streamRagQuery (+ sources), listDocuments
│   ├── nginx.conf            # SPA fallback, /api/ reverse-proxy, rate-limit, gzip
│   ├── Dockerfile            # node:22 build stage → nginx:1.27-alpine serve stage
│   ├── vite.config.ts        # Vite + Tailwind CSS v4 + vite-plugin-pwa (Workbox)
│   └── .env.example
│
├── docker-compose.yml        # Three services: postgres + backend (internal) + frontend (:80)
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

---

## Inference Server Deep-Dive

### Ollama + Gemma4 E4B (local inference server)

Ollama acts as a **local OpenAI-compatible inference server** that runs entirely on your machine. When `INFERENCE_PROVIDER=ollama` the FastAPI proxy talks to it over `http://localhost:11434`.

#### How the request flows

```mermaid
sequenceDiagram
    participant Proxy as FastAPI Proxy
    participant OL    as Ollama daemon<br/>(:11434)
    participant GPU   as Local GPU / CPU<br/>(gemma4:e4b weights)

    Proxy->>OL: POST /api/chat<br/>{"model":"gemma4:e4b","messages":[…],"stream":true}
    OL->>GPU: load model weights (cached after first call)
    loop NDJSON lines
        GPU-->>OL: next token logits → sampled token
        OL-->>Proxy: {"message":{"content":"tok"},"done":false}
        Proxy-->>Proxy: re-emit as SSE frame: data: "tok"\n\n
    end
    OL-->>Proxy: {"done":true}
    Proxy-->>Proxy: emit data: [DONE]\n\n
```

#### Gemma4 E4B model facts

| Property | Value |
|---|---|
| Model family | Gemma 4 (Google DeepMind) |
| Variant | `e4b` — 4-bit quantised, ~3 GB on disk |
| Context window | 8 192 tokens |
| Strengths | Instruction following, coding, reasoning |
| Hardware requirement | 8 GB RAM minimum; GPU optional (falls back to CPU) |
| Privacy | 100% on-device — zero external network calls |

#### Wire format — Ollama NDJSON

Ollama streams newline-delimited JSON. The proxy reads each line, extracts `message.content`, and re-wraps it as an SSE frame:

```
# Ollama raw output (one JSON object per line)
{"model":"gemma4:e4b","message":{"role":"assistant","content":"Hello"},"done":false}
{"model":"gemma4:e4b","message":{"role":"assistant","content":" there"},"done":false}
{"model":"gemma4:e4b","done":true,"total_duration":1234567}

# Normalised SSE output (what the browser receives)
data: "Hello"\n\n
data: " there"\n\n
data: [DONE]\n\n
```

#### Ollama setup commands

```bash
# Install (macOS)
brew install ollama

# Start the inference daemon
ollama serve                   # http://localhost:11434

# Pull the model (one-time, ~3 GB)
ollama pull gemma4:e4b

# Verify it responds
curl http://localhost:11434/api/chat \
  -d '{"model":"gemma4:e4b","messages":[{"role":"user","content":"ping"}],"stream":false}'

# List all downloaded models
ollama list

# Switch to a different local model (no code change needed)
OLLAMA_MODEL=llama3.1:8b uvicorn main:app --reload --port 8000
```

---

### Google Gemini 2.5 Flash (cloud inference server)

When `INFERENCE_PROVIDER=gemini` the proxy forwards requests to the **Google Generative Language API** over HTTPS. The API key stays server-side.

#### How the request flows

```mermaid
sequenceDiagram
    participant Proxy  as FastAPI Proxy
    participant GAPI   as Google AI API<br/>(generativelanguage.googleapis.com)
    participant DC     as Google Data Centre<br/>(gemini-2.5-flash)

    Proxy->>GAPI: POST /v1beta/models/gemini-2.5-flash:streamGenerateContent<br/>?alt=sse&key=*** (server-side only)
    Note over Proxy,GAPI: Body: {contents:[{role,parts:[{text}]}]}
    GAPI->>DC: route to inference cluster
    loop Gemini SSE stream
        DC-->>GAPI: token batch
        GAPI-->>Proxy: data: {candidates:[{content:{parts:[{text:"tok"}]}}]}
        Proxy-->>Proxy: extract text → emit data: "tok"\n\n
    end
    GAPI-->>Proxy: stream ends (connection close)
    Proxy-->>Proxy: emit data: [DONE]\n\n
```

#### Gemini 2.5 Flash model facts

| Property | Value |
|---|---|
| Model family | Gemini 2.5 (Google DeepMind) |
| Variant | Flash — optimised for speed and cost |
| Context window | 1 048 576 tokens (1M) |
| Strengths | Long-context, multimodal reasoning, instruction following |
| Latency | First token typically < 500 ms |
| Cost | Pay-per-token via Google AI Studio |
| Privacy | Data processed by Google; review their [data policy](https://ai.google.dev/gemini-api/terms) |

#### Wire format — Gemini SSE

Gemini natively streams SSE when `?alt=sse` is appended. The proxy extracts the text token from the nested candidate structure:

```
# Gemini raw SSE line
data: {"candidates":[{"content":{"parts":[{"text":"Hello"}],"role":"model"},"index":0}]}

# Normalised SSE output (what the browser receives)
data: "Hello"\n\n
data: [DONE]\n\n
```

#### Getting and rotating API keys

```bash
# 1. Create a key at Google AI Studio
open https://aistudio.google.com/app/apikey

# 2. Set it in backend/.env (never commit this file)
echo "GOOGLE_API_KEY=your_key_here" >> backend/.env

# 3. List available models for your key
curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=$GOOGLE_API_KEY" \
  | python3 -c "import json,sys; [print(m['name']) for m in json.load(sys.stdin)['models']]"

# 4. Switch model without rebuild
GEMINI_MODEL=gemini-2.5-pro docker compose up -d
```

---

### Claude (Native & Custom Endpoints)

When `INFERENCE_PROVIDER=claude` the proxy supports **both native Anthropic API and OpenAI-compatible Claude endpoints**. The backend automatically detects which API format to use based on the configured URL.

#### Supported API Types

**1. Native Anthropic Messages API** (auto-detected when URL contains `anthropic.com`)
- Direct access to Anthropic's official API
- Uses `Authorization: Bearer` authentication
- Endpoint: `/v1/messages`
- Optimal for direct Anthropic API usage

**2. OpenAI-Compatible Format** (auto-detected for other URLs)
- Enterprise proxies, AWS Bedrock, managed platforms
- Uses `x-api-key` authentication
- Endpoint: `/v1/chat/completions` or `/chat/completions`
- Works with any OpenAI-compatible Claude proxy

#### Configuration

Required environment variables:

| Variable | Required | Description | Example |
|---|---|---|---|
| `CLAUDE_BASE_URL` | ✓ | Base URL (auto-detects API type) | `https://api.anthropic.com` or `https://api.example.com/v1` |
| `CLAUDE_API_KEY` | ✓ | API key (format depends on endpoint) | `sk-ant-...` (Anthropic) or custom key |
| `CLAUDE_MODEL` | ✓ | Model identifier | `claude-3-5-sonnet-20241022` |
| `CLAUDE_API_TYPE` | Optional | Override auto-detection: `anthropic` or `openai` | `anthropic` |

#### Example 1: Native Anthropic API

```bash
# 1. Set environment variables in .env
echo "INFERENCE_PROVIDER=claude" >> .env
echo "CLAUDE_BASE_URL=https://api.anthropic.com" >> .env
echo "CLAUDE_API_KEY=sk-ant-api03-..." >> .env
echo "CLAUDE_MODEL=claude-3-5-sonnet-20241022" >> .env

# 2. Start the backend
docker compose up -d backend

# 3. Verify configuration
docker compose logs backend | grep -i claude
# Should show: "Claude API type: native Anthropic API (auto-detected)"
```

#### Example 2: OpenAI-Compatible Endpoint

```bash
# 1. Set environment variables in .env
echo "INFERENCE_PROVIDER=claude" >> .env
echo "CLAUDE_BASE_URL=https://api.example.com/v1" >> .env
echo "CLAUDE_API_KEY=your-custom-key" >> .env
echo "CLAUDE_MODEL=claude-3-5-sonnet-20241022" >> .env

# 2. Start the backend
docker compose up -d backend

# 3. Verify configuration
docker compose logs backend | grep -i claude
# Should show: "Claude API type: OpenAI-compatible (auto-detected)"
```

#### Example 3: Explicit API Type Override

```bash
# Force OpenAI-compatible mode even for anthropic.com URLs
echo "CLAUDE_API_TYPE=openai" >> .env

# Force native Anthropic mode for custom proxy
echo "CLAUDE_API_TYPE=anthropic" >> .env
```

#### How the request flows

**Native Anthropic API:**
```mermaid
sequenceDiagram
    participant Proxy as FastAPI Proxy
    participant API as Anthropic API<br/>(api.anthropic.com)
    participant LLM as Claude Model

    Proxy->>API: POST /v1/messages<br/>Header: Authorization: Bearer ***<br/>Header: anthropic-version: 2023-06-01<br/>Body: {model, messages, system, stream:true}
    API->>LLM: route to model
    loop SSE stream
        LLM-->>API: token batch
        API-->>Proxy: data: {type:"content_block_delta",delta:{text:"tok"}}
        Proxy-->>Proxy: extract text → emit data: "tok"\n\n
    end
    API-->>Proxy: data: {type:"message_stop"}
```

**OpenAI-Compatible:**
```mermaid
sequenceDiagram
    participant Proxy as FastAPI Proxy
    participant CAPI as Custom Endpoint<br/>(OpenAI-compatible)
    participant LLM as Claude Model

    Proxy->>CAPI: POST /chat/completions<br/>Header: x-api-key: ***<br/>Body: {model, messages, stream:true}
    CAPI->>LLM: route to model
    loop SSE stream
        LLM-->>CAPI: token batch
        CAPI-->>Proxy: data: {choices:[{delta:{content:"tok"}}]}
        Proxy-->>Proxy: extract content → emit data: "tok"\n\n
    end
    CAPI-->>Proxy: data: [DONE]
```

#### Endpoint Compatibility

✅ **Native Anthropic API Compatible:**
- `https://api.anthropic.com` (official Anthropic API)
- Any endpoint implementing Anthropic's Messages API format

✅ **OpenAI-Compatible Format:**
- AWS Bedrock (via OpenAI-compatible proxy)
- Enterprise Claude proxies
- Managed platforms (government AI platforms, etc.)
- Custom middleware implementing `/chat/completions`

#### Testing

```bash
# Test with a simple query
curl -N http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Say hello"}]}'

# Switch models on the fly
CLAUDE_MODEL=claude-3-opus-20240229 docker compose up -d

#### 4. Switch model without rebuild
GEMINI_MODEL=gemini-2.5-pro docker compose up -d
```

#### Comparing the inference backends

| | Ollama + Gemma4 E4B | Google Gemini 2.5 Flash | Claude (Native & Custom) |
|---|---|---|---|
| **Cost** | Free (electricity only) | Pay-per-token | Depends on endpoint provider |
| **Privacy** | 100% on-device | Google processes data | Depends on endpoint provider |
| **Latency** | Depends on local hardware | ~500 ms first token | Depends on endpoint |
| **Context window** | 8 192 tokens | 1 048 576 tokens | Varies by model |
| **Offline capable** | Yes | No | Depends on endpoint |
| **Setup** | `ollama pull gemma4:e4b` | Google AI Studio API key | Native API key or custom endpoint |
| **Best for** | Dev, testing, private data | Production, long context, quality | Direct Anthropic access, enterprise proxies |

---

## Contributing

Contributions are welcome! Here's how to get started:

### Workflow

```bash
# 1. Fork the repo and clone your fork
git clone https://github.com/<your-username>/InferMesh.git
cd InferMesh

# 2. Create a feature branch off main
git checkout -b feat/your-feature-name

# 3. Set up local dev environment
cd backend && python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
cd ../frontend && npm install

# 4. Make your changes, then verify nothing is broken
cd backend && uvicorn main:app --reload --port 8000 &
cd ../frontend && npm run build   # must produce 0 errors

# 5. Commit using conventional commits
git commit -m "feat: add streaming abort support"
git commit -m "fix: handle empty Gemini candidate list"
git commit -m "docs: add custom model guide"

# 6. Push and open a PR against main
git push origin feat/your-feature-name
```

### Conventional commit prefixes

| Prefix | When to use |
|---|---|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `chore:` | Build, deps, tooling |
| `refactor:` | Code change with no behaviour change |
| `test:` | Adding or fixing tests |

### Good first contributions

- Add a system-prompt field to the UI
- Support abort/cancel of an in-flight stream
- Add a model selector dropdown
- Add end-to-end tests (Playwright)
- Add support for a third upstream (e.g. Anthropic Claude via Bedrock)

### Code style

- **Python** — PEP 8; type annotations on all public functions; Pydantic for all I/O boundaries
- **TypeScript** — strict mode; no `any`; prefer `const`
- Keep PRs focused: one concern per PR

---

## License

MIT © 2026 [Htunn](https://github.com/Htunn)

See [LICENSE](LICENSE) for the full text.
