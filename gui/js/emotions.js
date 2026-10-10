/**
 * NEUTRON Emotion Visualization
 * Maps emotion state to visual changes (color, intensity, expression)
 */

const Emotions = {
    state: {
        valence: 0.5,
        arousal: 0.3,
        trust: 0.6,
        fatigue: 0.2,
        confidence: 0.7,
    },

    thresholds: {
        high: 0.7,
        low: 0.3,
    },

    init() {
        // Apply initial neutral state
        this.applyState(this.state);
    },

    update(emotionData) {
        if (!emotionData) return;

        this.state.valence = emotionData.valence ?? this.state.valence;
        this.state.arousal = emotionData.arousal ?? this.state.arousal;
        this.state.trust = emotionData.trust ?? this.state.trust;
        this.state.fatigue = emotionData.fatigue ?? this.state.fatigue;
        this.state.confidence = emotionData.confidence ?? this.state.confidence;

        this.applyState(this.state);
    },

    applyState(state) {
        const expression = this.getExpression(state);
        const colors = this.getColors(state);

        // Apply expression to eyes and mouth
        if (typeof Eyes !== 'undefined') {
            Eyes.setExpression(expression);
            Eyes.setPupilDilation(this.getPupilDilation(state));
        }

        if (typeof Mouth !== 'undefined') {
            Mouth.setExpression(expression);
        }

        // Apply color theme
        this.applyColors(colors);

        // Apply body class for CSS styling
        this.applyExpressionClass(expression);
    },

    getExpression(state) {
        const { valence, arousal, fatigue } = state;

        // Fatigue overrides
        if (fatigue > this.thresholds.high) {
            return 'sleepy';
        }

        // High valence (positive)
        if (valence > this.thresholds.high) {
            if (arousal > this.thresholds.high) {
                return 'excited'; // Happy + excited
            }
            return 'happy';
        }

        // Low valence (negative)
        if (valence < this.thresholds.low) {
            if (arousal > this.thresholds.high) {
                return 'surprised'; // Concerned
            }
            return 'sad';
        }

        // Neutral valence
        if (arousal > this.thresholds.high) {
            return 'widen'; // Alert
        }
        if (arousal < this.thresholds.low) {
            return 'squint'; // Relaxed/focused
        }

        return 'neutral';
    },

    getColors(state) {
        const { valence, arousal } = state;

        // Color interpolation based on valence and arousal
        let hue, saturation, lightness;

        if (valence > 0.6) {
            // Positive: green-blue range
            hue = 120 + (180 - 120) * (1 - valence);
        } else if (valence < 0.4) {
            // Negative: blue-purple range
            hue = 220 + (280 - 220) * (0.5 - valence);
        } else {
            // Neutral: cyan
            hue = 180;
        }

        saturation = 70 + arousal * 30;
        lightness = 50 + (1 - arousal) * 10;

        return {
            primary: `hsl(${hue}, ${saturation}%, ${lightness}%)`,
            glow: `hsl(${hue}, ${saturation}%, ${lightness + 20}%)`,
        };
    },

    getPupilDilation(state) {
        const { arousal, trust } = state;
        // Higher arousal and trust = more dilated
        return 0.8 + arousal * 0.3 + trust * 0.2;
    },

    applyColors(colors) {
        document.documentElement.style.setProperty('--iris-color', colors.primary);
        document.documentElement.style.setProperty('--iris-glow', colors.glow);
        document.documentElement.style.setProperty('--mouth-color', colors.primary);
        document.documentElement.style.setProperty('--accent-color', colors.primary);
    },

    applyExpressionClass(expression) {
        const body = document.body;
        const classes = ['emotion-happy', 'emotion-sad', 'emotion-excited', 'emotion-neutral'];

        classes.forEach(cls => body.classList.remove(cls));
        body.classList.add(`emotion-${expression}`);
    },

    destroy() {
        // Reset to neutral state
        this.state = {
            valence: 0.5,
            arousal: 0.3,
            trust: 0.6,
            fatigue: 0.2,
            confidence: 0.7,
        };
    },
};

