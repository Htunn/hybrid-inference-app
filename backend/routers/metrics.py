"""
Prometheus metrics for inference monitoring.
Tracks throughput, latency, cache performance, and errors.
"""
import time
from functools import wraps
from typing import Any, Callable

from prometheus_client import (
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)


# Request metrics
inference_requests_total = Counter(
    "inference_requests_total",
    "Total number of inference requests",
    ["backend", "status"],
)

inference_tokens_total = Counter(
    "inference_tokens_total",
    "Total number of tokens generated",
    ["backend"],
)

inference_latency_seconds = Histogram(
    "inference_latency_seconds",
    "Time to first token (TTFT) in seconds",
    ["backend"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

inference_throughput_tokens_per_second = Histogram(
    "inference_throughput_tokens_per_second",
    "Tokens per second during generation",
    ["backend"],
    buckets=(1, 5, 10, 25, 50, 100, 200),
)

# Cache metrics
prefix_cache_hits_total = Counter(
    "prefix_cache_hits_total",
    "Number of prefix cache hits",
)

prefix_cache_misses_total = Counter(
    "prefix_cache_misses_total",
    "Number of prefix cache misses",
)

prefix_cache_size = Gauge(
    "prefix_cache_size",
    "Current number of entries in prefix cache",
)

# Batch metrics
batch_size = Histogram(
    "batch_size",
    "Number of requests processed per batch",
    buckets=(1, 2, 4, 8, 16, 32),
)

batch_wait_time_seconds = Histogram(
    "batch_wait_time_seconds",
    "Time requests wait in queue before batching",
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
)

# Queue metrics
queue_length = Gauge(
    "queue_length",
    "Current number of requests in batch queue",
)

# RAG metrics
rag_retrieval_latency_seconds = Histogram(
    "rag_retrieval_latency_seconds",
    "Time to retrieve documents from vector store",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0),
)

rag_documents_retrieved_total = Counter(
    "rag_documents_retrieved_total",
    "Total number of documents retrieved",
)


def track_inference(backend: str):
    """Decorator to track inference request metrics."""
    def decorator(func: Callable) -> Callable:  # type: ignore[type-arg]
        @wraps(func)
        async def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
            start = time.time()
            token_count = 0
            first_token_time = None

            try:
                async for token in func(*args, **kwargs):
                    if first_token_time is None:
                        first_token_time = time.time()
                        ttft = first_token_time - start
                        inference_latency_seconds.labels(backend=backend).observe(ttft)
                    
                    token_count += 1
                    yield token

                # Success
                inference_requests_total.labels(backend=backend, status="success").inc()
                inference_tokens_total.labels(backend=backend).inc(token_count)

                # Calculate throughput
                duration = time.time() - start
                if duration > 0:
                    tps = token_count / duration
                    inference_throughput_tokens_per_second.labels(backend=backend).observe(tps)

            except Exception as e:
                inference_requests_total.labels(backend=backend, status="error").inc()
                raise e

        return wrapper
    return decorator


def get_metrics() -> bytes:
    """Generate Prometheus metrics in text format."""
    return generate_latest(REGISTRY)


def update_cache_metrics(cache_stats: dict[str, Any]):
    """Update prefix cache metrics from cache stats."""
    prefix_cache_size.set(cache_stats["size"])
    
    # Note: hits/misses are cumulative, so we only update the gauge
    # The actual increment happens in the cache get() method


def update_batch_metrics(batch_len: int, wait_time: float):
    """Update batch processing metrics."""
    batch_size.observe(batch_len)
    batch_wait_time_seconds.observe(wait_time)


def update_queue_metrics(queue_len: int):
    """Update queue length gauge."""
    queue_length.set(queue_len)
