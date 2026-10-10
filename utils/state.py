"""
NEUTRON Global State Management

Thread-safe global state for emotion vectors, mode flags,
system status, and runtime information.
"""

from __future__ import annotations

import asyncio
import copy
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from functools import lru_cache
from threading import RLock
from typing import Any, Callable

from config.constants import (
    EmotionVector,
    NEUTRAL_EMOTION,
    GUIState,
    CortexLayer,
    EMOTION_DECAY_RATE,
    EMOTION_DECAY_MIN_DELTA,
)
from config.settings import get_settings, OperationMode


class PrivacyMode(Enum):
    """Privacy mode states."""
    NORMAL = auto()
    PRIVATE = auto()
    FORGET_LAST = auto()


@dataclass
class ConversationContext:
    """Current conversation context."""
    turn_count: int = 0
    last_user_input: str = ""
    last_response: str = ""
    topic: str = ""
    start_time: datetime | None = None
    participants_detected: int = 1
    is_active: bool = False


@dataclass
class VoiceState:
    """Voice pipeline state."""
    is_listening: bool = False
    is_speaking: bool = False
    is_processing: bool = False
    current_transcript: str = ""
    audio_level: float = 0.0
    wake_word_detected: bool = False
    last_speech_time: float = 0.0


@dataclass
class SystemHealth:
    """System health metrics."""
    cpu_usage: float = 0.0
    memory_usage_mb: float = 0.0
    disk_usage_percent: float = 0.0
    network_connected: bool = True
    api_status: dict[str, bool] = field(default_factory=dict)
    last_check: datetime | None = None
    uptime_seconds: float = 0.0


