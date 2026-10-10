"""
NEUTRON Cloud Sync

Nightly sync to GCS (JSON summaries only, no raw audio/video).
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import get_settings
from memory.database import get_memory_db
from utils.logging_config import get_logger


class CloudSyncManager:
    """Manages cloud synchronization of memory summaries."""
    
    def __init__(self) -> None:
        self._logger = get_logger("CloudSyncManager")
        self._settings = get_settings()
        self._db = get_memory_db()
        self._client = None
        self._bucket = None
        self._enabled = self._settings.cloud_sync.enabled
    
    async def initialize(self) -> None:
        """Initialize GCS client if enabled."""
        if not self._enabled:
            self._logger.info("Cloud sync disabled")
            return
        
        try:
            from google.cloud import storage
            
            self._client = storage.Client()
            self._bucket = self._client.bucket(self._settings.cloud_sync.gcs_bucket_name)
            self._logger.info("Cloud sync initialized")
        except Exception as e:
            self._logger.error(f"Cloud sync init error: {e}")
            self._enabled = False
    
    async def sync_daily_summary(self) -> bool:
        """Sync daily summary to cloud."""
        if not self._enabled or not self._bucket:
            return False
        
        try:
            summary = await self._generate_daily_summary()
            
            # Create blob name with date
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            blob_name = f"summaries/{date_str}.json"
            
            blob = self._bucket.blob(blob_name)
            blob.upload_from_string(
                json.dumps(summary, indent=2),
                content_type="application/json"
            )
            
            self._logger.info(f"Synced daily summary: {blob_name}")
            return True
        except Exception as e:
            self._logger.error(f"Sync error: {e}")
            return False
    
    async def _generate_daily_summary(self) -> dict[str, Any]:
        """Generate summary of today's memories."""
        await self._db._ensure_connected()
        
        # Get today's episodic memories
        cursor = await self._db._connection.execute(
            """SELECT id, content, summary, emotion_valence, timestamp 
               FROM episodic_memories 
               WHERE DATE(timestamp) = DATE('now')"""
        )
        memories = await cursor.fetchall()
        
        # Get conversation stats
        cursor = await self._db._connection.execute(
            """SELECT COUNT(*) as count, AVG(turn_count) as avg_turns
               FROM conversations 
               WHERE DATE(started_at) = DATE('now')"""
        )
        conv_stats = await cursor.fetchone()
        
        return {
            "sync_id": str(uuid.uuid4()),
            "date": datetime.now(timezone.utc).isoformat(),
            "memory_count": len(memories),
            "memory_summaries": [
                {"summary": m["summary"] or m["content"][:100], "valence": m["emotion_valence"]}
                for m in memories
            ],
            "conversation_count": conv_stats["count"] if conv_stats else 0,
            "avg_turns": conv_stats["avg_turns"] if conv_stats else 0,
        }


__all__ = ["CloudSyncManager"]
