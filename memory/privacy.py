"""
NEUTRON Privacy Controls

Handles "forget this" and "private mode" commands.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from memory.database import get_memory_db
from utils.logging_config import get_logger
from utils.state import get_state, PrivacyMode
from utils.events import EventEmitter
from config.constants import SystemEvent


class PrivacyController(EventEmitter):
    """Controls privacy features for memory system."""
    
    def __init__(self) -> None:
        self._logger = get_logger("PrivacyController")
        self._db = get_memory_db()
        self._state = get_state()
        self._current_conversation_id: str | None = None
    
    def set_conversation(self, conversation_id: str) -> None:
        """Set current conversation for forget commands."""
        self._current_conversation_id = conversation_id
    
    async def enable_private_mode(self) -> None:
        """Enable private mode (no memory storage)."""
        self._state.privacy_mode = PrivacyMode.PRIVATE
        await self._log_privacy_action("private_mode_on")
        await self.emit(SystemEvent.PRIVATE_MODE_ON, {})
        self._logger.info("Private mode enabled")
    
    async def disable_private_mode(self) -> None:
        """Disable private mode."""
        self._state.privacy_mode = PrivacyMode.NORMAL
        await self._log_privacy_action("private_mode_off")
        await self.emit(SystemEvent.PRIVATE_MODE_OFF, {})
        self._logger.info("Private mode disabled")
    
    async def forget_last(self) -> bool:
        """Forget the last interaction."""
        if not self._current_conversation_id:
            self._logger.warning("No conversation to forget")
            return False
        
        success = await self._db.forget_last_turn(self._current_conversation_id)
        if success:
            await self._log_privacy_action("forget_last", "conversation", self._current_conversation_id)
            await self.emit(SystemEvent.FORGET_COMMAND, {"type": "last_turn"})
            self._logger.info("Last interaction forgotten")
        return success
    
    async def forget_memory(self, memory_id: str) -> bool:
        """Forget a specific memory."""
        success = await self._db.forget_memory(memory_id)
        if success:
            await self._log_privacy_action("forget", "memory", memory_id)
            await self.emit(SystemEvent.FORGET_COMMAND, {"type": "memory", "id": memory_id})
            self._logger.info(f"Memory forgotten: {memory_id}")
        return success
    
    @property
    def is_private(self) -> bool:
        """Check if in private mode."""
        return self._state.privacy_mode == PrivacyMode.PRIVATE
    
    async def _log_privacy_action(
        self,
        action: str,
        target_type: str | None = None,
        target_id: str | None = None
    ) -> None:
        """Log privacy action for audit."""
        await self._db._ensure_connected()
        await self._db._connection.execute(
            "INSERT INTO privacy_log (id, action, target_type, target_id) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), action, target_type, target_id)
        )
        await self._db._connection.commit()


__all__ = ["PrivacyController"]
