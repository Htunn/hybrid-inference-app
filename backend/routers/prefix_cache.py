"""
Prefix caching for repeated prompt patterns.
Inspired by vLLM's automatic prefix caching to reduce redundant computation.
"""
import hashlib
from collections import OrderedDict
from typing import Any


class PrefixCache:
    """
    LRU cache for prompt prefixes to avoid recomputing common contexts.
    
    Example use cases:
    - Chat applications with system prompts (cache the system message)
    - RAG pipelines (cache retrieved context that appears in multiple queries)
    - Few-shot prompts (cache example demonstrations)
    
    vLLM Reference:
    https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/
    """

    def __init__(self, max_size: int = 100, min_prefix_len: int = 3):
        """
        Args:
            max_size: Maximum number of cached prefixes (LRU eviction)
            min_prefix_len: Minimum number of messages to consider as prefix
        """
        self.max_size = max_size
        self.min_prefix_len = min_prefix_len
        self.cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def _hash_messages(self, messages: list[dict]) -> str:
        """Create deterministic hash of message sequence."""
        content = "|".join(f"{m['role']}:{m['content']}" for m in messages)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get(self, messages: list[dict]) -> dict[str, Any] | None:
        """
        Check if prefix of these messages is cached.
        
        Returns cached state if prefix matches, else None.
        """
        if len(messages) < self.min_prefix_len:
            self.misses += 1
            return None

        # Try progressively shorter prefixes
        for prefix_len in range(len(messages) - 1, self.min_prefix_len - 1, -1):
            prefix = messages[:prefix_len]
            key = self._hash_messages(prefix)
            
            if key in self.cache:
                self.hits += 1
                # Move to end (LRU)
                self.cache.move_to_end(key)
                return {
                    "prefix_messages": prefix,
                    "remaining_messages": messages[prefix_len:],
                    "cache_key": key,
                    "prefix_length": prefix_len,
                }

        self.misses += 1
        return None

    def put(self, messages: list[dict], state: dict[str, Any] | None = None):
        """
        Cache a message prefix.
        
        Args:
            messages: Message sequence to cache
            state: Optional opaque state (e.g., KV cache blocks)
        """
        if len(messages) < self.min_prefix_len:
            return

        key = self._hash_messages(messages)
        
        # Add to cache
        self.cache[key] = {
            "messages": messages,
            "state": state,
        }
        
        # Evict oldest if over capacity
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

    def clear(self):
        """Clear all cached prefixes."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0.0
        
        return {
            "size": len(self.cache),
            "capacity": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
        }


# Global cache instance
_prefix_cache: PrefixCache | None = None


def get_prefix_cache() -> PrefixCache:
    """Get or create the global prefix cache."""
    global _prefix_cache
    if _prefix_cache is None:
        import os
        cache_size = int(os.getenv("PREFIX_CACHE_SIZE", "100"))
        min_prefix = int(os.getenv("PREFIX_MIN_LENGTH", "3"))
        _prefix_cache = PrefixCache(max_size=cache_size, min_prefix_len=min_prefix)
    return _prefix_cache
