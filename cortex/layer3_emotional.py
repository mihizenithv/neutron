"""
NEUTRON Cortex Layer 3 - Emotional

Manages continuous emotion state:
- Emotion vector (valence, arousal, trust, fatigue, confidence)
- Decay/hysteresis toward neutral
- Sentiment analysis of input
"""

from __future__ import annotations

import re
from typing import Any

from config.constants import CortexLayer, EmotionVector, NEUTRAL_EMOTION, SystemEvent
from cortex.base import DeepPathLayer, LayerInput, LayerResult


class EmotionalLayer(DeepPathLayer):
    """Layer 3: Emotional state management with decay."""
    
    # Sentiment keywords
    POSITIVE_WORDS = frozenset([
        "love", "great", "awesome", "amazing", "happy", "thanks", "thank",
        "wonderful", "fantastic", "excellent", "good", "nice", "beautiful",
        "excited", "joy", "pleased", "glad", "fun", "best", "appreciate",
    ])
    
    NEGATIVE_WORDS = frozenset([
        "hate", "bad", "terrible", "awful", "sad", "angry", "annoyed",
        "frustrated", "upset", "disappointed", "wrong", "worst", "horrible",
        "stupid", "boring", "sucks", "tired", "stressed", "worried",
    ])
    
    TRUST_POSITIVE = frozenset([
        "trust", "believe", "honest", "reliable", "count on", "depend",
        "faithful", "confident", "sure", "certain",
    ])
    
    TRUST_NEGATIVE = frozenset([
        "lie", "liar", "cheat", "fake", "wrong", "mistake", "distrust",
        "doubt", "suspicious", "sketchy",
    ])
    
    def __init__(self) -> None:
        super().__init__()
        self._last_update_time = 0.0
    
    @property
    def layer(self) -> CortexLayer:
        return CortexLayer.EMOTIONAL
    
    async def process(self, input_data: LayerInput) -> LayerResult:
        text = input_data.text.lower()
        context = input_data.context
        
        # Apply decay first
        self._state.decay_emotion()
        current_emotion = self._state.emotion
        
        # Analyze sentiment from text
        sentiment = self._analyze_sentiment(text)
        
        # Calculate emotion adjustments
        valence_delta = sentiment["valence_delta"]
        arousal_delta = sentiment["arousal_delta"]
        trust_delta = sentiment["trust_delta"]
        
        # Adjust fatigue based on conversation length
        conv = self._state.conversation
        fatigue_delta = 0.0
        if conv.turn_count > 10:
            fatigue_delta = 0.01 * (conv.turn_count / 10)
        
        # Apply adjustments with bounds
        new_emotion = EmotionVector(
            valence=max(0.0, min(1.0, current_emotion.valence + valence_delta)),
            arousal=max(0.0, min(1.0, current_emotion.arousal + arousal_delta)),
            trust=max(0.0, min(1.0, current_emotion.trust + trust_delta)),
            fatigue=max(0.0, min(1.0, current_emotion.fatigue + fatigue_delta)),
            confidence=current_emotion.confidence,  # Updated by other factors
        )
        
        # Update state
        self._state.emotion = new_emotion
        
        # Emit emotion change if significant
        if self._is_significant_change(current_emotion, new_emotion):
            await self.emit(SystemEvent.EMOTION_CHANGE, new_emotion.to_dict())
        
        return LayerResult(
            success=True,
            data={
                "emotion": new_emotion.to_dict(),
                "sentiment": sentiment,
                "previous_emotion": current_emotion.to_dict(),
                "deltas": {
                    "valence": valence_delta,
                    "arousal": arousal_delta,
                    "trust": trust_delta,
                    "fatigue": fatigue_delta,
                },
            },
            confidence=0.8,
            should_propagate=True,
        )
    
    def _analyze_sentiment(self, text: str) -> dict[str, Any]:
        words = set(re.findall(r'\b\w+\b', text))
        
        # Count sentiment words
        positive_count = len(words & self.POSITIVE_WORDS)
        negative_count = len(words & self.NEGATIVE_WORDS)
        trust_pos = len(words & self.TRUST_POSITIVE)
        trust_neg = len(words & self.TRUST_NEGATIVE)
        
        total_sentiment = positive_count + negative_count
        if total_sentiment == 0:
            valence_delta = 0.0
        else:
            valence_delta = (positive_count - negative_count) / (total_sentiment + 5) * 0.2
        
        # Arousal from exclamation marks and caps
        exclamation_count = text.count("!")
        caps_ratio = sum(1 for c in text if c.isupper()) / max(1, len(text))
        arousal_delta = min(0.1, (exclamation_count * 0.02) + (caps_ratio * 0.1))
        
        # Trust delta
        trust_total = trust_pos + trust_neg
        if trust_total == 0:
            trust_delta = 0.0
        else:
            trust_delta = (trust_pos - trust_neg) / (trust_total + 3) * 0.15
        
        return {
            "valence_delta": valence_delta,
            "arousal_delta": arousal_delta,
            "trust_delta": trust_delta,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "is_positive": positive_count > negative_count,
            "is_negative": negative_count > positive_count,
            "is_neutral": positive_count == negative_count,
        }
    
    def _is_significant_change(self, old: EmotionVector, new: EmotionVector) -> bool:
        threshold = 0.1
        return (
            abs(old.valence - new.valence) > threshold or
            abs(old.arousal - new.arousal) > threshold or
            abs(old.trust - new.trust) > threshold
        )


__all__ = ["EmotionalLayer"]
