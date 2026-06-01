import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routers import inference

load_dotenv()

app = FastAPI(title="Hybrid Inference Proxy", version="1.0.0")

# ---------------------------------------------------------------------------
# CORS — restrict to the configured frontend origin.
# In production this must be set to the Vercel domain to prevent API key abuse.
# ---------------------------------------------------------------------------
frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_credentials=False,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.include_router(inference.router, prefix="/api")


@app.get("/health")
async def health() -> dict:
    """Simple liveness probe used by Render/Railway health checks."""
    node_env = os.getenv("NODE_ENV", "development")
    return {"status": "ok", "env": node_env}
