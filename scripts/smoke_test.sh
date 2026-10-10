#!/bin/bash
# NEUTRON Smoke Test
# Validates installation and core functionality

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                  NEUTRON Smoke Test                           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Activate virtual environment
if [[ -f "venv/bin/activate" ]]; then
    source venv/bin/activate
elif [[ -f "venv/Scripts/activate" ]]; then
    source venv/Scripts/activate
fi

PASSED=0
FAILED=0

# Test function
test_step() {
    local name="$1"
    local cmd="$2"
    
    echo -n "Testing: $name... "
    if eval "$cmd" > /dev/null 2>&1; then
        echo "✓ PASS"
        ((PASSED++))
    else
        echo "✗ FAIL"
        ((FAILED++))
    fi
}

# Python import tests
echo "🐍 Python Import Tests"
echo "----------------------"

test_step "config.settings" "python -c 'from config.settings import get_settings; get_settings()'"
test_step "config.constants" "python -c 'from config.constants import VERSION'"
test_step "utils.logging" "python -c 'from utils.logging_config import get_logger'"
test_step "utils.events" "python -c 'from utils.events import get_event_bus'"
test_step "utils.state" "python -c 'from utils.state import get_state'"
test_step "cortex.orchestrator" "python -c 'from cortex.orchestrator import get_orchestrator'"
test_step "ai.router" "python -c 'from ai.router import get_router'"
test_step "speech.pipeline" "python -c 'from speech.pipeline import get_voice_pipeline'"
test_step "memory.database" "python -c 'from memory.database import get_memory_db'"

echo ""
echo "📦 Component Tests"
echo "------------------"

# Test settings loading
test_step "Settings load" "python -c '
from config.settings import get_settings
s = get_settings()
assert s.server.port == 8000
'"

# Test event bus
test_step "Event bus" "python -c '
import asyncio
from utils.events import EventBus, Event
from config.constants import SystemEvent

async def test():
    bus = EventBus()
    received = []
    bus.subscribe(SystemEvent.WAKE_WORD_DETECTED, lambda e: received.append(e))
    await bus.publish(SystemEvent.WAKE_WORD_DETECTED, {\"test\": True})
    await asyncio.sleep(0.1)
    assert len(received) == 1

asyncio.run(test())
'"

# Test global state
test_step "Global state" "python -c '
from utils.state import get_state
from config.settings import OperationMode
state = get_state()
state.operation_mode = OperationMode.EXTREME
assert state.operation_mode == OperationMode.EXTREME
'"

# Test database schema
test_step "Database schema" "python -c '
import asyncio
from memory.database import get_memory_db

async def test():
    db = get_memory_db()
    await db.initialize()
    stats = await db.get_stats()
    assert \"episodic_memories\" in stats
    await db.close()

asyncio.run(test())
'"

echo ""
echo "🔌 Optional Component Tests"
echo "---------------------------"

# Test Vosk (optional)
python -c "import vosk" 2>/dev/null && \
    test_step "Vosk STT" "python -c 'import vosk'" || \
    echo "⚠ Vosk not installed (optional)"

# Test Piper (optional)
which piper > /dev/null 2>&1 && \
    test_step "Piper TTS" "piper --help" || \
    echo "⚠ Piper not installed (optional)"

# Test sentence-transformers
python -c "from sentence_transformers import SentenceTransformer" 2>/dev/null && \
    test_step "Embeddings" "python -c 'from sentence_transformers import SentenceTransformer'" || \
    echo "⚠ sentence-transformers not installed (optional)"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "Results: $PASSED passed, $FAILED failed"
echo "════════════════════════════════════════════════════════════════"

if [[ $FAILED -gt 0 ]]; then
    echo "❌ Some tests failed. Check the output above."
    exit 1
else
    echo "✅ All tests passed! NEUTRON is ready to run."
    echo ""
    echo "Start with: python -m server.main"
fi
