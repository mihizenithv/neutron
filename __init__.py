"""
NEUTRON Package

Production-grade personal assistant robot for Raspberry Pi 4.
"""

__version__ = "1.0.0"

# Core imports for convenience
from config.settings import get_settings, OperationMode
from config.constants import VERSION, SYSTEM_NAME
from utils.state import get_state
from utils.events import get_event_bus
from utils.logging_config import get_logger

__all__ = [
    "__version__",
    "get_settings",
    "OperationMode",
    "get_state",
    "get_event_bus",
    "get_logger",
    "VERSION",
    "SYSTEM_NAME",
]
