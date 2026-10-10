"""
NEUTRON Cortex Layer 7 - Executive

Highest-level cognitive functions:
- Tool routing and planning
- Reflection and self-model updates
- Response generation orchestration
"""

from __future__ import annotations

from typing import Any

from config.constants import CortexLayer, SystemEvent, IntentCategory
from cortex.base import DeepPathLayer, LayerInput, LayerResult


class ExecutiveLayer(DeepPathLayer):
    """Layer 7: Executive functions for planning and response generation."""
    
    def __init__(self) -> None:
        super().__init__()
        self._ai_router = None  # Injected at runtime
        self._pending_actions: list[dict] = []
        self._reflection_buffer: list[str] = []
    
    @property
    def layer(self) -> CortexLayer:
        return CortexLayer.EXECUTIVE
    
    def set_ai_router(self, router) -> None:
        """Inject AI router dependency."""
        self._ai_router = router
    
    async def process(self, input_data: LayerInput) -> LayerResult:
        text = input_data.text
        previous_results = input_data.previous_results
        context = input_data.context
        
        result_data: dict[str, Any] = {
            "response": None,
            "intent": None,
            "provider_used": None,
            "actions_planned": [],
            "reflection": None,
            "confidence_adjustment": 0.0,
        }
        
        if not text:
            return LayerResult(success=True, data=result_data, should_propagate=False)
        
        # Build context from previous layer results
        enriched_context = self._build_context(previous_results, context)
        
        # Classify intent
        intent = await self._classify_intent(text)
        result_data["intent"] = intent.value
        
        # Route to AI provider using consciousness-driven approach
        if self._ai_router:
            try:
                # Use conscious routing for human-like thinking
                if hasattr(self._ai_router, 'conscious_route'):
                    response = await self._ai_router.conscious_route(
                        query=text,
                        context=enriched_context,
                        vision_context=enriched_context.get("vision_description", ""),
                    )
                    result_data["response"] = response.get("text", "")
                    result_data["provider_used"] = response.get("provider", "unknown")
                    result_data["thoughts"] = response.get("thoughts", [])
                    result_data["current_thought"] = response.get("current_thought", "")
                    result_data["model"] = response.get("model", "")
                    result_data["routing_reason"] = response.get("routing_reason", "")
                else:
                    # Fallback to standard routing
                    response = await self._ai_router.route(
                        query=text,
                        intent=intent,
                        context=enriched_context,
                    )
                    result_data["response"] = response.get("text", "")
                    result_data["provider_used"] = response.get("provider", "unknown")
            except Exception as e:
                self._logger.error(f"AI routing error: {e}")
                result_data["response"] = "my bad, hit a snag there. try again?"
                result_data["provider_used"] = "fallback"
        else:
            result_data["response"] = await self._generate_fallback_response(text, intent)
            result_data["provider_used"] = "offline"
        
        # Plan follow-up actions
        result_data["actions_planned"] = self._plan_actions(text, result_data["response"])
        
        # Update self-model through reflection
        if len(self._reflection_buffer) > 5:
            result_data["reflection"] = await self._reflect()
        
        # Emit response event
        await self.emit(
            SystemEvent.AI_RESPONSE,
            {"text": result_data["response"], "provider": result_data["provider_used"]},
            correlation_id=input_data.correlation_id,
        )
        
        return LayerResult(
            success=True,
            data=result_data,
            confidence=0.8,
            should_propagate=False,
            should_respond=True,
        )
    
    def _build_context(self, previous_results: list[LayerResult], context: dict) -> dict:
        """Build enriched context from layer results."""
        enriched = dict(context)
        
        for result in previous_results:
            if result.layer and result.success:
                layer_name = result.layer.name.lower()
                enriched[f"{layer_name}_data"] = result.data
                
                # Extract specific useful data
                if result.layer == CortexLayer.EMOTIONAL:
                    enriched["emotion"] = result.data.get("emotion", {})
                elif result.layer == CortexLayer.MEMORY:
                    memories = result.data.get("retrieved_memories", [])
                    if memories:
                        enriched["relevant_memories"] = [m.get("content", "") for m in memories[:3]]
        
        return enriched
    
    async def _classify_intent(self, text: str) -> IntentCategory:
        """Classify query intent for AI routing."""
        text_lower = text.lower()
        
        # Command patterns
        if any(w in text_lower for w in ["stop", "mute", "forget", "private", "quiet"]):
            return IntentCategory.COMMAND
        
        # News/factual patterns
        if any(w in text_lower for w in ["news", "latest", "today", "current", "what happened"]):
            return IntentCategory.NEWS
        
        if any(w in text_lower for w in ["how many", "what is", "when was", "where is", "who is"]):
            return IntentCategory.FACTUAL
        
        # Emotional patterns
        if any(w in text_lower for w in ["feel", "sad", "happy", "stressed", "worried", "anxious"]):
            return IntentCategory.EMOTIONAL
        
        # Personal patterns
        if any(w in text_lower for w in ["remember", "last time", "my", "i told you"]):
            return IntentCategory.PERSONAL
        
        # Reflective patterns
        if any(w in text_lower for w in ["think about", "meaning", "why do", "purpose", "philosophy"]):
            return IntentCategory.REFLECTIVE
        
        # Search patterns
        if any(w in text_lower for w in ["search", "find", "look up", "google"]):
            return IntentCategory.SEARCH
        
        # Default to small talk
        return IntentCategory.SMALL_TALK
    
    async def _generate_fallback_response(self, text: str, intent: IntentCategory) -> str:
        """Generate offline fallback response."""
        import random
        
        if intent == IntentCategory.COMMAND:
            return "got it"
        
        fallbacks = [
            "yo, i'm having trouble connecting rn. maybe try again in a sec?",
            "lowkey can't get online atm, but i'm still here for basic stuff",
            "my connection's being weird, but what's up?",
        ]
        return random.choice(fallbacks)
    
    def _plan_actions(self, query: str, response: str) -> list[dict]:
        """Plan follow-up actions based on interaction."""
        actions = []
        
        # Store interaction if meaningful
        if len(query) > 20 and len(response) > 20:
            actions.append({"type": "store_memory", "priority": 1})
        
        # Schedule follow-up if care-related
        if any(w in query.lower() for w in ["worried", "stressed", "anxious"]):
            actions.append({"type": "schedule_followup", "delay_hours": 2})
        
        return actions
    
    async def _reflect(self) -> str:
        """Perform self-reflection on recent interactions."""
        self._reflection_buffer.clear()
        return "interactions analyzed, adjusting approach"


__all__ = ["ExecutiveLayer"]
