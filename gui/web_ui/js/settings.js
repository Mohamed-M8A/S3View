const SettingsManager = {
    init() {
        this.bindEvents();
    },

    renderData(settings) {
        const coreData = {};
        const reportData = {};

        Object.entries(settings).forEach(([k, v]) => {
            if (k.toUpperCase() === 'DRY_RUN') return;
            if (k.toUpperCase() === 'UI_THEME') return;

            if (k.toUpperCase().includes('REPORT')) {
                reportData[k] = v;
            } else {
                coreData[k] = v;
            }
        });

        FormManager.render('form_settings_core', coreData, 'set');
        FormManager.render('form_settings_reports', reportData, 'set');
    },

    bindEvents() {
        document.getElementById('btn_save_settings_final').onclick = async () => {
            const data = FormManager.collect('.set-input');
            const res = await Bridge.saveWorkspace({
                settings: data,
                commands: EditorManager.getCommandsContent(),
                protected: EditorManager.getProtectedContent()
            });
            if (res.status === 'success') {
                ConsoleManager.append("Global settings and workspace updated", "success");
            }
        };
    }
};
