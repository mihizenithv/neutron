"""
NEUTRON Cortex Orchestrator

Coordinates all 7 cortex layers based on operation mode.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from functools import lru_cache
from typing import Any

from config.constants import CortexLayer, SystemEvent, NORMAL_MODE_LAYERS, EXTREME_MODE_LAYERS
from config.settings import get_settings, OperationMode
from cortex.base import CortexLayerBase, LayerInput, LayerResult
from cortex.layer1_reflex import ReflexLayer
from cortex.layer2_sensory import SensoryLayer
from cortex.layer3_emotional import EmotionalLayer
from cortex.layer4_memory import MemoryLayer
from cortex.layer5_motivation import MotivationLayer
from cortex.layer6_social import SocialLayer
from cortex.layer7_executive import ExecutiveLayer
from utils.logging_config import get_logger
from utils.events import EventEmitter, get_event_bus
from utils.state import get_state


class CortexOrchestrator(EventEmitter):
    """Orchestrates processing through all cortex layers."""
    
    _instance: "CortexOrchestrator | None" = None
    
    def __init__(self) -> None:
        self._logger = get_logger("CortexOrchestrator")
        self._settings = get_settings()
        self._state = get_state()
        
        # Initialize layers
        self._layers: dict[CortexLayer, CortexLayerBase] = {
            CortexLayer.REFLEX: ReflexLayer(),
            CortexLayer.SENSORY: SensoryLayer(),
            CortexLayer.EMOTIONAL: EmotionalLayer(),
            CortexLayer.MEMORY: MemoryLayer(),
            CortexLayer.MOTIVATION: MotivationLayer(),
            CortexLayer.SOCIAL: SocialLayer(),
            CortexLayer.EXECUTIVE: ExecutiveLayer(),
        }
        
        self._initialized = False
        self._processing = False
        self._total_requests = 0
        self._total_processing_time = 0.0
    
    @classmethod
    def get_instance(cls) -> "CortexOrchestrator":
        if cls._instance is None:
            cls._instance = CortexOrchestrator()
        return cls._instance
    
    async def initialize(self) -> None:
        """Initialize all cortex layers."""
        if self._initialized:
            return
        
        self._logger.info("Initializing cortex layers")
        
        for layer_type, layer in self._layers.items():
            try:
                await layer.initialize()
            except Exception as e:
                self._logger.error(f"Failed to initialize {layer_type.name}: {e}")
        
        self._initialized = True
        self._logger.info("Cortex initialization complete")
    
    async def shutdown(self) -> None:
        """Shutdown all cortex layers."""
        self._logger.info("Shutting down cortex layers")
        
        for layer in reversed(list(self._layers.values())):
            try:
                await layer.shutdown()
            except Exception as e:
                self._logger.error(f"Error shutting down layer: {e}")
        
        self._initialized = False
    
    def get_layer(self, layer: CortexLayer) -> CortexLayerBase:
        """Get a specific layer instance."""
        return self._layers[layer]
    
    def set_memory_manager(self, manager) -> None:
        """Inject memory manager into Layer 4."""
        self._layers[CortexLayer.MEMORY].set_memory_manager(manager)  # type: ignore
    
    def set_ai_router(self, router) -> None:
        """Inject AI router into Layer 7."""
        self._layers[CortexLayer.EXECUTIVE].set_ai_router(router)  # type: ignore
    
    async def process(
        self,
        text: str = "",
        audio_data: bytes | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Process input through active cortex layers.
        
        Args:
            text: Input text
            audio_data: Raw audio data (optional)
            context: Additional context
            
        Returns:
            Combined results from all layers
        """
        if not self._initialized:
            await self.initialize()
        
        correlation_id = str(uuid.uuid4())
        start_time = time.time()
        self._processing = True
        
        input_data = LayerInput(
            text=text,
            audio_data=audio_data,
            context=context or {},
            correlation_id=correlation_id,
        )
        
        results: list[LayerResult] = []
        final_result: dict[str, Any] = {
            "correlation_id": correlation_id,
            "response": None,
            "should_respond": False,
            "layer_results": {},
            "active_layers": [],
            "processing_time_ms": 0.0,
        }
        
        try:
            # Determine active layers based on mode
            active_layer_types = self._get_active_layers()
            final_result["active_layers"] = [l.name for l in active_layer_types]
            
            # Process through each active layer
            for layer_type in active_layer_types:
                layer = self._layers[layer_type]
                
                # Update input with previous results
                input_data.previous_results = results.copy()
                
                # Process layer
                result = await layer.safe_process(input_data)
                results.append(result)
                
                final_result["layer_results"][layer_type.name] = {
                    "success": result.success,
                    "confidence": result.confidence,
                    "processing_time_ms": result.processing_time_ms,
                    "data": result.data,
                }
                
                # Check for response trigger
                if result.should_respond and result.data.get("response"):
                    final_result["response"] = result.data["response"]
                    final_result["should_respond"] = True
                
                # Check if we should stop propagation
                if not result.should_propagate:
                    break
            
            # If Executive layer produced response, use it
            exec_result = final_result["layer_results"].get("EXECUTIVE", {})
            if exec_result.get("data", {}).get("response"):
                final_result["response"] = exec_result["data"]["response"]
                final_result["should_respond"] = True
        
        except Exception as e:
            self._logger.error(f"Cortex processing error: {e}", exc_info=True)
            final_result["error"] = str(e)
        
        finally:
            self._processing = False
            elapsed = (time.time() - start_time) * 1000
            final_result["processing_time_ms"] = elapsed
            self._total_requests += 1
            self._total_processing_time += elapsed
        
        return final_result
    
    def _get_active_layers(self) -> list[CortexLayer]:
        """Get list of active layers based on current mode."""
        if self._state.operation_mode == OperationMode.NORMAL:
            return [CortexLayer.REFLEX, CortexLayer.SENSORY]
        
        return [
            CortexLayer.REFLEX,
            CortexLayer.SENSORY,
            CortexLayer.EMOTIONAL,
            CortexLayer.MEMORY,
            CortexLayer.MOTIVATION,
            CortexLayer.SOCIAL,
            CortexLayer.EXECUTIVE,
        ]
    
    async def process_fast(self, text: str) -> dict[str, Any]:
        """Fast-path processing (layers 1-2 only)."""
        original_mode = self._state.operation_mode
        try:
            self._state.operation_mode = OperationMode.NORMAL
            return await self.process(text=text)
        finally:
            self._state.operation_mode = original_mode
    
    async def process_deep(self, text: str, context: dict | None = None) -> dict[str, Any]:
        """Deep processing (all layers)."""
        original_mode = self._state.operation_mode
        try:
            self._state.operation_mode = OperationMode.EXTREME
            return await self.process(text=text, context=context)
        finally:
            self._state.operation_mode = original_mode
    
    def get_stats(self) -> dict[str, Any]:
        """Get orchestrator statistics."""
        avg_time = self._total_processing_time / self._total_requests if self._total_requests > 0 else 0
        return {
            "initialized": self._initialized,
            "processing": self._processing,
            "current_mode": self._state.operation_mode.value,
            "total_requests": self._total_requests,
            "avg_processing_time_ms": avg_time,
            "layer_stats": {
                layer_type.name: layer.stats
                for layer_type, layer in self._layers.items()
            },
        }


@lru_cache()
def get_orchestrator() -> CortexOrchestrator:
    return CortexOrchestrator.get_instance()


__all__ = ["CortexOrchestrator", "get_orchestrator"]
