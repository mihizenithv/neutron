"""
NEUTRON Offline Provider

Rules-based fallback when APIs are unavailable.
"""

from __future__ import annotations

import random
import time
from datetime import datetime
from typing import Any

from ai.providers.base import AIProviderBase, ProviderResponse
from config.constants import (
    GREETING_PHRASES, ACKNOWLEDGMENT_PHRASES, ERROR_PHRASES,
    UNCERTAINTY_PHRASES, IntentCategory,
)
from utils.logging_config import get_logger


class OfflineProvider(AIProviderBase):
    """Offline fallback provider with rules-based responses."""
    
    def __init__(self) -> None:
        super().__init__("offline")
        self._logger = get_logger("OfflineProvider")
        self._cached_facts: dict[str, str] = {}
    
    async def initialize(self) -> None:
        """Initialize offline provider."""
        self._load_cached_facts()
        self._initialized = True
        self._logger.info("Offline provider initialized")
    
    def _load_cached_facts(self) -> None:
        """Load cached facts from local storage."""
        self._cached_facts = {
            "time": "",  # Will be computed dynamically
            "date": "",
            "greeting": random.choice(GREETING_PHRASES),
        }
    
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        context: dict[str, Any] | None = None,
        max_tokens: int = 150,
        temperature: float = 0.7,
    ) -> ProviderResponse:
        """Generate offline response."""
        start_time = time.time()
        self._request_count += 1
        
        intent = context.get("intent", IntentCategory.UNKNOWN) if context else IntentCategory.UNKNOWN
        prompt_lower = prompt.lower()
        
        response_text = self._generate_response(prompt_lower, intent, context)
        
        latency = (time.time() - start_time) * 1000
        self._total_latency += latency
        
        return ProviderResponse(
            text=response_text,
            provider="offline",
            model="rules-v1",
            latency_ms=latency,
            metadata={"offline": True},
        )
    
    def _generate_response(
        self,
        prompt: str,
        intent: IntentCategory,
        context: dict[str, Any] | None,
    ) -> str:
        """Generate response based on patterns."""
        
        # Time queries
        if any(w in prompt for w in ["time", "what time", "current time"]):
            now = datetime.now()
            return f"it's {now.strftime('%I:%M %p').lstrip('0')}"
        
        # Date queries
        if any(w in prompt for w in ["date", "what day", "today"]):
            now = datetime.now()
            return f"it's {now.strftime('%A, %B %d')}"
        
        # Greeting patterns
        if any(w in prompt for w in ["hello", "hi", "hey", "sup", "what's up"]):
            return random.choice(GREETING_PHRASES)
        
        # How are you
        if "how are you" in prompt:
            return "doing good! thanks for asking. what's on your mind?"
        
        # Thanks
        if any(w in prompt for w in ["thank", "thanks", "thx"]):
            return "no problem! happy to help"
        
        # Name query
        if "your name" in prompt or "who are you" in prompt:
            return "i'm neutron, your personal assistant. nice to meet you!"
        
        # Help
        if prompt == "help" or "what can you do" in prompt:
            return "i can help with questions, chat, set reminders, and just be here if you need someone to talk to"
        
        # Capability limits (offline)
        if intent in [IntentCategory.NEWS, IntentCategory.SEARCH, IntentCategory.FACTUAL]:
            return f"{random.choice(UNCERTAINTY_PHRASES)} i'm offline rn so i can't look that up, but try again later?"
        
        # Emotional support
        if intent == IntentCategory.EMOTIONAL:
            return "i hear you. even offline, i'm here to listen. what's going on?"
        
        # Default fallback
        return f"{random.choice(ERROR_PHRASES)} i'm having connection issues. basic stuff still works though!"
    
    async def health_check(self) -> bool:
        """Offline provider is always available."""
        return True


__all__ = ["OfflineProvider"]
