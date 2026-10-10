/**
 * NEUTRON Main Application v5
 * RAG integration, real-time speech display, file upload
 */

const App = {
    state: {
        mode: 'idle',
        speaking: false,
        transcript: '',
        emotion: 'neutral',
        memories: [],
        currentUtterance: null,
        spokenText: '',
        spokenIndex: 0,
        docCount: 0,
    },

    _initialized: false,

    init() {
        if (this._initialized) return;
        this._initialized = true;

        console.log('[App] Initializing NEUTRON v5...');

        Eyes.init();
        if (typeof Mouth !== 'undefined') Mouth.init();
        if (typeof Emotions !== 'undefined') Emotions.init();

        this.registerEventHandlers();
        if (typeof WebSocketClient !== 'undefined') WebSocketClient.startHeartbeat();

        this.setupMouthAnimation();
        this.loadMemories();
        this.loadDocCount();

        console.log('[App] NEUTRON v5 initialized');
    },

    registerEventHandlers() {
        if (typeof WebSocketClient === 'undefined') return;
        WebSocketClient.on('stateUpdate', (data) => this.handleStateUpdate(data));
        WebSocketClient.on('connected', () => this.onConnected());
        WebSocketClient.on('disconnected', () => this.onDisconnected());
    },

    handleStateUpdate(data) {
        if (!data) return;
        if (data.mode !== this.state.mode) {
            this.state.mode = data.mode;
            this.updateModeDisplay();
        }
    },

    setupMouthAnimation() {
        const mouth = document.getElementById('animated-mouth');
        if (mouth) mouth.classList.add('idle');
    },

    setMode(mode) {
        this.state.mode = mode;
        this.updateModeDisplay();
    },

    updateModeDisplay() {
        const modeEl = document.getElementById('status-mode');
        const indicator = document.getElementById('status-dot');

        if (modeEl) modeEl.textContent = this.state.mode.toUpperCase();
        if (indicator) {
            indicator.className = 'status-indicator';
            if (this.state.mode !== 'idle') indicator.classList.add(this.state.mode);
        }

        switch (this.state.mode) {
            case 'listening': Eyes.setExpression('neutral'); break;
            case 'thinking': Eyes.setExpression('squint'); break;
            case 'speaking': Eyes.setExpression('happy'); break;
        }
    },

    // === SPEECH BUBBLE ===
    showSpeechBubble(text, typewriter = true) {
        const bubble = document.getElementById('speech-bubble');
        const bubbleText = document.getElementById('bubble-text');
        const mouth = document.getElementById('animated-mouth');

        if (!bubble || !bubbleText) return;

        bubble.classList.remove('hidden');
        if (mouth) {
            mouth.classList.remove('idle');
            mouth.classList.add('speaking');
        }

        if (typewriter) {
            this.state.spokenText = text;
            this.state.spokenIndex = 0;
            this.typewriterEffect(bubbleText, text);
        } else {
            bubbleText.textContent = text;
        }
    },

    typewriterEffect(element, text) {
        let i = this.state.spokenIndex;
        const speed = 30;

        const type = () => {
            if (!this.state.speaking) return;
            if (i < text.length) {
                element.textContent = text.substring(0, i + 1);
                this.state.spokenIndex = i;
                i++;
                setTimeout(type, speed);
            }
        };
        type();
    },

    hideSpeechBubble() {
        const bubble = document.getElementById('speech-bubble');
        const mouth = document.getElementById('animated-mouth');

        if (bubble) bubble.classList.add('hidden');
        if (mouth) {
            mouth.classList.remove('speaking');
            mouth.classList.add('idle');
        }
    },

    // === REAL-TIME SPEECH DISPLAY ===
    showSpeechInput(text) {
        const display = document.getElementById('speech-input-display');
        const textEl = document.getElementById('realtime-text');

        if (display) display.classList.remove('hidden');
        if (textEl) textEl.textContent = text || 'Listening...';
    },

    hideSpeechInput() {
        const display = document.getElementById('speech-input-display');
        if (display) display.classList.add('hidden');
    },

    // === THINKING DISPLAY ===
    showThinking(text = '') {
        const panel = document.getElementById('thinking-panel');
        const content = document.getElementById('thinking-content');

        if (panel) panel.classList.remove('hidden');
        if (content) content.textContent = text || 'Processing your request...';
    },

    hideThinking() {
        const panel = document.getElementById('thinking-panel');
        if (panel) panel.classList.add('hidden');
    },

    // === FEELINGS DISPLAY ===
    updateFeelings(feeling) {
        const content = document.getElementById('feelings-content');
        if (content) content.innerHTML = feeling;
    },

    // === MEMORY PANEL ===
    loadMemories() {
        fetch('/api/memories')
            .then(r => r.json())
            .then(data => {
                if (data.memories) {
                    this.state.memories = data.memories;
                    this.renderMemories();
                }
            })
            .catch(() => {
                const stored = localStorage.getItem('neutron_memories');
                if (stored) {
                    this.state.memories = JSON.parse(stored);
                    this.renderMemories();
                }
            });
    },

    addMemory(text) {
        const memory = {
            text: text,
            time: new Date().toLocaleString(),
            timestamp: Date.now()
        };
        this.state.memories.unshift(memory);
        if (this.state.memories.length > 20) this.state.memories.pop();

        localStorage.setItem('neutron_memories', JSON.stringify(this.state.memories));
        this.renderMemories();
    },

    renderMemories() {
        const content = document.getElementById('memory-content');
        if (!content) return;

        if (this.state.memories.length === 0) {
            content.innerHTML = '<div class="memory-item placeholder">No memories yet...</div>';
            return;
        }

        content.innerHTML = this.state.memories.slice(0, 10).map(m => `
            <div class="memory-item">
                ${m.text.substring(0, 80)}${m.text.length > 80 ? '...' : ''}
                <span class="memory-time">${m.time}</span>
            </div>
        `).join('');
    },

    // === RAG DOC COUNT ===
    loadDocCount() {
        fetch('/api/rag/count')
            .then(r => r.json())
            .then(data => {
                this.state.docCount = data.count || 0;
                this.updateDocCount();
            })
            .catch(() => { });
    },

    updateDocCount() {
        const el = document.getElementById('doc-count');
        if (el) el.textContent = this.state.docCount;
    },

    onConnected() {
        console.log('[App] Connected to backend');
        this.setMode('idle');
    },

    onDisconnected() {
        console.log('[App] Disconnected from backend');
    },

    destroy() {
        Eyes.destroy();
        if (typeof Particles !== 'undefined') Particles.destroy();
        if (typeof Webcam !== 'undefined') Webcam.destroy();
        this._initialized = false;
    },
};

