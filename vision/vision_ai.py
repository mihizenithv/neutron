"""
NEUTRON Vision AI — LLaVA webcam analysis.

Sends webcam frames to LLaVA and returns real descriptions of what it sees.
"""

from __future__ import annotations

import time
import httpx
from dataclasses import dataclass
from typing import Optional

from utils.logging_config import get_logger

_logger = get_logger("VisionAI")
_client = httpx.AsyncClient(timeout=120.0)
_model: Optional[str] = None
_initialized = False

OLLAMA_URL = "http://localhost:11434"


@dataclass
class VisionAnalysis:
    description: str
    confidence: float
    latency_ms: float
    success: bool
    error: Optional[str] = None


async def _find_llava() -> Optional[str]:
    """Find LLaVA model in Ollama."""
    try:
        r = await _client.get(f"{OLLAMA_URL}/api/tags")
        if r.status_code == 200:
            models = [m.get("name", "") for m in r.json().get("models", [])]
            _logger.info(f"Ollama models: {models}")
            for name in models:
                if "llava" in name.lower():
                    return name
            _logger.warning("LLaVA not found. Run: ollama pull llava:7b")
    except Exception as e:
        _logger.error(f"Cannot reach Ollama: {e}")
    return None


async def analyze(image_base64: str, context: str = "webcam") -> VisionAnalysis:
    """
    Analyze a webcam frame with LLaVA.

    Args:
        image_base64: Base64-encoded JPEG from webcam
        context: Hint for what we're analyzing

    Returns:
        VisionAnalysis with real description of what LLaVA sees
    """
    global _model, _initialized

    start = time.time()

    # Initialize once
    if not _initialized:
        _model = await _find_llava()
        _initialized = True

    if not _model:
        return VisionAnalysis(
            description="",
            confidence=0.0,
            latency_ms=0,
            success=False,
            error="LLaVA not available. Run: ollama pull llava:7b",
        )

    prompt = (
        "Look at this webcam image and describe what you see in 1-2 sentences. "
        "Focus on: what the person is doing, what they're wearing, their posture. "
        "Be specific and natural. Example: 'I see you typing on your laptop, "
        "wearing a blue hoodie, looking focused.'"
    )

    try:
        r = await _client.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": _model,
                "prompt": prompt,
                "images": [image_base64],
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": 120},
            },
        )

        latency = (time.time() - start) * 1000

        if r.status_code == 200:
            description = r.json().get("response", "").strip()

            # Strip DeepSeek thinking tokens if present
            if "<think>" in description and "</think>" in description:
                description = description.split("</think>")[-1].strip()

            _logger.info(f'LLaVA: "{description[:120]}" ({latency:.0f}ms)')

            if not description:
                description = "I can see you, but couldn't describe the scene clearly."

            return VisionAnalysis(
                description=description,
                confidence=0.85,
                latency_ms=latency,
                success=True,
            )
        else:
            _logger.error(f"LLaVA HTTP {r.status_code}")
            return VisionAnalysis(
                description="",
                confidence=0.0,
                latency_ms=latency,
                success=False,
                error=f"HTTP {r.status_code}",
            )

    except httpx.TimeoutException:
        _logger.warning("LLaVA timed out (>120s)")
        return VisionAnalysis(
            description="",
            confidence=0.0,
            latency_ms=(time.time() - start) * 1000,
            success=False,
            error="Timeout",
        )
    except Exception as e:
        _logger.error(f"Vision error: {e}")
        return VisionAnalysis(
            description="",
            confidence=0.0,
            latency_ms=(time.time() - start) * 1000,
            success=False,
            error=str(e),
        )


# Convenience class for backwards compatibility with routes.py
class VisionAI:
    async def initialize(self) -> bool:
        global _model, _initialized
        if not _initialized:
            _model = await _find_llava()
            _initialized = True
        return _model is not None

    async def analyze(self, image_base64: str, context: str = "webcam") -> VisionAnalysis:
        return await analyze(image_base64, context)


def get_vision_ai() -> VisionAI:
    """Get VisionAI instance (stateless module-level functions do the real work)."""
    return VisionAI()


__all__ = ["VisionAI", "get_vision_ai", "VisionAnalysis", "analyze"]
