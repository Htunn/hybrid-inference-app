import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import inference

load_dotenv()

# ---------------------------------------------------------------------------
# Logging — structured to stdout so Docker / log aggregators can consume it
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Resolve config once at module level so it is available before lifespan
# ---------------------------------------------------------------------------
_INFERENCE_PROVIDER = os.getenv("INFERENCE_PROVIDER", "ollama")
_FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")


# ---------------------------------------------------------------------------
# Lifespan — startup validation, no-op shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    logger.info("Starting Hybrid Inference Proxy")
    logger.info("Inference provider : %s", _INFERENCE_PROVIDER)
    logger.info("CORS allowed origin: %s", _FRONTEND_ORIGIN)

    if _INFERENCE_PROVIDER == "gemini" and not os.getenv("GOOGLE_API_KEY"):
        logger.warning(
            "INFERENCE_PROVIDER=gemini but GOOGLE_API_KEY is not set — "
            "all /api/chat requests will return 500 until the key is added."
        )

    yield  # application runs here

    logger.info("Shutting down Hybrid Inference Proxy")


# ---------------------------------------------------------------------------
# App — hide interactive docs in production to reduce attack surface
# ---------------------------------------------------------------------------
_is_production = _INFERENCE_PROVIDER == "gemini"

app = FastAPI(
    title="Hybrid Inference Proxy",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if _is_production else "/docs",
    redoc_url=None,
    openapi_url=None if _is_production else "/openapi.json",
)

# ---------------------------------------------------------------------------
# CORS — strict allowlist; never use wildcard in production
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_FRONTEND_ORIGIN],
    allow_credentials=False,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.include_router(inference.router, prefix="/api")


@app.get("/health")
async def health() -> dict:
    """Liveness probe for Docker / load-balancer health checks."""
    return {
        "status": "ok",
        "provider": _INFERENCE_PROVIDER,
    }
