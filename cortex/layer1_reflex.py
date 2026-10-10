"""
NEUTRON Cortex Layer 1 - Reflex

Handles immediate, low-latency responses:
- Wake word detection
- Emergency stop
- Mute/privacy toggles
- Name call recognition
"""

from __future__ import annotations

import re
import time
from typing import Any

from config.constants import CortexLayer, SystemEvent, PRIVACY_ACKNOWLEDGMENT, FORGET_ACKNOWLEDGMENT
from cortex.base import FastPathLayer, LayerInput, LayerResult
from utils.state import PrivacyMode


class ReflexLayer(FastPathLayer):
    """
    Layer 1: Reflex responses for low-latency actions.
    
    Detects:
    - Wake word activation
    - Emergency stop commands
    - Privacy mode commands
    - Mute toggle commands
    """
    
    # Command patterns (compiled for performance)
    WAKE_PATTERNS = [
        re.compile(r"\b(hey\s+)?neutron\b", re.IGNORECASE),
        re.compile(r"\bneutron[,!.]?\s*$", re.IGNORECASE),
    ]
    
    STOP_PATTERNS = [
        re.compile(r"\b(stop|shut\s*up|be\s+quiet|silence)\b", re.IGNORECASE),
        re.compile(r"\b(emergency\s+)?stop\b", re.IGNORECASE),
    ]
    
    MUTE_PATTERNS = [
        re.compile(r"\b(mute|unmute)\b", re.IGNORECASE),
        re.compile(r"\bgo\s+(to\s+)?sleep\b", re.IGNORECASE),
        re.compile(r"\bwake\s+up\b", re.IGNORECASE),
    ]
    
    PRIVACY_PATTERNS = [
        re.compile(r"\b(go\s+)?private(\s+mode)?\b", re.IGNORECASE),
        re.compile(r"\bprivacy\s+mode\s+(on|off)\b", re.IGNORECASE),
        re.compile(r"\bstop\s+(recording|listening)\b", re.IGNORECASE),
    ]
    
    FORGET_PATTERNS = [
        re.compile(r"\bforget\s+(that|this|it)\b", re.IGNORECASE),
        re.compile(r"\bdelete\s+(that|this|last)\b", re.IGNORECASE),
        re.compile(r"\bnever\s+mind\b", re.IGNORECASE),
    ]
    
    def __init__(self) -> None:
        super().__init__()
        self._is_muted = False
        self._last_wake_time = 0.0
        self._wake_refractory_ms = 2000
    
    @property
    def layer(self) -> CortexLayer:
        return CortexLayer.REFLEX
    
    @property
    def is_muted(self) -> bool:
        return self._is_muted
    
    async def process(self, input_data: LayerInput) -> LayerResult:
        text = input_data.text.strip().lower()
        if not text:
            return LayerResult(success=True, should_propagate=True)
        
        result_data: dict[str, Any] = {
            "wake_word_detected": False,
            "stop_commanded": False,
            "mute_toggled": False,
            "privacy_changed": False,
            "forget_requested": False,
            "response": None,
        }
        
        # Check for wake word
        current_time = time.time() * 1000
        if current_time - self._last_wake_time > self._wake_refractory_ms:
            for pattern in self.WAKE_PATTERNS:
                if pattern.search(text):
                    result_data["wake_word_detected"] = True
                    self._last_wake_time = current_time
                    self._state.update_voice(wake_word=True)
                    await self.emit(
                        SystemEvent.WAKE_WORD_DETECTED,
                        {"text": text, "timestamp": current_time}
                    )
                    break
        
        # Check for stop command
        for pattern in self.STOP_PATTERNS:
            if pattern.search(text):
                result_data["stop_commanded"] = True
                await self.emit(SystemEvent.TTS_END, {"reason": "stop_command"})
                return LayerResult(
                    success=True,
                    data=result_data,
                    should_propagate=False,
                    should_respond=False,
                )
        
        # Check for mute toggle
        for pattern in self.MUTE_PATTERNS:
            match = pattern.search(text)
            if match:
                matched_text = match.group().lower()
                if "unmute" in matched_text or "wake up" in matched_text:
                    self._is_muted = False
                    result_data["mute_toggled"] = True
                    result_data["response"] = "I'm back!"
                elif "mute" in matched_text or "sleep" in matched_text:
                    self._is_muted = True
                    result_data["mute_toggled"] = True
                    result_data["response"] = "Going quiet, say 'wake up' when you need me."
                
                if result_data["mute_toggled"]:
                    return LayerResult(
                        success=True,
                        data=result_data,
                        should_propagate=False,
                        should_respond=True,
                    )
        
        # Check for privacy mode
        for pattern in self.PRIVACY_PATTERNS:
            match = pattern.search(text)
            if match:
                matched_text = match.group().lower()
                if "off" in matched_text:
                    self._state.privacy_mode = PrivacyMode.NORMAL
                    await self.emit(SystemEvent.PRIVATE_MODE_OFF, {})
                    result_data["response"] = "Privacy mode off, back to normal."
                else:
                    self._state.privacy_mode = PrivacyMode.PRIVATE
                    await self.emit(SystemEvent.PRIVATE_MODE_ON, {})
                    import random
                    result_data["response"] = random.choice(PRIVACY_ACKNOWLEDGMENT)
                
                result_data["privacy_changed"] = True
                return LayerResult(
                    success=True,
                    data=result_data,
                    should_propagate=False,
                    should_respond=True,
                )
        
        # Check for forget command
        for pattern in self.FORGET_PATTERNS:
            if pattern.search(text):
                self._state.privacy_mode = PrivacyMode.FORGET_LAST
                await self.emit(SystemEvent.FORGET_COMMAND, {"text": text})
                import random
                result_data["forget_requested"] = True
                result_data["response"] = random.choice(FORGET_ACKNOWLEDGMENT)
                return LayerResult(
                    success=True,
                    data=result_data,
                    should_propagate=False,
                    should_respond=True,
                )
        
        # If muted, don't propagate
        if self._is_muted and not result_data["wake_word_detected"]:
            return LayerResult(success=True, should_propagate=False)
        
        return LayerResult(
            success=True,
            data=result_data,
            should_propagate=True,
        )


__all__ = ["ReflexLayer"]
