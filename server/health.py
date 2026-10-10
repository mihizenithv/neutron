"""
NEUTRON Health Check

Health endpoints and watchdog integration.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import APIRouter

from config.constants import VERSION
from config.settings import get_settings
from utils.state import get_state


health_router = APIRouter(tags=["health"])


@health_router.get("/health")
async def health_check() -> dict:
    """Basic health check endpoint."""
    state = get_state()
    health = state.health
    
    return {
        "status": "ok",
        "version": VERSION,
        "mode": state.operation_mode.value,
        "uptime_seconds": health.uptime_seconds,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@health_router.get("/health/detailed")
async def detailed_health() -> dict:
    """Detailed health check with component status."""
    from cortex.orchestrator import get_orchestrator
    from ai.router import get_router
    from speech.pipeline import get_voice_pipeline
    from memory.database import get_memory_db
    
    state = get_state()
    
    cortex = get_orchestrator()
    ai_router = get_router()
    voice = get_voice_pipeline()
    db = get_memory_db()
    
    components = {
        "cortex": cortex._initialized,
        "ai_router": ai_router._initialized,
        "voice_pipeline": voice._initialized,
        "database": db._initialized,
    }
    
    all_healthy = all(components.values())
    
    return {
        "status": "ok" if all_healthy else "degraded",
        "version": VERSION,
        "mode": state.operation_mode.value,
        "components": components,
        "system": {
            "uptime_seconds": state.health.uptime_seconds,
            "memory_mb": state.health.memory_usage_mb,
            "cpu_percent": state.health.cpu_usage,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@health_router.get("/ready")
async def readiness_check() -> dict:
    """Readiness check for startup probes."""
    from cortex.orchestrator import get_orchestrator
    
    cortex = get_orchestrator()
    
    if not cortex._initialized:
        return {"status": "not_ready", "reason": "cortex not initialized"}
    
    return {"status": "ready"}


@health_router.get("/live")
async def liveness_check() -> dict:
    """Liveness check for health probes."""
    return {"status": "alive", "timestamp": time.time()}


__all__ = ["health_router"]
