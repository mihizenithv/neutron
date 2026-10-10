"""
NEUTRON Voice Pipeline

Orchestrates wake word → STT → process → TTS flow.
"""

from __future__ import annotations

import asyncio
import time
from functools import lru_cache
from typing import Callable, Awaitable

import numpy as np

from config.settings import get_settings
from config.constants import (
    SystemEvent, GUIState, AUDIO_SAMPLE_RATE, AUDIO_BLOCK_SIZE,
    STT_SILENCE_TIMEOUT_MS
)
from speech.wakeword import WakeWordDetectorBase, create_wake_word_detector
from speech.stt import STTEngineBase, create_stt_engine
from speech.tts import TTSEngineBase, create_tts_engine
from speech.bargein import BargeInController
from utils.logging_config import get_logger
from utils.events import EventEmitter
from utils.state import get_state


import queue

try:  # audio hardware libs are optional so the API server can boot headless
    import sounddevice as sd
except (ImportError, OSError):  # PortAudio missing
    sd = None

class MicrophoneStream:
    """Microphone audio stream wrapper."""
    
    def __init__(self, rate: int, block_size: int, device: int | None = None):
        self.rate = rate
        self.block_size = block_size
        self.device = device
        self._buff = queue.Queue()
        self._stream = None
        self._closed = True
    
    def __enter__(self):
        if sd is None:
            raise RuntimeError("sounddevice/PortAudio is not available; microphone input is disabled")
        self._closed = False
        self._stream = sd.InputStream(
            samplerate=self.rate,
            blocksize=self.block_size,
            device=self.device,
            channels=1,
            dtype="int16",
            callback=self._callback
        )
        self._stream.start()
        return self
    
    def __exit__(self, type, value, traceback):
        if self._stream:
            self._stream.stop()
            self._stream.close()
        self._closed = True
    
    def _callback(self, indata, frames, time, status):
        """Audio callback."""
        if status:
            print(status)
        self._buff.put(indata.copy())
    
    def read(self) -> np.ndarray | None:
        """Read a block of audio data."""
        try:
            return self._buff.get(block=False)
        except queue.Empty:
            return None


