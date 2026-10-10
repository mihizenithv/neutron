"""
NEUTRON Configuration Module

Pydantic-based configuration management with environment loading,
mode switching (Normal/Extreme), and comprehensive validation.
"""

from __future__ import annotations

import os
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class OperationMode(str, Enum):
    """System operation modes affecting layer activation and resource usage."""
    NORMAL = "NORMAL"   # Fast path: layers 1-2, <1GB RAM, <2s latency
    EXTREME = "EXTREME" # Full reasoning: layers 1-7, up to 2.5GB RAM


class PersonalityStyle(str, Enum):
    """Personality styles for response generation."""
    GENZ = "genz"       # Gen-Z friendly, chill, uses slang
    FORMAL = "formal"   # Professional, proper grammar
    FRIENDLY = "friendly"  # Warm, approachable, balanced


class WakeWordEngine(str, Enum):
    """Available wake word detection engines."""
    OPENWAKEWORD = "openwakeword"
    PORCUPINE = "porcupine"


class STTEngine(str, Enum):
    """Available speech-to-text engines."""
    VOSK = "vosk"


class TTSEngine(str, Enum):
    """Available text-to-speech engines."""
    PIPER = "piper"


class AIProvider(str, Enum):
    """Available AI providers for response generation."""
    GEMINI = "gemini"
    PERPLEXITY = "perplexity"
    OLLAMA = "ollama"
    OFFLINE = "offline"


class LogFormat(str, Enum):
    """Log output formats."""
    JSON = "json"
    CONSOLE = "console"


class ServoController(str, Enum):
    """Servo controller types for hardware integration."""
    PCA9685 = "pca9685"
    PIGPIO = "pigpio"


