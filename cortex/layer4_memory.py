"""
NEUTRON Cortex Layer 4 - Memory

Integrates with memory system for context retrieval and storage triggers.
"""

from __future__ import annotations

from typing import Any

from config.constants import CortexLayer, SystemEvent
from cortex.base import DeepPathLayer, LayerInput, LayerResult


class MemoryLayer(DeepPathLayer):
    """Layer 4: Memory integration for context building."""
    
    def __init__(self) -> None:
        super().__init__()
        self._memory_manager = None  # Injected at runtime
        self._retrieval_count = 0
    
    @property
    def layer(self) -> CortexLayer:
        return CortexLayer.MEMORY
    
    def set_memory_manager(self, manager) -> None:
        """Inject memory manager dependency."""
        self._memory_manager = manager
    
    async def process(self, input_data: LayerInput) -> LayerResult:
        text = input_data.text
        context = input_data.context
        
        result_data: dict[str, Any] = {
            "retrieved_memories": [],
            "context_added": [],
            "should_store": False,
            "retrieval_score": 0.0,
        }
        
        # Skip if private mode
        if self._state.is_private:
            return LayerResult(
                success=True,
                data=result_data,
                metadata={"private_mode": True},
                should_propagate=True,
            )
        
        # Retrieve relevant memories
        if self._memory_manager and text:
            try:
                memories = await self._retrieve_memories(text)
                result_data["retrieved_memories"] = memories
                self._retrieval_count += 1
                
                # Calculate relevance score
                if memories:
                    result_data["retrieval_score"] = sum(
                        m.get("score", 0) for m in memories
                    ) / len(memories)
                    
                    # Add to context for downstream layers
                    result_data["context_added"] = [
                        m.get("content", "") for m in memories[:3]
                    ]
            except Exception as e:
                self._logger.error(f"Memory retrieval error: {e}")
        
        # Determine if current input should be stored
        result_data["should_store"] = self._should_store(text, input_data)
        
        if result_data["should_store"]:
            await self.emit(
                SystemEvent.MEMORY_STORE,
                {"text": text, "type": "episodic"},
                correlation_id=input_data.correlation_id,
            )
        
        return LayerResult(
            success=True,
            data=result_data,
            confidence=min(1.0, result_data["retrieval_score"] + 0.5),
            should_propagate=True,
        )
    
    async def _retrieve_memories(self, query: str) -> list[dict]:
        """Retrieve relevant memories for query."""
        if not self._memory_manager:
            return []
        
        try:
            results = await self._memory_manager.search(query, limit=5)
            return [
                {
                    "content": r.get("content", ""),
                    "score": r.get("score", 0.0),
                    "timestamp": r.get("timestamp", ""),
                    "type": r.get("type", "episodic"),
                }
                for r in results
            ]
        except Exception:
            return []
    
    def _should_store(self, text: str, input_data: LayerInput) -> bool:
        """Determine if input should be stored in memory."""
        if not text or len(text) < 10:
            return False
        
        # Don't store commands
        command_words = ["stop", "mute", "forget", "private", "quiet"]
        if any(word in text.lower() for word in command_words):
            return False
        
        # Store meaningful interactions
        meaningful_indicators = [
            len(text) > 50,  # Longer messages
            "?" in text,  # Questions
            any(word in text.lower() for word in ["remember", "don't forget", "important"]),
        ]
        
        return any(meaningful_indicators)


__all__ = ["MemoryLayer"]
