"""
NEUTRON AI Provider Base Class
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ProviderResponse:
    """Response from an AI provider."""
    text: str
    provider: str
    model: str = ""
    tokens_used: int = 0
    latency_ms: float = 0.0
    cached: bool = False
    success: bool = True
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "provider": self.provider,
            "model": self.model,
            "tokens_used": self.tokens_used,
            "latency_ms": self.latency_ms,
            "cached": self.cached,
            "success": self.success,
            "error": self.error,
        }


class AIProviderBase(ABC):
    """Abstract base class for AI providers."""
    
    def __init__(self, name: str) -> None:
        self.name = name
        self._initialized = False
        self._request_count = 0
        self._error_count = 0
        self._total_latency = 0.0
    
    @property
    def is_available(self) -> bool:
        return self._initialized
    
    @property
    def stats(self) -> dict[str, Any]:
        avg_latency = self._total_latency / self._request_count if self._request_count > 0 else 0
        return {
            "name": self.name,
            "initialized": self._initialized,
            "requests": self._request_count,
            "errors": self._error_count,
            "avg_latency_ms": avg_latency,
        }
    
    async def initialize(self) -> None:
        """Initialize the provider."""
        self._initialized = True
    
    async def shutdown(self) -> None:
        """Shutdown the provider."""
        self._initialized = False
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        context: dict[str, Any] | None = None,
        max_tokens: int = 150,
        temperature: float = 0.7,
    ) -> ProviderResponse:
        """Generate a response."""
        ...
    
    async def health_check(self) -> bool:
        """Check if provider is healthy."""
        return self._initialized


__all__ = ["AIProviderBase", "ProviderResponse"]
