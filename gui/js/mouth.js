/**
 * NEUTRON Mouth Animation v4
 * SVG-based animated mouth with speaking sync
 */

const Mouth = {
    elements: {
        svg: null,
        outer: null,
        inner: null,
        teeth: null,
    },

    state: {
        isSpeaking: false,
        audioLevel: 0,
        expression: 'idle',
    },

    animationFrame: null,

    init() {
        this.elements.svg = document.getElementById('animated-mouth');
        this.elements.outer = document.getElementById('mouth-outer');
        this.elements.inner = document.getElementById('mouth-inner-path');
        this.elements.teeth = document.getElementById('mouth-teeth');

        if (this.elements.svg) {
            this.elements.svg.classList.add('idle');
        }

        console.log('[Mouth] Initialized');
    },

    startSpeaking() {
        this.state.isSpeaking = true;
        if (this.elements.svg) {
            this.elements.svg.classList.remove('idle', 'happy');
            this.elements.svg.classList.add('speaking');
        }
    },

    stopSpeaking() {
        this.state.isSpeaking = false;
        if (this.elements.svg) {
            this.elements.svg.classList.remove('speaking');
            this.elements.svg.classList.add('idle');
        }
    },

    setExpression(expression) {
        this.state.expression = expression;
        if (!this.elements.svg) return;

        this.elements.svg.classList.remove('idle', 'happy', 'speaking');

        switch (expression) {
            case 'happy':
                this.elements.svg.classList.add('happy');
                break;
            case 'speaking':
                this.elements.svg.classList.add('speaking');
                break;
            default:
                this.elements.svg.classList.add('idle');
        }
    },

    setAudioLevel(level) {
        this.state.audioLevel = Math.max(0, Math.min(1, level));
        // Could animate mouth opening based on audio level
    },

    destroy() {
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
        }
    },
};
