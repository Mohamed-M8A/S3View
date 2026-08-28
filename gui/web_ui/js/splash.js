const SplashManager = {
    minDisplayMs: 1100,
    startTime: null,
    el: null,

    markStart() {
        this.startTime = performance.now();
        this.el = document.getElementById('app_splash');
    },

    async hide() {
        if (!this.el) this.el = document.getElementById('app_splash');
        if (!this.el) return;

        const elapsed = performance.now() - (this.startTime || 0);
        const remaining = Math.max(0, this.minDisplayMs - elapsed);

        await new Promise(resolve => setTimeout(resolve, remaining));

        this.el.classList.add('splash-hide');
        setTimeout(() => {
            if (this.el && this.el.parentNode) {
                this.el.parentNode.removeChild(this.el);
            }
        }, 550); // matches the CSS opacity transition duration
    }
};

SplashManager.markStart();
