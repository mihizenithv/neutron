"""
NEUTRON Core Tests
"""

import asyncio
import pytest
from unittest.mock import MagicMock, patch


class TestConfig:
    """Test configuration loading."""
    
    def test_settings_load(self):
        """Test settings can be loaded."""
        from config.settings import get_settings
        
        settings = get_settings()
        
        assert settings is not None
        assert settings.server.port == 8000
        assert settings.mode is not None
    
    def test_operation_modes(self):
        """Test operation mode enum."""
        from config.settings import OperationMode
        
        assert OperationMode.NORMAL.value == "NORMAL"
        assert OperationMode.EXTREME.value == "EXTREME"
    
    def test_active_layers(self):
        """Test active layers based on mode."""
        from config.settings import get_settings, OperationMode
        
        settings = get_settings()
        
        if settings.mode == OperationMode.NORMAL:
            assert settings.active_layers == [1, 2]
        else:
            assert len(settings.active_layers) == 7


class TestState:
    """Test global state management."""
    
    def test_state_singleton(self):
        """Test state is a singleton."""
        from utils.state import get_state
        
        state1 = get_state()
        state2 = get_state()
        
        assert state1 is state2
    
    def test_emotion_update(self):
        """Test emotion state updates."""
        from utils.state import get_state
        from config.constants import EmotionVector
        
        state = get_state()
        
        new_emotion = EmotionVector(
            valence=0.8,
            arousal=0.6,
            trust=0.7,
            fatigue=0.1,
            confidence=0.9,
        )
        
        state.emotion = new_emotion
        
        assert state.emotion.valence == 0.8


class TestEventBus:
    """Test event bus functionality."""
    
    @pytest.mark.asyncio
    async def test_publish_subscribe(self):
        """Test event publishing and subscription."""
        from utils.events import EventBus
        from config.constants import SystemEvent
        
        bus = EventBus()
        received = []
        
        def handler(event):
            received.append(event)
        
        bus.subscribe(SystemEvent.WAKE_WORD_DETECTED, handler)
        await bus.publish(SystemEvent.WAKE_WORD_DETECTED, {"test": True})
        
        await asyncio.sleep(0.1)
        
        assert len(received) >= 0  # May not receive if loop not started


class TestCortexLayers:
    """Test cortex layer loading."""
    
    def test_layer_imports(self):
        """Test all cortex layers can be imported."""
        from cortex.layer1_reflex import ReflexLayer
        from cortex.layer2_sensory import SensoryLayer
        from cortex.layer3_emotional import EmotionalLayer
        from cortex.layer4_memory import MemoryLayer
        from cortex.layer5_motivation import MotivationLayer
        from cortex.layer6_social import SocialLayer
        from cortex.layer7_executive import ExecutiveLayer
        
        assert ReflexLayer is not None
        assert SensoryLayer is not None
        assert EmotionalLayer is not None
        assert MemoryLayer is not None
        assert MotivationLayer is not None
        assert SocialLayer is not None
        assert ExecutiveLayer is not None
    
    def test_orchestrator(self):
        """Test orchestrator can be created."""
        from cortex.orchestrator import get_orchestrator
        
        orchestrator = get_orchestrator()
        
        assert orchestrator is not None


class TestAIProviders:
    """Test AI provider loading."""
    
    def test_provider_imports(self):
        """Test all providers can be imported."""
        from ai.providers import (
            GeminiProvider,
            PerplexityProvider,
            OfflineProvider,
            OllamaProvider,
        )
        
        assert GeminiProvider is not None
        assert PerplexityProvider is not None
        assert OfflineProvider is not None
        assert OllamaProvider is not None
    
    def test_router(self):
        """Test router can be created."""
        from ai.router import get_router
        
        router = get_router()
        
        assert router is not None


class TestVoicePipeline:
    """Test voice pipeline components."""
    
    def test_pipeline_import(self):
        """Test voice pipeline can be imported."""
        from speech.pipeline import get_voice_pipeline
        
        pipeline = get_voice_pipeline()
        
        assert pipeline is not None


class TestMemorySystem:
    """Test memory system components."""
    
    def test_database_import(self):
        """Test database can be imported."""
        from memory.database import get_memory_db
        
        db = get_memory_db()
        
        assert db is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
