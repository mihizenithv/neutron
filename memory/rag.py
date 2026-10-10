"""
NEUTRON RAG

Small, dependency-free retrieval-augmented generation store.

Documents are split into overlapping word chunks and persisted to a JSON file.
Retrieval scores chunks by IDF-weighted term overlap, which is good enough for a
local personal knowledge base and keeps the server bootable without any embedding
model. `query_with_rag` hands the best chunks to whichever AI provider the router
selects.
"""

from __future__ import annotations

import json
import math
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any

from utils.logging_config import get_logger

_WORD = re.compile(r"[a-z0-9']+")
_STOPWORDS = frozenset(
    "a an and are as at be by for from has have in is it its of on or that the this to was were will with".split()
)
_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "rag" / "documents.json"


def _tokens(text: str) -> list[str]:
    return [t for t in _WORD.findall(text.lower()) if t not in _STOPWORDS and len(t) > 1]


class RAGSystem:
    """Local document store with keyword retrieval."""

    _instance: "RAGSystem | None" = None

    def __init__(self, path: Path | None = None, chunk_words: int = 120, overlap: int = 20) -> None:
        self._logger = get_logger("RAG")
        self._path = Path(path) if path else _DEFAULT_PATH
        self._chunk_words = chunk_words
        self._overlap = overlap
        self._chunks: list[dict[str, Any]] = []
        self._initialized = False

    @classmethod
    def get_instance(cls) -> "RAGSystem":
        if cls._instance is None:
            cls._instance = RAGSystem()
        return cls._instance

    async def initialize(self) -> None:
        if self._initialized:
            return
        if self._path.exists():
            try:
                self._chunks = json.loads(self._path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                self._logger.warning(f"Could not load RAG store, starting empty: {exc}")
                self._chunks = []
        self._initialized = True

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._chunks, ensure_ascii=False), encoding="utf-8")

    def _split(self, text: str) -> list[str]:
        words = text.split()
        if not words:
            return []
        step = max(1, self._chunk_words - self._overlap)
        return [" ".join(words[i : i + self._chunk_words]) for i in range(0, len(words), step)]

    async def add_document(self, content: str, source: str, metadata: dict | None = None) -> int:
        """Add a document (replacing any previous version of `source`). Returns chunk count."""
        await self.initialize()
        self._chunks = [c for c in self._chunks if c["source"] != source]
        pieces = self._split(content)
        now = time.time()
        for index, piece in enumerate(pieces):
            self._chunks.append(
                {"source": source, "index": index, "text": piece, "metadata": metadata or {}, "added": now}
            )
        self._save()
        return len(pieces)

    def get_document_count(self) -> int:
        """Number of distinct documents."""
        return len({c["source"] for c in self._chunks})

    async def list_sources(self) -> list[dict[str, Any]]:
        await self.initialize()
        counts = Counter(c["source"] for c in self._chunks)
        return [{"source": source, "chunks": n} for source, n in sorted(counts.items())]

    async def search(self, query: str, limit: int = 4) -> list[dict[str, Any]]:
        await self.initialize()
        query_terms = set(_tokens(query))
        if not query_terms or not self._chunks:
            return []
        doc_freq: Counter[str] = Counter()
        chunk_terms: list[set[str]] = []
        for chunk in self._chunks:
            terms = set(_tokens(chunk["text"]))
            chunk_terms.append(terms)
            doc_freq.update(terms)
        total = len(self._chunks)
        scored: list[tuple[float, dict[str, Any]]] = []
        for chunk, terms in zip(self._chunks, chunk_terms):
            score = sum(math.log(1 + total / doc_freq[t]) for t in query_terms & terms)
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [{**chunk, "score": round(score, 3)} for score, chunk in scored[:limit]]

    async def query_with_rag(self, query: str, router: Any) -> str:
        """Answer `query` using retrieved context via the AI router."""
        hits = await self.search(query)
        if not hits:
            result = await router.route(query)
            return result.get("text", "")
        context = "\n\n".join(f"[{h['source']}] {h['text']}" for h in hits)
        prompt = (
            "Answer the question using only the context below. If the context does not "
            "contain the answer, say so.\n\n"
            f"Context:\n{context}\n\nQuestion: {query}"
        )
        result = await router.route(prompt)
        return result.get("text", "")

    async def clear(self) -> None:
        await self.initialize()
        self._chunks = []
        self._save()


__all__ = ["RAGSystem"]
