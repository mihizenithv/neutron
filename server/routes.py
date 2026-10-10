"""
NEUTRON API Routes

REST endpoints for configuration, status, and commands.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from config.settings import get_settings, OperationMode
from cortex.orchestrator import get_orchestrator
from ai.router import get_router
from speech.pipeline import get_voice_pipeline
from memory.database import get_memory_db
from utils.state import get_state


router = APIRouter()


class QueryRequest(BaseModel):
    text: str
    mode: str | None = None


class QueryResponse(BaseModel):
    response: str
    provider: str | None = None
    processing_time_ms: float
    mode: str


class ModeRequest(BaseModel):
    mode: str


class StatusResponse(BaseModel):
    mode: str
    is_listening: bool
    is_speaking: bool
    emotion: dict
    uptime_seconds: float


@router.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest) -> QueryResponse:
    """Process a text query through the cortex."""
    cortex = get_orchestrator()
    state = get_state()
    
    # Temporarily switch mode if specified
    original_mode = state.operation_mode
    if request.mode:
        try:
            state.operation_mode = OperationMode(request.mode.upper())
        except ValueError:
            raise HTTPException(400, f"Invalid mode: {request.mode}")
    
    try:
        result = await cortex.process(text=request.text)
        
        # Extract response from layer results (executive layer)
        layer_results = result.get("layer_results", {})
        executive_data = layer_results.get("EXECUTIVE", {}).get("data", {})
        response_text = executive_data.get("response") or result.get("response") or ""
        provider_used = executive_data.get("provider_used", "unknown")
        
        return QueryResponse(
            response=response_text if response_text else "I'm processing your request...",
            provider=provider_used,
            processing_time_ms=result.get("processing_time_ms", 0),
            mode=state.operation_mode.value,
        )
    finally:
        if request.mode:
            state.operation_mode = original_mode


@router.get("/status", response_model=StatusResponse)
async def get_status() -> StatusResponse:
    """Get current system status."""
    state = get_state()
    voice = state.voice
    health = state.health
    
    return StatusResponse(
        mode=state.operation_mode.value,
        is_listening=voice.is_listening,
        is_speaking=voice.is_speaking,
        emotion=state.emotion.to_dict(),
        uptime_seconds=health.uptime_seconds,
    )


@router.post("/mode")
async def set_mode(request: ModeRequest) -> dict:
    """Set operation mode."""
    state = get_state()
    try:
        state.operation_mode = OperationMode(request.mode.upper())
        return {"mode": state.operation_mode.value}
    except ValueError:
        raise HTTPException(400, f"Invalid mode: {request.mode}")


@router.get("/stats")
async def get_stats() -> dict:
    """Get system statistics."""
    cortex = get_orchestrator()
    ai_router = get_router()
    voice = get_voice_pipeline()
    db = get_memory_db()
    
    return {
        "cortex": cortex.get_stats(),
        "ai": ai_router.get_stats(),
        "voice": voice.get_stats(),
        "memory": await db.get_stats(),
    }


@router.post("/speak")
async def speak_text(request: QueryRequest) -> dict:
    """Speak text through TTS."""
    voice = get_voice_pipeline()
    await voice.speak(request.text)
    return {"status": "speaking", "text": request.text}


@router.post("/privacy/private-mode")
async def toggle_private_mode(enable: bool = True) -> dict:
    """Toggle private mode."""
    from memory.privacy import PrivacyController
    
    privacy = PrivacyController()
    if enable:
        await privacy.enable_private_mode()
    else:
        await privacy.disable_private_mode()
    
    return {"private_mode": enable}


@router.post("/privacy/forget-last")
async def forget_last() -> dict:
    """Forget the last interaction."""
    from memory.privacy import PrivacyController
    
    privacy = PrivacyController()
    success = await privacy.forget_last()
    return {"success": success}


# ==================== Nano Banana Expression Endpoints ====================

@router.get("/expressions/list")
async def list_expressions() -> dict:
    """List available and cached expressions."""
    from gui.expressions import get_expression_generator
    from config.constants import EyeExpression
    
    generator = get_expression_generator()
    
    return {
        "available": [e.name for e in EyeExpression],
        "cached": generator.get_cached_expressions(),
    }


@router.post("/expressions/generate/{expression}")
async def generate_expression(expression: str) -> dict:
    """Generate a specific expression using Nano Banana."""
    from gui.expressions import get_expression_generator
    from config.constants import EyeExpression
    from fastapi.responses import Response
    
    # Validate expression
    try:
        expr_type = EyeExpression[expression.upper()]
    except KeyError:
        raise HTTPException(400, f"Invalid expression: {expression}")
    
    generator = get_expression_generator()
    
    if not generator._initialized:
        await generator.initialize()
    
    state = get_state()
    emotion_context = state.emotion.to_dict()
    
    image_data = await generator.generate_expression(expr_type, emotion_context)
    
    if image_data:
        return {"success": True, "expression": expression, "size_bytes": len(image_data)}
    else:
        return {"success": False, "error": "Generation failed or unavailable"}


@router.get("/expressions/image/{expression}")
async def get_expression_image(expression: str):
    """Get expression image (from cache or generate)."""
    from gui.expressions import get_expression_generator
    from config.constants import EyeExpression
    from fastapi.responses import Response
    
    try:
        expr_type = EyeExpression[expression.upper()]
    except KeyError:
        raise HTTPException(400, f"Invalid expression: {expression}")
    
    generator = get_expression_generator()
    
    if not generator._initialized:
        await generator.initialize()
    
    image_data = await generator.generate_expression(expr_type)
    
    if image_data:
        return Response(content=image_data, media_type="image/png")
    else:
        raise HTTPException(503, "Expression generation unavailable")


@router.post("/expressions/generate-all")
async def generate_all_expressions() -> dict:
    """Pre-generate all expression types."""
    from gui.expressions import get_expression_generator
    
    generator = get_expression_generator()
    
    if not generator._initialized:
        await generator.initialize()
    
    results = await generator.generate_all_expressions()
    
    return {
        "generated": [e.name for e in results.keys()],
        "count": len(results),
    }


# ==================== Ollama Monitoring & Emotions ====================

@router.post("/monitor")
async def local_monitor(request: QueryRequest) -> dict:
    """Query local Ollama for system monitoring."""
    from ai.router import get_router
    
    ai_router = get_router()
    result = await ai_router.monitor_system(request.text)
    return result


@router.post("/emotion/analyze")
async def analyze_emotion(request: QueryRequest) -> dict:
    """Analyze emotional content of text."""
    from ai.router import get_router
    
    ai_router = get_router()
    emotions = await ai_router.analyze_emotion(request.text)
    
    return {
        "text": request.text[:100],
        "emotions": emotions,
    }


@router.get("/ollama/status")
async def ollama_status() -> dict:
    """Check Ollama availability."""
    from ai.providers.ollama import OllamaProvider
    from config.settings import get_settings
    
    settings = get_settings()
    
    if not settings.ai.ollama_enabled:
        return {"enabled": False, "available": False}
    
    provider = OllamaProvider()
    await provider.initialize()
    health = await provider.health_check()
    
    return {
        "enabled": settings.ai.ollama_enabled,
        "available": health,
        "base_url": settings.ai.ollama_base_url,
        "model": settings.ai.ollama_model,
        "for_monitoring": settings.ai.ollama_for_monitoring,
        "for_emotions": settings.ai.ollama_for_emotions,
    }


# ==================== RAG (Retrieval-Augmented Generation) ====================

@router.get("/rag/count")
async def get_rag_count() -> dict:
    """Get count of documents in RAG system."""
    try:
        from memory.rag import RAGSystem
        rag = RAGSystem.get_instance()
        await rag.initialize()
        return {"count": rag.get_document_count()}
    except Exception as e:
        return {"count": 0, "error": str(e)}


@router.get("/rag/sources")
async def get_rag_sources() -> dict:
    """List all document sources in RAG."""
    try:
        from memory.rag import RAGSystem
        rag = RAGSystem.get_instance()
        await rag.initialize()
        sources = await rag.list_sources()
        return {"sources": sources}
    except Exception as e:
        return {"sources": [], "error": str(e)}


@router.post("/rag/upload")
async def upload_rag_document(file: UploadFile = File(...)) -> dict:
    """Upload a document to the RAG system."""
    try:
        from memory.rag import RAGSystem
        
        rag = RAGSystem.get_instance()
        await rag.initialize()
        
        # Read file content
        content = await file.read()
        text_content = content.decode('utf-8', errors='ignore')
        
        # Add to RAG
        chunks = await rag.add_document(
            content=text_content,
            source=file.filename or "uploaded_file",
            metadata={"content_type": file.content_type}
        )
        
        return {
            "success": True,
            "filename": file.filename,
            "chunks": chunks,
            "total_docs": rag.get_document_count()
        }
    except Exception as e:
        raise HTTPException(500, f"Upload failed: {str(e)}")


@router.post("/rag/query")
async def rag_query(request: QueryRequest) -> dict:
    """Query with RAG augmentation."""
    try:
        from memory.rag import RAGSystem
        
        rag = RAGSystem.get_instance()
        await rag.initialize()
        
        response = await rag.query_with_rag(request.text, get_router())
        
        return {
            "response": response,
            "used_rag": True,
            "doc_count": rag.get_document_count()
        }
    except Exception as e:
        return {"response": f"Error: {str(e)}", "used_rag": False}


@router.delete("/rag/clear")
async def clear_rag() -> dict:
    """Clear all documents from RAG system."""
    try:
        from memory.rag import RAGSystem
        rag = RAGSystem.get_instance()
        await rag.initialize()
        await rag.clear()
        return {"success": True, "message": "RAG cleared"}
    except Exception as e:
        raise HTTPException(500, f"Clear failed: {str(e)}")


# ==================== Memories Endpoint ====================

@router.get("/memories")
async def get_memories() -> dict:
    """Get stored memories."""
    try:
        db = get_memory_db()
        memories = await db.recent_memories(limit=20)
        return {
            "memories": [
                {"text": m.content, "time": str(m.timestamp)}
                for m in memories
            ]
        }
    except Exception:
        return {"memories": []}


# ==================== Vision AI (DeepSeek) ====================

class VisionAnalyzeRequest(BaseModel):
    image: str  # Base64-encoded image
    context: str = "webcam_user_observation"


@router.post("/vision/analyze")
async def analyze_vision(request: VisionAnalyzeRequest) -> dict:
    """Analyze webcam image using LLaVA vision AI."""
    try:
        from vision.vision_ai import get_vision_ai
        
        vision_ai = get_vision_ai()
        await vision_ai.initialize()
        
        result = await vision_ai.analyze(
            image_base64=request.image,
            context=request.context
        )
        
        return {
            "description": result.description,
            "confidence": result.confidence,
            "latency_ms": result.latency_ms,
            "success": result.success,
            "error": result.error,
        }
    except Exception as e:
        return {"description": "", "success": False, "error": str(e)}


__all__ = ["router"]

