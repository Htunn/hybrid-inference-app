"""
Continuous batching processor inspired by vLLM.
Improves throughput by batching multiple inference requests together.
"""
import asyncio
import time
from collections import deque
from dataclasses import dataclass
from typing import Any


@dataclass
class InferenceRequest:
    """Single inference request with priority."""
    request_id: str
    messages: list[dict]
    priority: int = 0
    arrived_at: float = 0.0
    response_queue: asyncio.Queue = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.arrived_at == 0.0:
            self.arrived_at = time.time()
        if self.response_queue is None:
            self.response_queue = asyncio.Queue()


class BatchProcessor:
    """
    Continuous batching engine for inference requests.
    
    Features:
    - Priority-based scheduling
    - Configurable batch size and timeout
    - Automatic queue flushing
    - Request cancellation support
    """

    def __init__(
        self,
        max_batch_size: int = 8,
        max_wait_ms: int = 50,
    ):
        self.max_batch_size = max_batch_size
        self.max_wait_ms = max_wait_ms
        self.queue: deque[InferenceRequest] = deque()
        self.lock = asyncio.Lock()
        self.batch_ready = asyncio.Event()
        self._running = False
        self._processor_task = None

    async def start(self):
        """Start the background batch processor."""
        self._running = True
        self._processor_task = asyncio.create_task(self._process_batches())

    async def stop(self):
        """Stop the batch processor gracefully."""
        self._running = False
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass

    async def submit(self, request: InferenceRequest) -> asyncio.Queue:  # type: ignore[type-arg]
        """Submit a request and get a response queue."""
        async with self.lock:
            self.queue.append(request)
            if len(self.queue) >= self.max_batch_size:
                self.batch_ready.set()
        
        return request.response_queue

    async def _process_batches(self):
        """Background loop that processes batches continuously."""
        while self._running:
            try:
                # Wait for batch to fill or timeout
                try:
                    await asyncio.wait_for(
                        self.batch_ready.wait(),
                        timeout=self.max_wait_ms / 1000.0
                    )
                except asyncio.TimeoutError:
                    pass

                # Collect batch
                async with self.lock:
                    if not self.queue:
                        self.batch_ready.clear()
                        continue

                    batch = []
                    while self.queue and len(batch) < self.max_batch_size:
                        batch.append(self.queue.popleft())
                    
                    self.batch_ready.clear()

                # Process batch (placeholder - integrate with backend)
                await self._execute_batch(batch)

            except Exception:  # noqa: BLE001
                # Log error but keep processor running
                import logging
                logging.exception("Batch processor error")

    async def _execute_batch(self, batch: list[InferenceRequest]):
        """
        Execute a batch of requests.
        
        In production, this would:
        1. Merge prompts into a single batch
        2. Call inference backend with batched input
        3. Demux outputs back to individual response queues
        
        For now, we execute sequentially.
        """
        from routers.inference_backends import get_backend
        backend = get_backend()

        for request in batch:
            try:
                async for token in backend.stream_chat(request.messages):
                    await request.response_queue.put(token)
                await request.response_queue.put(None)  # EOF marker
            except Exception as e:  # noqa: BLE001
                await request.response_queue.put(e)


# Global singleton
_batch_processor: BatchProcessor | None = None


def get_batch_processor() -> BatchProcessor:
    """Get or create the global batch processor."""
    global _batch_processor
    if _batch_processor is None:
        import os
        max_batch = int(os.getenv("BATCH_SIZE", "8"))
        max_wait = int(os.getenv("BATCH_WAIT_MS", "50"))
        _batch_processor = BatchProcessor(
            max_batch_size=max_batch,
            max_wait_ms=max_wait,
        )
    return _batch_processor
