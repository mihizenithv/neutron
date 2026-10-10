"""
NEUTRON Memory Embeddings

Local embeddings generation using sentence-transformers.
"""

from __future__ import annotations

import asyncio
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from config.settings import get_settings
from utils.logging_config import get_logger


class EmbeddingsManager:
    """Manages local embeddings generation and storage."""
    
    _instance: "EmbeddingsManager | None" = None
    
    def __init__(self) -> None:
        self._logger = get_logger("EmbeddingsManager")
        self._settings = get_settings()
        self._model = None
        self._initialized = False
    
    @classmethod
    def get_instance(cls) -> "EmbeddingsManager":
        if cls._instance is None:
            cls._instance = EmbeddingsManager()
        return cls._instance
    
    async def initialize(self) -> None:
        """Initialize embeddings model."""
        if self._initialized:
            return
        
        try:
            from sentence_transformers import SentenceTransformer
            
            model_name = self._settings.memory.embeddings_model
            self._model = await asyncio.get_event_loop().run_in_executor(
                None, lambda: SentenceTransformer(model_name)
            )
            self._initialized = True
            self._logger.info(f"Embeddings model loaded: {model_name}")
        except ImportError:
            self._logger.warning("sentence-transformers not installed")
        except Exception as e:
            self._logger.error(f"Embeddings init error: {e}")
    
    async def embed(self, text: str) -> np.ndarray | None:
        """Generate embedding for text."""
        if not self._initialized or self._model is None:
            return None
        
        try:
            embedding = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._model.encode(text, convert_to_numpy=True)
            )
            return embedding
        except Exception as e:
            self._logger.error(f"Embedding error: {e}")
            return None
    
    async def embed_batch(self, texts: list[str]) -> list[np.ndarray] | None:
        """Generate embeddings for multiple texts."""
        if not self._initialized or self._model is None:
            return None
        
        try:
            embeddings = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._model.encode(texts, convert_to_numpy=True)
            )
            return list(embeddings)
        except Exception as e:
            self._logger.error(f"Batch embedding error: {e}")
            return None
    
    def similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(vec1, vec2) / (norm1 * norm2))


@lru_cache()
def get_embeddings_manager() -> EmbeddingsManager:
    return EmbeddingsManager.get_instance()


__all__ = ["EmbeddingsManager", "get_embeddings_manager"]