class VoicePipeline(EventEmitter):
    """Orchestrates the complete voice interaction pipeline."""
    
    _instance: "VoicePipeline | None" = None
    
    def __init__(self) -> None:
        super().__init__()
        self._logger = get_logger("VoicePipeline")
        self._settings = get_settings()
        self._state = get_state()
        
        # Components
        self._wake_word = create_wake_word_detector()
        self._stt = create_stt_engine()
        self._tts = create_tts_engine()
        self._barge_in = BargeInController(enabled=self._settings.voice.barge_in_enabled)
        
        # State
        self._initialized = False
        self._running = False
        self._listening = False
        self._speaking = False
        
        # Callbacks
        self._on_transcription: Callable[[str], Awaitable[str]] | None = None
        
        # Audio stream
        self._mic_stream: MicrophoneStream | None = None
        self._last_input_time = 0.0
    
    @classmethod
    def get_instance(cls) -> "VoicePipeline":
        if cls._instance is None:
            cls._instance = VoicePipeline()
        return cls._instance
    
    async def initialize(self) -> None:
        """Initialize all pipeline components."""
        if self._initialized:
            return
        
        self._logger.info("Initializing voice pipeline")
        
        await self._wake_word.initialize()
        await self._stt.initialize()
        await self._tts.initialize()
        
        self._barge_in.on_barge_in(self._on_barge_in)
        
        self._initialized = True
        self._logger.info("Voice pipeline initialized")
    
    async def shutdown(self) -> None:
        """Shutdown pipeline."""
        self._logger.info("Shutting down voice pipeline")
        self._running = False
        
        await self._wake_word.shutdown()
        await self._stt.shutdown()
        await self._tts.shutdown()
        
        self._initialized = False
    
    def set_transcription_handler(self, handler: Callable[[str], Awaitable[str]]) -> None:
        """Set handler for processing transcriptions."""
        self._on_transcription = handler
    
    async def start(self) -> None:
        """Start the voice pipeline."""
        if not self._initialized:
            await self.initialize()
        
        self._running = True
        self._logger.info("Voice pipeline started")
        
        # Start listening loop
        asyncio.create_task(self._listen_loop())
    
    async def stop(self) -> None:
        """Stop the voice pipeline."""
        self._running = False
        self._listening = False
    
    async def _listen_loop(self) -> None:
        """Main listening loop."""
        device_id = self._settings.voice.audio_input_device
        self._logger.info(f"Starting microphone stream (Device ID: {device_id})...")
        
        try:
            with MicrophoneStream(AUDIO_SAMPLE_RATE, AUDIO_BLOCK_SIZE, device_id) as stream:
                while self._running:
                    # Read audio block
                    data = stream.read()
                    if data is None:
                        await asyncio.sleep(0.01)
                        continue
                        
                    # Process audio
                    await self.process_audio(data.flatten())
                    await asyncio.sleep(0.001)  # Yield
                    
        except Exception as e:
            self._logger.error(f"Microphone error: {e}")
            self._state.update_voice(error=str(e))
    
    async def process_audio(self, audio_data: np.ndarray) -> None:
        """Process incoming audio data."""
        if not self._running:
            return
        
        # SOFTWARE GAIN BOOST (Fix for low volume mics)
        # Multiply signal by 5.0 to boost levels
        audio_data = audio_data * 5.0
        
        # Calculate energy for barge-in detection
        energy = np.sqrt(np.mean(audio_data.astype(float) ** 2)) / 32768.0
        self._state.update_voice(audio_level=energy)
        
        # Get current time for timing calculations
        current_time = time.time() * 1000
        
        # Debug logging for audio levels (throttled)
        if not hasattr(self, "_frames_processed"):
            self._frames_processed = 0
        self._frames_processed += 1
        if self._frames_processed % 50 == 0:
             # Only log if there's significant energy to avoid spamming silence
             if energy > 0.005:
                 self._logger.info(f"Audio Input Level: {energy:.4f}")
        
        # Update last input time if speech energy detected
        if energy > 0.002:  # Lowered VAD threshold (was 0.01)
            self._last_input_time = current_time
        # Emit audio level for GUI
        if self._speaking:
             # Only emit while speaking, otherwise it's too noisy
             pass
        else:
             # Emit level for visualization
             pass
        
        # Check for barge-in during TTS
        if self._speaking:
            if await self._barge_in.check_barge_in(energy):
                await self._stop_speaking()
                return
        
        # Wake word detection
        if not self._listening:
            wake_word = await self._wake_word.process(audio_data)
            if wake_word:
                await self._on_wake_word(wake_word)
        else:
            # Send to STT
            text = await self._stt.process(audio_data)
            if text:
                await self._handle_final_transcript(text)
                return
            
            # Check silence timeout
            if self._last_input_time > 0:
                silence_duration = current_time - self._last_input_time
                if silence_duration > STT_SILENCE_TIMEOUT_MS:
                    self._logger.info(f"Silence timeout ({silence_duration:.0f}ms), finalizing")
                    final_text = await self._stt.finish()
                    if final_text:
                        await self._handle_final_transcript(final_text)
                    else:
                        # Just silence, reset
                        self._listening = False
                        self._state.gui_state = GUIState.IDLE
                    self._last_input_time = 0
    
    async def _handle_final_transcript(self, text: str) -> None:
        """Handle final transcription result."""
        if len(text) > 1:  # Ignore very short noise
            await self.process_transcription(text)
            self._listening = False
            self._state.gui_state = GUIState.IDLE
        self._last_input_time = 0

    async def _on_wake_word(self, wake_word: str) -> None:
        """Handle wake word detection."""
        self._logger.info(f"Wake word detected: {wake_word}")
        self._listening = True
        self._last_input_time = time.time() * 1000  # Reset timer
        self._state.update_voice(wake_word=True, listening=True)
        self._state.gui_state = GUIState.LISTENING
        
        await self.emit(SystemEvent.WAKE_WORD_DETECTED, {"wake_word": wake_word})
    
    async def process_transcription(self, text: str) -> str:
        """Process a transcription and generate response."""
        self._logger.info(f"Processing: {text}")
        self._state.update_voice(transcript=text, processing=True)
        self._state.gui_state = GUIState.THINKING
        
        await self.emit(SystemEvent.TRANSCRIPTION_READY, {"text": text})
        
        response = ""
        if self._on_transcription:
            response = await self._on_transcription(text)
        
        self._state.update_voice(processing=False)
        
        if response:
            await self.speak(response)
        
        return response
    
    async def speak(self, text: str) -> None:
        """Speak text through TTS."""
        if not text:
            return
        
        self._logger.info(f"Speaking: {text[:50]}...")
        self._speaking = True
        self._state.update_voice(speaking=True)
        self._state.gui_state = GUIState.SPEAKING
        self._barge_in.set_tts_active(True)
        
        await self.emit(SystemEvent.TTS_START, {"text": text})
        
        try:
            audio = await self._tts.synthesize(text)
            # Audio playback
            if audio is not None and sd is not None:
                sd.play(audio, AUDIO_SAMPLE_RATE)
                sd.wait()
                
        except Exception as e:
            self._logger.error(f"TTS error: {e}")
        finally:
            await self._stop_speaking()
    
    async def _stop_speaking(self) -> None:
        """Stop TTS playback."""
        if sd is not None:
            sd.stop()
        self._speaking = False
        self._tts.stop()
        self._barge_in.set_tts_active(False)
        self._state.update_voice(speaking=False)
        self._state.gui_state = GUIState.IDLE
        
        await self.emit(SystemEvent.TTS_END, {})
    
    async def _on_barge_in(self) -> None:
        """Handle barge-in event."""
        self._logger.info("Barge-in: stopping TTS")
        await self._stop_speaking()
        self._listening = True
        self._state.gui_state = GUIState.LISTENING
    
    def get_stats(self) -> dict:
        """Get pipeline statistics."""
        return {
            "initialized": self._initialized,
            "running": self._running,
            "listening": self._listening,
            "speaking": self._speaking,
            "wake_word_available": self._wake_word._initialized,
            "stt_available": self._stt._initialized,
            "tts_available": self._tts._initialized,
        }


@lru_cache()
def get_voice_pipeline() -> VoicePipeline:
    return VoicePipeline.get_instance()


__all__ = ["VoicePipeline", "get_voice_pipeline"]
