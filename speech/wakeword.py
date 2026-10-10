"""
NEUTRON Wake Word Detection

Pluggable wake word detection with openWakeWord/Porcupine support.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Callable

import numpy as np

from config.settings import get_settings, WakeWordEngine
from utils.logging_config import get_logger


class WakeWordDetectorBase(ABC):
    """Abstract base for wake word detectors."""
    
    def __init__(self) -> None:
        self._logger = get_logger(self.__class__.__name__)
        self._initialized = False
        self._callback: Callable[[str], None] | None = None
    
    @abstractmethod
    async def initialize(self) -> None: ...
    
    @abstractmethod
    async def shutdown(self) -> None: ...
    
    @abstractmethod
    async def process(self, audio_data: np.ndarray) -> str | None:
        """Process audio and return detected wake word or None."""
        ...
    
    def set_callback(self, callback: Callable[[str], None]) -> None:
        self._callback = callback


class OpenWakeWordDetector(WakeWordDetectorBase):
    """openWakeWord-based wake word detection."""
    
    def __init__(self, sensitivity: float = 0.5) -> None:
        super().__init__()
        self._sensitivity = sensitivity
        self._model = None
    
    async def initialize(self) -> None:
        try:
            # Import only when needed to save memory
            from openwakeword.model import Model
            self._model = Model(inference_framework="onnx")
            self._initialized = True
            self._logger.info("openWakeWord initialized")
        except ImportError:
            self._logger.warning("openWakeWord not installed")
            self._initialized = False
        except Exception as e:
            self._logger.error(f"openWakeWord init error: {e}")
            self._initialized = False
    
    async def shutdown(self) -> None:
        self._model = None
        self._initialized = False
    
    async def process(self, audio_data: np.ndarray) -> str | None:
        if not self._initialized or self._model is None:
            return None
        
        try:
            prediction = self._model.predict(audio_data)
            
            for wake_word, scores in prediction.items():
                if isinstance(scores, (list, np.ndarray)):
                    max_score = max(scores) if len(scores) > 0 else 0
                else:
                    max_score = scores
                
                if max_score > self._sensitivity:
                    if self._callback:
                        self._callback(wake_word)
                    return wake_word
        except Exception as e:
            self._logger.debug(f"Wake word detection error: {e}")
        
        return None


class SimpleWakeWordDetector(WakeWordDetectorBase):
    """Simple keyword-based fallback detector (for testing)."""
    
    def __init__(self, keywords: list[str] | None = None) -> None:
        super().__init__()
        self._keywords = keywords or ["neutron", "hey neutron"]
    
    async def initialize(self) -> None:
        self._initialized = True
        self._logger.info("Simple wake word detector initialized")
    
    async def shutdown(self) -> None:
        self._initialized = False
    
    async def process(self, audio_data: np.ndarray) -> str | None:
        # This is a placeholder - actual implementation would use STT
        return None
    
    def check_text(self, text: str) -> str | None:
        """Check text for wake words (used with STT output)."""
        text_lower = text.lower()
        for keyword in self._keywords:
            if keyword in text_lower:
                if self._callback:
                    self._callback(keyword)
                return keyword
        return None


class VoskWakeWordDetector(WakeWordDetectorBase):
    """Vosk-based wake word detection with constrained grammar."""
    
    def __init__(self, keywords: list[str] | None = None) -> None:
        super().__init__()
        settings = get_settings()
        self._keywords = keywords or list(settings.voice.wakeword_phrases)
        self._model_path = settings.voice.vosk_model_path
        self._recognizer = None
    
    async def initialize(self) -> None:
        try:
            from vosk import Model, KaldiRecognizer
            
            if not self._model_path.exists():
                self._logger.warning(f"Vosk model not found at {self._model_path}")
                self._initialized = False
                return
            
            model = Model(str(self._model_path))
            # Create grammar for keywords
            grammar = str(self._keywords).replace("'", '"')
            self._recognizer = KaldiRecognizer(model, 16000, grammar)
            self._initialized = True
            self._logger.info(f"Vosk wake word detector initialized with: {self._keywords}")
        except Exception as e:
            self._logger.error(f"Vosk wake word init error: {e}")
            self._initialized = False
            
    async def shutdown(self) -> None:
        self._recognizer = None
        self._initialized = False
        
    async def process(self, audio_data: np.ndarray) -> str | None:
        if not self._initialized or self._recognizer is None:
            return None
        
        try:
            audio_bytes = audio_data.tobytes()
            if self._recognizer.AcceptWaveform(audio_bytes):
                result = self._recognizer.Result()
                import json
                text = json.loads(result).get("text", "")
                
                for keyword in self._keywords:
                    if keyword in text:
                        if self._callback:
                            self._callback(keyword)
                        return keyword
        except Exception as e:
            self._logger.error(f"Vosk wake word error: {e}")
            
        return None

def create_wake_word_detector() -> WakeWordDetectorBase:
    """Factory to create appropriate wake word detector."""
    settings = get_settings()
    
    detector = None
    
    if settings.voice.wakeword_engine == WakeWordEngine.OPENWAKEWORD:
        try:
            import openwakeword
            detector = OpenWakeWordDetector(sensitivity=settings.voice.wakeword_sensitivity)
        except ImportError:
            get_logger("WakeWordFactory").warning("openWakeWord selected but not installed. Falling back.")
            detector = None
    
    # Check if openWakeWord failed to init or wasn't chosen, fallback to Vosk
    if detector is None:
        # Check if Vosk model exists, if so use Vosk
        if settings.voice.vosk_model_path.exists():
             detector = VoskWakeWordDetector()
        else:
             detector = SimpleWakeWordDetector(keywords=list(settings.voice.wakeword_phrases))

    return detector


__all__ = ["WakeWordDetectorBase", "OpenWakeWordDetector", "SimpleWakeWordDetector", "VoskWakeWordDetector", "create_wake_word_detector"]
