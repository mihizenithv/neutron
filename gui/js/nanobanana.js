const NanoBanana = {
    config: {
        assetsBase: 'assets/expressions',  // Static pre-generated images
        apiBase: '/api/expressions',       // Fallback to API generation
        cacheExpiry: 3600000, // 1 hour in ms
        useStaticAssets: true,  // Prefer static assets
    },

    cache: new Map(),
    currentExpression: null,
    expressionElement: null,

    init(containerId = 'expression-overlay') {
        // Create expression overlay element
        this.expressionElement = document.getElementById(containerId);
        if (!this.expressionElement) {
            this.expressionElement = document.createElement('div');
            this.expressionElement.id = containerId;
            this.expressionElement.className = 'expression-overlay';
            document.querySelector('.face-container')?.appendChild(this.expressionElement);
        }

        // Preload static assets
        this.preloadStaticAssets();

        console.log('Nano Banana expression client initialized');
    },

    async loadExpression(expression) {
        if (this.currentExpression === expression) return;

        const cached = this.getFromCache(expression);
        if (cached) {
            this.displayExpression(cached);
            this.currentExpression = expression;
            return;
        }

        // Try static asset first
        if (this.config.useStaticAssets) {
            const staticUrl = `${this.config.assetsBase}/${expression}.png`;
            const exists = await this.checkAssetExists(staticUrl);
            if (exists) {
                this.addToCache(expression, staticUrl);
                this.displayExpression(staticUrl);
                this.currentExpression = expression;
                return;
            }
        }

        // Fallback to API-generated images
        try {
            const response = await fetch(`${this.config.apiBase}/image/${expression}`);

            if (response.ok) {
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);

                this.addToCache(expression, url);
                this.displayExpression(url);
                this.currentExpression = expression;
            } else {
                console.warn(`Expression not available: ${expression}`);
            }
        } catch (error) {
            console.error('Failed to load expression:', error);
        }
    },

    async checkAssetExists(url) {
        try {
            const response = await fetch(url, { method: 'HEAD' });
            return response.ok;
        } catch {
            return false;
        }
    },

    preloadStaticAssets() {
        const expressions = ['neutral', 'happy', 'sad', 'surprised', 'thinking', 'sleepy', 'listening', 'speaking'];
        expressions.forEach(expr => {
            const img = new Image();
            img.src = `${this.config.assetsBase}/${expr}.png`;
        });
    },

    displayExpression(imageUrl) {
        if (!this.expressionElement) return;

        // Fade transition
        this.expressionElement.style.opacity = '0';

        setTimeout(() => {
            this.expressionElement.style.backgroundImage = `url(${imageUrl})`;
            this.expressionElement.style.opacity = '1';
        }, 150);
    },

    getFromCache(expression) {
        const cached = this.cache.get(expression);
        if (cached && Date.now() - cached.timestamp < this.config.cacheExpiry) {
            return cached.url;
        }
        return null;
    },

    addToCache(expression, url) {
        this.cache.set(expression, {
            url: url,
            timestamp: Date.now(),
        });
    },

    async preloadExpressions() {
        const expressions = [
            'neutral', 'happy', 'sad', 'surprised',
            'thinking', 'sleepy', 'listening', 'speaking'
        ];

        console.log('Preloading Nano Banana expressions...');

        for (const expr of expressions) {
            await this.loadExpression(expr);
            await new Promise(r => setTimeout(r, 500)); // Rate limit
        }

        console.log('Expression preload complete');
    },

    mapEmotionToExpression(emotion) {
        const { valence, arousal, fatigue } = emotion;

        if (fatigue > 0.7) return 'sleepy';
        if (valence > 0.7 && arousal > 0.6) return 'happy';
        if (valence < 0.3) return 'sad';
        if (arousal > 0.8) return 'surprised';

        return 'neutral';
    },

    updateFromState(state) {
        if (!state) return;

        let expression = 'neutral';

        // Priority: mode state > emotion
        if (state.mode === 'listening') {
            expression = 'listening';
        } else if (state.mode === 'speaking') {
            expression = 'speaking';
        } else if (state.mode === 'thinking') {
            expression = 'thinking';
        } else if (state.valence !== undefined) {
            expression = this.mapEmotionToExpression({
                valence: state.valence,
                arousal: state.arousal || 0.3,
                fatigue: state.fatigue || 0.2,
            });
        }

        this.loadExpression(expression);
    },

    destroy() {
        // Revoke any blob URLs to free memory
        this.cache.forEach((cached) => {
            if (cached.url && cached.url.startsWith('blob:')) {
                URL.revokeObjectURL(cached.url);
            }
        });
        this.cache.clear();
        this.currentExpression = null;

        if (this.expressionElement) {
            this.expressionElement.style.backgroundImage = '';
        }
    },
};

// CSS for expression overlay
const nanoBananaStyles = `
.expression-overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-size: contain;
    background-position: center;
    background-repeat: no-repeat;
    opacity: 0;
    transition: opacity 0.3s ease;
    pointer-events: none;
    z-index: 5;
    mix-blend-mode: screen;
}

.expression-overlay.active {
    opacity: 0.8;
}
`;

// Inject styles
const styleSheet = document.createElement('style');
styleSheet.textContent = nanoBananaStyles;
document.head.appendChild(styleSheet);
