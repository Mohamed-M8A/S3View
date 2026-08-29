const ThemeManager = {
    // Reduced to 2 themes, both dark, per request: a true #000000 theme
    // and a GitHub Dark–style theme. Folders renamed to match:
    // css/theme-true-black/theme.css and css/theme-github-dark/theme.css.
    // All 7 previous theme folders should be deleted from css/.
    themes: [
        { id: 'theme-true-black', label: 'True Black', swatch: '#e8a33d' },
        { id: 'theme-github-dark', label: 'GitHub Dark', swatch: '#58a6ff' }
    ],

    defaultTheme: 'theme-true-black',
    activeTheme: null,
    linkEl: null,

    init() {
        this.linkEl = document.getElementById('theme_style');
        this.renderSwitcher();
        // Applied here as a safe fallback; App.loadInitialData() will call
        // applyFromSettings() once real settings arrive from the backend.
        this.apply(this.defaultTheme, false);
    },

    // Called from core.js right after settings are loaded from Python,
    // so a previously saved theme choice (UI_THEME) persists across runs.
    applyFromSettings(settings) {
        const saved = settings && settings.UI_THEME;
        const valid = this.themes.some(t => t.id === saved);
        this.apply(valid ? saved : this.defaultTheme, false);
    },

    apply(themeId, persist = true) {
        const theme = this.themes.find(t => t.id === themeId) || this.themes[0];
        this.activeTheme = theme.id;
        if (this.linkEl) {
            this.linkEl.setAttribute('href', `css/${theme.id}/theme.css`);
        }
        this.updateSwitcherState();

        if (persist) this.persist(theme.id);
    },

    async persist(themeId) {
        try {
            await Bridge.saveWorkspace({ settings: { UI_THEME: themeId } });
        } catch (e) {
            // Non-fatal: theme still applies visually even if save fails
        }
    },

    renderSwitcher() {
        const container = document.getElementById('theme_switcher');
        if (!container) return;
        container.innerHTML = '';

        this.themes.forEach(theme => {
            const dot = document.createElement('button');
            dot.type = 'button';
            dot.className = 'theme-dot';
            dot.title = theme.label;
            dot.style.setProperty('--dot-color', theme.swatch);
            dot.dataset.themeId = theme.id;
            dot.onclick = () => this.apply(theme.id, true);
            container.appendChild(dot);
        });
    },

    updateSwitcherState() {
        const dots = document.querySelectorAll('.theme-dot');
        dots.forEach(dot => {
            dot.classList.toggle('active', dot.dataset.themeId === this.activeTheme);
        });
    }
};
