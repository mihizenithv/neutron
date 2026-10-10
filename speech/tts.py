"""
NEUTRON Text-to-Speech

Piper-based TTS with pluggable architecture.
"""

from __future__ import annotations

import asyncio
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import AsyncIterator

import numpy as np

from config.settings import get_settings
from config.constants import TTS_SAMPLE_RATE
from utils.logging_config import get_logger


class TTSEngineBase(ABC):
    """Abstract base for TTS engines."""
    
    def __init__(self) -> None:
        self._logger = get_logger(self.__class__.__name__)
        self._initialized = False
        self._speaking = False
    
    @property
    def is_speaking(self) -> bool:
        return self._speaking
    
    @abstractmethod
    async def initialize(self) -> None: ...
    
    @abstractmethod
    async def shutdown(self) -> None: ...
    
    @abstractmethod
    async def synthesize(self, text: str) -> np.ndarray:
        """Synthesize text to audio."""
        ...
    
    @abstractmethod
    async def stream_synthesize(self, text: str) -> AsyncIterator[np.ndarray]:
        """Stream synthesize text to audio chunks."""
        ...
    
    def stop(self) -> None:
        """Stop current synthesis."""
        self._speaking = False


class PiperTTS(TTSEngineBase):
    """Piper-based text-to-speech engine."""
    
    def __init__(self, voice: str | None = None, model_path: Path | None = None) -> None:
        super().__init__()
        settings = get_settings()
        self._voice = voice or settings.voice.piper_voice
        self._model_path = model_path or settings.voice.piper_model_path
        self._piper_path: Path | None = None
    
    async def initialize(self) -> None:
        try:
            # Check for piper executable
            result = await asyncio.create_subprocess_exec(
                "piper", "--help",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await result.wait()
            
            if result.returncode == 0:
                self._initialized = True
                self._logger.info("Piper TTS initialized")
            else:
                self._initialized = False
                self._logger.warning("Piper not available")
        except FileNotFoundError:
            self._logger.warning("Piper not installed")
            self._initialized = False
        except Exception as e:
            self._logger.error(f"Piper init error: {e}")
            self._initialized = False
    
    async def shutdown(self) -> None:
        self._initialized = False
    
    async def synthesize(self, text: str) -> np.ndarray:
        if not self._initialized:
            return np.array([], dtype=np.int16)
        
        self._speaking = True
        try:
            model_file = self._model_path / f"{self._voice}.onnx"
            
            process = await asyncio.create_subprocess_exec(
                "piper",
                "-m", str(model_file),
                "--output-raw",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, _ = await process.communicate(text.encode())
            
            audio = np.frombuffer(stdout, dtype=np.int16)
            return audio
        except Exception as e:
            self._logger.error(f"TTS synthesis error: {e}")
            return np.array([], dtype=np.int16)
        finally:
            self._speaking = False
    
    async def stream_synthesize(self, text: str) -> AsyncIterator[np.ndarray]:
        if not self._initialized:
            return
        
        self._speaking = True
        try:
            model_file = self._model_path / f"{self._voice}.onnx"
            
            process = await asyncio.create_subprocess_exec(
                "piper",
                "-m", str(model_file),
                "--output-raw",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            process.stdin.write(text.encode())  # type: ignore
            await process.stdin.drain()  # type: ignore
            process.stdin.close()  # type: ignore
            
            chunk_size = 4096
            while self._speaking:
                chunk = await process.stdout.read(chunk_size)  # type: ignore
                if not chunk:
                    break
                audio = np.frombuffer(chunk, dtype=np.int16)
                yield audio
            
            await process.wait()
        except Exception as e:
            self._logger.error(f"TTS stream error: {e}")
        finally:
            self._speaking = False


class MockTTS(TTSEngineBase):
    """Mock TTS for testing without audio output."""
    
    async def initialize(self) -> None:
        self._initialized = True
    
    async def shutdown(self) -> None:
        self._initialized = False
    
    async def synthesize(self, text: str) -> np.ndarray:
        # Generate silence
        duration_samples = int(TTS_SAMPLE_RATE * len(text) * 0.05)
        return np.zeros(duration_samples, dtype=np.int16)
    
    async def stream_synthesize(self, text: str) -> AsyncIterator[np.ndarray]:
        audio = await self.synthesize(text)
        chunk_size = 4096
        for i in range(0, len(audio), chunk_size):
            yield audio[i:i + chunk_size]


class SystemTTS(TTSEngineBase):
    """System default TTS using pyttsx3."""
    
    def __init__(self) -> None:
        super().__init__()
        self._engine = None
    
    async def initialize(self) -> None:
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._initialized = True
            self._logger.info("System TTS (pyttsx3) initialized")
        except Exception as e:
            self._logger.error(f"System TTS init error: {e}")
            self._initialized = False
            
    async def shutdown(self) -> None:
        if self._engine:
            self._engine.stop()
        self._initialized = False
        
    async def synthesize(self, text: str) -> np.ndarray:
        if not self._initialized or not self._engine:
            return np.array([], dtype=np.int16)
            
        self._speaking = True
        try:
            # Note: pyttsx3 is blocking, running in executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._speak_blocking, text)
            # pyttsx3 plays directly, we return empty array as signal
            return np.array([], dtype=np.int16) 
        except Exception as e:
            self._logger.error(f"System TTS error: {e}")
            return np.array([], dtype=np.int16)
        finally:
            self._speaking = False
            
    def _speak_blocking(self, text: str):
        """Blocking speak call."""
        if self._engine:
            self._engine.say(text)
            self._engine.runAndWait()

    async def stream_synthesize(self, text: str) -> AsyncIterator[np.ndarray]:
        # System TTS doesn't support streaming audio bytes easily, just play it
        await self.synthesize(text)
        yield np.array([], dtype=np.int16)


def create_tts_engine() -> TTSEngineBase:
    """Factory to create TTS engine."""
    # Try Piper first
    try:
        piper = PiperTTS()
        # We need to await initialize to know if it really works, but factory is sync.
        # So we return PiperTTS and let it fail to initialize if bin is missing,
        # checking availability in a slightly hacky way or just relying on fallback logic elsewhere?
        # Actually, let's try to instantiate SystemTTS as backup if Piper fails at runtime?
        # For now, let's return SystemTTS if we know Piper bin is likely missing,
        # but checking bin existence synchronously is better.
        import shutil
        if shutil.which("piper"):
             return piper
    except Exception:
        pass
        
    # Fallback to SystemTTS
    try:
        return SystemTTS()
    except Exception:
        return MockTTS()


__all__ = ["TTSEngineBase", "PiperTTS", "MockTTS", "create_tts_engine"]