// ============================================
// TOGGLE FUNCTIONS
// ============================================

function toggleMemoryPanel() {
    const content = document.getElementById('memory-content');
    const toggle = document.querySelector('.panel-toggle');

    if (content) content.classList.toggle('collapsed');
    if (toggle) toggle.classList.toggle('expanded');
}

// ============================================
// FILE UPLOAD
// ============================================

async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const status = document.getElementById('upload-status');
    const statusText = document.getElementById('upload-text');

    if (status) status.classList.remove('hidden');
    if (statusText) statusText.textContent = `Uploading ${file.name}...`;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/rag/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (statusText) {
            statusText.textContent = `✓ Added ${data.chunks || 0} chunks from ${file.name}`;
        }

        App.loadDocCount();

        setTimeout(() => {
            if (status) status.classList.add('hidden');
        }, 3000);

    } catch (error) {
        console.error('[Upload] Error:', error);
        if (statusText) statusText.textContent = `Failed to upload ${file.name}`;

        setTimeout(() => {
            if (status) status.classList.add('hidden');
        }, 3000);
    }

    // Reset input
    event.target.value = '';
}

// ============================================
// SPEECH & RESPONSE
// ============================================

let currentUtterance = null;
let isSpeaking = false;
let fullResponseText = '';
let spokenIndex = 0;

async function sendTextMessage() {
    const input = document.getElementById('text-input');
    const text = input.value.trim();

    if (!text) return;
    input.value = '';

    App.setMode('thinking');
    App.showThinking('Understanding your message...');
    Eyes.setExpression('thinking');

    try {
        // Use RAG-enabled endpoint
        const response = await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text, use_rag: true })
        });

        const data = await response.json();
        fullResponseText = data.response || data.text || 'I couldn\'t process that.';

        App.hideThinking();
        App.addMemory(`You: ${text}`);
        App.addMemory(`Neutron: ${fullResponseText.substring(0, 100)}`);

        await speakResponse(fullResponseText);

    } catch (error) {
        console.error('[App] Query error:', error);
        App.hideThinking();
        App.showSpeechBubble('Connection error. Is the backend running?', false);

        setTimeout(() => {
            App.hideSpeechBubble();
            App.setMode('idle');
        }, 3000);
    }
}

