// ============================================================
// WORKSPACE.JS
// Merged from: forms.js, settings.js
// Responsibility: dynamic form rendering/collection (credentials,
// settings) and the Settings tab logic that consumes FormManager.
// ============================================================

const FormManager = {
    render(containerId, data, prefix, isVertical = false) {
        const container = document.getElementById(containerId);
        if (!container || !data) return;

        container.innerHTML = '';
        container.classList.toggle('form-vertical', isVertical);

        Object.entries(data).forEach(([key, value]) => {
            const row = document.createElement('div');
            row.className = 'form-row';

            const inputId = `${prefix}_${key.toLowerCase().replace(/\s+/g, '_')}`;

            const label = document.createElement('label');
            label.textContent = key;
            label.setAttribute('for', inputId);
            row.appendChild(label);

            const wrapper = document.createElement('div');
            wrapper.className = 'field-wrapper';

            const isSecret = key.toLowerCase().includes('secret') || key.toLowerCase().includes('key');
            const isBool = typeof value === 'boolean';

            if (isBool) {
                const switchLabel = document.createElement('label');
                switchLabel.className = 'switch';

                const input = document.createElement('input');
                input.type = 'checkbox';
                input.id = inputId;
                input.name = inputId;
                input.className = `${prefix}-input`;
                input.dataset.key = key;
                input.checked = !!value;

                const slider = document.createElement('span');
                slider.className = 'slider';

                switchLabel.appendChild(input);
                switchLabel.appendChild(slider);
                wrapper.appendChild(switchLabel);
            } else if (isSecret) {
                const secretWrap = document.createElement('div');
                secretWrap.className = 'secret-field';

                const input = document.createElement('input');
                input.type = 'password';
                input.id = inputId;
                input.name = inputId;
                input.className = `${prefix}-input`;
                input.dataset.key = key;
                input.value = value;
                input.setAttribute('autocomplete', 'current-password');

                const eyeBtn = document.createElement('button');
                eyeBtn.type = 'button';
                eyeBtn.className = 'eye-toggle-btn';
                eyeBtn.innerHTML = FormManager.eyeIcon(false);
                eyeBtn.onclick = () => FormManager.toggleSecret(eyeBtn, input);

                secretWrap.appendChild(input);
                secretWrap.appendChild(eyeBtn);
                wrapper.appendChild(secretWrap);
            } else {
                const input = document.createElement('input');
                input.type = 'text';
                input.id = inputId;
                input.name = inputId;
                input.className = `${prefix}-input`;
                input.dataset.key = key;
                input.value = value;
                input.setAttribute('autocomplete', 'off');
                wrapper.appendChild(input);
            }

            row.appendChild(wrapper);
            container.appendChild(row);
        });
    },

    eyeIcon(open) {
        return open
            ? '<svg width="14" height="14"><use href="#icon-eye-open"></use></svg>'
            : '<svg width="14" height="14"><use href="#icon-eye-closed"></use></svg>';
    },

    toggleSecret(btn, input) {
        const isHidden = input.type === 'password';
        input.type = isHidden ? 'text' : 'password';
        btn.innerHTML = FormManager.eyeIcon(isHidden);
        btn.classList.toggle('active', isHidden);
    },

    collect(selector) {
        const data = {};
        document.querySelectorAll(selector).forEach(input => {
            const key = input.getAttribute('data-key');
            data[key] = input.type === 'checkbox' ? input.checked : input.value;
        });
        return data;
    }
};


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
        const saveBtn = document.getElementById('btn_save_settings_final');
        if (saveBtn) {
            saveBtn.onclick = async () => {
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
    }
};
