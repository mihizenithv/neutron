/**
 * NEUTRON Particle System
 * Ambient floating particles for background atmosphere
 */

const Particles = {
    canvas: null,
    ctx: null,
    particles: [],
    config: {
        count: 50,
        maxSize: 3,
        minSize: 1,
        maxSpeed: 0.3,
        colors: ['rgba(0, 212, 255, 0.5)', 'rgba(106, 58, 237, 0.4)', 'rgba(6, 255, 165, 0.4)'],
        connectionDistance: 150,
        connectionOpacity: 0.1,
    },
    animationFrame: null,

    init() {
        this.canvas = document.getElementById('particle-canvas');
        if (!this.canvas) return;

        this.ctx = this.canvas.getContext('2d');
        this.resize();
        this.createParticles();
        this.animate();

        window.addEventListener('resize', () => this.resize());
        console.log('[Particles] Initialized');
    },

    resize() {
        if (!this.canvas) return;
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
    },

    createParticles() {
        this.particles = [];
        for (let i = 0; i < this.config.count; i++) {
            this.particles.push({
                x: Math.random() * this.canvas.width,
                y: Math.random() * this.canvas.height,
                size: Math.random() * (this.config.maxSize - this.config.minSize) + this.config.minSize,
                speedX: (Math.random() - 0.5) * this.config.maxSpeed,
                speedY: (Math.random() - 0.5) * this.config.maxSpeed,
                color: this.config.colors[Math.floor(Math.random() * this.config.colors.length)],
                pulse: Math.random() * Math.PI * 2,
                pulseSpeed: 0.02 + Math.random() * 0.02,
            });
        }
    },

    animate() {
        if (!this.ctx) return;

        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // Update and draw particles
        this.particles.forEach((p, i) => {
            // Update position
            p.x += p.speedX;
            p.y += p.speedY;
            p.pulse += p.pulseSpeed;

            // Wrap around edges
            if (p.x < 0) p.x = this.canvas.width;
            if (p.x > this.canvas.width) p.x = 0;
            if (p.y < 0) p.y = this.canvas.height;
            if (p.y > this.canvas.height) p.y = 0;

            // Pulsing size
            const pulseSize = p.size + Math.sin(p.pulse) * 0.5;

            // Draw particle
            this.ctx.beginPath();
            this.ctx.arc(p.x, p.y, pulseSize, 0, Math.PI * 2);
            this.ctx.fillStyle = p.color;
            this.ctx.fill();

            // Draw connections
            for (let j = i + 1; j < this.particles.length; j++) {
                const p2 = this.particles[j];
                const dx = p.x - p2.x;
                const dy = p.y - p2.y;
                const distance = Math.sqrt(dx * dx + dy * dy);

                if (distance < this.config.connectionDistance) {
                    const opacity = (1 - distance / this.config.connectionDistance) * this.config.connectionOpacity;
                    this.ctx.beginPath();
                    this.ctx.moveTo(p.x, p.y);
                    this.ctx.lineTo(p2.x, p2.y);
                    this.ctx.strokeStyle = `rgba(0, 212, 255, ${opacity})`;
                    this.ctx.lineWidth = 0.5;
                    this.ctx.stroke();
                }
            }
        });

        this.animationFrame = requestAnimationFrame(() => this.animate());
    },

    // React to audio/emotion
    pulse(intensity = 1) {
        this.particles.forEach(p => {
            p.speedX += (Math.random() - 0.5) * intensity * 0.5;
            p.speedY += (Math.random() - 0.5) * intensity * 0.5;

            // Clamp speed
            const maxSpeed = this.config.maxSpeed * 3;
            p.speedX = Math.max(-maxSpeed, Math.min(maxSpeed, p.speedX));
            p.speedY = Math.max(-maxSpeed, Math.min(maxSpeed, p.speedY));
        });

        // Gradually return to normal speed
        setTimeout(() => {
            this.particles.forEach(p => {
                p.speedX *= 0.9;
                p.speedY *= 0.9;
            });
        }, 500);
    },

    setMood(mood) {
        const moodColors = {
            happy: ['rgba(0, 255, 136, 0.5)', 'rgba(0, 204, 102, 0.4)'],
            sad: ['rgba(107, 138, 255, 0.5)', 'rgba(68, 102, 204, 0.4)'],
            excited: ['rgba(255, 107, 53, 0.5)', 'rgba(255, 136, 85, 0.4)'],
            calm: ['rgba(0, 212, 255, 0.5)', 'rgba(106, 58, 237, 0.4)'],
            focused: ['rgba(168, 85, 247, 0.5)', 'rgba(124, 58, 237, 0.4)'],
        };

        if (moodColors[mood]) {
            this.particles.forEach(p => {
                p.color = moodColors[mood][Math.floor(Math.random() * moodColors[mood].length)];
            });
        }
    },

    destroy() {
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
        }
    }
};

// Auto-init when DOM ready
document.addEventListener('DOMContentLoaded', () => {
    Particles.init();
});