class AISettings(BaseSettings):
    """AI provider configuration."""
    
    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # API Keys
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    perplexity_api_key: str = Field(default="", alias="PERPLEXITY_API_KEY")
    
    # Ollama (local LLM)
    ollama_enabled: bool = Field(default=False, alias="OLLAMA_ENABLED")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="tinyllama:1.1b", alias="OLLAMA_MODEL")
    ollama_for_monitoring: bool = Field(default=True, alias="OLLAMA_FOR_MONITORING")
    ollama_for_emotions: bool = Field(default=True, alias="OLLAMA_FOR_EMOTIONS")
    
    # Router settings
    default_provider: AIProvider = Field(default=AIProvider.GEMINI, alias="AI_DEFAULT_PROVIDER")
    cache_enabled: bool = Field(default=True, alias="AI_CACHE_ENABLED")
    cache_ttl_seconds: int = Field(default=3600, alias="AI_CACHE_TTL_SECONDS", ge=60)
    cache_max_size_mb: int = Field(default=100, alias="AI_CACHE_MAX_SIZE_MB", ge=10)
    rate_limit_gemini: int = Field(default=60, alias="AI_RATE_LIMIT_GEMINI", ge=1)
    rate_limit_perplexity: int = Field(default=30, alias="AI_RATE_LIMIT_PERPLEXITY", ge=1)
    
    @field_validator("gemini_api_key", "perplexity_api_key", mode="before")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Strip whitespace from API keys."""
        return v.strip() if v else ""


class VoiceSettings(BaseSettings):
    """Voice pipeline configuration."""
    
    model_config = SettingsConfigDict(extra="ignore")
    
    # Wake word
    wakeword_engine: WakeWordEngine = Field(
        default=WakeWordEngine.OPENWAKEWORD,
        alias="WAKEWORD_ENGINE"
    )
    wakeword_sensitivity: float = Field(
        default=0.5,
        alias="WAKEWORD_SENSITIVITY",
        ge=0.0,
        le=1.0
    )
    wakeword_phrases: list[str] = Field(
        default=["neutron", "hey neutron"],
        alias="WAKEWORD_PHRASES"
    )
    
    # STT
    stt_engine: STTEngine = Field(default=STTEngine.VOSK, alias="STT_ENGINE")
    vosk_model_path: Path = Field(
        default=Path("./models/vosk-model-small-en-us-0.15"),
        alias="VOSK_MODEL_PATH"
    )
    
    # TTS
    tts_engine: TTSEngine = Field(default=TTSEngine.PIPER, alias="TTS_ENGINE")
    piper_voice: str = Field(default="en_US-lessac-medium", alias="PIPER_VOICE")
    piper_model_path: Path = Field(default=Path("./models/piper"), alias="PIPER_MODEL_PATH")
    
    # Audio devices
    audio_input_device: int | None = Field(default=None, alias="AUDIO_INPUT_DEVICE")
    audio_output_device: int | None = Field(default=None, alias="AUDIO_OUTPUT_DEVICE")
    
    # Barge-in
    barge_in_enabled: bool = Field(default=True, alias="BARGE_IN_ENABLED")
    
    @field_validator("wakeword_phrases", mode="before")
    @classmethod
    def parse_wakeword_phrases(cls, v: str | list) -> list[str]:
        """Parse comma-separated wake word phrases."""
        if isinstance(v, str):
            return [p.strip().lower() for p in v.split(",") if p.strip()]
        return [p.lower() for p in v]


class MemorySettings(BaseSettings):
    """Memory system configuration."""
    
    model_config = SettingsConfigDict(extra="ignore")
    
    # SQLite
    sqlite_database_path: Path = Field(
        default=Path("./data/neutron.db"),
        alias="SQLITE_DATABASE_PATH"
    )
    
    # Embeddings
    embeddings_model: str = Field(
        default="all-MiniLM-L6-v2",
        alias="EMBEDDINGS_MODEL"
    )
    chroma_persist_path: Path = Field(
        default=Path("./data/chroma"),
        alias="CHROMA_PERSIST_PATH"
    )
    
    # Limits
    max_episodic_memories: int = Field(
        default=10000,
        alias="MAX_EPISODIC_MEMORIES",
        ge=100
    )
    memory_consolidation_interval_hours: int = Field(
        default=24,
        alias="MEMORY_CONSOLIDATION_INTERVAL_HOURS",
        ge=1
    )


class CloudSyncSettings(BaseSettings):
    """Cloud synchronization configuration."""
    
    model_config = SettingsConfigDict(extra="ignore")
    
    enabled: bool = Field(default=False, alias="CLOUD_SYNC_ENABLED")
    gcs_bucket_name: str = Field(default="neutron-memory-backup", alias="GCS_BUCKET_NAME")
    google_credentials_path: Path | None = Field(
        default=None,
        alias="GOOGLE_APPLICATION_CREDENTIALS"
    )
    sync_interval_hours: int = Field(default=24, alias="CLOUD_SYNC_INTERVAL_HOURS", ge=1)


class EmotionSettings(BaseSettings):
    """Emotion system configuration with decay parameters."""
    
    model_config = SettingsConfigDict(extra="ignore")
    
    decay_rate: float = Field(default=0.01, alias="EMOTION_DECAY_RATE", ge=0.0, le=1.0)
    
    # Neutral baseline values
    neutral_valence: float = Field(default=0.5, alias="EMOTION_NEUTRAL_VALENCE", ge=0.0, le=1.0)
    neutral_arousal: float = Field(default=0.3, alias="EMOTION_NEUTRAL_AROUSAL", ge=0.0, le=1.0)
    neutral_trust: float = Field(default=0.6, alias="EMOTION_NEUTRAL_TRUST", ge=0.0, le=1.0)
    neutral_fatigue: float = Field(default=0.2, alias="EMOTION_NEUTRAL_FATIGUE", ge=0.0, le=1.0)
    neutral_confidence: float = Field(default=0.7, alias="EMOTION_NEUTRAL_CONFIDENCE", ge=0.0, le=1.0)


class MotivationSettings(BaseSettings):
    """Motivation and initiative system configuration."""
    
    model_config = SettingsConfigDict(extra="ignore")
    
    initiative_cooldown_seconds: int = Field(
        default=300,
        alias="INITIATIVE_COOLDOWN_SECONDS",
        ge=60
    )
    quiet_hours: str = Field(default="22:00-07:00", alias="QUIET_HOURS")
    annoyance_threshold: float = Field(
        default=0.7,
        alias="ANNOYANCE_THRESHOLD",
        ge=0.0,
        le=1.0
    )


class SocialSettings(BaseSettings):
    """Social cortex configuration."""
    
    model_config = SettingsConfigDict(extra="ignore")
    
    interrupt_confidence_threshold: float = Field(
        default=0.7,
        alias="INTERRUPT_CONFIDENCE_THRESHOLD",
        ge=0.0,
        le=1.0
    )
    conversation_window_seconds: int = Field(
        default=30,
        alias="CONVERSATION_WINDOW_SECONDS",
        ge=5
    )


class ServerSettings(BaseSettings):
    """FastAPI server configuration."""
    
    model_config = SettingsConfigDict(extra="ignore")
    
    host: str = Field(default="0.0.0.0", alias="SERVER_HOST")
    port: int = Field(default=8000, alias="SERVER_PORT", ge=1, le=65535)
    websocket_path: str = Field(default="/ws", alias="WEBSOCKET_PATH")
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        alias="CORS_ORIGINS"
    )
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list) -> list[str]:
        """Parse comma-separated CORS origins."""
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


class GUISettings(BaseSettings):
    """GUI configuration."""
    
    model_config = SettingsConfigDict(extra="ignore")
    
    websocket_url: str = Field(default="ws://localhost:8000/ws", alias="GUI_WEBSOCKET_URL")
    animation_fps: int = Field(default=30, alias="EYE_ANIMATION_FPS", ge=15, le=60)
    boot_retry_interval_ms: int = Field(default=1000, alias="BOOT_RETRY_INTERVAL_MS", ge=100)
    boot_max_retries: int = Field(default=30, alias="BOOT_MAX_RETRIES", ge=5)


class HardwareSettings(BaseSettings):
    """Hardware integration configuration."""
    
    model_config = SettingsConfigDict(extra="ignore")
    
    enabled: bool = Field(default=False, alias="HARDWARE_ENABLED")
    servo_controller: ServoController = Field(
        default=ServoController.PCA9685,
        alias="SERVO_CONTROLLER"
    )
    pca9685_i2c_address: int = Field(default=0x40, alias="PCA9685_I2C_ADDRESS")
    status_led_pin: int = Field(default=17, alias="STATUS_LED_PIN")
    mute_button_pin: int = Field(default=27, alias="MUTE_BUTTON_PIN")


class LoggingSettings(BaseSettings):
    """Logging configuration."""
    
    model_config = SettingsConfigDict(extra="ignore")
    
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        alias="LOG_LEVEL"
    )
    format: LogFormat = Field(default=LogFormat.CONSOLE, alias="LOG_FORMAT")
    file_path: Path | None = Field(default=None, alias="LOG_FILE_PATH")
    max_bytes: int = Field(default=10485760, alias="LOG_MAX_BYTES", ge=1048576)
    backup_count: int = Field(default=5, alias="LOG_BACKUP_COUNT", ge=1)


class PersonalitySettings(BaseSettings):
    """Personality and response generation configuration."""
    
    model_config = SettingsConfigDict(extra="ignore")
    
    style: PersonalityStyle = Field(default=PersonalityStyle.GENZ, alias="PERSONALITY_STYLE")
    max_tokens: int = Field(default=150, alias="RESPONSE_MAX_TOKENS", ge=50, le=1000)
    temperature: float = Field(default=0.7, alias="RESPONSE_TEMPERATURE", ge=0.0, le=2.0)


class Settings(BaseSettings):
    """
    Main NEUTRON settings container.
    
    Loads configuration from environment variables and .env files.
    Includes validation and nested configuration objects.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
    )
    
    # Core settings
    mode: OperationMode = Field(default=OperationMode.NORMAL, alias="NEUTRON_MODE")
    debug: bool = Field(default=False, alias="NEUTRON_DEBUG")
    
    # Project paths
    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent)
    data_dir: Path = Field(default=Path("./data"))
    models_dir: Path = Field(default=Path("./models"))
    logs_dir: Path = Field(default=Path("./logs"))
    
    # Nested configurations
    ai: AISettings = Field(default_factory=AISettings)
    voice: VoiceSettings = Field(default_factory=VoiceSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    cloud_sync: CloudSyncSettings = Field(default_factory=CloudSyncSettings)
    emotion: EmotionSettings = Field(default_factory=EmotionSettings)
    motivation: MotivationSettings = Field(default_factory=MotivationSettings)
    social: SocialSettings = Field(default_factory=SocialSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    gui: GUISettings = Field(default_factory=GUISettings)
    hardware: HardwareSettings = Field(default_factory=HardwareSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    personality: PersonalitySettings = Field(default_factory=PersonalitySettings)
    
    @model_validator(mode="after")
    def validate_mode_requirements(self) -> "Settings":
        """Validate settings based on operation mode."""
        if self.mode == OperationMode.NORMAL:
            # In normal mode, ensure we're not loading heavy models
            pass
        return self
    
    @property
    def active_layers(self) -> list[int]:
        """Get list of active cortex layer numbers based on mode."""
        if self.mode == OperationMode.NORMAL:
            return [1, 2]  # Fast path: reflex + sensory only
        return [1, 2, 3, 4, 5, 6, 7]  # Full cortex
    
    @property
    def is_extreme_mode(self) -> bool:
        """Check if in extreme (full reasoning) mode."""
        return self.mode == OperationMode.EXTREME
    
    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        for dir_path in [self.data_dir, self.models_dir, self.logs_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def get_api_key(self, provider: AIProvider) -> str:
        """Get API key for specified provider."""
        if provider == AIProvider.GEMINI:
            return self.ai.gemini_api_key
        elif provider == AIProvider.PERPLEXITY:
            return self.ai.perplexity_api_key
        return ""


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses LRU cache to avoid re-parsing environment on every call.
    Call get_settings.cache_clear() to reload settings.
    """
    return Settings()


def reload_settings() -> Settings:
    """Reload settings from environment."""
    get_settings.cache_clear()
    return get_settings()


# Convenience exports
__all__ = [
    "Settings",
    "get_settings",
    "reload_settings",
    "OperationMode",
    "PersonalityStyle",
    "WakeWordEngine",
    "STTEngine",
    "TTSEngine",
    "AIProvider",
    "LogFormat",
    "ServoController",
    "AISettings",
    "VoiceSettings",
    "MemorySettings",
    "CloudSyncSettings",
    "EmotionSettings",
    "MotivationSettings",
    "SocialSettings",
    "ServerSettings",
    "GUISettings",
    "HardwareSettings",
    "LoggingSettings",
    "PersonalitySettings",
]
