"""
NEUTRON AI Router

Intelligent multi-provider routing with caching and fallback.
Enhanced with inner consciousness and multi-model orchestration.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from config.constants import IntentCategory, INTENT_PROVIDER_MAP
from config.settings import get_settings, AIProvider
from ai.cache import ResponseCache
from ai.intent import IntentClassifier
from ai.providers.base import AIProviderBase, ProviderResponse
from ai.providers.gemini import GeminiProvider
from ai.providers.perplexity import PerplexityProvider
from ai.providers.offline import OfflineProvider
from ai.providers.ollama import OllamaProvider
from ai.model_orchestrator import get_model_orchestrator, TaskType
from cognition.consciousness import get_consciousness
from utils.logging_config import get_logger
from utils.events import EventEmitter
from config.constants import SystemEvent


class AIRouter(EventEmitter):
    """Routes queries to appropriate AI providers."""
    
    _instance: "AIRouter | None" = None
    
    def __init__(self) -> None:
        self._logger = get_logger("AIRouter")
        self._settings = get_settings()
        
        self._providers: dict[str, AIProviderBase] = {
            "gemini": GeminiProvider(),
            "perplexity": PerplexityProvider(),
            "ollama": OllamaProvider(),
            "offline": OfflineProvider(),
        }
        
        # Ollama for local monitoring and emotion analysis
        self._ollama = self._providers["ollama"]
        
        self._intent_classifier = IntentClassifier()
        
        cache_path = Path(self._settings.data_dir) / "cache" / "responses.json"
        self._cache = ResponseCache(
            max_size=self._settings.ai.cache_max_size_mb * 10,
            ttl_seconds=self._settings.ai.cache_ttl_seconds,
            persist_path=cache_path if self._settings.ai.cache_enabled else None,
        )
        
        self._initialized = False
        self._request_count = 0
    
    @classmethod
    def get_instance(cls) -> "AIRouter":
        if cls._instance is None:
            cls._instance = AIRouter()
        return cls._instance
    
    async def initialize(self) -> None:
        """Initialize all providers."""
        if self._initialized:
            return
        
        self._logger.info("Initializing AI router")
        
        for name, provider in self._providers.items():
            try:
                await provider.initialize()
            except Exception as e:
                self._logger.error(f"Failed to initialize {name}: {e}")
        
        if self._settings.ai.cache_enabled:
            await self._cache.load()
        
        self._initialized = True
        self._logger.info("AI router initialized")
    
    async def shutdown(self) -> None:
        """Shutdown all providers."""
        self._logger.info("Shutting down AI router")
        
        if self._settings.ai.cache_enabled:
            await self._cache.save()
        
        for provider in self._providers.values():
            try:
                await provider.shutdown()
            except Exception as e:
                self._logger.error(f"Provider shutdown error: {e}")
        
        self._initialized = False
    
    async def route(
        self,
        query: str,
        intent: IntentCategory | None = None,
        context: dict[str, Any] | None = None,
        force_provider: str | None = None,
    ) -> dict[str, Any]:
        """Route query to appropriate provider."""
        if not self._initialized:
            await self.initialize()
        
        self._request_count += 1
        context = context or {}
        
        # Classify intent if not provided
        if intent is None:
            intent, confidence = self._intent_classifier.classify(query)
            context["intent_confidence"] = confidence
        
        # Convert intent enum to string for serialization/caching
        context["intent"] = intent.value if intent else "unknown"
        
        # Check cache first
        if self._settings.ai.cache_enabled:
            provider_name = force_provider or INTENT_PROVIDER_MAP.get(intent, "gemini")
            cached = await self._cache.get(query, provider_name, context)
            if cached:
                return {"text": cached["text"], "provider": provider_name, "cached": True}
        
        # Determine provider order
        provider_order = self._get_provider_order(intent, force_provider)
        
        # Try providers in order
        last_error = None
        for provider_name in provider_order:
            provider = self._providers.get(provider_name)
            if not provider or not provider.is_available:
                continue
            
            try:
                response = await provider.generate(
                    prompt=query,
                    context=context,
                    max_tokens=self._settings.personality.max_tokens,
                    temperature=self._settings.personality.temperature,
                )

                # Providers report failures via the response object; fall through to the next one.
                if not getattr(response, "success", True) or not response.text:
                    last_error = getattr(response, "error", None) or "empty response"
                    self._logger.warning(f"Provider {provider_name} returned no usable text: {last_error}")
                    continue

                result = {
                    "text": response.text,
                    "provider": provider_name,
                    "cached": False,
                    "latency_ms": response.latency_ms,
                }
                
                # Cache successful response
                if self._settings.ai.cache_enabled:
                    await self._cache.set(query, provider_name, result, context)
                
                await self.emit(SystemEvent.AI_RESPONSE, result)
                return result
                
            except Exception as e:
                last_error = e
                self._logger.warning(f"Provider {provider_name} failed: {e}")
                continue
        
        # All providers failed, use offline
        self._logger.error(f"All providers failed, using offline: {last_error}")
        offline = self._providers["offline"]
        response = await offline.generate(prompt=query, context=context)
        return {"text": response.text, "provider": "offline", "cached": False, "fallback": True}
    
    def _get_provider_order(self, intent: IntentCategory, force: str | None) -> list[str]:
        """Determine provider order based on intent."""
        if force and force in self._providers:
            return [force, "offline"]
        
        primary = INTENT_PROVIDER_MAP.get(intent, "gemini")
        
        if primary == "gemini":
            return ["gemini", "perplexity", "ollama", "offline"]
        elif primary == "perplexity":
            return ["perplexity", "gemini", "ollama", "offline"]
        else:
            # Command/system queries can use local Ollama if available
            if self._settings.ai.ollama_enabled:
                return ["ollama", "offline"]
            return ["offline"]
    
    async def analyze_emotion(self, text: str) -> dict[str, float]:
        """
        Analyze emotional content using Ollama (local) or Gemini.
        
        Returns:
            Dict with valence, arousal, trust values
        """
        # Prefer Ollama for privacy and latency
        if self._settings.ai.ollama_enabled and self._settings.ai.ollama_for_emotions:
            if isinstance(self._ollama, OllamaProvider):
                result = await self._ollama.analyze_emotion(text)
                if result:
                    return result
        
        # Fallback to simple heuristic
        return self._simple_emotion_analysis(text)
    
    def _simple_emotion_analysis(self, text: str) -> dict[str, float]:
        """Simple keyword-based emotion analysis."""
        text_lower = text.lower()
        
        positive = ["happy", "great", "love", "awesome", "good", "excellent", "thank", "please"]
        negative = ["sad", "angry", "hate", "bad", "terrible", "awful", "frustrated", "annoyed"]
        excited = ["!", "wow", "amazing", "incredible", "omg", "excited"]
        
        pos_count = sum(1 for w in positive if w in text_lower)
        neg_count = sum(1 for w in negative if w in text_lower)
        exc_count = sum(1 for w in excited if w in text_lower)
        
        valence = 0.5 + (pos_count - neg_count) * 0.1
        arousal = 0.3 + exc_count * 0.15
        
        return {
            "valence": max(0, min(1, valence)),
            "arousal": max(0, min(1, arousal)),
            "trust": 0.6,
        }
    
    async def monitor_system(self, query: str) -> dict[str, Any]:
        """
        Use Ollama for local system monitoring queries.
        """
        if not self._settings.ai.ollama_enabled or not self._settings.ai.ollama_for_monitoring:
            return {"text": "Local monitoring not available", "provider": "none"}
        
        if isinstance(self._ollama, OllamaProvider):
            system_prompt = await self._ollama.get_system_prompt_for_monitoring()
            response = await self._ollama.generate(
                prompt=query,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=200,
            )
            return {"text": response.text, "provider": "ollama", "success": response.success}
        
        return {"text": "Ollama not initialized", "provider": "none"}
    
    async def conscious_route(
        self,
        query: str,
        context: dict[str, Any] | None = None,
        vision_context: str = "",
    ) -> dict[str, Any]:
        """
        Route query using consciousness-driven decision making.
        
        This is the main entry point for human-like processing:
        1. Consciousness thinks about the query
        2. Model orchestrator selects best model
        3. Response is generated with inner reflection
        
        Args:
            query: User's question or input
            context: Additional context (audio, memory, etc.)
            vision_context: What the robot currently sees
            
        Returns:
            Response with thoughts, provider info, and generated text
        """
        context = context or {}
        
        # Get consciousness and orchestrator
        consciousness = get_consciousness()
        orchestrator = get_model_orchestrator()
        
        # Initialize orchestrator if needed
        if not orchestrator._initialized:
            await orchestrator.initialize()
        
        # 1. Feed vision context to consciousness
        if vision_context:
            await consciousness.perceive_vision(vision_context)
            context["vision_context"] = vision_context
        
        # 2. Let consciousness think about the query
        thought_result = await consciousness.process_query(query)
        
        # 3. Get routing decision from orchestrator
        task_type = orchestrator.classify_task(query, context)
        routing = orchestrator.route(task_type)
        
        # Map orchestrator model to provider
        model_to_provider = {
            "llava": "ollama",
            "tinyllama": "ollama",
            "deepseek": "ollama",
            "gemini": "gemini",
            "perplexity": "perplexity",
        }
        
        force_provider = model_to_provider.get(routing.primary_model, "ollama")
        
        # 4. Generate response using selected provider
        self._logger.info(f"Conscious route: {routing.reasoning} -> {force_provider}")
        
        # Add consciousness context for richer responses
        context["inner_thoughts"] = thought_result.get("thoughts", [])
        context["task_type"] = task_type.name
        
        # Route to the provider
        result = await self.route(
            query=query,
            context=context,
            force_provider=force_provider,
        )
        
        # 5. Reflect on the response
        await consciousness.reflect_on_response(result.get("text", ""))
        
        # Enrich result with consciousness info
        result["thoughts"] = thought_result.get("thoughts", [])
        result["current_thought"] = consciousness.get_current_thought()
        result["routing_reason"] = routing.reasoning
        result["task_type"] = task_type.name
        result["model"] = routing.primary_model
        
        return result
    
    def get_stats(self) -> dict[str, Any]:
        """Get router statistics."""
        return {
            "initialized": self._initialized,
            "total_requests": self._request_count,
            "cache": self._cache.stats,
            "providers": {name: p.stats for name, p in self._providers.items()},
            "ollama_enabled": self._settings.ai.ollama_enabled,
        }


@lru_cache()
def get_router() -> AIRouter:
    return AIRouter.get_instance()


__all__ = ["AIRouter", "get_router"]
