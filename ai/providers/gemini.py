"""
NEUTRON Gemini AI Provider

Integration with Google Gemini API for emotional/personal queries.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from config.constants import GEMINI_SYSTEM_PROMPT
from config.settings import get_settings
from ai.providers.base import AIProviderBase, ProviderResponse
from utils.logging_config import get_logger
from utils.decorators import async_retry, rate_limit


class GeminiProvider(AIProviderBase):
    """Google Gemini API provider."""
    
    def __init__(self) -> None:
        super().__init__("gemini")
        self._logger = get_logger("GeminiProvider")
        self._client = None
        self._model = None
    
    async def initialize(self) -> None:
        """Initialize Gemini client."""
        settings = get_settings()
        api_key = settings.ai.gemini_api_key
        
        if not api_key or api_key == "your_gemini_api_key_here":
            self._logger.warning("Gemini API key not configured")
            self._initialized = False
            return
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self._model = genai.GenerativeModel(
                "gemini-1.5-flash",
                generation_config=genai.GenerationConfig(
                    max_output_tokens=200,
                    temperature=0.7,
                ),
            )
            self._initialized = True
            self._logger.info("Gemini provider initialized")
        except Exception as e:
            self._logger.error(f"Gemini initialization error: {e}")
            self._initialized = False
    
    @async_retry(max_attempts=3, min_wait=1.0, max_wait=10.0)
    @rate_limit(calls=60, per=60.0, key="gemini")
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        context: dict[str, Any] | None = None,
        max_tokens: int = 150,
        temperature: float = 0.7,
    ) -> ProviderResponse:
        """Generate response using Gemini."""
        if not self._initialized or not self._model:
            raise RuntimeError("Gemini provider not initialized")
        
        start_time = time.time()
        self._request_count += 1
        
        try:
            # Build full prompt
            full_prompt = self._build_prompt(prompt, system_prompt, context)
            
            # Generate response
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._model.generate_content(full_prompt)
            )
            
            latency = (time.time() - start_time) * 1000
            self._total_latency += latency
            
            text = response.text.strip() if response.text else ""
            
            return ProviderResponse(
                text=text,
                provider="gemini",
                model="gemini-1.5-flash",
                latency_ms=latency,
                metadata={"finish_reason": "stop"},
            )
            
        except Exception as e:
            self._error_count += 1
            self._logger.error(f"Gemini generation error: {e}")
            raise
    
    def _build_prompt(
        self,
        prompt: str,
        system_prompt: str | None,
        context: dict[str, Any] | None,
    ) -> str:
        """Build full prompt with system instructions and context."""
        parts = []
        
        # System prompt
        parts.append(system_prompt or GEMINI_SYSTEM_PROMPT)
        
        # Add emotion context if available
        if context and "emotion" in context:
            emotion = context["emotion"]
            parts.append(f"\n[Emotional context: valence={emotion.get('valence', 0.5):.2f}, arousal={emotion.get('arousal', 0.3):.2f}]")
        
        # Add relevant memories if available
        if context and "relevant_memories" in context:
            memories = context["relevant_memories"][:2]
            if memories:
                parts.append(f"\n[Relevant context: {'; '.join(memories)}]")
        
        # User prompt
        parts.append(f"\nUser: {prompt}\nNEUTRON:")
        
        return "\n".join(parts)
    
    async def health_check(self) -> bool:
        """Check Gemini API health."""
        if not self._initialized:
            return False
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._model.generate_content("hi")
            )
            return bool(response.text)
        except Exception:
            return False


__all__ = ["GeminiProvider"]
