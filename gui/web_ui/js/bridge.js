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