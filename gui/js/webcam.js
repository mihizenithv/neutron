/**
 * NEUTRON Webcam — Face presence detection and auto-greeting.
 * No fake emotion detection. Real observations come from LLaVA via vision-bridge.js.
 */

const Webcam = {
    video: null,
    canvas: null,
    ctx: null,
    stream: null,
    faceIndicator: null,
    initialized: false,
    detecting: false,

    // Face presence tracking
    faceDetectedCount: 0,
    faceWasPresent: false,
    hasGreeted: false,
    lastFaceTime: 0,
    brightnessHistory: [],
    movementHistory: [],

    greetings: [
        "Hey there! Nice to see you! 👋",
        "Hello! I noticed you're here. How can I help?",
        "Hi! Ready to chat whenever you are!",
        "Welcome back! What's on your mind?",
    ],

    async init() {
        this.video = document.getElementById('webcam-feed');
        this.faceIndicator = document.getElementById('face-indicator');

        if (!this.video) return false;

        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { width: { ideal: 320 }, height: { ideal: 240 }, facingMode: 'user' },
                audio: false
            });

            this.video.srcObject = this.stream;
            await this.video.play();

            this.initialized = true;
            this.startDetection();
            console.log('[Webcam] Initialized');
            return true;

        } catch (err) {
            console.log('[Webcam] Access denied:', err.message);
            const overlay = document.getElementById('webcam-overlay');
            if (overlay) {
                overlay.innerHTML = `
                    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;color:#ff6b6b;font-size:12px;text-align:center;padding:10px;">
                        <span style="font-size:24px">📷</span>
                        <span>Camera unavailable</span>
                    </div>
                `;
            }
            return false;
        }
    },

    startDetection() {
        if (!this.initialized || this.detecting) return;
        this.detecting = true;
        this.detectLoop();
    },

    stopDetection() {
        this.detecting = false;
    },

    detectLoop() {
        if (!this.detecting) return;
        this.analyzeFrame();
        setTimeout(() => this.detectLoop(), 200);
    },

    analyzeFrame() {
        if (!this.video || this.video.readyState < 2) return;

        if (!this.canvas) {
            this.canvas = document.createElement('canvas');
            this.canvas.width = 160;
            this.canvas.height = 120;
            this.ctx = this.canvas.getContext('2d', { willReadFrequently: true });
        }

        this.ctx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);

        try {
            const imageData = this.ctx.getImageData(40, 30, 80, 60);
            const faceDetected = this.detectFacePresence(imageData);
            this.updatePresence(faceDetected);
        } catch (e) {
            // Security error in some contexts
        }
    },

    detectFacePresence(imageData) {
        const data = imageData.data;
        let skinPixels = 0;
        let totalBrightness = 0;

        for (let i = 0; i < data.length; i += 4) {
            const r = data[i], g = data[i + 1], b = data[i + 2];
            totalBrightness += (r + g + b) / 3;
            // Skin tone heuristic
            if (r > 95 && g > 40 && b > 20 && r > g && r > b && Math.abs(r - g) > 15) {
                skinPixels++;
            }
        }

        const pixelCount = data.length / 4;
        const avgBrightness = totalBrightness / pixelCount;

        // Track movement for head tracking
        this.movementHistory.push(avgBrightness);
        if (this.movementHistory.length > 10) this.movementHistory.shift();

        return (skinPixels / pixelCount) > 0.15;
    },

    updatePresence(faceDetected) {
        // Update face indicator dot
        if (this.faceIndicator) {
            this.faceIndicator.classList.toggle('detected', faceDetected);
        }

        if (faceDetected) {
            this.faceDetectedCount++;
            this.lastFaceTime = Date.now();

            // Greet once when face first appears
            if (this.faceDetectedCount > 5 && !this.hasGreeted && !this.faceWasPresent) {
                this.greetUser();
            }
            this.faceWasPresent = true;
        } else {
            this.faceDetectedCount = 0;
            // Reset after 10s absence
            if (this.faceWasPresent && Date.now() - this.lastFaceTime > 10000) {
                this.faceWasPresent = false;
                this.hasGreeted = false;
            }
        }
    },

    greetUser() {
        this.hasGreeted = true;
        const greeting = this.greetings[Math.floor(Math.random() * this.greetings.length)];

        if (typeof App !== 'undefined') {
            App.showSpeechBubble(greeting);
            App.setMode('speaking');
        }

        const utterance = new SpeechSynthesisUtterance(greeting);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;

        const voices = speechSynthesis.getVoices();
        const voice = voices.find(v => v.name.includes('Google') || v.lang === 'en-US');
        if (voice) utterance.voice = voice;

        const mouth = document.getElementById('animated-mouth');
        if (mouth) mouth.classList.replace('idle', 'speaking');

        utterance.onend = () => {
            if (mouth) mouth.classList.replace('speaking', 'idle');
            if (typeof App !== 'undefined') App.setMode('idle');
        };

        speechSynthesis.speak(utterance);
    },

    /** Capture current frame as base64 JPEG for LLaVA. */
    captureFrame(quality = 0.7) {
        if (!this.video || this.video.readyState < 2) return null;
        if (!this.canvas) return null;
        // Use a larger canvas for LLaVA
        const cap = document.createElement('canvas');
        cap.width = 320;
        cap.height = 240;
        cap.getContext('2d').drawImage(this.video, 0, 0, 320, 240);
        const dataUrl = cap.toDataURL('image/jpeg', quality);
        return dataUrl.split(',')[1]; // Return base64 only
    },

    isFacePresent() {
        return this.faceWasPresent;
    },

    destroy() {
        this.stopDetection();
        if (this.stream) this.stream.getTracks().forEach(t => t.stop());
    }
};

document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => Webcam.init(), 3000);
});
