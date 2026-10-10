"""
NEUTRON Cortex Layer 5 - Motivation

Initiative engine with anti-annoyance controls:
- Curiosity, care, boredom drives
- Cooldowns and quiet hours
- Proactive engagement decisions
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from config.constants import (
    CortexLayer, SystemEvent,
    INITIATIVE_COOLDOWN_SECONDS, QUIET_HOURS_DEFAULT, BOREDOM_THRESHOLD_SECONDS,
)
from cortex.base import DeepPathLayer, LayerInput, LayerResult


class MotivationLayer(DeepPathLayer):
    """Layer 5: Motivation and initiative engine."""
    
    def __init__(self) -> None:
        super().__init__()
        self._last_initiative_time = 0.0
        self._idle_start_time = time.time()
        self._initiative_count = 0
        self._suppressed_count = 0
        
        # Drive states (0-1)
        self._curiosity = 0.3
        self._care = 0.5
        self._boredom = 0.0
        
        # Parse quiet hours
        self._quiet_start = 22  # 10 PM
        self._quiet_end = 7    # 7 AM
        self._parse_quiet_hours(QUIET_HOURS_DEFAULT)
    
    @property
    def layer(self) -> CortexLayer:
        return CortexLayer.MOTIVATION
    
    def _parse_quiet_hours(self, quiet_hours: str) -> None:
        """Parse quiet hours string (e.g., '22:00-07:00')."""
        try:
            parts = quiet_hours.split("-")
            if len(parts) == 2:
                self._quiet_start = int(parts[0].split(":")[0])
                self._quiet_end = int(parts[1].split(":")[0])
        except (ValueError, IndexError):
            pass
    
    def _is_quiet_hours(self) -> bool:
        """Check if current time is within quiet hours."""
        current_hour = datetime.now().hour
        if self._quiet_start > self._quiet_end:
            return current_hour >= self._quiet_start or current_hour < self._quiet_end
        return self._quiet_start <= current_hour < self._quiet_end
    
    async def process(self, input_data: LayerInput) -> LayerResult:
        text = input_data.text
        context = input_data.context
        current_time = time.time()
        
        result_data: dict[str, Any] = {
            "should_initiate": False,
            "initiative_type": None,
            "initiative_message": None,
            "drives": {
                "curiosity": self._curiosity,
                "care": self._care,
                "boredom": self._boredom,
            },
            "suppression_reason": None,
        }
        
        # Update drives based on input
        await self._update_drives(text, context, current_time)
        result_data["drives"] = {
            "curiosity": self._curiosity,
            "care": self._care,
            "boredom": self._boredom,
        }
        
        # Check for initiative opportunity (only if no user input)
        if not text:
            should_initiate, init_type, message, reason = self._evaluate_initiative(current_time)
            result_data["should_initiate"] = should_initiate
            result_data["initiative_type"] = init_type
            result_data["initiative_message"] = message
            
            if not should_initiate and reason:
                result_data["suppression_reason"] = reason
                self._suppressed_count += 1
            elif should_initiate:
                self._last_initiative_time = current_time
                self._initiative_count += 1
                await self.emit(
                    SystemEvent.INITIATIVE_TRIGGER,
                    {"type": init_type, "message": message},
                )
        else:
            # User input resets idle timer
            self._idle_start_time = current_time
            self._boredom = max(0, self._boredom - 0.2)
        
        return LayerResult(
            success=True,
            data=result_data,
            confidence=0.7,
            should_propagate=True,
            should_respond=result_data["should_initiate"],
        )
    
    async def _update_drives(self, text: str, context: dict, current_time: float) -> None:
        """Update drive states based on interaction."""
        idle_duration = current_time - self._idle_start_time
        
        # Boredom increases with idle time
        self._boredom = min(1.0, idle_duration / BOREDOM_THRESHOLD_SECONDS)
        
        if text:
            text_lower = text.lower()
            
            # Curiosity increases with questions or learning
            if "?" in text or any(w in text_lower for w in ["curious", "wonder", "think about"]):
                self._curiosity = min(1.0, self._curiosity + 0.1)
            else:
                self._curiosity = max(0.1, self._curiosity - 0.02)
            
            # Care increases with emotional content
            emotional = self._state.emotion
            if emotional.valence < 0.3:  # User seems negative
                self._care = min(1.0, self._care + 0.15)
            elif emotional.valence > 0.7:  # User seems positive
                self._care = max(0.3, self._care - 0.05)
    
    def _evaluate_initiative(self, current_time: float) -> tuple[bool, str | None, str | None, str | None]:
        """Evaluate whether to take initiative."""
        # Check cooldown
        time_since_last = current_time - self._last_initiative_time
        if time_since_last < INITIATIVE_COOLDOWN_SECONDS:
            remaining = INITIATIVE_COOLDOWN_SECONDS - time_since_last
            return False, None, None, f"cooldown ({remaining:.0f}s remaining)"
        
        # Check quiet hours
        if self._is_quiet_hours():
            return False, None, None, "quiet hours"
        
        # Check annoyance threshold
        emotion = self._state.emotion
        if emotion.fatigue > 0.7:
            return False, None, None, "user fatigue detected"
        
        # Evaluate drive thresholds
        if self._boredom > 0.8:
            return True, "boredom", "hey, it's been a while - everything good?", None
        
        if self._care > 0.8 and emotion.valence < 0.4:
            return True, "care", "you doing okay? i'm here if you need anything", None
        
        if self._curiosity > 0.7:
            return True, "curiosity", "random thought - what's something you've been curious about lately?", None
        
        return False, None, None, "no drive threshold met"


__all__ = ["MotivationLayer"]
