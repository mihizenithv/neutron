"""
NEUTRON Structured Logging Configuration

Provides structured logging with rotation, multiple outputs,
and systemd-compatible formatting.
"""

from __future__ import annotations

import logging
import sys
from functools import lru_cache
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

import structlog
from structlog.types import Processor

from config.settings import get_settings, LogFormat


def _add_log_level(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Add log level to event dict."""
    event_dict["level"] = method_name.upper()
    return event_dict


def _add_timestamp(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Add ISO timestamp to event dict."""
    import datetime
    event_dict["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return event_dict


def _add_caller_info(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Add caller filename and line number."""
    import inspect
    
    # Walk up the stack to find the actual caller
    frame = inspect.currentframe()
    try:
        # Skip structlog internals
        for _ in range(10):
            if frame is None:
                break
            frame = frame.f_back
            if frame is None:
                break
            filename = frame.f_code.co_filename
            if "structlog" not in filename and "logging" not in filename:
                event_dict["caller"] = f"{Path(filename).name}:{frame.f_lineno}"
                break
    finally:
        del frame
    
    return event_dict


def _censor_sensitive_data(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Censor sensitive data like API keys."""
    sensitive_keys = {"api_key", "password", "secret", "token", "credential"}
    
    def censor_value(key: str, value: Any) -> Any:
        key_lower = key.lower()
        for sensitive in sensitive_keys:
            if sensitive in key_lower:
                if isinstance(value, str) and len(value) > 4:
                    return f"{value[:4]}***"
                return "***"
        return value
    
    censored = {}
    for key, value in event_dict.items():
        if isinstance(value, dict):
            censored[key] = {k: censor_value(k, v) for k, v in value.items()}
        else:
            censored[key] = censor_value(key, value)
    
    return censored


def setup_logging() -> None:
    """
    Set up structured logging for NEUTRON.
    
    Configures:
    - Console output (colored for development)
    - File output with rotation (if configured)
    - JSON or console format based on settings
    - Systemd-compatible output (no colors when not TTY)
    """
    settings = get_settings()
    
    # Determine output format
    is_tty = sys.stdout.isatty()
    use_colors = is_tty and settings.logging.format == LogFormat.CONSOLE
    
    # Build processor chain
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        _add_timestamp,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]
    
    # Add caller info in debug mode
    if settings.debug:
        processors.insert(2, _add_caller_info)
    
    # Add sensitive data censoring
    processors.append(_censor_sensitive_data)
    
    # Configure output format
    if settings.logging.format == LogFormat.JSON:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(
            structlog.dev.ConsoleRenderer(
                colors=use_colors,
                exception_formatter=structlog.dev.rich_traceback
                if use_colors else structlog.dev.plain_traceback,
            )
        )
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    log_level = getattr(logging, settings.logging.level)
    
    # Root handler
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(
        "%(message)s" if settings.logging.format == LogFormat.CONSOLE
        else '{"time": "%(asctime)s", "name": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if configured)
    if settings.logging.file_path:
        log_dir = settings.logging.file_path.parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            settings.logging.file_path,
            maxBytes=settings.logging.max_bytes,
            backupCount=settings.logging.backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        
        # Always use JSON for file logs
        file_formatter = logging.Formatter(
            '{"time": "%(asctime)s", "name": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Suppress noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)


@lru_cache(maxsize=100)
def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger for the given name.
    
    Args:
        name: Logger name (typically __name__ of the module)
        
    Returns:
        Configured structlog BoundLogger
    """
    return structlog.get_logger(name)


class LoggerMixin:
    """Mixin class providing a logger property."""
    
    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """Get logger for this class."""
        return get_logger(self.__class__.__name__)


def log_context(**kwargs: Any):
    """
    Context manager for adding context to all log messages within scope.
    
    Usage:
        with log_context(user_id="123", session="abc"):
            logger.info("Processing request")  # Includes user_id and session
    """
    return structlog.contextvars.bound_contextvars(**kwargs)


def bind_logger_context(**kwargs: Any) -> None:
    """Bind context variables to all subsequent log messages."""
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_logger_context() -> None:
    """Clear all context variables."""
    structlog.contextvars.clear_contextvars()


__all__ = [
    "setup_logging",
    "get_logger",
    "LoggerMixin",
    "log_context",
    "bind_logger_context",
    "clear_logger_context",
]
