"""
NEUTRON Speech-to-Text

Vosk-based streaming STT with pluggable architecture.
"""

from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import AsyncIterator

import numpy as np

from config.settings import get_settings
from config.constants import AUDIO_SAMPLE_RATE
from utils.logging_config import get_logger


class STTEngineBase(ABC):
    """Abstract base for STT engines."""
    
    def __init__(self) -> None:
        self._logger = get_logger(self.__class__.__name__)
        self._initialized = False
    
    @abstractmethod
    async def initialize(self) -> None: ...
    
    @abstractmethod
    async def shutdown(self) -> None: ...
    
    @abstractmethod
    async def process(self, audio_data: np.ndarray) -> str:
        """Process streaming audio chunk and return text if complete."""
        ...
        
    @abstractmethod
    async def finish(self) -> str:
        """Force finish processing and return any pending text."""
        ...

class VoskSTT(STTEngineBase):
    """Vosk-based speech-to-text engine."""
    
    def __init__(self, model_path: Path | None = None) -> None:
        super().__init__()
        settings = get_settings()
        self._model_path = model_path or settings.voice.vosk_model_path
        self._model = None
        self._recognizer = None
    
    async def initialize(self) -> None:
        try:
            from vosk import Model, KaldiRecognizer
            
            model_path_str = str(self._model_path)
            
            # Check if model exists
            if not self._model_path.exists():
                self._logger.warning(f"Vosk model not found at {model_path_str}")
                self._initialized = False
                return
            
            self._model = Model(model_path_str)
            self._recognizer = KaldiRecognizer(self._model, AUDIO_SAMPLE_RATE)
            self._initialized = True
            self._logger.info("Vosk STT initialized")
        except ImportError:
            self._logger.warning("Vosk not installed")
            self._initialized = False
        except Exception as e:
            self._logger.error(f"Vosk init error: {e}")
            self._initialized = False
    
    async def shutdown(self) -> None:
        self._model = None
        self._recognizer = None
        self._initialized = False
    
    async def process(self, audio_data: np.ndarray) -> str:
        """Process audio chunk."""
        if not self._initialized or self._recognizer is None:
            return ""
        
        try:
            audio_bytes = audio_data.tobytes()
            if self._recognizer.AcceptWaveform(audio_bytes):
                result = json.loads(self._recognizer.Result())
                return result.get("text", "")
        except Exception as e:
            self._logger.error(f"Vosk process error: {e}")
        
        return ""
        
    async def finish(self) -> str:
        """Force finish processing."""
        if not self._initialized or self._recognizer is None:
            return ""
            
        try:
            # FinalResult returns the last text and resets the recognizer
            result = json.loads(self._recognizer.FinalResult())
            return result.get("text", "")
        except Exception as e:
            self._logger.error(f"Vosk finish error: {e}")
            return ""

    async def transcribe(self, audio_data: np.ndarray) -> str:
        """Transcribe entire buffer (oneshot)."""
        if not self._initialized or self._recognizer is None:
            return ""
        
        try:
            # Create a fresh recognizer for oneshot to not mess up streaming state
            from vosk import KaldiRecognizer
            rec = KaldiRecognizer(self._model, AUDIO_SAMPLE_RATE)
            
            audio_bytes = audio_data.tobytes()
            rec.AcceptWaveform(audio_bytes)
            result = json.loads(rec.FinalResult())
            return result.get("text", "")
        except Exception as e:
            self._logger.error(f"Transcription error: {e}")
            return ""

class MockSTT(STTEngineBase):
    """Mock STT for testing without audio."""
    
    async def initialize(self) -> None:
        self._initialized = True
    
    async def shutdown(self) -> None:
        self._initialized = False
        
    async def process(self, audio_data: np.ndarray) -> str:
        return ""
        
    async def finish(self) -> str:
        return ""
    
    async def transcribe(self, audio_data: np.ndarray) -> str:
        return ""
    
    async def stream_transcribe(self, audio_stream: AsyncIterator[np.ndarray]) -> AsyncIterator[tuple[str, bool]]:
        async for _ in audio_stream:
            pass
        yield "", True


def create_stt_engine() -> STTEngineBase:
    """Factory to create STT engine."""
    settings = get_settings()
    
    try:
        return VoskSTT(model_path=settings.voice.vosk_model_path)
    except Exception:
        return MockSTT()


__all__ = ["STTEngineBase", "VoskSTT", "MockSTT", "create_stt_engine"]