class GlobalState:
    """Thread-safe global state container for NEUTRON."""
    
    _instance: "GlobalState | None" = None
    _lock: RLock = RLock()
    
    def __init__(self) -> None:
        self._state_lock = RLock()
        self._start_time = time.time()
        self._operation_mode = get_settings().mode
        self._privacy_mode = PrivacyMode.NORMAL
        self._gui_state = GUIState.BOOTING
        self._emotion = NEUTRAL_EMOTION
        self._emotion_last_update = time.time()
        self._conversation = ConversationContext()
        self._voice = VoiceState()
        self._health = SystemHealth()
        self._active_layers: set[CortexLayer] = set()
        self._update_active_layers()
        self._callbacks: dict[str, list[Callable]] = {}
        self._gaze_target: tuple[float, float] = (0.5, 0.5)
        self._attention_level: float = 0.5
    
    @classmethod
    def get_instance(cls) -> "GlobalState":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = GlobalState()
        return cls._instance
    
    def _update_active_layers(self) -> None:
        if self._operation_mode == OperationMode.NORMAL:
            self._active_layers = {CortexLayer.REFLEX, CortexLayer.SENSORY}
        else:
            self._active_layers = set(CortexLayer)
    
    @property
    def operation_mode(self) -> OperationMode:
        with self._state_lock:
            return self._operation_mode
    
    @operation_mode.setter
    def operation_mode(self, mode: OperationMode) -> None:
        with self._state_lock:
            self._operation_mode = mode
            self._update_active_layers()
    
    @property
    def is_extreme_mode(self) -> bool:
        return self.operation_mode == OperationMode.EXTREME
    
    @property
    def active_layers(self) -> set[CortexLayer]:
        with self._state_lock:
            return self._active_layers.copy()
    
    def is_layer_active(self, layer: CortexLayer) -> bool:
        with self._state_lock:
            return layer in self._active_layers
    
    @property
    def privacy_mode(self) -> PrivacyMode:
        with self._state_lock:
            return self._privacy_mode
    
    @privacy_mode.setter
    def privacy_mode(self, mode: PrivacyMode) -> None:
        with self._state_lock:
            self._privacy_mode = mode
    
    @property
    def is_private(self) -> bool:
        return self.privacy_mode == PrivacyMode.PRIVATE
    
    @property
    def gui_state(self) -> GUIState:
        with self._state_lock:
            return self._gui_state
    
    @gui_state.setter
    def gui_state(self, state: GUIState) -> None:
        with self._state_lock:
            self._gui_state = state
    
    @property
    def emotion(self) -> EmotionVector:
        with self._state_lock:
            return self._emotion
    
    @emotion.setter
    def emotion(self, emotion: EmotionVector) -> None:
        with self._state_lock:
            self._emotion = emotion
            self._emotion_last_update = time.time()
    
    def update_emotion(self, **kwargs) -> EmotionVector:
        with self._state_lock:
            new_emotion = EmotionVector(
                valence=kwargs.get("valence", self._emotion.valence),
                arousal=kwargs.get("arousal", self._emotion.arousal),
                trust=kwargs.get("trust", self._emotion.trust),
                fatigue=kwargs.get("fatigue", self._emotion.fatigue),
                confidence=kwargs.get("confidence", self._emotion.confidence),
            )
            self.emotion = new_emotion
            return new_emotion
    
    def decay_emotion(self, dt: float | None = None) -> EmotionVector:
        with self._state_lock:
            if dt is None:
                dt = time.time() - self._emotion_last_update
            decay = max(0.0, min(1.0, 1.0 - (EMOTION_DECAY_RATE * dt)))
            
            def decay_toward(current: float, neutral: float) -> float:
                diff = current - neutral
                if abs(diff) < EMOTION_DECAY_MIN_DELTA:
                    return neutral
                return neutral + diff * decay
            
            new_emotion = EmotionVector(
                valence=decay_toward(self._emotion.valence, NEUTRAL_EMOTION.valence),
                arousal=decay_toward(self._emotion.arousal, NEUTRAL_EMOTION.arousal),
                trust=decay_toward(self._emotion.trust, NEUTRAL_EMOTION.trust),
                fatigue=decay_toward(self._emotion.fatigue, NEUTRAL_EMOTION.fatigue),
                confidence=decay_toward(self._emotion.confidence, NEUTRAL_EMOTION.confidence),
            )
            self.emotion = new_emotion
            return new_emotion
    
    @property
    def conversation(self) -> ConversationContext:
        with self._state_lock:
            return copy.copy(self._conversation)
    
    def update_conversation(self, **kwargs) -> None:
        with self._state_lock:
            if "user_input" in kwargs:
                self._conversation.last_user_input = kwargs["user_input"]
                self._conversation.turn_count += 1
            if "response" in kwargs:
                self._conversation.last_response = kwargs["response"]
            if "topic" in kwargs:
                self._conversation.topic = kwargs["topic"]
            if "participants" in kwargs:
                self._conversation.participants_detected = kwargs["participants"]
            if not self._conversation.is_active and kwargs.get("user_input"):
                self._conversation.is_active = True
                self._conversation.start_time = datetime.now(timezone.utc)
    
    def end_conversation(self) -> None:
        with self._state_lock:
            self._conversation = ConversationContext()
    
    @property
    def voice(self) -> VoiceState:
        with self._state_lock:
            return copy.copy(self._voice)
    
    def update_voice(self, **kwargs) -> None:
        with self._state_lock:
            for key, val in kwargs.items():
                if hasattr(self._voice, key) or key == "listening":
                    if key == "listening":
                        self._voice.is_listening = val
                    elif key == "speaking":
                        self._voice.is_speaking = val
                    elif key == "processing":
                        self._voice.is_processing = val
                    elif key == "transcript":
                        self._voice.current_transcript = val
                    elif key == "audio_level":
                        self._voice.audio_level = val
                    elif key == "wake_word":
                        self._voice.wake_word_detected = val
                        if val:
                            self._voice.last_speech_time = time.time()
    
    @property
    def health(self) -> SystemHealth:
        with self._state_lock:
            health = copy.copy(self._health)
            health.uptime_seconds = time.time() - self._start_time
            return health
    
    def update_health(self, **kwargs) -> None:
        with self._state_lock:
            if "cpu" in kwargs:
                self._health.cpu_usage = kwargs["cpu"]
            if "memory" in kwargs:
                self._health.memory_usage_mb = kwargs["memory"]
            if "disk" in kwargs:
                self._health.disk_usage_percent = kwargs["disk"]
            if "network" in kwargs:
                self._health.network_connected = kwargs["network"]
            if "api_status" in kwargs:
                self._health.api_status.update(kwargs["api_status"])
            self._health.last_check = datetime.now(timezone.utc)
    
    @property
    def gaze_target(self) -> tuple[float, float]:
        with self._state_lock:
            return self._gaze_target
    
    @gaze_target.setter
    def gaze_target(self, target: tuple[float, float]) -> None:
        with self._state_lock:
            self._gaze_target = (max(0.0, min(1.0, target[0])), max(0.0, min(1.0, target[1])))
    
    @property
    def attention_level(self) -> float:
        with self._state_lock:
            return self._attention_level
    
    @attention_level.setter
    def attention_level(self, level: float) -> None:
        with self._state_lock:
            self._attention_level = max(0.0, min(1.0, level))
    
    def to_gui_state(self) -> dict[str, Any]:
        with self._state_lock:
            voice = self._voice
            emotion = self._emotion
            if voice.is_speaking:
                mode = "speaking"
            elif voice.is_processing:
                mode = "thinking"
            elif voice.is_listening:
                mode = "listening"
            elif self._gui_state == GUIState.BOOTING:
                mode = "booting"
            else:
                mode = "idle"
            return {
                "mode": mode, "speaking": voice.is_speaking,
                "valence": emotion.valence, "arousal": emotion.arousal,
                "trust": emotion.trust, "fatigue": emotion.fatigue,
                "confidence": emotion.confidence, "attention_level": self._attention_level,
                "gaze_target": {"x": self._gaze_target[0], "y": self._gaze_target[1]},
                "audio_level": voice.audio_level, "transcript": voice.current_transcript,
            }
    
    def to_dict(self) -> dict[str, Any]:
        with self._state_lock:
            return {
                "operation_mode": self._operation_mode.value,
                "privacy_mode": self._privacy_mode.name,
                "gui_state": self._gui_state.name,
                "emotion": self._emotion.to_dict(),
                "active_layers": [l.name for l in self._active_layers],
                "uptime_seconds": time.time() - self._start_time,
            }


@lru_cache()
def get_state() -> GlobalState:
    return GlobalState.get_instance()


__all__ = ["GlobalState", "get_state", "PrivacyMode", "ConversationContext", "VoiceState", "SystemHealth"]
