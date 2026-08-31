// ============================================================
// SHELL.JS
// Merged from: splash.js, console.js, sidebar.js, ui.js
// Responsibility: app chrome (splash screen, system console,
// sidebar navigation, tab switching). No business/API logic here.
// ============================================================

const SplashManager = {
    minDisplayMs: 1100,

    // FIX: independent safety net. Previously the only timeout that could
    // force-hide the splash lived *inside* App.init() (core.js). If
    // core.js ever failed to load or parse (404, typo'd path, syntax
    // error, etc.) that watchdog was never even created, and nothing
    // else in the app could close the splash -- it would sit there
    // forever. This timer is scheduled here instead, in the very first
    // script that runs, so it fires no matter what happens to any other
    // file. core.js still has its own (shorter) watchdog for the normal
    // "backend is just slow" case; this one is the last line of defense.
    maxDisplayMs: 12000,

    startTime: null,
    el: null,
    _hidden: false,
    _failsafeTimer: null,

    markStart() {
        this.startTime = performance.now();
        this.el = document.getElementById('app_splash');
        this._failsafeTimer = setTimeout(() => this.hide(), this.maxDisplayMs);
    },

    async hide() {
        // FIX: idempotent. App.init()'s own watchdog and this failsafe can
        // both legitimately fire (e.g. one right after the other) -- make
        // sure a second call is a harmless no-op instead of re-running the
        // fade/remove sequence on an already-detached node.
        if (this._hidden) return;
        this._hidden = true;

        if (this._failsafeTimer) {
            clearTimeout(this._failsafeTimer);
            this._failsafeTimer = null;
        }

        if (!this.el) this.el = document.getElementById('app_splash');
        if (!this.el) return;

        const elapsed = performance.now() - (this.startTime || 0);
        const remaining = Math.max(0, this.minDisplayMs - elapsed);

        await new Promise(resolve => setTimeout(resolve, remaining));

        // FIX: set this directly from JS rather than relying on the CSS
        // theme file to define it on `.splash-hide`. Guarantees the
        // fading splash can never intercept clicks on the app underneath
        // it during the 550ms transition, regardless of what any given
        // theme.css does or doesn't define.
        this.el.style.pointerEvents = 'none';
        this.el.classList.add('splash-hide');

        setTimeout(() => {
            if (this.el && this.el.parentNode) {
                this.el.parentNode.removeChild(this.el);
            }
            this.el = null;
        }, 550); // matches the CSS opacity transition duration
    }
};

// Must run immediately at parse time so the elapsed-time calculation
// in hide() is accurate, and so the failsafe timer above starts
// counting from page load rather than from whenever core.js happens
// to finish. Keep this call at the top of the merged file.
SplashManager.markStart();


const ConsoleManager = {
    init() {
        this.bindEvents();
    },

    append(message, logType = 'info') {
        const consoleElement = document.getElementById('console_output');
        if (!consoleElement) return;

        const logEntry = document.createElement('div');
        logEntry.className = `log-${logType}`;

        const timestamp = new Date().toLocaleTimeString();

        if (logType === 'info' && message.includes('Step_')) {
            const parts = message.split('_');
            const action = parts[parts.length - 1].toLowerCase();
            const color = (window.UI && UI.pluginColors[action]) ? UI.pluginColors[action] : 'var(--accent)';
            logEntry.innerHTML = `[${timestamp}] <span style="color:${color}; font-weight:bold">${message.toUpperCase()}</span>`;
        } else {
            logEntry.innerText = `[${timestamp}] ${message}`;
        }

        consoleElement.appendChild(logEntry);
        consoleElement.scrollTop = consoleElement.scrollHeight;
    },

    logSummary(results) {
        if (!results) return;
        let totalFiles = 0;
        let totalSize = 0;

        Object.values(results).forEach(step => {
            if (step && typeof step === 'object') {
                totalFiles += (step.count || 0);
                totalSize += (step.total_size || 0);
            }
        });

        const sizeStr = this.formatBytes(totalSize);
        this.append(`Pipeline Result | Processed: ${totalFiles} | Total Volume: ${sizeStr}`, 'success');
    },

    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    // FIX: every lookup is now null-checked before use. Previously a
    // missing element here (e.g. #btn_console_toggle) threw inside
    // App.init()'s try-block and silently aborted the rest of startup
    // (Macro/Settings/Reports/Theme/UI managers never got initialized).
    bindEvents() {
        const toggle = document.getElementById('btn_console_toggle');
        const consoleEl = document.getElementById('app_console');

        if (toggle && consoleEl) {
            toggle.onclick = () => {
                const collapsed = consoleEl.classList.toggle('console-collapsed');
                toggle.innerText = collapsed ? '▲' : '▼';
                if (window.EditorManager && EditorManager.isReady) {
                    setTimeout(() => EditorManager.layout(), 300);
                }
            };
        }

        const clearBtn = document.getElementById('btn_console_clear');
        if (clearBtn) {
            clearBtn.onclick = () => {
                const out = document.getElementById('console_output');
                if (out) out.innerHTML = '';
            };
        }

        const copyBtn = document.getElementById('btn_console_copy');
        if (copyBtn) {
            copyBtn.onclick = () => {
                const out = document.getElementById('console_output');
                if (out) navigator.clipboard.writeText(out.innerText);
            };
        }
    }
};


const SidebarManager = {
    init() {
        this.bindEvents();
    },

    bindEvents() {
        const execBtn = document.getElementById('btn_sidebar_execute');
        if (execBtn) execBtn.onclick = () => { if (window.App) App.executePipeline(); };

        const reportsBtn = document.getElementById('btn_nav_reports');
        if (reportsBtn) reportsBtn.onclick = () => Bridge.openReportsFolder();

        const latestBtn = document.getElementById('btn_nav_latest');
        if (latestBtn) latestBtn.onclick = () => Bridge.showLatestReport();
    }
};


const UI = {
    pluginColors: {},
    statusColors: {},
    availableStatuses: new Set(["ERROR", "SKIPPED"]),

    init() {
        this.bindTabs();
    },

    setPluginMeta(meta) {
        if (!meta) return;
        meta.forEach(plugin => {
            const color = plugin.color || '#cccccc';
            this.pluginColors[plugin.action.toLowerCase()] = color;

            if (plugin.exec_status) {
                this.availableStatuses.add(plugin.exec_status);
                this.statusColors[plugin.exec_status.toUpperCase()] = color;
            }
            if (plugin.sim_status) {
                this.availableStatuses.add(plugin.sim_status);
                this.statusColors[plugin.sim_status.toUpperCase()] = color;
            }
        });
    },

    bindTabs() {
        const tabs = document.querySelectorAll('#tab_group .tab-item');
        const panels = document.querySelectorAll('.view-panel');

        tabs.forEach(tab => {
            tab.onclick = () => {
                const targetId = tab.getAttribute('data-target');
                const targetView = document.getElementById(targetId);
                if (!targetView) return;

                tabs.forEach(t => t.classList.remove('active'));
                panels.forEach(p => p.classList.remove('active'));

                tab.classList.add('active');
                targetView.classList.add('active');

                if (window.EditorManager && EditorManager.isReady) {
                    setTimeout(() => {
                        if (EditorManager.editors.commands) EditorManager.editors.commands.layout();
                        if (EditorManager.editors.protected) EditorManager.editors.protected.layout();
                    }, 50);
                }

                if (targetId === 'view_reports' && window.ReportsManager) {
                    ReportsManager.onShow();
                }
            };
        });
    }
};
