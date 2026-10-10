"""
NEUTRON Nano Banana Expression Generator

Uses Google Gemini's image generation (codename "Nano Banana")
to dynamically generate expressive face assets.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
from pathlib import Path
from typing import Any

from config.settings import get_settings
from config.constants import EyeExpression
from utils.logging_config import get_logger
from utils.decorators import cached_async, rate_limit


class NanoBananaExpressions:
    """
    Generates expressive face assets using Gemini's image generation.
    
    Uses the Gemini 2.0 Flash model with native image generation
    (internally known as "Nano Banana") for consistent, emotion-driven
    expressions.
    """
    
    # Expression prompts for different emotional states
    EXPRESSION_PROMPTS = {
        EyeExpression.NEUTRAL: (
            "A friendly robot eye with cyan iris, looking forward neutrally. "
            "Clean digital art style, glowing cyan, dark background. "
            "Minimalist, futuristic, approachable. No text."
        ),
        EyeExpression.HAPPY: (
            "A happy robot eye with bright green iris, slightly squinted from smiling. "
            "Warm glow, cheerful, digital art style, dark background. "
            "Sparkle highlights, curved happy shape. No text."
        ),
        EyeExpression.SAD: (
            "A sad robot eye with blue iris, drooping downward. "
            "Soft blue glow, melancholic, digital art style, dark background. "
            "Gentle, sympathetic expression. No text."
        ),
        EyeExpression.SURPRISED: (
            "A surprised robot eye with orange iris, wide open. "
            "Bright glow, alert, digital art style, dark background. "
            "Dilated pupil, raised shape. No text."
        ),
        EyeExpression.THINKING: (
            "A thinking robot eye with purple iris, looking slightly up-left. "
            "Thoughtful glow, contemplative, digital art style, dark background. "
            "Slight squint, focused. No text."
        ),
        EyeExpression.SLEEPY: (
            "A sleepy robot eye with dim cyan iris, half-closed eyelids. "
            "Soft dim glow, tired, digital art style, dark background. "
            "Heavy eyelids, relaxed. No text."
        ),
        EyeExpression.LISTENING: (
            "A listening robot eye with bright cyan iris, attentive. "
            "Pulsing cyan glow, focused, digital art style, dark background. "
            "Wide open, receptive expression. No text."
        ),
        EyeExpression.SPEAKING: (
            "A speaking robot eye with animated cyan iris, engaged. "
            "Dynamic glow with rings, expressive, digital art style, dark background. "
            "Lively, communicating. No text."
        ),
    }
    
    def __init__(self) -> None:
        self._logger = get_logger("NanoBananaExpressions")
        self._settings = get_settings()
        self._model = None
        self._cache_dir = Path(self._settings.data_dir) / "expressions"
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize Gemini image generation model."""
        api_key = self._settings.ai.gemini_api_key
        
        if not api_key or api_key == "your_gemini_api_key_here":
            self._logger.warning("Gemini API key not configured for image generation")
            self._initialized = False
            return
        
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=api_key)
            
            # Use Gemini 2.0 Flash for image generation (Nano Banana)
            self._model = genai.GenerativeModel("gemini-2.0-flash-exp")
            
            # Create cache directory
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            
            self._initialized = True
            self._logger.info("Nano Banana expression generator initialized")
            
        except ImportError:
            self._logger.warning("google-generativeai not installed")
            self._initialized = False
        except Exception as e:
            self._logger.error(f"Nano Banana init error: {e}")
            self._initialized = False
    
    @rate_limit(calls=10, per=60.0, key="nano_banana")
    async def generate_expression(
        self,
        expression: EyeExpression,
        emotion_context: dict[str, float] | None = None,
    ) -> bytes | None:
        """
        Generate an expression image using Nano Banana.
        
        Args:
            expression: The eye expression type
            emotion_context: Optional emotion values to influence generation
            
        Returns:
            PNG image bytes or None if failed
        """
        if not self._initialized or not self._model:
            return None
        
        # Check cache first
        cache_key = self._get_cache_key(expression, emotion_context)
        cached = await self._get_cached(cache_key)
        if cached:
            return cached
        
        # Build prompt
        base_prompt = self.EXPRESSION_PROMPTS.get(
            expression,
            self.EXPRESSION_PROMPTS[EyeExpression.NEUTRAL]
        )
        
        enhanced_prompt = self._enhance_prompt(base_prompt, emotion_context)
        
        try:
            # Generate image using Gemini
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._model.generate_content(
                    [enhanced_prompt],
                    generation_config={
                        "response_mime_type": "image/png",
                    }
                )
            )
            
            # Extract image data
            if response.parts:
                for part in response.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        image_data = part.inline_data.data
                        if isinstance(image_data, str):
                            image_data = base64.b64decode(image_data)
                        
                        # Cache the result
                        await self._cache_image(cache_key, image_data)
                        
                        self._logger.info(f"Generated expression: {expression.name}")
                        return image_data
            
            self._logger.warning(f"No image in response for {expression.name}")
            return None
            
        except Exception as e:
            self._logger.error(f"Expression generation error: {e}")
            return None
    
    async def generate_all_expressions(self) -> dict[EyeExpression, bytes]:
        """Pre-generate all expression types."""
        results = {}
        
        for expression in EyeExpression:
            if expression in self.EXPRESSION_PROMPTS:
                image = await self.generate_expression(expression)
                if image:
                    results[expression] = image
                await asyncio.sleep(1)  # Rate limiting
        
        return results
    
    def _enhance_prompt(
        self,
        base_prompt: str,
        emotion_context: dict[str, float] | None,
    ) -> str:
        """Enhance prompt with emotion context."""
        if not emotion_context:
            return base_prompt
        
        enhancements = []
        
        valence = emotion_context.get("valence", 0.5)
        arousal = emotion_context.get("arousal", 0.3)
        
        if valence > 0.7:
            enhancements.append("warm, inviting colors")
        elif valence < 0.3:
            enhancements.append("cooler, softer tones")
        
        if arousal > 0.7:
            enhancements.append("intense glow, dynamic energy")
        elif arousal < 0.3:
            enhancements.append("calm, subdued glow")
        
        if enhancements:
            return f"{base_prompt} Style emphasis: {', '.join(enhancements)}."
        
        return base_prompt
    
    def _get_cache_key(
        self,
        expression: EyeExpression,
        emotion_context: dict[str, float] | None,
    ) -> str:
        """Generate cache key for expression."""
        key_parts = [expression.name]
        
        if emotion_context:
            # Quantize emotions to reduce cache variations
            valence = round(emotion_context.get("valence", 0.5) * 10) / 10
            arousal = round(emotion_context.get("arousal", 0.3) * 10) / 10
            key_parts.extend([f"v{valence}", f"a{arousal}"])
        
        key_str = "_".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()[:16]
    
    async def _get_cached(self, cache_key: str) -> bytes | None:
        """Get cached expression image."""
        cache_file = self._cache_dir / f"{cache_key}.png"
        if cache_file.exists():
            return cache_file.read_bytes()
        return None
    
    async def _cache_image(self, cache_key: str, image_data: bytes) -> None:
        """Cache expression image."""
        cache_file = self._cache_dir / f"{cache_key}.png"
        cache_file.write_bytes(image_data)
    
    def get_cached_expressions(self) -> list[str]:
        """List cached expression files."""
        if not self._cache_dir.exists():
            return []
        return [f.stem for f in self._cache_dir.glob("*.png")]


# Singleton accessor
_expression_generator: NanoBananaExpressions | None = None


def get_expression_generator() -> NanoBananaExpressions:
    global _expression_generator
    if _expression_generator is None:
        _expression_generator = NanoBananaExpressions()
    return _expression_generator


__all__ = ["NanoBananaExpressions", "get_expression_generator"]
