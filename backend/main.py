import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from db.base import init_db
from rag.embedder import get_embedder
from routers import inference
from routers import rag as rag_router
from routers.metrics import get_metrics

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
# Lifespan — startup validation, graceful shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    logger.info("Starting Hybrid Inference Proxy")
    logger.info("Inference provider : %s", _INFERENCE_PROVIDER)
    logger.info("CORS allowed origin: %s", _FRONTEND_ORIGIN)

    # Validate provider-specific config
    if _INFERENCE_PROVIDER == "gemini" and not os.getenv("GOOGLE_API_KEY"):
        logger.warning(
            "INFERENCE_PROVIDER=gemini but GOOGLE_API_KEY is not set — "
            "all /api/chat requests will return 500 until the key is added."
        )
    elif _INFERENCE_PROVIDER == "openai" and not os.getenv("OPENAI_API_KEY"):
        logger.warning("INFERENCE_PROVIDER=openai but OPENAI_API_KEY is not set")
    elif _INFERENCE_PROVIDER == "vllm":
        vllm_url = os.getenv("VLLM_BASE_URL", "http://localhost:8000")
        logger.info("vLLM backend URL: %s", vllm_url)

    # Initialize batch processor (optional, configurable)
    batch_enabled = os.getenv("BATCH_ENABLED", "false").lower() == "true"
    if batch_enabled:
        from routers.batch_processor import get_batch_processor
        processor = get_batch_processor()
        await processor.start()
        logger.info("Batch processor started (max_batch=%d)", processor.max_batch_size)
        app.state.batch_processor = processor
    else:
        logger.info("Batch processing disabled (set BATCH_ENABLED=true to enable)")
        app.state.batch_processor = None

    # RAG pipeline — initialise DB tables and load the embedding model once
    _db_enabled = os.getenv("DATABASE_URL") is not None
    if _db_enabled:
        try:
            await init_db()
            app.state.embedder = get_embedder()
            logger.info("RAG pipeline ready (embedder: %s)", os.getenv("EMBEDDER_PROVIDER", "local"))
        except Exception:  # noqa: BLE001
            logger.exception(
                "RAG pipeline failed to initialise — /api/rag/* endpoints will return 503. "
                "Set DATABASE_URL to enable RAG."
            )
            app.state.embedder = None
    else:
        logger.info("DATABASE_URL not set — RAG pipeline disabled")
        app.state.embedder = None

    yield  # application runs here

    # Shutdown
    logger.info("Shutting down Hybrid Inference Proxy")
    if app.state.batch_processor:
        await app.state.batch_processor.stop()
        logger.info("Batch processor stopped")


# ---------------------------------------------------------------------------
# App — hide interactive docs in production to reduce attack surface
# ---------------------------------------------------------------------------
_is_production = _INFERENCE_PROVIDER in ("gemini", "openai", "vllm")

app = FastAPI(
    title="Hybrid Inference Proxy",
    version="2.0.0",
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
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.include_router(inference.router, prefix="/api")
app.include_router(rag_router.router, prefix="/api/rag")


@app.get("/health")
async def health_root() -> dict:
    """Liveness probe for Docker health checks (internal, no /api prefix)."""
    from routers.prefix_cache import get_prefix_cache
    
    cache = get_prefix_cache()
    cache_stats = cache.stats()
    
    health_data = {
        "status": "ok",
        "provider": _INFERENCE_PROVIDER,
        "cache": {
            "size": cache_stats["size"],
            "hit_rate": round(cache_stats["hit_rate"], 3),
        },
    }
    
    if app.state.batch_processor:
        processor = app.state.batch_processor
        health_data["batch"] = {
            "enabled": True,
            "queue_length": len(processor.queue),
        }
    
    return health_data


@app.get("/api/health")
async def health_api() -> dict:
    """Health endpoint accessible through nginx proxy."""
    return await health_root()


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics_root() -> str:
    """
    Prometheus metrics endpoint.
    
    Exposes:
    - inference_requests_total (counter by backend, status)
    - inference_tokens_total (counter by backend)
    - inference_latency_seconds (histogram - TTFT)
    - inference_throughput_tokens_per_second (histogram)
    - prefix_cache_hits_total / misses_total
    - batch_size, batch_wait_time_seconds
    - queue_length
    
    Scrape config for Prometheus:
    ```yaml
    scrape_configs:
      - job_name: 'hybrid-inference'
        static_configs:
          - targets: ['backend:8000']
        metrics_path: '/metrics'
    ```
    """
    return get_metrics().decode()


@app.get("/api/metrics", response_class=PlainTextResponse)
async def metrics_api() -> str:
    """Metrics endpoint accessible through nginx proxy."""
    return await metrics_root()

