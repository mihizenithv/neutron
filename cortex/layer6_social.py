"""
NEUTRON Cortex Layer 6 - Social

Conversation observation and interrupt decision making.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Any

from config.constants import (
    CortexLayer, SystemEvent,
    INTERRUPT_CONFIDENCE_THRESHOLD, CONVERSATION_PAUSE_THRESHOLD_MS,
)
from cortex.base import DeepPathLayer, LayerInput, LayerResult


@dataclass
class ConversationTurn:
    """Single turn in conversation history."""
    text: str
    timestamp: float
    is_user: bool
    speaker_id: int = 0


class SocialLayer(DeepPathLayer):
    """Layer 6: Social cortex for conversation observation and interrupts."""
    
    def __init__(self, max_history: int = 50) -> None:
        super().__init__()
        self._conversation_history: deque[ConversationTurn] = deque(maxlen=max_history)
        self._last_user_speech_time = 0.0
        self._interrupt_count = 0
        self._successful_interrupts = 0
    
    @property
    def layer(self) -> CortexLayer:
        return CortexLayer.SOCIAL
    
    async def process(self, input_data: LayerInput) -> LayerResult:
        text = input_data.text
        context = input_data.context
        current_time = time.time() * 1000
        
        result_data: dict[str, Any] = {
            "should_interrupt": False,
            "interrupt_confidence": 0.0,
            "interrupt_reason": None,
            "conversation_state": "active",
            "pause_detected": False,
            "topic_relevance": 0.0,
        }
        
        # Add to conversation history
        if text:
            self._conversation_history.append(ConversationTurn(
                text=text,
                timestamp=current_time,
                is_user=True,
                speaker_id=context.get("speaker_id", 0),
            ))
            self._last_user_speech_time = current_time
        
        # Detect conversation pause
        time_since_speech = current_time - self._last_user_speech_time
        result_data["pause_detected"] = time_since_speech > CONVERSATION_PAUSE_THRESHOLD_MS
        
        # Analyze conversation state
        conv_analysis = self._analyze_conversation()
        result_data["conversation_state"] = conv_analysis["state"]
        result_data["topic_relevance"] = conv_analysis["topic_relevance"]
        
        # Evaluate interrupt opportunity
        interrupt_eval = self._evaluate_interrupt(text, context, conv_analysis)
        result_data["should_interrupt"] = interrupt_eval["should_interrupt"]
        result_data["interrupt_confidence"] = interrupt_eval["confidence"]
        result_data["interrupt_reason"] = interrupt_eval["reason"]
        
        if result_data["should_interrupt"]:
            self._interrupt_count += 1
            await self.emit(
                SystemEvent.INTERRUPT_DECISION,
                {"reason": interrupt_eval["reason"], "confidence": interrupt_eval["confidence"]},
            )
        
        return LayerResult(
            success=True,
            data=result_data,
            confidence=result_data["interrupt_confidence"],
            should_propagate=True,
            should_respond=result_data["should_interrupt"],
        )
    
    def _analyze_conversation(self) -> dict[str, Any]:
        """Analyze current conversation state."""
        if not self._conversation_history:
            return {"state": "idle", "topic_relevance": 0.0, "speaker_count": 0}
        
        recent = list(self._conversation_history)[-10:]
        
        # Count speakers
        speaker_ids = set(turn.speaker_id for turn in recent)
        
        # Determine state
        if len(recent) < 2:
            state = "starting"
        elif len(speaker_ids) > 1:
            state = "multi_party"
        else:
            state = "one_on_one"
        
        # Simple topic relevance (mentions of NEUTRON or direct address)
        topic_relevance = 0.0
        for turn in recent:
            text_lower = turn.text.lower()
            if "neutron" in text_lower:
                topic_relevance += 0.3
            if any(word in text_lower for word in ["you", "your", "help"]):
                topic_relevance += 0.1
        
        topic_relevance = min(1.0, topic_relevance)
        
        return {
            "state": state,
            "topic_relevance": topic_relevance,
            "speaker_count": len(speaker_ids),
            "turn_count": len(recent),
        }
    
    def _evaluate_interrupt(self, text: str, context: dict, analysis: dict) -> dict[str, Any]:
        """Evaluate whether to interrupt conversation."""
        result = {
            "should_interrupt": False,
            "confidence": 0.0,
            "reason": None,
        }
        
        # Never interrupt in multi-party unless directly addressed
        if analysis["state"] == "multi_party" and analysis["topic_relevance"] < 0.5:
            result["reason"] = "multi-party conversation, not addressed"
            return result
        
        # Calculate interrupt confidence
        confidence = 0.0
        reasons = []
        
        # Direct address boost
        if text and "neutron" in text.lower():
            confidence += 0.5
            reasons.append("directly addressed")
        
        # Question directed at NEUTRON
        if text and "?" in text and analysis["topic_relevance"] > 0.3:
            confidence += 0.3
            reasons.append("question detected")
        
        # Long pause in conversation
        if analysis.get("pause_detected", False):
            confidence += 0.1
            reasons.append("pause detected")
        
        # Help request
        if text and any(w in text.lower() for w in ["help", "can you", "please"]):
            confidence += 0.2
            reasons.append("help requested")
        
        # Urgent keywords
        if text and any(w in text.lower() for w in ["urgent", "emergency", "important", "asap"]):
            confidence += 0.3
            reasons.append("urgency detected")
        
        result["confidence"] = min(1.0, confidence)
        result["reason"] = ", ".join(reasons) if reasons else None
        
        # Only interrupt if above threshold
        if confidence >= INTERRUPT_CONFIDENCE_THRESHOLD:
            result["should_interrupt"] = True
        
        return result
    
    def add_assistant_turn(self, text: str) -> None:
        """Add assistant response to conversation history."""
        self._conversation_history.append(ConversationTurn(
            text=text,
            timestamp=time.time() * 1000,
            is_user=False,
        ))


__all__ = ["SocialLayer", "ConversationTurn"]
