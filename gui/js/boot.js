/**
 * NEUTRON Boot Animation v3
 * Premium boot sequence with smooth transitions
 */

const Boot = {
    bootComplete: false,
    statusMessages: [
        'Initializing neural pathways...',
        'Loading DeepSeek R1...',
        'Connecting to consciousness...',
        'Calibrating emotions...',
        'Starting vision system...',
        'Ready.',
    ],
    currentStatus: 0,

    init() {
        console.log('[Boot] Starting boot sequence');
        this.animateStatus();
    },

    animateStatus() {
        const statusEl = document.querySelector('.boot-status');
        if (!statusEl) return;

        const showNext = () => {
            if (this.currentStatus < this.statusMessages.length) {
                statusEl.textContent = this.statusMessages[this.currentStatus];
                this.currentStatus++;
                setTimeout(showNext, 400);
            }
        };

        showNext();
    },

    onConnectionSuccess() {
        if (this.bootComplete) return;

        console.log('[Boot] Connection successful, completing boot...');

        const bootScreen = document.getElementById('boot-screen');
        const mainScreen = document.getElementById('main-screen');
        const statusEl = document.querySelector('.boot-status');

        if (statusEl) {
            statusEl.textContent = 'Ready.';
        }

        // Fade out boot screen
        setTimeout(() => {
            if (bootScreen) {
                bootScreen.style.transition = 'opacity 0.5s ease-out';
                bootScreen.style.opacity = '0';
            }

            setTimeout(() => {
                if (bootScreen) bootScreen.classList.add('hidden');
                if (mainScreen) {
                    mainScreen.classList.remove('hidden');
                    mainScreen.style.opacity = '0';
                    mainScreen.style.transition = 'opacity 0.8s ease-out';

                    // Trigger reflow
                    mainScreen.offsetHeight;

                    mainScreen.style.opacity = '1';
                }

                this.bootComplete = true;
                console.log('[Boot] Boot complete');
            }, 500);
        }, 500);
    },

    onConnectionFailure() {
        console.log('[Boot] Connection failed');

        const bootScreen = document.getElementById('boot-screen');
        const errorScreen = document.getElementById('error-screen');

        if (bootScreen) bootScreen.classList.add('hidden');
        if (errorScreen) errorScreen.classList.remove('hidden');
    },

    destroy() {
        // Cleanup
    }
};

// Auto-start boot on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    Boot.init();

    // Auto-complete boot after 2.5 seconds for standalone mode
    setTimeout(() => {
        if (!Boot.bootComplete) {
            Boot.onConnectionSuccess();
        }
    }, 2500);
});
