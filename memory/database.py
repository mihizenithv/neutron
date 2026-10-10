"""
NEUTRON Memory Database

SQLite database manager with connection pooling.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import aiosqlite

from config.settings import get_settings
from utils.logging_config import get_logger


class MemoryDatabase:
    """SQLite database manager for memory storage."""
    
    _instance: "MemoryDatabase | None" = None
    
    def __init__(self, db_path: Path | None = None) -> None:
        self._logger = get_logger("MemoryDatabase")
        settings = get_settings()
        self._db_path = db_path or settings.memory.sqlite_database_path
        self._connection: aiosqlite.Connection | None = None
        self._initialized = False
    
    @classmethod
    def get_instance(cls) -> "MemoryDatabase":
        if cls._instance is None:
            cls._instance = MemoryDatabase()
        return cls._instance
    
    async def initialize(self) -> None:
        """Initialize database and run migrations."""
        if self._initialized:
            return
        
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = await aiosqlite.connect(self._db_path)
        self._connection.row_factory = aiosqlite.Row
        
        # Run schema
        schema_path = Path(__file__).parent / "schema.sql"
        if schema_path.exists():
            schema = schema_path.read_text()
            await self._connection.executescript(schema)
            await self._connection.commit()
        
        self._initialized = True
        self._logger.info(f"Database initialized: {self._db_path}")
    
    async def close(self) -> None:
        """Close database connection."""
        if self._connection:
            await self._connection.close()
        self._initialized = False
    
    async def store_episodic(self, content: str, **kwargs) -> str:
        """Store episodic memory."""
        await self._ensure_connected()
        
        memory_id = str(uuid.uuid4())
        await self._connection.execute(
            """INSERT INTO episodic_memories 
               (id, content, summary, emotion_valence, emotion_arousal, importance, tags, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                memory_id,
                content,
                kwargs.get("summary", ""),
                kwargs.get("valence", 0.5),
                kwargs.get("arousal", 0.3),
                kwargs.get("importance", 0.5),
                str(kwargs.get("tags", [])),
                str(kwargs.get("metadata", {})),
            )
        )
        await self._connection.commit()
        return memory_id
    
    async def get_episodic(self, memory_id: str) -> dict | None:
        """Get episodic memory by ID."""
        await self._ensure_connected()
        
        cursor = await self._connection.execute(
            "SELECT * FROM episodic_memories WHERE id = ?", (memory_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    
    async def search_episodic(self, query: str, limit: int = 10) -> list[dict]:
        """Search episodic memories by content."""
        await self._ensure_connected()
        
        cursor = await self._connection.execute(
            """SELECT * FROM episodic_memories 
               WHERE content LIKE ? 
               ORDER BY timestamp DESC LIMIT ?""",
            (f"%{query}%", limit)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    
    async def store_conversation_turn(
        self,
        conversation_id: str,
        role: str,
        content: str,
        **kwargs
    ) -> str:
        """Store a conversation turn."""
        await self._ensure_connected()
        
        # Get turn number
        cursor = await self._connection.execute(
            "SELECT MAX(turn_number) FROM conversation_turns WHERE conversation_id = ?",
            (conversation_id,)
        )
        row = await cursor.fetchone()
        turn_number = (row[0] or 0) + 1
        
        turn_id = str(uuid.uuid4())
        await self._connection.execute(
            """INSERT INTO conversation_turns 
               (id, conversation_id, turn_number, role, content, emotion_valence, emotion_arousal, intent)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                turn_id,
                conversation_id,
                turn_number,
                role,
                content,
                kwargs.get("valence"),
                kwargs.get("arousal"),
                kwargs.get("intent"),
            )
        )
        
        # Update conversation turn count
        await self._connection.execute(
            "UPDATE conversations SET turn_count = ?, ended_at = CURRENT_TIMESTAMP WHERE id = ?",
            (turn_number, conversation_id)
        )
        await self._connection.commit()
        return turn_id
    
    async def start_conversation(self, topic: str = "") -> str:
        """Start a new conversation."""
        await self._ensure_connected()
        
        conv_id = str(uuid.uuid4())
        await self._connection.execute(
            "INSERT INTO conversations (id, topic) VALUES (?, ?)",
            (conv_id, topic)
        )
        await self._connection.commit()
        return conv_id
    
    async def forget_memory(self, memory_id: str) -> bool:
        """Delete a memory (privacy command)."""
        await self._ensure_connected()
        
        await self._connection.execute(
            "DELETE FROM episodic_memories WHERE id = ?", (memory_id,)
        )
        
        # Log privacy action
        await self._connection.execute(
            "INSERT INTO privacy_log (id, action, target_type, target_id) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), "forget", "episodic", memory_id)
        )
        await self._connection.commit()
        return True
    
    async def forget_last_turn(self, conversation_id: str) -> bool:
        """Delete the last conversation turn."""
        await self._ensure_connected()
        
        cursor = await self._connection.execute(
            """SELECT id FROM conversation_turns 
               WHERE conversation_id = ? 
               ORDER BY turn_number DESC LIMIT 1""",
            (conversation_id,)
        )
        row = await cursor.fetchone()
        
        if row:
            await self._connection.execute(
                "DELETE FROM conversation_turns WHERE id = ?", (row[0],)
            )
            await self._connection.commit()
            return True
        return False
    
    async def get_stats(self) -> dict[str, Any]:
        """Get database statistics."""
        await self._ensure_connected()
        
        stats = {}
        for table in ["episodic_memories", "semantic_facts", "conversations"]:
            cursor = await self._connection.execute(f"SELECT COUNT(*) FROM {table}")
            row = await cursor.fetchone()
            stats[table] = row[0] if row else 0
        
        return stats
    
    async def _ensure_connected(self) -> None:
        if not self._initialized:
            await self.initialize()


@lru_cache()
def get_memory_db() -> MemoryDatabase:
    return MemoryDatabase.get_instance()


__all__ = ["MemoryDatabase", "get_memory_db"]
