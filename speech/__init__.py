"""
NEUTRON Speech Module

Voice pipeline with pluggable wake word, STT, and TTS.
"""

from speech.pipeline import VoicePipeline, get_voice_pipeline

__all__ = ["VoicePipeline", "get_voice_pipeline"]
