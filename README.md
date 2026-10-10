# NEUTRON: Local-First Cognitive Assistant

A personal AI companion with a seven-layer "cortex", persistent memory, a voice pipeline and an
animated-eyes web GUI. It routes each request to the right model (Gemini, Perplexity, a local
Ollama model, or a fully offline fallback) and keeps working when the network or hardware isn't
there.

> Built with Google Antigravity as a personal exploration of layered cognitive architectures for
> assistants. Runs headless on a laptop; designed to be portable to a Raspberry Pi.

## Highlights

- **Seven-layer cortex**: Reflex, Sensory, Emotional, Memory, Motivation, Social, Executive.
  `NORMAL` mode runs only the fast layers (1-2); `EXTREME` mode runs all seven.
- **Multi-provider AI router**: intent classification, per-provider rate limits, response cache,
  automatic fallback across Gemini, Perplexity, Ollama and an offline provider.
- **Persistent memory**: SQLite episodic memory with privacy controls (private mode, forget-last).
- **Local RAG**: upload documents and ask questions; dependency-free chunking and IDF retrieval.
- **Voice pipeline**: wake word, Vosk STT, cortex, TTS, with barge-in. Optional; the server boots
  without any audio libraries.
- **Expressive GUI**: canvas-rendered eyes and mouth driven by an emotion vector, over WebSocket.

## Architecture

```
 mic -> wake word -> STT -> Cortex orchestrator -> AI router -> Gemini / Perplexity / Ollama / offline
                              |   L1 reflex . L2 sensory . L3 emotional . L4 memory
                              |   L5 motivation . L6 social . L7 executive
                              +-> Memory (SQLite) . RAG store . emotion state
                              |
                  GUI (WebSocket) <-> eyes, mouth, particles, webcam bridge
                              |
                             TTS -> speaker
```

| Folder | Responsibility |
|---|---|
| `cortex/` | The seven layers and the orchestrator that sequences them per mode |
| `ai/` | Router, intent classifier, response cache, provider adapters |
| `speech/` | Wake word, STT (Vosk), TTS, barge-in, pipeline |
| `memory/` | SQLite store, embeddings, retrieval, local RAG |
| `server/` | FastAPI app, REST routes, WebSocket, health probes |
| `gui/` | Browser UI (eyes, mouth, particles, webcam bridge) |
| `config/`, `utils/` | Settings, constants, events, state, logging |
| `tests/` | Pytest suite (config, state, providers, RAG) |

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env                 # add GEMINI_API_KEY and/or PERPLEXITY_API_KEY (optional)
python -m server.main                # http://localhost:8000
```

With no API keys the router falls back to the offline provider, so the app still runs.

Optional extras:

```bash
pip install -r requirements-voice.txt     # voice + embeddings (needs PortAudio)
python scripts/download_vosk_model.py     # fetch the small English Vosk model
```

Local models via [Ollama](https://ollama.com): set `OLLAMA_ENABLED=true` and `OLLAMA_MODEL` in `.env`.

## API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/query` | Send text through the cortex |
| `GET` | `/api/status`, `/api/stats` | Mode, emotion, uptime, router stats |
| `POST` | `/api/mode` | Switch `NORMAL` / `EXTREME` |
| `POST` | `/api/rag/upload`, `/api/rag/query` | Add a document / ask with retrieval |
| `GET` | `/api/rag/count`, `/api/rag/sources` | Inspect the knowledge base |
| `DELETE` | `/api/rag/clear` | Wipe the knowledge base |
| `GET` | `/api/memories` | Recent stored memories |
| `POST` | `/api/privacy/private-mode`, `/api/privacy/forget-last` | Privacy controls |
| `POST` | `/api/vision/analyze` | Describe a webcam frame (LLaVA via Ollama) |
| `GET` | `/health`, `/ready`, `/live` | Probes |
| `WS` | `/ws` | GUI event stream |

## Tests

```bash
pytest
```

## Notes and limitations

- Wake word and STT require the optional voice dependencies and a downloaded Vosk model.
- Vector search over memories is a stub; text search is used today (see `memory/retrieval.py`).
- Cloud sync (`memory/cloud_sync.py`) is optional and off by default.

## License

MIT
