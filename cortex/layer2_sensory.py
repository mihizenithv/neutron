"""
NEUTRON Cortex Layer 2 - Sensory

Handles perception and environmental awareness:
- Voice activity detection
- Multi-speaker detection heuristic
- Face presence detection
- Ambient sound classification
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

from config.constants import CortexLayer, VAD_SPEECH_PAD_MS
from cortex.base import FastPathLayer, LayerInput, LayerResult


class AmbientSound(Enum):
    """Ambient sound classification."""
    SILENCE = auto()
    SPEECH = auto()
    MUSIC = auto()
    NOISE = auto()
    TV_AUDIO = auto()
    OUTDOOR = auto()


@dataclass
class VoiceActivityState:
    """Voice activity detection state."""
    is_speech: bool = False
    speech_start_time: float = 0.0
    speech_duration_ms: float = 0.0
    silence_duration_ms: float = 0.0
    energy_level: float = 0.0
    is_final: bool = False


@dataclass
class SpeakerInfo:
    """Detected speaker information (heuristic only)."""
    speaker_count: int = 0
    primary_direction: float = 0.0  # -1 to 1 (left to right)
    confidence: float = 0.0


@dataclass
class FacePresenceInfo:
    """Face presence detection info."""
    faces_detected: int = 0
    attention_direction: tuple[float, float] = (0.5, 0.5)  # Normalized gaze target
    closest_face_distance: float = 0.0  # Arbitrary units


class SensoryLayer(FastPathLayer):
    """
    Layer 2: Sensory processing.
    
    Detects:
    - Voice activity in audio stream
    - Number of speakers (heuristic)
    - Face presence for attention
    - Ambient sound type
    """
    
    def __init__(self) -> None:
        super().__init__()
        self._vad_state = VoiceActivityState()
        self._speaker_info = SpeakerInfo()
        self._face_info = FacePresenceInfo()
        self._ambient_sound = AmbientSound.SILENCE
        self._last_speech_time = 0.0
        self._speech_history: list[float] = []  # Energy levels
    
    @property
    def layer(self) -> CortexLayer:
        return CortexLayer.SENSORY
    
    async def process(self, input_data: LayerInput) -> LayerResult:
        text = input_data.text
        audio_data = input_data.audio_data
        context = input_data.context
        
        result_data: dict[str, Any] = {
            "vad": self._vad_state.__dict__.copy(),
            "speakers": self._speaker_info.__dict__.copy(),
            "faces": self._face_info.__dict__.copy(),
            "ambient_sound": self._ambient_sound.name,
            "should_listen": False,
            "attention_target": (0.5, 0.5),
        }
        
        # Process audio if available
        if audio_data:
            await self._process_audio(audio_data, result_data)
        
        # Process text for speech patterns
        if text:
            self._analyze_speech_patterns(text, result_data)
        
        # Process face data if in context
        if "face_data" in context:
            await self._process_faces(context["face_data"], result_data)
        
        # Determine if we should be listening
        result_data["should_listen"] = self._should_listen()
        
        # Update gaze target based on detected attention
        if self._face_info.faces_detected > 0:
            self._state.gaze_target = self._face_info.attention_direction
            result_data["attention_target"] = self._face_info.attention_direction
        
        return LayerResult(
            success=True,
            data=result_data,
            confidence=self._calculate_confidence(),
            should_propagate=True,
        )
    
    async def _process_audio(self, audio_data: bytes, result_data: dict) -> None:
        """Process audio data for VAD and ambient classification."""
        import numpy as np
        
        # Convert bytes to numpy array
        try:
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            if len(audio_array) == 0:
                return
            
            # Calculate energy level
            energy = np.sqrt(np.mean(audio_array.astype(float) ** 2))
            normalized_energy = min(1.0, energy / 32768.0 * 10)  # Normalize
            
            self._speech_history.append(normalized_energy)
            if len(self._speech_history) > 100:
                self._speech_history = self._speech_history[-100:]
            
            # Simple VAD based on energy threshold
            speech_threshold = 0.05
            is_speech = normalized_energy > speech_threshold
            
            current_time = time.time() * 1000
            
            if is_speech and not self._vad_state.is_speech:
                # Speech started
                self._vad_state.is_speech = True
                self._vad_state.speech_start_time = current_time
                self._last_speech_time = current_time
            elif is_speech and self._vad_state.is_speech:
                # Speech continuing
                self._vad_state.speech_duration_ms = current_time - self._vad_state.speech_start_time
                self._last_speech_time = current_time
            elif not is_speech and self._vad_state.is_speech:
                # Check if silence is long enough to end speech
                silence_duration = current_time - self._last_speech_time
                self._vad_state.silence_duration_ms = silence_duration
                if silence_duration > VAD_SPEECH_PAD_MS:
                    self._vad_state.is_speech = False
                    self._vad_state.is_final = True
            
            self._vad_state.energy_level = normalized_energy
            
            # Update result
            result_data["vad"] = {
                "is_speech": self._vad_state.is_speech,
                "energy_level": normalized_energy,
                "speech_duration_ms": self._vad_state.speech_duration_ms,
                "is_final": self._vad_state.is_final,
            }
            
            # Classify ambient sound
            self._classify_ambient(audio_array, normalized_energy)
            result_data["ambient_sound"] = self._ambient_sound.name
            
            # Estimate speaker count from audio patterns
            self._estimate_speakers(audio_array)
            result_data["speakers"] = self._speaker_info.__dict__.copy()
            
        except Exception as e:
            self._logger.debug(f"Audio processing error: {e}")
    
    def _analyze_speech_patterns(self, text: str, result_data: dict) -> None:
        """Analyze text for speech pattern clues."""
        words = text.split()
        
        # Simple multi-speaker detection heuristics
        speaker_indicators = [
            "he said", "she said", "they said",
            "someone", "another person", "somebody",
        ]
        
        text_lower = text.lower()
        speaker_count = 1  # At least one speaker
        
        for indicator in speaker_indicators:
            if indicator in text_lower:
                speaker_count = 2
                break
        
        # Question marks might indicate dialogue
        if text.count("?") > 1:
            speaker_count = max(speaker_count, 2)
        
        self._speaker_info.speaker_count = speaker_count
        result_data["speakers"]["speaker_count"] = speaker_count
    
    async def _process_faces(self, face_data: dict, result_data: dict) -> None:
        """Process face detection data."""
        faces = face_data.get("faces", [])
        self._face_info.faces_detected = len(faces)
        
        if faces:
            # Find closest/most prominent face
            primary_face = max(faces, key=lambda f: f.get("size", 0))
            
            # Calculate gaze target (center of face, normalized 0-1)
            x = primary_face.get("x", 0.5)
            y = primary_face.get("y", 0.5)
            self._face_info.attention_direction = (
                max(0.0, min(1.0, x)),
                max(0.0, min(1.0, y)),
            )
            self._face_info.closest_face_distance = primary_face.get("distance", 1.0)
        
        result_data["faces"] = self._face_info.__dict__.copy()
    
    def _classify_ambient(self, audio_array, energy: float) -> None:
        """Classify ambient sound type."""
        import numpy as np
        
        if energy < 0.01:
            self._ambient_sound = AmbientSound.SILENCE
        elif energy > 0.3:
            # High energy - likely speech or loud noise
            # Check for speech-like patterns (energy variance)
            if len(self._speech_history) > 10:
                variance = np.var(self._speech_history[-10:])
                if variance > 0.01:
                    self._ambient_sound = AmbientSound.SPEECH
                else:
                    self._ambient_sound = AmbientSound.NOISE
            else:
                self._ambient_sound = AmbientSound.SPEECH
        else:
            # Medium energy
            self._ambient_sound = AmbientSound.NOISE
    
    def _estimate_speakers(self, audio_array) -> None:
        """Estimate number of speakers from audio (heuristic)."""
        import numpy as np
        
        if len(audio_array) < 1600:  # Too short
            return
        
        # Simple zero-crossing rate analysis
        zero_crossings = np.sum(np.abs(np.diff(np.sign(audio_array)))) / 2
        zcr = zero_crossings / len(audio_array)
        
        # Higher ZCR variance might indicate multiple speakers
        # This is a very rough heuristic
        if zcr > 0.1:
            self._speaker_info.speaker_count = min(3, self._speaker_info.speaker_count + 1)
        else:
            self._speaker_info.speaker_count = 1
        
        self._speaker_info.confidence = 0.5  # Low confidence for heuristic
    
    def _should_listen(self) -> bool:
        """Determine if we should be actively listening."""
        # Listen if speech is detected
        if self._vad_state.is_speech:
            return True
        
        # Listen if faces are detected
        if self._face_info.faces_detected > 0:
            return True
        
        # Listen if recent speech (within 5 seconds)
        if time.time() * 1000 - self._last_speech_time < 5000:
            return True
        
        return False
    
    def _calculate_confidence(self) -> float:
        """Calculate overall sensory confidence."""
        confidence = 0.5  # Base confidence
        
        if self._vad_state.is_speech:
            confidence += 0.2
        if self._face_info.faces_detected > 0:
            confidence += 0.2
        if self._ambient_sound != AmbientSound.NOISE:
            confidence += 0.1
        
        return min(1.0, confidence)


__all__ = ["SensoryLayer", "VoiceActivityState", "SpeakerInfo", "FacePresenceInfo", "AmbientSound"]
