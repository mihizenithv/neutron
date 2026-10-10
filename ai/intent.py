"""
NEUTRON Intent Classifier

Classifies user queries for AI provider routing.
"""

from __future__ import annotations

import re
from typing import Any

from config.constants import IntentCategory


class IntentClassifier:
    """Classifies user intent for AI provider routing."""
    
    # Category patterns
    PATTERNS = {
        IntentCategory.EMOTIONAL: [
            r"\b(feel|feeling|felt)\b",
            r"\b(sad|happy|angry|anxious|stressed|worried|scared)\b",
            r"\b(love|hate|miss)\b.*\b(you|me|them)\b",
            r"\b(lonely|depressed|overwhelmed)\b",
            r"\bhow are you\b",
        ],
        IntentCategory.PERSONAL: [
            r"\bremember\b.*\b(when|that|my)\b",
            r"\blast time\b",
            r"\bi told you\b",
            r"\bmy\b.*\b(name|birthday|favorite)\b",
            r"\bdo you know me\b",
        ],
        IntentCategory.REFLECTIVE: [
            r"\bwhat do you think\b",
            r"\bmeaning of\b",
            r"\bphilosophy\b",
            r"\bpurpose of\b",
            r"\bwhy do (we|people|humans)\b",
        ],
        IntentCategory.NEWS: [
            r"\bnews\b",
            r"\blatest\b",
            r"\btoday\b.*\b(happen|happened)\b",
            r"\bcurrent events?\b",
            r"\bwhat('s| is) happening\b",
        ],
        IntentCategory.FACTUAL: [
            r"\bhow (many|much|long|far)\b",
            r"\bwhat is\b.*\b(the|a)\b",
            r"\bwhen (was|did|is)\b",
            r"\bwhere (is|are|was)\b",
            r"\bwho (is|was|are)\b",
            r"\bdefine\b",
        ],
        IntentCategory.SEARCH: [
            r"\bsearch\b",
            r"\bgoogle\b",
            r"\blook up\b",
            r"\bfind\b.*\b(about|for|information)\b",
        ],
        IntentCategory.COMMAND: [
            r"^(stop|mute|unmute|quiet|silence)$",
            r"\bgo (to )?sleep\b",
            r"\bwake up\b",
            r"\bprivate mode\b",
            r"\bforget (this|that|it)\b",
        ],
    }
    
    def __init__(self) -> None:
        self._compiled_patterns: dict[IntentCategory, list[re.Pattern]] = {}
        for category, patterns in self.PATTERNS.items():
            self._compiled_patterns[category] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
    
    def classify(self, text: str) -> tuple[IntentCategory, float]:
        """
        Classify text intent.
        
        Returns:
            Tuple of (IntentCategory, confidence 0-1)
        """
        if not text or not text.strip():
            return IntentCategory.UNKNOWN, 0.0
        
        text_clean = text.strip()
        scores: dict[IntentCategory, float] = {cat: 0.0 for cat in IntentCategory}
        
        for category, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(text_clean):
                    scores[category] += 1.0
        
        # Add heuristic boosts
        if "?" in text_clean:
            scores[IntentCategory.FACTUAL] += 0.3
            scores[IntentCategory.NEWS] += 0.2
        
        word_count = len(text_clean.split())
        if word_count < 5:
            scores[IntentCategory.COMMAND] += 0.5
            scores[IntentCategory.SMALL_TALK] += 0.3
        
        # Find best category
        best_category = max(scores, key=lambda c: scores[c])
        best_score = scores[best_category]
        
        if best_score == 0:
            return IntentCategory.SMALL_TALK, 0.5
        
        confidence = min(1.0, best_score / 3.0)
        return best_category, confidence
    
    def get_provider_for_intent(self, intent: IntentCategory) -> str:
        """Get recommended provider for intent."""
        from config.constants import INTENT_PROVIDER_MAP
        return INTENT_PROVIDER_MAP.get(intent, "gemini")


__all__ = ["IntentClassifier"]
