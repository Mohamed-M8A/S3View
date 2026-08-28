const ThemeManager = {
    // Registry of the 7 self-contained themes. Add a new folder + entry
    // here to introduce another theme later without touching anything else.
    themes: [
        { id: 'theme-01-obsidian', label: 'Obsidian', swatch: '#3b82f6' },
        { id: 'theme-02-crimson', label: 'Crimson', swatch: '#ef4444' },
        { id: 'theme-03-emerald', label: 'Emerald', swatch: '#10b981' },
        { id: 'theme-04-royal', label: 'Royal', swatch: '#a855f7' },
        { id: 'theme-05-daylight', label: 'Daylight', swatch: '#2563eb' },
        { id: 'theme-06-navy', label: 'Navy', swatch: '#1e40af' },
        { id: 'theme-07-azure', label: 'Azure', swatch: '#2f7dde' }
    ],

    defaultTheme: 'theme-01-obsidian',
    activeTheme: null,
    linkEl: null,

    init() {
        this.linkEl = document.getElementById('theme_style');
        this.renderSwitcher();
        // Applied here as a safe fallback; App.loadInitialData() will call
        // applyFromSettings() once real settings arrive from the backend.
        this.apply(this.defaultTheme, false);
    },

    // Called from app.js right after settings are loaded from Python,
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
