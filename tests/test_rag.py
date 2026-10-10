"""Tests for the local RAG store and the router's failure fallback."""

import pytest

from memory.rag import RAGSystem


@pytest.fixture()
def rag(tmp_path):
    return RAGSystem(path=tmp_path / "docs.json", chunk_words=20, overlap=5)


class _FakeRouter:
    def __init__(self):
        self.prompts = []

    async def route(self, prompt, **_):
        self.prompts.append(prompt)
        return {"text": "ok"}


@pytest.mark.asyncio
async def test_add_search_and_replace(rag):
    chunks = await rag.add_document("Neutron speaks using the Piper text to speech engine.", "a.txt")
    assert chunks == 1
    hits = await rag.search("what does neutron use to speak with piper")
    assert hits and hits[0]["source"] == "a.txt"

    await rag.add_document("Completely different content about gardening.", "a.txt")
    assert rag.get_document_count() == 1
    assert await rag.search("piper") == []


@pytest.mark.asyncio
async def test_persistence_roundtrip(tmp_path):
    first = RAGSystem(path=tmp_path / "d.json")
    await first.add_document("alpha beta gamma delta", "doc")
    second = RAGSystem(path=tmp_path / "d.json")
    await second.initialize()
    assert second.get_document_count() == 1


@pytest.mark.asyncio
async def test_query_injects_context(rag):
    await rag.add_document("The reactor core temperature limit is 400 degrees.", "ops.txt")
    router = _FakeRouter()
    answer = await rag.query_with_rag("what is the reactor temperature limit", router)
    assert answer == "ok"
    assert "400 degrees" in router.prompts[0]


@pytest.mark.asyncio
async def test_clear(rag):
    await rag.add_document("some text here", "x")
    await rag.clear()
    assert rag.get_document_count() == 0
