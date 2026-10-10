"""
NEUTRON Response Cache

LRU cache with TTL for AI responses.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any

import aiofiles


class ResponseCache:
    """LRU cache with TTL for AI responses."""
    
    def __init__(
        self,
        max_size: int = 1000,
        ttl_seconds: int = 3600,
        persist_path: Path | None = None,
    ) -> None:
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._persist_path = persist_path
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0
    
    @staticmethod
    def _make_key(query: str, provider: str, context_hash: str = "") -> str:
        """Create cache key from query and context."""
        key_data = f"{provider}:{query}:{context_hash}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def get(self, query: str, provider: str, context: dict | None = None) -> dict | None:
        """Get cached response if available and not expired."""
        context_hash = hashlib.md5(json.dumps(context or {}, sort_keys=True).encode()).hexdigest()[:8]
        key = self._make_key(query, provider, context_hash)
        
        async with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if time.time() - timestamp < self._ttl:
                    self._cache.move_to_end(key)
                    self._hits += 1
                    return value
                del self._cache[key]
            
            self._misses += 1
            return None
    
    async def set(self, query: str, provider: str, response: dict, context: dict | None = None) -> None:
        """Cache a response."""
        context_hash = hashlib.md5(json.dumps(context or {}, sort_keys=True).encode()).hexdigest()[:8]
        key = self._make_key(query, provider, context_hash)
        
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
            elif len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
            
            self._cache[key] = (response, time.time())
    
    async def clear(self) -> None:
        """Clear the cache."""
        async with self._lock:
            self._cache.clear()
    
    @property
    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
        }
    
    async def save(self) -> None:
        """Persist cache to disk."""
        if not self._persist_path:
            return
        
        async with self._lock:
            data = {
                key: {"value": value, "timestamp": ts}
                for key, (value, ts) in self._cache.items()
            }
        
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(self._persist_path, "w") as f:
            await f.write(json.dumps(data))
    
    async def load(self) -> None:
        """Load cache from disk."""
        if not self._persist_path or not self._persist_path.exists():
            return
        
        try:
            async with aiofiles.open(self._persist_path, "r") as f:
                data = json.loads(await f.read())
            
            async with self._lock:
                current_time = time.time()
                for key, entry in data.items():
                    if current_time - entry["timestamp"] < self._ttl:
                        self._cache[key] = (entry["value"], entry["timestamp"])
        except Exception:
            pass


__all__ = ["ResponseCache"]
