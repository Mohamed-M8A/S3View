// ============================================================
// CORE.JS
// Merged from: bridge.js, app.js
// Responsibility: pywebview API bridge + top-level app orchestration
// and bootstrapping. Kept together since App depends on Bridge in
// almost every method.
// ============================================================

const Bridge = {
    pywebviewApi: null,
    isSystemProcessing: false,

    async initialize() {
        if (window.pywebview && window.pywebview.api) {
            this.pywebviewApi = window.pywebview.api;
            return;
        }

        return new Promise((resolve) => {
            let settled = false;
            const finish = () => {
                if (settled) return;
                settled = true;
                clearInterval(pollId);
                this.pywebviewApi = window.pywebview ? window.pywebview.api : null;
                resolve();
            };

            window.addEventListener('pywebviewready', finish);
            const pollId = setInterval(() => {
                if (window.pywebview && window.pywebview.api) finish();
            }, 100);

            setTimeout(finish, 5000);
        });
    },

    setProcessingState(state) {
        this.isSystemProcessing = state;
        const mainBtn = document.getElementById('btn_main_execute');
        const sideBtn = document.getElementById('btn_sidebar_execute');

        if (mainBtn) mainBtn.innerText = state ? "PROCESSING..." : "EXECUTE";
        if (sideBtn) sideBtn.innerText = state ? "RUNNING..." : "RUN PIPELINE";

        document.querySelectorAll('button').forEach(btn => {
            if (!btn.classList.contains('console-tab-btn')) {
                btn.disabled = state;
                btn.style.opacity = state ? "0.5" : "1";
            }
        });
    },

    async callInternalApi(methodName, ...args) {
        if (!this.pywebviewApi || !this.pywebviewApi[methodName]) {
            return { status: 'error', message: `API_NOT_FOUND: ${methodName}` };
        }

        this.setProcessingState(true);
        try {
            return await this.pywebviewApi[methodName](...args);
        } catch (error) {
            return { status: 'error', message: error.toString() };
        } finally {
            this.setProcessingState(false);
        }
    },

    async fetchApplicationData() {
        return await this.callInternalApi('get_app_data');
    },

    async executePipeline(script, isDry) {
        return await this.callInternalApi('run_pipeline', script, isDry);
    },

    async saveWorkspace(payload) {
        return await this.callInternalApi('save_workspace', payload);
    },

    async saveMacro(name, code) {
        return await this.callInternalApi('save_macro', name, code);
    },

    async deleteMacro(name) {
        return await this.callInternalApi('delete_macro', name);
    },

    async openReportsFolder() {
        return await this.callInternalApi('open_reports_folder');
    },

    async showLatestReport() {
        return await this.callInternalApi('view_latest_report');
    },

    async listSavedReports() {
        return await this.callInternalApi('list_reports');
    },

    async getReportContent(filename) {
        return await this.callInternalApi('get_report', filename);
    }
};

window.Bridge = Bridge;


const App = {
    async init() {
        const watchdog = setTimeout(() => {
            const out = document.getElementById('console_output');
            if (out) {
                const entry = document.createElement('div');
                entry.className = 'log-error';
                entry.innerText = "[STARTUP ERROR] Sync Timeout - Check Backend Status";
                out.appendChild(entry);
            }
            if (window.SplashManager) SplashManager.hide();
        }, 10000);

        try {
            await Bridge.initialize();
            await EditorManager.init();

            SidebarManager.init();
            ConsoleManager.init();
            MacroManager.init();
            SettingsManager.init();
            ReportsManager.init();
            ThemeManager.init();
            UI.init();

            this.bindGlobalActions();
            this.bindShortcuts();

            await this.loadInitialData();

            window.App = this;
        } catch (err) {
            const out = document.getElementById('console_output');
            if (out) {
                const entry = document.createElement('div');
                entry.className = 'log-error';
                entry.innerText = `[ERROR] ${err.message || err}`;
                out.appendChild(entry);
            }
        } finally {
            clearTimeout(watchdog);
            if (window.SplashManager) SplashManager.hide();
        }
    },

    async loadInitialData() {
        const data = await Bridge.fetchApplicationData();

        if (data.status === 'error') {
            ConsoleManager.append("Load Failed: " + data.message, "error");
            return;
        }

        this.systemMetadata = {
            available_statuses: data.available_statuses
        };

        if (data.plugins_metadata) {
            EditorManager.registerDynamicLanguage(data.plugins_metadata);
            UI.setPluginMeta(data.plugins_metadata);
        }

        if (data.commands_script !== undefined) EditorManager.setCommandsContent(data.commands_script);
        if (data.protected_list !== undefined) EditorManager.setProtectedContent(data.protected_list);

        if (data.credentials) {
            FormManager.render('form_credentials', data.credentials, 'cred', true);
        }

        if (data.settings) {
            const dryRunEl = document.getElementById('check_dry_run');
            if (dryRunEl) dryRunEl.checked = !!data.settings.DRY_RUN;
            SettingsManager.renderData(data.settings);
            ThemeManager.applyFromSettings(data.settings);
        }

        if (data.macros) {
            MacroManager.renderList(data.macros);
        }

        ConsoleManager.append("System Synchronized", "success");
    },

    async executePipeline() {
        const script = EditorManager.getCommandsContent();
        const isDry = document.getElementById('check_dry_run').checked;

        if (!script.trim()) {
            ConsoleManager.append("Error: Script is empty", "error");
            return;
        }

        ConsoleManager.append("Pipeline execution triggered", "info");
        const response = await Bridge.executePipeline(script, isDry);
        this.handleResult(response);
    },

    handleResult(response) {
        if (response.status === 'completed') {
            ConsoleManager.logSummary(response.results);
        } else {
            ConsoleManager.append(response.message || "Execution Error", "error");
        }
    },

    setUILock(state) {
        Bridge.setProcessingState(state);
    },

    async reloadData() {
        ConsoleManager.append("Refreshing workspace...", "info");
        await this.loadInitialData();
    },

    async saveWorkspace() {
        if (Bridge.isSystemProcessing) return;

        ConsoleManager.append("Saving changes...", "info");

        const res = await Bridge.saveWorkspace({
            settings: FormManager.collect('.set-input'),
            credentials: FormManager.collect('.cred-input'),
            commands: EditorManager.getCommandsContent(),
            protected: EditorManager.getProtectedContent()
        });

        if (res.status === 'success') {
            ConsoleManager.append("Workspace saved successfully", "success");
        } else {
            ConsoleManager.append(res.message || "Save operation failed", "error");
        }
    },

    bindShortcuts() {
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && (e.key === 's' || e.key === 'S')) {
                e.preventDefault();
                this.saveWorkspace();
            }
        });
    },

    bindGlobalActions() {
        const executeBtn = document.getElementById('btn_main_execute');
        if (executeBtn) executeBtn.onclick = () => this.executePipeline();

        const saveCredsBtn = document.getElementById('btn_save_creds');
        if (saveCredsBtn) {
            saveCredsBtn.onclick = async () => {
                const creds = FormManager.collect('.cred-input');
                const res = await Bridge.saveWorkspace({ credentials: creds });
                if (res.status === 'success') {
                    ConsoleManager.append("Credentials secured", "success");
                }
            };
        }
    }
};

document.addEventListener('DOMContentLoaded', () => App.init());
