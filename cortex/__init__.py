"""
NEUTRON Cortex Module

7-layer cognitive architecture for emotional, social, and executive processing.
"""

from cortex.base import CortexLayerBase, LayerResult
from cortex.orchestrator import CortexOrchestrator, get_orchestrator

__all__ = [
    "CortexLayerBase",
    "LayerResult",
    "CortexOrchestrator",
    "get_orchestrator",
]