async function speakResponse(text, startFrom = 0) {
    return new Promise((resolve) => {
        isSpeaking = true;
        App.state.speaking = true;
        App.setMode('speaking');

        App.showSpeechBubble(text);

        const textToSpeak = text.substring(startFrom);
        currentUtterance = new SpeechSynthesisUtterance(textToSpeak);
        currentUtterance.rate = 1.0;
        currentUtterance.pitch = 1.0;

        const voices = speechSynthesis.getVoices();
        const voice = voices.find(v =>
            v.name.includes('David') || v.name.includes('Google') || v.lang === 'en-US'
        );
        if (voice) currentUtterance.voice = voice;

        currentUtterance.onend = () => {
            finishSpeaking();
            resolve();
        };

        currentUtterance.onerror = () => {
            finishSpeaking();
            resolve();
        };

        speechSynthesis.speak(currentUtterance);
        startBargeInDetection();
    });
}

function stopSpeaking() {
    if (isSpeaking) {
        speechSynthesis.cancel();
        spokenIndex = App.state.spokenIndex;
        isSpeaking = false;
        App.state.speaking = false;

        const bubbleText = document.getElementById('bubble-text');
        if (bubbleText) {
            bubbleText.innerHTML = fullResponseText.substring(0, spokenIndex) +
                '<span style="color:#ff4444"> [paused]</span>';
        }

        const mouth = document.getElementById('animated-mouth');
        if (mouth) {
            mouth.classList.remove('speaking');
            mouth.classList.add('idle');
        }

        App.setMode('idle');
        stopBargeInDetection();
    }
}

function finishSpeaking() {
    isSpeaking = false;
    App.state.speaking = false;

    const mouth = document.getElementById('animated-mouth');
    if (mouth) {
        mouth.classList.remove('speaking');
        mouth.classList.add('idle');
    }

    App.setMode('idle');
    stopBargeInDetection();

    setTimeout(() => {
        App.hideSpeechBubble();
    }, 2000);
}

// ============================================
// BARGE-IN DETECTION
// ============================================

let bargeInStream = null;
let bargeInContext = null;
let bargeInAnalyser = null;
let bargeInInterval = null;

async function startBargeInDetection() {
    try {
        bargeInStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        bargeInContext = new AudioContext();
        const source = bargeInContext.createMediaStreamSource(bargeInStream);
        bargeInAnalyser = bargeInContext.createAnalyser();
        bargeInAnalyser.fftSize = 256;
        source.connect(bargeInAnalyser);

        const dataArray = new Uint8Array(bargeInAnalyser.frequencyBinCount);

        bargeInInterval = setInterval(() => {
            bargeInAnalyser.getByteFrequencyData(dataArray);
            const avg = dataArray.reduce((a, b) => a + b) / dataArray.length;

            if (avg > 50 && isSpeaking) {
                console.log('[BargeIn] Voice detected, pausing...');
                stopSpeaking();
            }
        }, 100);

    } catch (e) {
        console.log('[BargeIn] Could not start:', e.message);
    }
}

function stopBargeInDetection() {
    if (bargeInInterval) clearInterval(bargeInInterval);
    if (bargeInStream) bargeInStream.getTracks().forEach(t => t.stop());
    if (bargeInContext) bargeInContext.close().catch(() => { });
    bargeInStream = null;
    bargeInContext = null;
    bargeInAnalyser = null;
}

// ============================================
// MICROPHONE INPUT - REAL-TIME DISPLAY
// ============================================

let isListening = false;
let recognition = null;
let micStream = null;
let micContext = null;
let micAnalyser = null;
let micAnimationFrame = null;

async function toggleMic() {
    const micBtn = document.getElementById('mic-btn');

    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        alert('Speech recognition not supported. Please use Chrome or Edge browser.');
        return;
    }

    if (isListening) {
        stopMic();
    } else {
        startMic();
    }
}

