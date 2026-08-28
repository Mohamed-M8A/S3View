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

    bindEvents() {
        const toggle = document.getElementById('btn_console_toggle');
        const consoleEl = document.getElementById('app_console');

        toggle.onclick = () => {
            const collapsed = consoleEl.classList.toggle('console-collapsed');
            toggle.innerText = collapsed ? '▲' : '▼';
            if (window.EditorManager && EditorManager.isReady) {
                setTimeout(() => EditorManager.layout(), 300);
            }
        };

        document.getElementById('btn_console_clear').onclick = () => {
            document.getElementById('console_output').innerHTML = '';
        };

        document.getElementById('btn_console_copy').onclick = () => {
            const text = document.getElementById('console_output').innerText;
            navigator.clipboard.writeText(text);
        };
    }
};
