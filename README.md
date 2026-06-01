# Hybrid Inference App

A mobile-first Progressive Web App (PWA) that uses **local Gemma (via Ollama)** during development and **Google Gemini 1.5 Flash** in production — all routed through a secure FastAPI proxy so API keys never touch the browser.

```
[ PWA (React + Vite) ]
        │  HTTPS / SSE
        ▼
[ FastAPI Proxy ]
        ├──► NODE_ENV=development ──► Ollama (gemma3:2b, localhost:11434)
        └──► NODE_ENV=production  ──► Google AI Studio (Gemini 1.5 Flash)
```

---

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Node.js | ≥ 20 | Frontend build |
| Python | ≥ 3.11 | Backend proxy |
| [Ollama](https://ollama.com) | latest | Local inference |

---

## 1 — Install Ollama & pull the model

```bash
# macOS
brew install ollama

# Start the Ollama daemon
ollama serve

# Pull gemma3:2b (~1.6 GB)
ollama pull gemma3:2b

# Verify
curl http://localhost:11434/api/chat \
  -d '{"model":"gemma3:2b","messages":[{"role":"user","content":"ping"}]}'
```

---

## 2 — Backend (FastAPI Proxy)

```bash
cd backend

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env — set NODE_ENV=development for local dev

uvicorn main:app --reload --port 8000
```

The proxy listens at `http://localhost:8000/api/chat`.

---

## 3 — Frontend (React + Vite PWA)

```bash
cd frontend

npm install

cp .env.example .env.local
# VITE_API_URL=http://localhost:8000 is the default

npm run dev
```

Open `http://localhost:5173` in your browser.

---

## 4 — Switching to Production (Gemini)

1. Get an API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
2. In `backend/.env` set:
   ```
   NODE_ENV=production
   GOOGLE_API_KEY=your_key_here
   ```
3. Restart `uvicorn` — all requests now route to Gemini 1.5 Flash.

---

## Deployment

| Layer | Service | Notes |
|---|---|---|
| Frontend | Vercel | Set `VITE_API_URL` to your Render backend URL |
| Backend | Render | Set `NODE_ENV=production` + `GOOGLE_API_KEY` in env panel |

---

## Project Structure

```
hybrid-inference-app/
├── backend/
│   ├── main.py              # FastAPI app + CORS
│   ├── routers/
│   │   └── inference.py     # /api/chat — routing + normalization
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── ChatThread.tsx
    │   │   └── InputBar.tsx
    │   ├── hooks/
    │   │   └── useChat.ts
    │   ├── services/
    │   │   └── api.ts
    │   └── App.tsx
    ├── public/
    │   └── icons/
    ├── vite.config.ts
    └── .env.example
```
