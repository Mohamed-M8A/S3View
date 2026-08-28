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