"""
NEUTRON Barge-In Controller

Stops TTS when user speech is detected.
"""

from __future__ import annotations

import asyncio
import time

from config.constants import BARGE_IN_DETECTION_MS
from utils.logging_config import get_logger
from utils.events import EventEmitter, get_event_bus
from config.constants import SystemEvent


class BargeInController(EventEmitter):
    """Controls barge-in (interrupt TTS when user speaks)."""
    
    def __init__(self, enabled: bool = True) -> None:
        self._logger = get_logger("BargeInController")
        self._enabled = enabled
        self._tts_active = False
        self._last_speech_time = 0.0
        self._barge_in_threshold_ms = BARGE_IN_DETECTION_MS
        self._callbacks: list[callable] = []
    
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value
    
    def set_tts_active(self, active: bool) -> None:
        """Set whether TTS is currently playing."""
        self._tts_active = active
    
    def on_barge_in(self, callback: callable) -> None:
        """Register callback for barge-in events."""
        self._callbacks.append(callback)
    
    async def check_barge_in(self, audio_energy: float, threshold: float = 0.1) -> bool:
        """
        Check if user is speaking during TTS (barge-in).
        
        Args:
            audio_energy: Current audio input energy level
            threshold: Energy threshold for speech detection
            
        Returns:
            True if barge-in detected
        """
        if not self._enabled or not self._tts_active:
            return False
        
        current_time = time.time() * 1000
        
        if audio_energy > threshold:
            # Speech detected during TTS
            if self._last_speech_time == 0:
                self._last_speech_time = current_time
            
            speech_duration = current_time - self._last_speech_time
            
            if speech_duration >= self._barge_in_threshold_ms:
                # Barge-in confirmed
                self._logger.info("Barge-in detected")
                await self._trigger_barge_in()
                return True
        else:
            self._last_speech_time = 0
        
        return False
    
    async def _trigger_barge_in(self) -> None:
        """Trigger barge-in event."""
        await self.emit(SystemEvent.BARGE_IN, {"timestamp": time.time()})
        
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                self._logger.error(f"Barge-in callback error: {e}")
        
        self._last_speech_time = 0


__all__ = ["BargeInController"]
