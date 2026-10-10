import asyncio
import sys
import logging
from pathlib import Path

# Setup path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import get_settings
from memory.database import get_memory_db
from ai.router import get_router
from speech.pipeline import get_voice_pipeline
from cortex.orchestrator import get_orchestrator
from utils.logging_config import setup_logging

setup_logging()
logger = logging.getLogger("SystemVerification")

async def verify_memory():
    logger.info("--- Verifying Memory ---")
    db = get_memory_db()
    await db.initialize()
    
    # Store
    mem_id = await db.store_episodic("Test memory content", importance=0.8)
    logger.info(f"Stored memory: {mem_id}")
    
    # Retrieve
    mem = await db.get_episodic(mem_id)
    if mem and mem["content"] == "Test memory content":
        logger.info("[OK] Memory storage/retrieval verification passed")
    else:
        logger.error("[FAIL] Memory verification failed")

async def verify_ai():
    logger.info("--- Verifying AI Router ---")
    router = get_router()
    await router.initialize()
    
    stats = router.get_stats()
    logger.info(f"AI Router Stats: {stats}")
    
    if "ollama" in [name for name, _ in stats.get("providers", {}).items()]:
        logger.info("[OK] Ollama provider detected")
    else:
        logger.warning("[WARN] Ollama provider not detected")

async def verify_voice():
    logger.info("--- Verifying Voice Pipeline ---")
    voice = get_voice_pipeline()
    try:
        await voice.initialize()
        stats = voice.get_stats()
        logger.info(f"Voice Stats: {stats}")
        
        if stats["stt_available"] and stats["tts_available"]:
            logger.info("[OK] Voice pipeline components available")
        else:
            logger.warning("[WARN] Voice pipeline components incomplete")
            
        await voice.shutdown()
    except Exception as e:
        logger.error(f"[FAIL] Voice pipeline error: {e}")

async def verify_cortex():
    logger.info("--- Verifying Cortex Orchestrator ---")
    cortex = get_orchestrator()
    try:
        await cortex.initialize()
        logger.info("[OK] Cortex initialized successfully")
        await cortex.shutdown()
    except Exception as e:
        logger.error(f"[FAIL] Cortex initialization error: {e}")

async def main():
    logger.info("Starting System Verification...")
    
    try:
        await verify_memory()
        await verify_ai()
        await verify_voice()
        await verify_cortex()
        
        logger.info("\n*** System Verification Complete ***")
    except Exception as e:
        logger.error(f"Verification failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
