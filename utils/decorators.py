"""
NEUTRON Utility Decorators

Common decorators for async retry, rate limiting, timing, and caching.
"""

from __future__ import annotations

import asyncio
import functools
import hashlib
import time
from typing import Any, Callable, TypeVar, ParamSpec
from collections import OrderedDict

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

P = ParamSpec("P")
T = TypeVar("T")


def async_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    retry_on: tuple[type[Exception], ...] = (Exception,),
):
    """
    Decorator for async functions with exponential backoff retry.
    
    Args:
        max_attempts: Maximum retry attempts
        min_wait: Minimum wait between retries (seconds)
        max_wait: Maximum wait between retries (seconds)
        retry_on: Exception types that trigger retry
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except retry_on as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait_time = min(max_wait, min_wait * (2 ** attempt))
                        await asyncio.sleep(wait_time)
            raise last_exception  # type: ignore
        return wrapper  # type: ignore
    return decorator


class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, rate: float, per: float = 60.0):
        self.rate = rate
        self.per = per
        self.allowance = rate
        self.last_check = time.monotonic()
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        async with self._lock:
            current = time.monotonic()
            elapsed = current - self.last_check
            self.last_check = current
            self.allowance += elapsed * (self.rate / self.per)
            if self.allowance > self.rate:
                self.allowance = self.rate
            if self.allowance < 1.0:
                wait_time = (1.0 - self.allowance) * (self.per / self.rate)
                await asyncio.sleep(wait_time)
                self.allowance = 0.0
            else:
                self.allowance -= 1.0


_rate_limiters: dict[str, RateLimiter] = {}


def rate_limit(calls: int, per: float = 60.0, key: str | None = None):
    """
    Rate limiting decorator.
    
    Args:
        calls: Maximum calls allowed
        per: Time window in seconds
        key: Unique key for this limiter (defaults to function name)
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        limiter_key = key or f"{func.__module__}.{func.__name__}"
        if limiter_key not in _rate_limiters:
            _rate_limiters[limiter_key] = RateLimiter(calls, per)
        
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            await _rate_limiters[limiter_key].acquire()
            return await func(*args, **kwargs)
        return wrapper  # type: ignore
    return decorator


def timed(func: Callable[P, T]) -> Callable[P, T]:
    """Decorator to measure and log function execution time."""
    @functools.wraps(func)
    async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        start = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            elapsed = time.perf_counter() - start
            # Store timing on function for inspection
            if not hasattr(func, "_timings"):
                func._timings = []  # type: ignore
            func._timings.append(elapsed)  # type: ignore
    
    @functools.wraps(func)
    def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed = time.perf_counter() - start
            if not hasattr(func, "_timings"):
                func._timings = []  # type: ignore
            func._timings.append(elapsed)  # type: ignore
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper  # type: ignore
    return sync_wrapper  # type: ignore


class AsyncLRUCache:
    """LRU cache for async functions."""
    
    def __init__(self, maxsize: int = 128, ttl: float | None = None):
        self.maxsize = maxsize
        self.ttl = ttl
        self.cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = asyncio.Lock()
    
    def _make_key(self, args: tuple, kwargs: dict) -> str:
        key_data = str((args, sorted(kwargs.items())))
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def get(self, key: str) -> tuple[bool, Any]:
        async with self._lock:
            if key in self.cache:
                value, timestamp = self.cache[key]
                if self.ttl is None or (time.time() - timestamp) < self.ttl:
                    self.cache.move_to_end(key)
                    return True, value
                del self.cache[key]
            return False, None
    
    async def set(self, key: str, value: Any) -> None:
        async with self._lock:
            if key in self.cache:
                del self.cache[key]
            elif len(self.cache) >= self.maxsize:
                self.cache.popitem(last=False)
            self.cache[key] = (value, time.time())
    
    async def clear(self) -> None:
        async with self._lock:
            self.cache.clear()


def cached_async(maxsize: int = 128, ttl: float | None = None):
    """
    Async LRU cache decorator with optional TTL.
    
    Args:
        maxsize: Maximum cache entries
        ttl: Time-to-live in seconds (None = no expiry)
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        cache = AsyncLRUCache(maxsize=maxsize, ttl=ttl)
        
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            key = cache._make_key(args, kwargs)
            hit, value = await cache.get(key)
            if hit:
                return value
            result = await func(*args, **kwargs)
            await cache.set(key, result)
            return result
        
        wrapper.cache = cache  # type: ignore
        wrapper.cache_clear = cache.clear  # type: ignore
        return wrapper  # type: ignore
    return decorator


def ensure_initialized(init_method: str = "initialize"):
    """
    Decorator ensuring component is initialized before method call.
    
    Args:
        init_method: Name of the initialization method
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(self, *args: P.args, **kwargs: P.kwargs) -> T:
            if hasattr(self, "_initialized") and not self._initialized:
                init = getattr(self, init_method, None)
                if init and callable(init):
                    await init()
            return await func(self, *args, **kwargs)
        return wrapper  # type: ignore
    return decorator


def debounce(wait: float):
    """Debounce decorator - only execute if not called again within wait period."""
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        last_call = [0.0]
        pending: list[asyncio.Task] = []
        
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | None:
            current_time = time.time()
            last_call[0] = current_time
            
            for task in pending:
                task.cancel()
            pending.clear()
            
            async def delayed_call():
                await asyncio.sleep(wait)
                if last_call[0] == current_time:
                    return await func(*args, **kwargs)
                return None
            
            task = asyncio.create_task(delayed_call())
            pending.append(task)
            return await task
        return wrapper  # type: ignore
    return decorator


def throttle(interval: float):
    """Throttle decorator - limit execution to once per interval."""
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        last_call = [0.0]
        
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | None:
            current_time = time.time()
            if current_time - last_call[0] >= interval:
                last_call[0] = current_time
                return await func(*args, **kwargs)
            return None
        return wrapper  # type: ignore
    return decorator


__all__ = [
    "async_retry",
    "rate_limit",
    "timed",
    "cached_async",
    "ensure_initialized",
    "debounce",
    "throttle",
    "RateLimiter",
    "AsyncLRUCache",
]
