"""
NEUTRON Ollama Provider

Local LLM inference using Ollama for offline/monitoring mode.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from ai.providers.base import AIProviderBase, ProviderResponse
from config.settings import get_settings
from utils.decorators import async_retry, rate_limit


class OllamaProvider(AIProviderBase):
    """
    Ollama-based local LLM provider.
    
    Runs locally on the Raspberry Pi or connected machine for:
    - Offline operation
    - Privacy-sensitive queries
    - System monitoring and diagnostics
    """
    
    def __init__(self) -> None:
        super().__init__(name="ollama")
        self._settings = get_settings()
        self._base_url = self._settings.ai.ollama_base_url
        self._model = self._settings.ai.ollama_model
        self._client: httpx.AsyncClient | None = None
        
        # Add logger
        from utils.logging_config import get_logger
        self._logger = get_logger("OllamaProvider")
    
    async def initialize(self) -> None:
        if self._initialized:
            return
        
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=60.0,
        )
        
        # Check if Ollama is available
        try:
            response = await self._client.get("/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                
                if any(self._model in name for name in model_names):
                    self._initialized = True
                    self._logger.info(f"Ollama initialized with model: {self._model}")
                else:
                    self._logger.warning(f"Ollama model {self._model} not found. Available: {model_names}")
                    self._initialized = False
            else:
                self._initialized = False
        except Exception as e:
            self._logger.warning(f"Ollama not available: {e}")
            self._initialized = False
    
    async def shutdown(self) -> None:
        if self._client:
            await self._client.aclose()
        self._initialized = False
    
    @async_retry(max_attempts=2, min_wait=1.0)
    @rate_limit(calls=30, per=60.0, key="ollama")
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
        **kwargs: Any,
    ) -> ProviderResponse:
        if not self._initialized or not self._client:
            return ProviderResponse(
                text="Ollama is not available.",
                provider="ollama",
                success=False,
                error="Not initialized",
            )
        
        self._request_count += 1
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = await self._client.post(
                "/api/chat",
                json={
                    "model": self._model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                },
            )
            
            if response.status_code == 200:
                data = response.json()
                text = data.get("message", {}).get("content", "")
                
                return ProviderResponse(
                    text=text,
                    provider="ollama",
                    model=self._model,
                    success=True,
                    tokens_used=data.get("eval_count", 0),
                    latency_ms=(data.get("total_duration", 0) / 1_000_000),
                )
            else:
                return ProviderResponse(
                    text="",
                    provider="ollama",
                    success=False,
                    error=f"HTTP {response.status_code}",
                )
                
        except Exception as e:
            self._error_count += 1
            self._logger.error(f"Ollama error: {e}")
            return ProviderResponse(
                text="",
                provider="ollama",
                success=False,
                error=str(e),
            )
    
    async def health_check(self) -> bool:
        if not self._client:
            return False
        
        try:
            response = await self._client.get("/api/tags")
            return response.status_code == 200
        except Exception:
            return False
    
    async def analyze_emotion(self, text: str) -> dict[str, float]:
        """
        Use Ollama to analyze emotional content of text.
        Returns emotion values for valence, arousal, etc.
        """
        if not self._initialized:
            return {}
        
        prompt = f"""Analyze the emotional content of this text and return JSON with these values (0.0-1.0):
- valence: negative(0) to positive(1)
- arousal: calm(0) to excited(1)
- trust: suspicious(0) to trusting(1)

Text: "{text}"

Respond ONLY with valid JSON, no explanation."""
        
        response = await self.generate(prompt, temperature=0.3, max_tokens=100)
        
        if response.success:
            try:
                import json
                # Try to extract JSON from response
                text = response.text.strip()
                if text.startswith("```"):
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                return json.loads(text)
            except Exception:
                pass
        
        return {}
    
    async def get_system_prompt_for_monitoring(self) -> str:
        """Get system prompt optimized for local monitoring."""
        return """You are NEUTRON's local monitoring assistant. Provide brief, technical responses about:
- System status and health
- Resource usage (CPU, RAM)
- Component diagnostics
- Error analysis

Keep responses concise and actionable."""


__all__ = ["OllamaProvider"]
