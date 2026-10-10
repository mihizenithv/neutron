/**
 * NEUTRON Vision Bridge
 *
 * Polls the backend every 8 seconds with a webcam frame.
 * LLaVA analyzes it and returns a real description.
 * Displays that description in the "How I See You" panel.
 * Also drives head tracking for the robot eyes.
 */

const VisionBridge = {
    active: false,
    pollInterval: null,
    POLL_MS: 8000,   // LLaVA is slow — 8s between frames

    // Head tracking state
    targetX: 0.5,
    targetY: 0.5,
    currentX: 0.5,
    currentY: 0.5,

    init() {
        this.observationEl = document.getElementById('vision-observation');
        this.observationPanel = document.getElementById('vision-observation-panel');

        if (!this.observationEl) {
            console.warn('[VisionBridge] No #vision-observation element found');
        }

        // Start head tracking animation
        this.startHeadTracking();

        // Wait for webcam to be ready, then start polling
        setTimeout(() => this.startPolling(), 5000);

        console.log('[VisionBridge] Initialized');
    },

    startPolling() {
        if (this.active) return;
        this.active = true;

        // Poll immediately, then on interval
        this.poll();
        this.pollInterval = setInterval(() => this.poll(), this.POLL_MS);
    },

    stopPolling() {
        this.active = false;
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    },

    async poll() {
        if (!this.active) return;

        // Capture frame from webcam
        const frame = (typeof Webcam !== 'undefined') ? Webcam.captureFrame(0.7) : null;
        if (!frame) {
            console.log('[VisionBridge] No frame available yet');
            return;
        }

        try {
            const res = await fetch('/api/vision/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image: frame, context: 'webcam' }),
                signal: AbortSignal.timeout(30000),
            });

            if (!res.ok) {
                console.warn('[VisionBridge] API error:', res.status);
                return;
            }

            const data = await res.json();
            const description = data.description || '';

            console.log('[VisionBridge] AI:', description);

            if (description) {
                this.updateObservation(description);
                // Update head tracking based on description keywords
                this.updateHeadFromDescription(description);
            }

        } catch (err) {
            if (err.name !== 'AbortError') {
                console.warn('[VisionBridge] Poll error:', err.message);
            }
        }
    },

    updateObservation(text) {
        if (this.observationEl) {
            this.observationEl.textContent = text;
        }
        if (this.observationPanel) {
            this.observationPanel.style.display = 'block';
        }
    },

    updateHeadFromDescription(description) {
        const d = description.toLowerCase();
        // Nudge gaze based on what's described
        if (d.includes('left')) {
            this.targetX = 0.35;
        } else if (d.includes('right')) {
            this.targetX = 0.65;
        } else {
            this.targetX = 0.5;
        }

        if (d.includes('looking up') || d.includes('above')) {
            this.targetY = 0.35;
        } else if (d.includes('looking down') || d.includes('below')) {
            this.targetY = 0.65;
        } else {
            this.targetY = 0.5;
        }
    },

    startHeadTracking() {
        // Smooth interpolation loop for eye movement
        const track = () => {
            this.currentX += (this.targetX - this.currentX) * 0.05;
            this.currentY += (this.targetY - this.currentY) * 0.05;

            if (typeof Eyes !== 'undefined' && Eyes.setGaze) {
                Eyes.setGaze(this.currentX, this.currentY);
            }

            requestAnimationFrame(track);
        };
        requestAnimationFrame(track);
    },
};

document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => VisionBridge.init(), 1000);
});
