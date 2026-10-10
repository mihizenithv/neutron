"""
NEUTRON Model Orchestrator

Routes tasks to the best available AI model based on task type.
Simple, fast, no over-engineering.
"""

from __future__ import annotations

import httpx
from dataclasses import dataclass
from enum import Enum, auto
from functools import lru_cache
from typing import Optional

from utils.logging_config import get_logger

_logger = get_logger("ModelOrchestrator")


class TaskType(Enum):
    VISION = auto()       # Image analysis
    FAST = auto()         # Quick chat, greetings
    REASONING = auto()    # Deep analysis, explanations
    RESEARCH = auto()     # Real-time info, news
    CREATIVE = auto()     # Writing, ideas


@dataclass
class RoutingDecision:
    primary_model: str    # e.g. "tinyllama", "deepseek", "gemini"
    provider: str         # e.g. "ollama", "gemini", "perplexity"
    reasoning: str


# Simple keyword-based task classification
_RESEARCH_KEYWORDS = {"news", "today", "current", "latest", "weather", "who is", "what is", "when did"}
_CREATIVE_KEYWORDS = {"write", "create", "imagine", "story", "poem", "design", "suggest"}
_REASONING_KEYWORDS = {"why", "explain", "how does", "analyze", "compare", "should i", "what if"}

# Model → provider mapping
_MODEL_PROVIDERS = {
    "llava": "ollama",
    "tinyllama": "ollama",
    "deepseek": "ollama",
    "gemini": "gemini",
    "perplexity": "perplexity",
}

# Which Ollama models are available (populated at init)
_available_ollama: list[str] = []
_initialized = False


async def initialize() -> None:
    """Check which Ollama models are available."""
    global _available_ollama, _initialized
    if _initialized:
        return
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get("http://localhost:11434/api/tags")
            if r.status_code == 200:
                _available_ollama = [m.get("name", "") for m in r.json().get("models", [])]
                _logger.info(f"Model orchestrator ready. Available: {_available_ollama}")
    except Exception as e:
        _logger.warning(f"Ollama not reachable: {e}")
    _initialized = True


def _has_model(name: str) -> bool:
    return any(name in m.lower() for m in _available_ollama)


def classify_task(query: str, context: Optional[dict] = None) -> TaskType:
    """Classify what kind of task this query requires."""
    q = query.lower()
    if any(kw in q for kw in _RESEARCH_KEYWORDS):
        return TaskType.RESEARCH
    if any(kw in q for kw in _CREATIVE_KEYWORDS):
        return TaskType.CREATIVE
    if any(kw in q for kw in _REASONING_KEYWORDS):
        return TaskType.REASONING
    if len(query.split()) < 6:
        return TaskType.FAST
    return TaskType.REASONING


def route(task_type: TaskType) -> RoutingDecision:
    """Pick the best model for a task type."""
    if task_type == TaskType.RESEARCH:
        return RoutingDecision("perplexity", "perplexity", "Need real-time information, using Perplexity")

    if task_type == TaskType.CREATIVE:
        return RoutingDecision("gemini", "gemini", "Creative task, using Gemini")

    if task_type == TaskType.FAST:
        if _has_model("tinyllama"):
            return RoutingDecision("tinyllama", "ollama", "Using tinyllama for FAST_RESPONSE")
        return RoutingDecision("gemini", "gemini", "Fast response via Gemini")

    if task_type == TaskType.REASONING:
        if _has_model("deepseek"):
            return RoutingDecision("deepseek", "ollama", "Deep reasoning with DeepSeek")
        return RoutingDecision("gemini", "gemini", "Reasoning via Gemini")

    # Vision
    return RoutingDecision("llava", "ollama", "Vision task, using LLaVA")


class ModelOrchestrator:
    """Thin wrapper for backwards compatibility with ai/router.py."""

    _instance: Optional["ModelOrchestrator"] = None
    _initialized = False

    @classmethod
    def get_instance(cls) -> "ModelOrchestrator":
        if cls._instance is None:
            cls._instance = ModelOrchestrator()
        return cls._instance

    async def initialize(self) -> None:
        await initialize()
        self._initialized = True

    def classify_task(self, query: str, context: Optional[dict] = None) -> TaskType:
        return classify_task(query, context)

    def route(self, task_type: TaskType) -> RoutingDecision:
        return route(task_type)


@lru_cache()
def get_model_orchestrator() -> ModelOrchestrator:
    return ModelOrchestrator.get_instance()


__all__ = [
    "ModelOrchestrator",
    "get_model_orchestrator",
    "TaskType",
    "RoutingDecision",
    "classify_task",
    "route",
    "initialize",
]
