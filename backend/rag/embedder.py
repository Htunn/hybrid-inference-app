"""
rag/embedder.py — Embedding provider abstraction.

The abstract base `EmbeddingProvider` exposes a single `embed(texts)` method.
`LocalEmbedder` runs sentence-transformers on CPU inside a thread-pool executor
so it doesn't block FastAPI's async event loop (sentence-transformers is sync).

Factory
-------
`get_embedder()` reads EMBEDDER_PROVIDER from the environment:
  - "local" (default) → LocalEmbedder (all-MiniLM-L6-v2, 384-dim, no API key)
  - "openai"          → stub (raises NotImplementedError until implemented)
  - "gemini"          → stub (raises NotImplementedError until implemented)

The embedder is initialised once at startup and stored in app.state.embedder.
"""

import asyncio
import logging
import os
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base class for all embedding backends."""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Number of dimensions in the output vectors."""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""

    async def embed_one(self, text: str) -> list[float]:
        """Convenience wrapper that embeds a single string."""
        results = await self.embed([text])
        return results[0]


class LocalEmbedder(EmbeddingProvider):
    """
    Sentence-transformers embedder running fully on the local machine.

    Model: all-MiniLM-L6-v2 (384-dim, MIT licence, ~23 MB download).
    Inference runs in a thread pool so the async event loop is never blocked.
    Embeddings are L2-normalised, making cosine similarity equivalent to dot product.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        # Import is deferred so the module can be imported even if
        # sentence-transformers is not installed (unit-test friendly).
        from sentence_transformers import SentenceTransformer  # type: ignore[import]

        logger.info("Loading embedding model: %s", model_name)
        self._model = SentenceTransformer(model_name)
        self._dimensions: int = self._model.get_sentence_embedding_dimension()
        logger.info("Embedding model ready — %d dimensions", self._dimensions)

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        loop = asyncio.get_event_loop()
        vectors = await loop.run_in_executor(
            None,
            lambda: self._model.encode(
                texts,
                batch_size=32,
                normalize_embeddings=True,
                show_progress_bar=False,
            ),
        )
        return [v.tolist() for v in vectors]


# ---------------------------------------------------------------------------
# Stubs for future cloud embedding providers
# ---------------------------------------------------------------------------

class _OpenAIEmbedder(EmbeddingProvider):
    """Placeholder — implement when OPENAI_API_KEY is available."""

    @property
    def dimensions(self) -> int:
        return 1536  # text-embedding-3-small default

    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError(
            "OpenAI embedder is not yet implemented. Set EMBEDDER_PROVIDER=local."
        )


class _GeminiEmbedder(EmbeddingProvider):
    """Placeholder — implement when Gemini embedding API is needed."""

    @property
    def dimensions(self) -> int:
        return 768  # text-embedding-004 default

    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError(
            "Gemini embedder is not yet implemented. Set EMBEDDER_PROVIDER=local."
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_embedder() -> EmbeddingProvider:
    """Return the configured embedding provider (reads EMBEDDER_PROVIDER env var)."""
    provider = os.getenv("EMBEDDER_PROVIDER", "local").lower()
    if provider == "local":
        return LocalEmbedder()
    if provider == "openai":
        return _OpenAIEmbedder()
    if provider == "gemini":
        return _GeminiEmbedder()
    raise ValueError(
        f"Unknown EMBEDDER_PROVIDER={provider!r}. Valid values: local, openai, gemini."
    )
