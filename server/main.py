"""
NEUTRON FastAPI Server

Main server application with lifecycle management.
"""

from __future__ import annotations

import asyncio
import random
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from config.settings import get_settings
from config.constants import GREETING_PHRASES, VERSION, GUIState, SystemEvent
from cortex.orchestrator import get_orchestrator
from ai.router import get_router
from speech.pipeline import get_voice_pipeline
from memory.database import get_memory_db
from server.routes import router as api_router
from server.websocket import websocket_router
from server.health import health_router
from utils.logging_config import setup_logging, get_logger
from utils.events import get_event_bus
from utils.state import get_state


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    logger = get_logger("Server")
    logger.info(f"NEUTRON v{VERSION} starting...")
    
    state = get_state()
    state.gui_state = GUIState.BOOTING
    
    try:
        # Initialize components
        event_bus = get_event_bus()
        await event_bus.start()
        
        # Subscribe to connection events for greeting
        event_bus.subscribe(SystemEvent.CLIENT_CONNECTED, handle_client_connected)
        
        db = get_memory_db()
        await db.initialize()
        
        ai_router = get_router()
        await ai_router.initialize()
        
        cortex = get_orchestrator()
        cortex.set_ai_router(ai_router)
        await cortex.initialize()
        
        voice = get_voice_pipeline()
        voice.set_transcription_handler(process_transcription)
        await voice.initialize()
        await voice.start()  # Start microphone listening
        logger.info("Voice pipeline started - listening for wake word")
        
        # Vision is handled on-demand via /api/vision/analyze (LLaVA)
        logger.info("Vision: on-demand LLaVA via /api/vision/analyze")
        
        state.gui_state = GUIState.IDLE
        logger.info(f"NEUTRON ready! Greeting: {random.choice(GREETING_PHRASES)}")
        
        yield
        
    finally:
        logger.info("NEUTRON shutting down...")
        
        # Vision is on-demand, no shutdown needed
        
        voice = get_voice_pipeline()
        await voice.shutdown()
        
        cortex = get_orchestrator()
        await cortex.shutdown()
        
        ai_router = get_router()
        await ai_router.shutdown()
        
        db = get_memory_db()
        await db.close()
        
        event_bus = get_event_bus()
        await event_bus.stop()
        
        logger.info("NEUTRON shutdown complete")


async def process_transcription(text: str) -> str:
    """Process transcription through cortex and return response."""
    cortex = get_orchestrator()
    result = await cortex.process(text=text)
    return result.get("response", "")


async def handle_client_connected(data: dict) -> None:
    """Greet user on connection."""
    logger = get_logger("Server")
    logger.info("Client connected! Sending greeting...")
    
    # Wait a moment for UI to fade in
    await asyncio.sleep(1.0)
    
    voice = get_voice_pipeline()
    if not voice.get_stats()["speaking"]:
        greeting = random.choice(GREETING_PHRASES)
        await voice.speak(greeting)


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    setup_logging()
    settings = get_settings()
    
    app = FastAPI(
        title="NEUTRON",
        description="Personal Assistant Robot API",
        version=VERSION,
        lifespan=lifespan,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.server.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger = get_logger("Server")
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(exc)},
        )
    
    # Include routers
    app.include_router(api_router, prefix="/api")
    app.include_router(websocket_router)
    app.include_router(health_router)
    
    # Serve GUI static files
    gui_path = Path(__file__).parent.parent / "gui"
    if gui_path.exists():
        app.mount("/", StaticFiles(directory=str(gui_path), html=True), name="gui")
    
    return app


def run() -> None:
    """Run the server."""
    import uvicorn
    settings = get_settings()
    
    uvicorn.run(
        "server.main:create_app",
        factory=True,
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug",
    )


if __name__ == "__main__":
    run()
