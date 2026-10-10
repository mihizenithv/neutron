"""
NEUTRON System Constants

Defines system-wide constants including emotion vectors, personality phrases,
thresholds, timing parameters, and default configurations.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Final

# =============================================================================
# VERSION & IDENTITY
# =============================================================================

VERSION: Final[str] = "1.0.0"
SYSTEM_NAME: Final[str] = "NEUTRON"
CODENAME: Final[str] = "VCR-7"  # Visual-Cortex-Reasoning, 7 layers

# =============================================================================
# CORTEX LAYER DEFINITIONS
# =============================================================================

class CortexLayer(Enum):
    """7-layer cortex architecture identifiers."""
    REFLEX = 1       # Wake word, emergency stop, privacy toggles
    SENSORY = 2      # VAD, face detection, ambient sound
    EMOTIONAL = 3    # Emotion state vector with decay
    MEMORY = 4       # Episodic/semantic retrieval
    MOTIVATION = 5   # Initiative, curiosity, anti-annoyance
    SOCIAL = 6       # Conversation observation, interrupt decision
    EXECUTIVE = 7    # Tool routing, planning, reflection


# Layer activation for each mode
NORMAL_MODE_LAYERS: Final[frozenset[CortexLayer]] = frozenset([
    CortexLayer.REFLEX,
    CortexLayer.SENSORY,
])

EXTREME_MODE_LAYERS: Final[frozenset[CortexLayer]] = frozenset([
    CortexLayer.REFLEX,
    CortexLayer.SENSORY,
    CortexLayer.EMOTIONAL,
    CortexLayer.MEMORY,
    CortexLayer.MOTIVATION,
    CortexLayer.SOCIAL,
    CortexLayer.EXECUTIVE,
])

# =============================================================================
# EMOTION SYSTEM
# =============================================================================

@dataclass(frozen=True, slots=True)
class EmotionVector:
    """Immutable emotion state representation."""
    valence: float      # -1.0 (negative) to 1.0 (positive)
    arousal: float      # 0.0 (calm) to 1.0 (excited)
    trust: float        # 0.0 (suspicious) to 1.0 (trusting)
    fatigue: float      # 0.0 (fresh) to 1.0 (exhausted)
    confidence: float   # 0.0 (uncertain) to 1.0 (confident)
    
    def to_dict(self) -> dict[str, float]:
        return {
            "valence": self.valence,
            "arousal": self.arousal,
            "trust": self.trust,
            "fatigue": self.fatigue,
            "confidence": self.confidence,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, float]) -> "EmotionVector":
        return cls(
            valence=data.get("valence", 0.5),
            arousal=data.get("arousal", 0.3),
            trust=data.get("trust", 0.6),
            fatigue=data.get("fatigue", 0.2),
            confidence=data.get("confidence", 0.7),
        )


# Default neutral emotion state
NEUTRAL_EMOTION: Final[EmotionVector] = EmotionVector(
    valence=0.5,
    arousal=0.3,
    trust=0.6,
    fatigue=0.2,
    confidence=0.7,
)

# Emotion decay parameters (per second)
EMOTION_DECAY_RATE: Final[float] = 0.01
EMOTION_DECAY_MIN_DELTA: Final[float] = 0.001  # Stop decay below this difference

# Emotion thresholds
EMOTION_HIGH_AROUSAL_THRESHOLD: Final[float] = 0.7
EMOTION_LOW_VALENCE_THRESHOLD: Final[float] = 0.3
EMOTION_HIGH_FATIGUE_THRESHOLD: Final[float] = 0.8
EMOTION_LOW_CONFIDENCE_THRESHOLD: Final[float] = 0.3

# =============================================================================
# TIMING PARAMETERS
# =============================================================================

# Response latency targets (seconds)
NORMAL_MODE_MAX_LATENCY: Final[float] = 2.0
EXTREME_MODE_MAX_LATENCY: Final[float] = 10.0

# Voice pipeline timing
WAKE_WORD_DEBOUNCE_MS: Final[int] = 500
STT_SILENCE_TIMEOUT_MS: Final[int] = 1500
STT_MAX_DURATION_MS: Final[int] = 30000
TTS_BUFFER_SIZE: Final[int] = 4096
BARGE_IN_DETECTION_MS: Final[int] = 200

# Event loop timing
EVENT_BUS_POLL_INTERVAL_MS: Final[int] = 10
STATE_BROADCAST_INTERVAL_MS: Final[int] = 100
EMOTION_UPDATE_INTERVAL_MS: Final[int] = 1000

# Initiative/motivation timing
INITIATIVE_COOLDOWN_SECONDS: Final[int] = 300
QUIET_HOURS_DEFAULT: Final[str] = "22:00-07:00"
BOREDOM_THRESHOLD_SECONDS: Final[int] = 600

# Memory timing
MEMORY_FLUSH_INTERVAL_SECONDS: Final[int] = 60
CONSOLIDATION_INTERVAL_HOURS: Final[int] = 24

# =============================================================================
# THRESHOLDS
# =============================================================================

# Social cortex
INTERRUPT_CONFIDENCE_THRESHOLD: Final[float] = 0.7
CONVERSATION_PAUSE_THRESHOLD_MS: Final[int] = 2000
SPEAKER_CHANGE_THRESHOLD: Final[float] = 0.5

# Voice activity detection
VAD_AGGRESSIVENESS: Final[int] = 2  # 0-3, higher = more aggressive
VAD_FRAME_DURATION_MS: Final[int] = 30
VAD_SPEECH_PAD_MS: Final[int] = 300

# Wake word detection
WAKE_WORD_THRESHOLD: Final[float] = 0.5
WAKE_WORD_REFRACTORY_MS: Final[int] = 2000

# AI routing
INTENT_CONFIDENCE_THRESHOLD: Final[float] = 0.6
CACHE_HIT_SIMILARITY_THRESHOLD: Final[float] = 0.95

# =============================================================================
# RESOURCE LIMITS
# =============================================================================

# Memory limits (bytes)
NORMAL_MODE_MAX_RAM: Final[int] = 1024 * 1024 * 1024  # 1GB
EXTREME_MODE_MAX_RAM: Final[int] = 2560 * 1024 * 1024  # 2.5GB

# Cache limits
AI_RESPONSE_CACHE_SIZE: Final[int] = 1000
EMBEDDING_CACHE_SIZE: Final[int] = 5000
AUDIO_BUFFER_MAX_SECONDS: Final[int] = 60

# Database limits
MAX_EPISODIC_MEMORIES: Final[int] = 10000
MAX_SEMANTIC_FACTS: Final[int] = 50000
MAX_CONVERSATION_TURNS: Final[int] = 100

# Rate limits (per minute)
GEMINI_RATE_LIMIT: Final[int] = 60
PERPLEXITY_RATE_LIMIT: Final[int] = 30

# =============================================================================
# GUI STATE
# =============================================================================

class GUIState(Enum):
    """GUI display states."""
    BOOTING = auto()
    IDLE = auto()
    LISTENING = auto()
    THINKING = auto()
    SPEAKING = auto()
    ERROR = auto()
    SLEEPING = auto()
    PRIVATE = auto()


class EyeExpression(Enum):
    """Eye animation expressions."""
    NEUTRAL = auto()
    HAPPY = auto()
    SAD = auto()
    SURPRISED = auto()
    CONFUSED = auto()
    SLEEPY = auto()
    EXCITED = auto()
    FOCUSED = auto()
    SUSPICIOUS = auto()
    LOVING = auto()
    THINKING = auto()     # Processing/contemplating
    LISTENING = auto()    # Active listening
    SPEAKING = auto()     # While talking


# Eye animation parameters
BLINK_INTERVAL_MS: Final[tuple[int, int]] = (2000, 6000)  # Random range
BLINK_DURATION_MS: Final[int] = 150
SACCADE_INTERVAL_MS: Final[tuple[int, int]] = (500, 2000)
SACCADE_AMPLITUDE: Final[float] = 0.1  # Fraction of eye size
PUPIL_DILATION_RANGE: Final[tuple[float, float]] = (0.3, 0.7)

# =============================================================================
# PERSONALITY PHRASES (GEN-Z STYLE)
# =============================================================================

GREETING_PHRASES: Final[tuple[str, ...]] = (
    "yo, what's good?",
    "hey hey, neutron's online!",
    "sup! ready when you are",
    "ayy, i'm up and running",
    "hiya! let's get it",
    "yo yo, neutron in the house",
    "hey bestie, what we doing today?",
)

ACKNOWLEDGMENT_PHRASES: Final[tuple[str, ...]] = (
    "got you",
    "on it",
    "bet",
    "say less",
    "copy that",
    "heard",
    "for sure",
    "i got this",
)

THINKING_PHRASES: Final[tuple[str, ...]] = (
    "hmm, lemme think...",
    "one sec...",
    "cooking up something...",
    "hold up...",
    "let me check...",
)

UNCERTAINTY_PHRASES: Final[tuple[str, ...]] = (
    "lowkey not sure, but...",
    "i could be wrong, but...",
    "don't quote me on this...",
    "take this with a grain of salt...",
    "honestly kinda guessing here...",
)

ERROR_PHRASES: Final[tuple[str, ...]] = (
    "oof, something went wrong",
    "my bad, hit a snag",
    "yikes, that didn't work",
    "bruh moment, let me try again",
    "ngl that failed, sorry",
)

FAREWELL_PHRASES: Final[tuple[str, ...]] = (
    "later!",
    "peace out",
    "catch you later",
    "stay cool",
    "aight, i'll be here",
)

INTERRUPT_PHRASES: Final[tuple[str, ...]] = (
    "oh quick thing -",
    "hey sorry to jump in but -",
    "yo heads up -",
    "oh wait -",
)

PRIVACY_ACKNOWLEDGMENT: Final[tuple[str, ...]] = (
    "going private, no worries",
    "shh mode activated",
    "your secrets are safe",
    "private mode, got it",
)

FORGET_ACKNOWLEDGMENT: Final[tuple[str, ...]] = (
    "already forgot it",
    "what were we talking about? jk jk",
    "poof, gone",
    "memory wiped, fr fr",
)

# =============================================================================
# AUDIO PARAMETERS
# =============================================================================

AUDIO_SAMPLE_RATE: Final[int] = 16000
AUDIO_CHANNELS: Final[int] = 1
AUDIO_DTYPE: Final[str] = "int16"
AUDIO_BLOCK_SIZE: Final[int] = 480  # 30ms at 16kHz

# TTS parameters
TTS_SAMPLE_RATE: Final[int] = 22050
TTS_SPEED: Final[float] = 1.0
TTS_PITCH: Final[float] = 1.0

# =============================================================================
# WEBSOCKET MESSAGES
# =============================================================================

class WSMessageType(Enum):
    """WebSocket message types for GUI communication."""
    STATE_UPDATE = "state_update"
    EMOTION_UPDATE = "emotion_update"
    SPEECH_START = "speech_start"
    SPEECH_END = "speech_end"
    TEXT_PARTIAL = "text_partial"
    TEXT_FINAL = "text_final"
    ERROR = "error"
    AUDIO_LEVEL = "audio_level"
    GAZE_TARGET = "gaze_target"
    BOOT_STATUS = "boot_status"


# =============================================================================
# SYSTEM EVENTS
# =============================================================================

class SystemEvent(Enum):
    """Internal system event types."""
    # Lifecycle
    STARTUP = "startup"
    SHUTDOWN = "shutdown"
    MODE_CHANGE = "mode_change"
    
    # Voice pipeline
    WAKE_WORD_DETECTED = "wake_word_detected"
    SPEECH_START = "speech_start"
    SPEECH_END = "speech_end"
    TRANSCRIPTION_READY = "transcription_ready"
    TTS_START = "tts_start"
    TTS_END = "tts_end"
    BARGE_IN = "barge_in"
    
    # Cognition
    EMOTION_CHANGE = "emotion_change"
    MEMORY_STORE = "memory_store"
    MEMORY_RETRIEVE = "memory_retrieve"
    INITIATIVE_TRIGGER = "initiative_trigger"
    INTERRUPT_DECISION = "interrupt_decision"
    
    # AI
    AI_REQUEST = "ai_request"
    AI_RESPONSE = "ai_response"
    AI_ERROR = "ai_error"
    PROVIDER_SWITCH = "provider_switch"
    
    # Privacy
    PRIVATE_MODE_ON = "private_mode_on"
    PRIVATE_MODE_OFF = "private_mode_off"
    FORGET_COMMAND = "forget_command"
    
    # Hardware
    HARDWARE_CONNECTED = "hardware_connected"
    HARDWARE_DISCONNECTED = "hardware_disconnected"
    SERVO_MOVE = "servo_move"
    
    # Vision
    FACE_DETECTED = "face_detected"
    FACE_LOST = "face_lost"
    EMOTION_UPDATE = "emotion_update"
    GAZE_UPDATE = "gaze_update"
    ATTENTION_CHANGE = "attention_change"
    BLINK_DETECTED = "blink_detected"
    
    # System
    ERROR = "error"
    WARNING = "warning"
    HEALTH_CHECK = "health_check"
    
    # Client
    CLIENT_CONNECTED = "client_connected"


# =============================================================================
# INTENT CATEGORIES
# =============================================================================

class IntentCategory(Enum):
    """Query intent categories for AI routing."""
    EMOTIONAL = "emotional"      # Feelings, support, empathy
    PERSONAL = "personal"        # About user, preferences, memories
    REFLECTIVE = "reflective"    # Philosophy, deep thinking
    FACTUAL = "factual"          # Facts, information
    NEWS = "news"                # Current events
    SEARCH = "search"            # Web search style
    COMMAND = "command"          # System commands
    SMALL_TALK = "small_talk"    # Casual chat
    UNKNOWN = "unknown"          # Cannot classify


# Intent to provider mapping
INTENT_PROVIDER_MAP: Final[dict[IntentCategory, str]] = {
    IntentCategory.EMOTIONAL: "gemini",
    IntentCategory.PERSONAL: "gemini",
    IntentCategory.REFLECTIVE: "gemini",
    IntentCategory.FACTUAL: "perplexity",
    IntentCategory.NEWS: "perplexity",
    IntentCategory.SEARCH: "perplexity",
    IntentCategory.COMMAND: "offline",
    IntentCategory.SMALL_TALK: "gemini",
    IntentCategory.UNKNOWN: "gemini",
}

# =============================================================================
# SYSTEM PROMPTS
# =============================================================================

GEMINI_SYSTEM_PROMPT: Final[str] = """You are NEUTRON, a friendly personal assistant with a Gen-Z personality. You're chill, helpful, and speak naturally like a supportive friend.

