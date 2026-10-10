"""
NEUTRON Perplexity AI Provider

Integration with Perplexity API for news/factual queries.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from config.constants import PERPLEXITY_SYSTEM_PROMPT
from config.settings import get_settings
from ai.providers.base import AIProviderBase, ProviderResponse
from utils.logging_config import get_logger
from utils.decorators import async_retry, rate_limit


class PerplexityProvider(AIProviderBase):
    """Perplexity API provider for factual/news queries."""
    
    API_URL = "https://api.perplexity.ai/chat/completions"
    
    def __init__(self) -> None:
        super().__init__("perplexity")
        self._logger = get_logger("PerplexityProvider")
        self._client: httpx.AsyncClient | None = None
        self._api_key = ""
    
    async def initialize(self) -> None:
        """Initialize Perplexity client."""
        settings = get_settings()
        self._api_key = settings.ai.perplexity_api_key
        
        if not self._api_key or self._api_key == "your_perplexity_api_key_here":
            self._logger.warning("Perplexity API key not configured")
            self._initialized = False
            return
        
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )
        self._initialized = True
        self._logger.info("Perplexity provider initialized")
    
    async def shutdown(self) -> None:
        """Shutdown client."""
        if self._client:
            await self._client.aclose()
        self._initialized = False
    
    @async_retry(max_attempts=3, min_wait=1.0, max_wait=10.0)
    @rate_limit(calls=30, per=60.0, key="perplexity")
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        context: dict[str, Any] | None = None,
        max_tokens: int = 150,
        temperature: float = 0.7,
    ) -> ProviderResponse:
        """Generate response using Perplexity."""
        if not self._initialized or not self._client:
            raise RuntimeError("Perplexity provider not initialized")
        
        start_time = time.time()
        self._request_count += 1
        
        try:
            messages = [
                {"role": "system", "content": system_prompt or PERPLEXITY_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            
            payload = {
                "model": "llama-3.1-sonar-small-128k-online",
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            
            response = await self._client.post(self.API_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            
            latency = (time.time() - start_time) * 1000
            self._total_latency += latency
            
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            tokens = data.get("usage", {}).get("total_tokens", 0)
            
            return ProviderResponse(
                text=text.strip(),
                provider="perplexity",
                model="llama-3.1-sonar-small-128k-online",
                tokens_used=tokens,
                latency_ms=latency,
            )
            
        except Exception as e:
            self._error_count += 1
            self._logger.error(f"Perplexity generation error: {e}")
            raise
    
    async def health_check(self) -> bool:
        """Check Perplexity API health."""
        if not self._initialized or not self._client:
            return False
        try:
            response = await self._client.post(
                self.API_URL,
                json={
                    "model": "llama-3.1-sonar-small-128k-online",
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 5,
                },
            )
            return response.status_code == 200
        except Exception:
            return False


__all__ = ["PerplexityProvider"]
