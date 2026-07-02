"""
companion/utils/config.py
=========================
Central configuration loader. Reads from .env file and environment
variables. Provides typed access to all system settings.
"""

from __future__ import annotations

import os
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Try to load dotenv (graceful fallback if not installed yet)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


@dataclass
class APIConfig:
    """Cloud API credentials and endpoints."""
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))

    # Model selections
    groq_chat_model: str = field(default_factory=lambda: os.getenv("GROQ_CHAT_MODEL", "llama-3.3-70b-versatile"))
    groq_vision_model: str = field(default_factory=lambda: os.getenv("GROQ_VISION_MODEL", "llama-3.2-11b-vision-preview"))
    groq_whisper_model: str = field(default_factory=lambda: os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3"))
    openai_fallback_model: str = field(default_factory=lambda: os.getenv("OPENAI_FALLBACK_MODEL", "gpt-4o-mini"))
    anthropic_fallback_model: str = field(default_factory=lambda: os.getenv("ANTHROPIC_FALLBACK_MODEL", "claude-3-haiku-20240307"))


@dataclass
class RateLimitConfig:
    """Token rate limiting and quota settings."""
    # Daily quota (Groq Free: ~30k tokens/day, padded for safety)
    daily_token_quota: int = field(default_factory=lambda: int(os.getenv("DAILY_TOKEN_QUOTA", "28000")))
    # Tokens per minute (Groq Free: 6000 TPM)
    tokens_per_minute: int = field(default_factory=lambda: int(os.getenv("TOKENS_PER_MINUTE", "5500")))
    # Requests per minute (Groq Free: 30 RPM)
    requests_per_minute: int = field(default_factory=lambda: int(os.getenv("REQUESTS_PER_MINUTE", "25")))
    # Max tokens per single response
    max_tokens_per_response: int = field(default_factory=lambda: int(os.getenv("MAX_TOKENS_PER_RESPONSE", "512")))
    # Cache TTL in seconds
    cache_ttl_seconds: int = field(default_factory=lambda: int(os.getenv("CACHE_TTL_SECONDS", "3600")))


@dataclass
class VTSConfig:
    """VTube Studio WebSocket connection settings."""
    host: str = field(default_factory=lambda: os.getenv("VTS_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.getenv("VTS_PORT", "8001")))
    plugin_name: str = "MyCompanion"
    plugin_developer: str = "MyCompanion Contributors"
    plugin_icon: str = ""  # Base64 icon (optional)
    reconnect_interval: float = 5.0
    heartbeat_interval: float = 30.0

    @property
    def ws_url(self) -> str:
        return f"ws://{self.host}:{self.port}"


@dataclass
class VisionConfig:
    """Vision agent settings."""
    capture_interval: float = field(default_factory=lambda: float(os.getenv("VISION_CAPTURE_INTERVAL", "30.0")))
    jpeg_quality: int = field(default_factory=lambda: int(os.getenv("VISION_JPEG_QUALITY", "60")))
    max_image_width: int = field(default_factory=lambda: int(os.getenv("VISION_MAX_WIDTH", "1280")))
    max_image_height: int = field(default_factory=lambda: int(os.getenv("VISION_MAX_HEIGHT", "720")))
    duplicate_threshold: float = 0.99  # MD5 match = skip
    enabled: bool = field(default_factory=lambda: os.getenv("VISION_ENABLED", "true").lower() == "true")


@dataclass
class AudioConfig:
    """Audio input/output settings."""
    # STT settings
    stt_sample_rate: int = field(default_factory=lambda: int(os.getenv("STT_SAMPLE_RATE", "16000")))
    stt_channels: int = 1
    stt_chunk_duration: float = field(default_factory=lambda: float(os.getenv("STT_CHUNK_DURATION", "5.0")))
    stt_silence_threshold: float = field(default_factory=lambda: float(os.getenv("STT_SILENCE_THRESHOLD", "0.01")))
    stt_enabled: bool = field(default_factory=lambda: os.getenv("STT_ENABLED", "true").lower() == "true")

    # TTS settings
    tts_voice: str = field(default_factory=lambda: os.getenv("TTS_VOICE", "vi-VN-HoaiMyNeural"))
    tts_rate: str = field(default_factory=lambda: os.getenv("TTS_RATE", "+0%"))
    tts_volume: str = field(default_factory=lambda: os.getenv("TTS_VOLUME", "+0%"))
    tts_player: str = field(default_factory=lambda: os.getenv("TTS_PLAYER", "mpv"))  # mpv or paplay
    tts_enabled: bool = field(default_factory=lambda: os.getenv("TTS_ENABLED", "true").lower() == "true")


@dataclass
class IdleConfig:
    """Idle behavior thresholds."""
    movement_idle_threshold: float = field(default_factory=lambda: float(os.getenv("MOVEMENT_IDLE_THRESHOLD", "120.0")))
    boredom_idle_threshold: float = field(default_factory=lambda: float(os.getenv("BOREDOM_IDLE_THRESHOLD", "300.0")))
    dream_idle_threshold: float = field(default_factory=lambda: float(os.getenv("DREAM_IDLE_THRESHOLD", "600.0")))
    dream_cycle_duration: float = field(default_factory=lambda: float(os.getenv("DREAM_CYCLE_DURATION", "600.0")))


@dataclass
class UIConfig:
    """Chat widget UI settings."""
    window_width: int = field(default_factory=lambda: int(os.getenv("UI_WIDTH", "350")))
    window_height: int = field(default_factory=lambda: int(os.getenv("UI_HEIGHT", "500")))
    initial_x: int = field(default_factory=lambda: int(os.getenv("UI_INITIAL_X", "100")))
    initial_y: int = field(default_factory=lambda: int(os.getenv("UI_INITIAL_Y", "100")))
    opacity: float = field(default_factory=lambda: float(os.getenv("UI_OPACITY", "0.92")))
    font_family: str = "Noto Sans"
    font_size: int = 11
    accent_color: str = "#a78bfa"  # Violet accent
    bg_color: str = "#0d0d1a"
    text_color: str = "#e2e8f0"


@dataclass
class SystemConfig:
    """Top-level system configuration container."""
    api: APIConfig = field(default_factory=APIConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    vts: VTSConfig = field(default_factory=VTSConfig)
    vision: VisionConfig = field(default_factory=VisionConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    idle: IdleConfig = field(default_factory=IdleConfig)
    ui: UIConfig = field(default_factory=UIConfig)

    # Paths
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("DATA_DIR", "~/.mycompanion")).expanduser())
    db_path: Path = field(default_factory=lambda: Path(os.getenv("DB_PATH", "~/.mycompanion/companion.db")).expanduser())
    log_path: Path = field(default_factory=lambda: Path(os.getenv("LOG_PATH", "~/.mycompanion/companion.log")).expanduser())
    cache_dir: Path = field(default_factory=lambda: Path(os.getenv("CACHE_DIR", "~/.mycompanion/cache")).expanduser())

    # Persona
    companion_name: str = field(default_factory=lambda: os.getenv("COMPANION_NAME", "Hana"))
    user_name: str = field(default_factory=lambda: os.getenv("USER_NAME", "Chủ nhân"))
    language: str = field(default_factory=lambda: os.getenv("LANGUAGE", "vi"))

    # Feature flags
    debug_mode: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    enable_vision: bool = field(default_factory=lambda: os.getenv("ENABLE_VISION", "true").lower() == "true")
    enable_stt: bool = field(default_factory=lambda: os.getenv("ENABLE_STT", "true").lower() == "true")
    enable_tts: bool = field(default_factory=lambda: os.getenv("ENABLE_TTS", "true").lower() == "true")
    enable_vts: bool = field(default_factory=lambda: os.getenv("ENABLE_VTS", "true").lower() == "true")
    enable_movement: bool = field(default_factory=lambda: os.getenv("ENABLE_MOVEMENT", "true").lower() == "true")

    def ensure_dirs(self) -> None:
        """Create all required data directories."""
        for path in [self.data_dir, self.cache_dir]:
            path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Data directories ensured at {self.data_dir}")

    def validate(self) -> list[str]:
        """Return list of validation warnings."""
        warnings = []
        if not self.api.groq_api_key:
            warnings.append("GROQ_API_KEY not set — AI features will be disabled")
        if not self.api.openai_api_key:
            warnings.append("OPENAI_API_KEY not set — OpenAI fallback unavailable")
        if not self.api.anthropic_api_key:
            warnings.append("ANTHROPIC_API_KEY not set — Anthropic fallback unavailable")
        return warnings

    def to_dict(self) -> dict:
        """Export config as dictionary (masks API keys)."""
        return {
            "companion_name": self.companion_name,
            "user_name": self.user_name,
            "language": self.language,
            "data_dir": str(self.data_dir),
            "features": {
                "vision": self.enable_vision,
                "stt": self.enable_stt,
                "tts": self.enable_tts,
                "vts": self.enable_vts,
                "movement": self.enable_movement,
            },
            "api_keys_set": {
                "groq": bool(self.api.groq_api_key),
                "openai": bool(self.api.openai_api_key),
                "anthropic": bool(self.api.anthropic_api_key),
            }
        }


# Global singleton
_config: Optional[SystemConfig] = None


def get_config() -> SystemConfig:
    """Get or create the global configuration singleton."""
    global _config
    if _config is None:
        _config = SystemConfig()
        _config.ensure_dirs()
        warnings = _config.validate()
        for w in warnings:
            logger.warning(f"Config warning: {w}")
    return _config


def reload_config() -> SystemConfig:
    """Force reload configuration from environment."""
    global _config
    _config = None
    return get_config()