async function startMic() {
    const micBtn = document.getElementById('mic-btn');
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';
    recognition.maxAlternatives = 1;

    const input = document.getElementById('text-input');

    // Get mic stream for level visualization
    try {
        micStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            }
        });
        micContext = new AudioContext();
        const source = micContext.createMediaStreamSource(micStream);
        micAnalyser = micContext.createAnalyser();
        micAnalyser.fftSize = 256;
        source.connect(micAnalyser);

        visualizeMicLevel();
    } catch (e) {
        console.log('[Mic] Could not get audio stream:', e.message);
        alert('Could not access microphone. Please allow microphone access.');
        return;
    }

    recognition.onstart = () => {
        isListening = true;
        micBtn.classList.add('listening');
        App.setMode('listening');
        App.showSpeechInput('Listening...');
    };

    recognition.onresult = (event) => {
        let interimTranscript = '';
        let finalTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                finalTranscript += transcript;
            } else {
                interimTranscript += transcript;
            }
        }

        // Show real-time text
        const displayText = finalTranscript || interimTranscript;
        if (displayText) {
            App.showSpeechInput(displayText);
            if (input) input.value = displayText;
        }

        // If we have a final transcript, send it
        if (finalTranscript) {
            setTimeout(() => {
                stopMic();
                sendTextMessage();
            }, 500);
        }
    };

    recognition.onerror = (event) => {
        console.error('[Mic] Error:', event.error);
        if (event.error === 'no-speech') {
            App.showSpeechInput('No speech detected. Try again.');
        } else if (event.error === 'not-allowed') {
            alert('Microphone access denied. Please allow microphone access in browser settings.');
        }
        setTimeout(() => stopMic(), 1500);
    };

    recognition.onend = () => {
        if (isListening) {
            // Restart if still supposed to be listening
            try {
                recognition.start();
            } catch (e) {
                stopMic();
            }
        }
    };

    try {
        recognition.start();
        console.log('[Mic] Started listening');
    } catch (e) {
        console.error('[Mic] Could not start:', e);
        alert('Could not start speech recognition. Please try again.');
    }
}

function stopMic() {
    const micBtn = document.getElementById('mic-btn');

    isListening = false;

    if (recognition) {
        try { recognition.stop(); } catch (e) { }
        recognition = null;
    }
    if (micStream) {
        micStream.getTracks().forEach(t => t.stop());
        micStream = null;
    }
    if (micContext) {
        micContext.close().catch(() => { });
        micContext = null;
    }
    if (micAnimationFrame) {
        cancelAnimationFrame(micAnimationFrame);
        micAnimationFrame = null;
    }

    micBtn.classList.remove('listening');
    App.setMode('idle');
    App.hideSpeechInput();

    // Reset level indicator
    const levelFill = document.getElementById('mic-level-fill');
    if (levelFill) levelFill.style.width = '0%';
}

function visualizeMicLevel() {
    if (!micAnalyser || !isListening) return;

    const dataArray = new Uint8Array(micAnalyser.frequencyBinCount);

    const update = () => {
        if (!isListening || !micAnalyser) return;

        micAnalyser.getByteFrequencyData(dataArray);
        const avg = dataArray.reduce((a, b) => a + b) / dataArray.length;
        const level = Math.min(100, (avg / 128) * 100);

        const levelFill = document.getElementById('mic-level-fill');
        if (levelFill) {
            levelFill.style.width = `${level}%`;
        }

        micAnimationFrame = requestAnimationFrame(update);
    };
    update();
}

// ============================================
// WEBCAM FEELINGS
// ============================================

if (typeof Webcam !== 'undefined') {
    const originalOnEmotionChange = Webcam.onEmotionChange;
    Webcam.onEmotionChange = function (emotion) {
        if (originalOnEmotionChange) originalOnEmotionChange.call(Webcam, emotion);

        const feelings = {
            neutral: "You seem calm and focused. Ready when you are!",
            happy: "I see you're happy! That makes me happy too 😊",
            excited: "Wow, you're full of energy! What's exciting?",
            tired: "You look a bit tired. Maybe take a break?",
            focused: "I can see you're concentrating. I'll be helpful!",
            sad: "You seem a bit down. Want to talk about it?",
        };

        App.updateFeelings(feelings[emotion] || feelings.neutral);
    };
}

// ============================================
// INIT
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('[App] DOM loaded');

    if (typeof WebSocketClient !== 'undefined') {
        WebSocketClient.init();
        WebSocketClient.on('connected', () => {
            if (typeof Boot !== 'undefined' && !Boot.bootComplete) {
                Boot.onConnectionSuccess();
            }
        });
    }

    const checkBoot = () => {
        if (typeof Boot !== 'undefined' && Boot.bootComplete) {
            App.init();
        } else {
            setTimeout(checkBoot, 100);
        }
    };
    checkBoot();

    setTimeout(() => {
        if (typeof Boot !== 'undefined' && !Boot.bootComplete) {
            Boot.onConnectionSuccess();
        }
    }, 3000);

    // Enter key
    const input = document.getElementById('text-input');
    if (input) {
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendTextMessage();
        });
    }

    // Preload TTS voices
    if (speechSynthesis.onvoiceschanged !== undefined) {
        speechSynthesis.onvoiceschanged = () => speechSynthesis.getVoices();
    }
    speechSynthesis.getVoices();
});
