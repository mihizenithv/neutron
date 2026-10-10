/**
 * NEUTRON Eye Animation Engine v3
 * Premium stylized eye animations with organic movement
 */

const Eyes = {
    config: {
        blinkInterval: { min: 2500, max: 5000 },
        blinkDuration: 120,
        saccadeInterval: { min: 800, max: 2500 },
        saccadeAmplitude: 0.08,
        gazeSmoothing: 0.08,
        pupilDilationSpeed: 0.05,
        breathingSpeed: 0.02,
    },

    elements: {
        leftEye: null,
        rightEye: null,
        leftIris: null,
        rightIris: null,
        leftPupil: null,
        rightPupil: null,
    },

    state: {
        gazeX: 0.5,
        gazeY: 0.5,
        targetGazeX: 0.5,
        targetGazeY: 0.5,
        isBlinking: false,
        expression: 'neutral',
        pupilDilation: 1.0,
        targetDilation: 1.0,
        breathPhase: 0,
        visionMode: false,  // When true, face tracking overrides mouse
        faceDetected: false,
    },

    blinkTimer: null,
    saccadeTimer: null,
    animationFrame: null,

    init() {
        this.elements.leftEye = document.getElementById('left-eye');
        this.elements.rightEye = document.getElementById('right-eye');
        this.elements.leftIris = document.getElementById('left-iris');
        this.elements.rightIris = document.getElementById('right-iris');
        this.elements.leftPupil = document.getElementById('left-pupil');
        this.elements.rightPupil = document.getElementById('right-pupil');

        this.startAnimationLoop();
        this.scheduleBlink();
        this.scheduleSaccade();
        this.addMouseTracking();

        console.log('[Eyes] Initialized with vision support');
    },

    /**
     * Enable/disable vision mode (face tracking overrides mouse)
     */
    setVisionMode(enabled) {
        this.state.visionMode = enabled;
        console.log(`[Eyes] Vision mode: ${enabled ? 'ON' : 'OFF'}`);
    },

    /**
     * Track face position from webcam
     * @param {number} x - Normalized x position (0-1)
     * @param {number} y - Normalized y position (0-1)
     * @param {number} proximity - How close the face is (0-1)
     */
    trackFace(x, y, proximity = 0.5) {
        this.state.faceDetected = true;
        this.state.visionMode = true;

        // Map face position to gaze (with limits for natural look)
        this.state.targetGazeX = 0.25 + x * 0.5;
        this.state.targetGazeY = 0.25 + y * 0.5;

        // Adjust pupil dilation based on proximity (closer = more engaged)
        this.state.targetDilation = 1.0 + proximity * 0.25;
    },

    /**
     * Called when face is lost
     */
    onFaceLost() {
        this.state.faceDetected = false;
        // Return to center and start searching
        this.state.targetGazeX = 0.5;
        this.state.targetGazeY = 0.5;
        this.state.targetDilation = 0.9;
    },

    /**
     * React to user presence changes
     */
    reactToPresence(state) {
        switch (state) {
            case 'appeared':
                // Surprise/welcome
                this.setExpression('widened');
                setTimeout(() => this.setExpression('happy'), 400);
                setTimeout(() => this.setExpression('neutral'), 1200);
                break;
            case 'left':
                // Searching
                this.setExpression('neutral');
                this.state.targetDilation = 0.85;
                break;
            case 'engaged':
                // Attentive
                this.setExpression('neutral');
                this.state.targetDilation = 1.1;
                break;
        }
    },

    addMouseTracking() {
        document.addEventListener('mousemove', (e) => {
            // Only use mouse if vision mode is off
            if (this.state.visionMode && this.state.faceDetected) return;

            // Convert mouse position to normalized gaze coordinates
            const x = e.clientX / window.innerWidth;
            const y = e.clientY / window.innerHeight;

            // Limit range to prevent extreme eye positions
            this.state.targetGazeX = 0.3 + x * 0.4;
            this.state.targetGazeY = 0.3 + y * 0.4;
        });
    },

    startAnimationLoop() {
        const animate = () => {
            this.updateGaze();
            this.updatePupilDilation();
            this.updateBreathing();
            this.animationFrame = requestAnimationFrame(animate);
        };
        animate();
    },

    updateGaze() {
        // Smooth interpolation toward target
        const smooth = this.config.gazeSmoothing;
        this.state.gazeX += (this.state.targetGazeX - this.state.gazeX) * smooth;
        this.state.gazeY += (this.state.targetGazeY - this.state.gazeY) * smooth;

        // Convert normalized coordinates to pixel offsets
        const maxOffset = 20;
        const offsetX = (this.state.gazeX - 0.5) * maxOffset * 2;
        const offsetY = (this.state.gazeY - 0.5) * maxOffset * 2;

        // Apply to both irises with slight organic variation
        const transform = `translate(${offsetX}px, ${offsetY}px)`;
        if (this.elements.leftIris) this.elements.leftIris.style.transform = transform;
        if (this.elements.rightIris) this.elements.rightIris.style.transform = transform;
    },

    updatePupilDilation() {
        // Smooth pupil dilation
        this.state.pupilDilation += (this.state.targetDilation - this.state.pupilDilation) * this.config.pupilDilationSpeed;

        const baseSize = 45;
        const size = baseSize * this.state.pupilDilation;

        if (this.elements.leftPupil) {
            this.elements.leftPupil.style.width = `${size}px`;
            this.elements.leftPupil.style.height = `${size}px`;
        }
        if (this.elements.rightPupil) {
            this.elements.rightPupil.style.width = `${size}px`;
            this.elements.rightPupil.style.height = `${size}px`;
        }
    },

    updateBreathing() {
        // Subtle breathing animation for organic feel
        this.state.breathPhase += this.config.breathingSpeed;
        const breathScale = 1 + Math.sin(this.state.breathPhase) * 0.01;

        const eyeUnits = document.querySelectorAll('.eye-unit');
        eyeUnits.forEach(unit => {
            unit.style.transform = `scale(${breathScale})`;
        });
    },

    setGaze(x, y) {
        this.state.targetGazeX = Math.max(0.2, Math.min(0.8, x));
        this.state.targetGazeY = Math.max(0.2, Math.min(0.8, y));
    },

    scheduleBlink() {
        const interval = this.randomRange(
            this.config.blinkInterval.min,
            this.config.blinkInterval.max
        );

        this.blinkTimer = setTimeout(() => {
            this.blink();
            this.scheduleBlink();
        }, interval);
    },

    blink() {
        if (this.state.isBlinking) return;

        this.state.isBlinking = true;
        this.elements.leftEye?.classList.add('blinking');
        this.elements.rightEye?.classList.add('blinking');

        setTimeout(() => {
            this.elements.leftEye?.classList.remove('blinking');
            this.elements.rightEye?.classList.remove('blinking');
            this.state.isBlinking = false;
        }, this.config.blinkDuration);
    },

    scheduleSaccade() {
        const interval = this.randomRange(
            this.config.saccadeInterval.min,
            this.config.saccadeInterval.max
        );

        this.saccadeTimer = setTimeout(() => {
            this.saccade();
            this.scheduleSaccade();
        }, interval);
    },

    saccade() {
        // Small random eye movement for realism
        const amp = this.config.saccadeAmplitude;
        const dx = (Math.random() - 0.5) * amp;
        const dy = (Math.random() - 0.5) * amp;

        this.state.targetGazeX = Math.max(0.35, Math.min(0.65, 0.5 + dx));
        this.state.targetGazeY = Math.max(0.35, Math.min(0.65, 0.5 + dy));
    },

    setExpression(expression) {
        const expressions = ['neutral', 'happy', 'sad', 'surprised', 'squinting', 'widened', 'thinking'];

        // Remove all expression classes
        expressions.forEach(exp => {
            this.elements.leftEye?.classList.remove(exp);
            this.elements.rightEye?.classList.remove(exp);
        });

        // Set expression
        switch (expression) {
            case 'happy':
                this.state.targetDilation = 1.1;
                break;
            case 'squint':
            case 'thinking':
                this.elements.leftEye?.classList.add('squinting');
                this.elements.rightEye?.classList.add('squinting');
                this.state.targetDilation = 0.9;
                break;
            case 'widen':
            case 'surprised':
                this.elements.leftEye?.classList.add('widened');
                this.elements.rightEye?.classList.add('widened');
                this.state.targetDilation = 1.3;
                break;
            case 'sad':
                this.state.targetDilation = 0.95;
                break;
            default:
                this.state.targetDilation = 1.0;
        }

        this.state.expression = expression;
    },

    setPupilDilation(factor) {
        // factor: 0.7 (constricted) to 1.3 (dilated)
        this.state.targetDilation = Math.max(0.7, Math.min(1.3, factor));
    },

    // React to audio input
    reactToAudio(level) {
        // Subtle pupil dilation based on audio
        if (level > 0.5) {
            this.state.targetDilation = 1.0 + (level - 0.5) * 0.4;
        }
    },

    // React to emotion
    setEmotion(emotion) {
        const emotionExpressions = {
            happy: { dilation: 1.15, expression: 'happy' },
            sad: { dilation: 0.9, expression: 'neutral' },
            excited: { dilation: 1.25, expression: 'widened' },
            tired: { dilation: 0.85, expression: 'squinting' },
            focused: { dilation: 0.95, expression: 'squinting' },
            neutral: { dilation: 1.0, expression: 'neutral' },
        };

        const config = emotionExpressions[emotion] || emotionExpressions.neutral;
        this.state.targetDilation = config.dilation;

        // Update face container emotion class
        const container = document.querySelector('.face-container');
        if (container) {
            Object.keys(emotionExpressions).forEach(e => {
                container.classList.remove(`emotion-${e}`);
            });
            container.classList.add(`emotion-${emotion}`);
        }
    },

    randomRange(min, max) {
        return Math.random() * (max - min) + min;
    },

    destroy() {
        if (this.blinkTimer) clearTimeout(this.blinkTimer);
        if (this.saccadeTimer) clearTimeout(this.saccadeTimer);
        if (this.animationFrame) cancelAnimationFrame(this.animationFrame);
    },
};