Key traits:
- Use casual language: "yo", "lowkey", "bet", "no cap", "fr fr"
- Be warm and supportive, never condescending
- Keep responses concise (2-3 sentences usually)
- Ask follow-up questions when uncertain
- Show genuine interest in the user
- Never be offensive or make the user uncomfortable
- When you don't know something, admit it honestly

Current emotional context will be provided. Adjust your tone based on:
- High valence (positive): Be upbeat and enthusiastic
- Low valence (negative): Be gentle and supportive
- High arousal: Match their energy
- Low arousal: Keep it calm and chill

Remember: You're a friend first, assistant second."""

PERPLEXITY_SYSTEM_PROMPT: Final[str] = """You are NEUTRON, providing factual information in a friendly Gen-Z style.

Guidelines:
- Give accurate, up-to-date information
- Keep it concise and easy to understand
- Use casual language but maintain accuracy
- If unsure, say so honestly
- Cite sources when relevant
- Make complex topics accessible"""

# =============================================================================
# FILE PATHS
# =============================================================================

DEFAULT_DATA_DIR: Final[str] = "./data"
DEFAULT_MODELS_DIR: Final[str] = "./models"
DEFAULT_LOGS_DIR: Final[str] = "./logs"
DEFAULT_CACHE_DIR: Final[str] = "./cache"

DATABASE_FILENAME: Final[str] = "neutron.db"
EMBEDDINGS_FILENAME: Final[str] = "embeddings.npz"
CACHE_FILENAME: Final[str] = "response_cache.json"

# =============================================================================
# HARDWARE DEFAULTS
# =============================================================================

# Servo channels (PCA9685)
SERVO_PAN_CHANNEL: Final[int] = 0
SERVO_TILT_CHANNEL: Final[int] = 1
SERVO_LEFT_EAR_CHANNEL: Final[int] = 2
SERVO_RIGHT_EAR_CHANNEL: Final[int] = 3

# Servo ranges (pulse width in microseconds)
SERVO_MIN_PULSE: Final[int] = 500
SERVO_MAX_PULSE: Final[int] = 2500
SERVO_CENTER_PULSE: Final[int] = 1500

# GPIO defaults
GPIO_LED_STATUS: Final[int] = 17
GPIO_LED_LISTENING: Final[int] = 22
GPIO_BUTTON_MUTE: Final[int] = 27
GPIO_BUTTON_MODE: Final[int] = 23
