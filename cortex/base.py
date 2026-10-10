"""
NEUTRON Cortex Base Classes

Abstract base classes for cortex layers with common interfaces.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Generic, TypeVar

from config.constants import CortexLayer, SystemEvent
from utils.events import EventEmitter, get_event_bus
from utils.logging_config import get_logger
from utils.state import get_state


class LayerStatus(Enum):
    """Layer operational status."""
    INACTIVE = auto()
    INITIALIZING = auto()
    ACTIVE = auto()
    PROCESSING = auto()
    ERROR = auto()
    SHUTTING_DOWN = auto()


@dataclass
class LayerResult:
    """
    Result from a cortex layer processing step.
    
    Attributes:
        success: Whether processing succeeded
        data: Output data from layer
        confidence: Confidence in result (0-1)
        should_propagate: Whether to pass to next layer
        should_respond: Whether this result should trigger response
        metadata: Additional metadata
    """
    success: bool = True
    data: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    should_propagate: bool = True
    should_respond: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    processing_time_ms: float = 0.0
    layer: CortexLayer | None = None
    error: str | None = None
    
    @classmethod
    def error_result(cls, layer: CortexLayer, error: str) -> "LayerResult":
        return cls(
            success=False,
            layer=layer,
            error=error,
            should_propagate=False,
        )
    
    @classmethod
    def skip_result(cls, layer: CortexLayer) -> "LayerResult":
        return cls(success=True, layer=layer, should_propagate=True)


@dataclass
class LayerInput:
    """Input data for cortex layer processing."""
    text: str = ""
    audio_data: bytes | None = None
    previous_results: list[LayerResult] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: str = ""
    
    def get_result(self, layer: CortexLayer) -> LayerResult | None:
        for result in self.previous_results:
            if result.layer == layer:
                return result
        return None


class CortexLayerBase(ABC, EventEmitter):
    """
    Abstract base class for all cortex layers.
    
    Each layer must implement:
    - layer property: Which layer this is
    - process(): Main processing logic
    
    Optional overrides:
    - initialize(): Async initialization
    - shutdown(): Cleanup
    - is_available(): Check if layer can process
    """
    
    def __init__(self) -> None:
        self._status = LayerStatus.INACTIVE
        self._initialized = False
        self._processing_count = 0
        self._total_processing_time = 0.0
        self._error_count = 0
        self._logger = get_logger(self.__class__.__name__)
        self._state = get_state()
    
    @property
    @abstractmethod
    def layer(self) -> CortexLayer:
        """Return which cortex layer this is."""
        ...
    
    @property
    def status(self) -> LayerStatus:
        return self._status
    
    @property
    def is_active(self) -> bool:
        return self._status == LayerStatus.ACTIVE
    
    @property
    def stats(self) -> dict[str, Any]:
        avg_time = (
            self._total_processing_time / self._processing_count
            if self._processing_count > 0 else 0.0
        )
        return {
            "layer": self.layer.name,
            "status": self._status.name,
            "processing_count": self._processing_count,
            "avg_processing_time_ms": avg_time,
            "error_count": self._error_count,
        }
    
    async def initialize(self) -> None:
        """Initialize the layer. Override for custom initialization."""
        self._status = LayerStatus.INITIALIZING
        self._logger.info(f"Initializing {self.layer.name} layer")
        self._initialized = True
        self._status = LayerStatus.ACTIVE
        self._logger.info(f"{self.layer.name} layer active")
    
    async def shutdown(self) -> None:
        """Shutdown the layer. Override for cleanup."""
        self._status = LayerStatus.SHUTTING_DOWN
        self._logger.info(f"Shutting down {self.layer.name} layer")
        self._initialized = False
        self._status = LayerStatus.INACTIVE
    
    def is_available(self, input_data: LayerInput) -> bool:
        """Check if layer is available for processing. Override for conditions."""
        return self._initialized and self._status == LayerStatus.ACTIVE
    
    @abstractmethod
    async def process(self, input_data: LayerInput) -> LayerResult:
        """
        Process input through this layer.
        
        Args:
            input_data: Input data and context
            
        Returns:
            LayerResult with processing output
        """
        ...
    
    async def safe_process(self, input_data: LayerInput) -> LayerResult:
        """Process with error handling and timing."""
        if not self.is_available(input_data):
            return LayerResult.skip_result(self.layer)
        
        start_time = asyncio.get_event_loop().time()
        self._status = LayerStatus.PROCESSING
        
        try:
            result = await self.process(input_data)
            result.layer = self.layer
            result.processing_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            self._processing_count += 1
            self._total_processing_time += result.processing_time_ms
            return result
        except Exception as e:
            self._error_count += 1
            self._logger.error(f"Error in {self.layer.name}: {e}", exc_info=True)
            return LayerResult.error_result(self.layer, str(e))
        finally:
            self._status = LayerStatus.ACTIVE


class FastPathLayer(CortexLayerBase):
    """Base for fast-path layers (1-2) that run in normal mode."""
    
    @property
    def is_fast_path(self) -> bool:
        return True
    
    @property
    def max_processing_ms(self) -> float:
        return 100.0  # Fast path layers should complete quickly


class DeepPathLayer(CortexLayerBase):
    """Base for deep-path layers (3-7) that run in extreme mode."""
    
    @property
    def is_fast_path(self) -> bool:
        return False
    
    @property
    def max_processing_ms(self) -> float:
        return 2000.0  # Deep layers can take longer


__all__ = [
    "CortexLayerBase",
    "FastPathLayer",
    "DeepPathLayer",
    "LayerResult",
    "LayerInput",
    "LayerStatus",
]
