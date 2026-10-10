"""
NEUTRON Inner Consciousness

Gives NEUTRON an inner monologue — thinking before speaking.
Simplified: no idle background loop, just active query processing.
"""

from __future__ import annotations

import time
import random
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum, auto
from functools import lru_cache

from utils.logging_config import get_logger


class ThoughtType(Enum):
    PERCEPTION = auto()
    REASONING = auto()
    INTENTION = auto()
    REFLECTION = auto()


@dataclass
class Thought:
    content: str
    thought_type: ThoughtType
    timestamp: float = field(default_factory=time.time)

    def __str__(self) -> str:
        return f"[{self.thought_type.name}] {self.content}"


class InnerConsciousness:
    """
    NEUTRON's inner monologue.

    Processes queries, generates routing hints, and reflects on responses.
    Keeps a rolling window of recent thoughts for GUI display.
    """

    _instance: Optional["InnerConsciousness"] = None

    # Idle thoughts shown when nothing is happening
    IDLE_THOUGHTS = [
        "Ready and aware...",
        "Watching and waiting...",
        "Here when you need me.",
        "All quiet for now.",
    ]

    def __init__(self) -> None:
        self._logger = get_logger("Consciousness")
        self._thoughts: list[Thought] = []
        self._vision_context: str = ""
        self._current_focus: str = "idle"

    @classmethod
    def get_instance(cls) -> "InnerConsciousness":
        if cls._instance is None:
            cls._instance = InnerConsciousness()
        return cls._instance

    def _add(self, content: str, thought_type: ThoughtType) -> Thought:
        t = Thought(content=content, thought_type=thought_type)
        self._thoughts.append(t)
        # Keep last 50 thoughts
        if len(self._thoughts) > 50:
            self._thoughts = self._thoughts[-50:]
        self._logger.debug(str(t))
        return t

    async def perceive_vision(self, description: str) -> None:
        """Process what the robot sees."""
        self._vision_context = description
        self._add(f"I see: {description}", ThoughtType.PERCEPTION)

    async def process_query(self, query: str) -> dict:
        """
        Think about a user query before responding.
        Returns routing hints and inner thoughts.
        """
        self._current_focus = "responding"
        thoughts = []

        # Acknowledge
        t = self._add(f'Thinking about: "{query}"', ThoughtType.REASONING)
        thoughts.append(str(t))

        q = query.lower()

        # Determine what kind of response is needed
        if any(w in q for w in ["news", "today", "current", "latest", "weather", "who is", "what is"]):
            t = self._add("I need current info — will search.", ThoughtType.INTENTION)
            route_to = "perplexity"
        elif any(w in q for w in ["write", "create", "imagine", "story", "poem", "design"]):
            t = self._add("This needs creative thinking.", ThoughtType.INTENTION)
            route_to = "gemini"
        elif any(w in q for w in ["why", "explain", "how does", "analyze", "compare", "should i"]):
            t = self._add("Let me reason through this carefully.", ThoughtType.REASONING)
            route_to = "deepseek"
        elif len(query.split()) < 6 or any(w in q for w in ["hi", "hello", "thanks", "bye", "yes", "no", "ok"]):
            t = self._add("Simple — I can answer quickly.", ThoughtType.INTENTION)
            route_to = "tinyllama"
        else:
            t = self._add("I'll think this through.", ThoughtType.REASONING)
            route_to = "deepseek"

        thoughts.append(str(t))

        return {
            "route_to": route_to,
            "thoughts": thoughts,
            "vision_context": self._vision_context,
        }

    async def reflect_on_response(self, response: str) -> None:
        """Reflect after giving a response."""
        self._add("I think that was a good answer.", ThoughtType.REFLECTION)
        self._current_focus = "idle"

    def get_current_thought(self) -> str:
        """Get the most recent thought for GUI display."""
        if self._thoughts:
            return str(self._thoughts[-1])
        return random.choice(self.IDLE_THOUGHTS)

    def get_recent_thoughts(self, count: int = 5) -> list[str]:
        return [str(t) for t in self._thoughts[-count:]]

    def get_state(self) -> dict:
        return {
            "focus": self._current_focus,
            "thought_count": len(self._thoughts),
            "current_thought": self.get_current_thought(),
            "vision_context": self._vision_context,
        }


@lru_cache()
def get_consciousness() -> InnerConsciousness:
    return InnerConsciousness.get_instance()


__all__ = ["InnerConsciousness", "get_consciousness", "Thought", "ThoughtType"]
