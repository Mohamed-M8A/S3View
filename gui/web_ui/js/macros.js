const MacroManager = {
    macrosData: {},

    init() {
        this.bindEvents();
    },

    bindEvents() {
        document.getElementById('btn_macro_new').onclick = () => {
            document.getElementById('macro_name_input').value = '';
            document.getElementById('macro_code_input').value = '';
            document.getElementById('macro_name_input').focus();
            document.querySelectorAll('.macro-card').forEach(c => c.classList.remove('active-macro'));
        };

        document.getElementById('btn_macro_save').onclick = async () => {
            const name = document.getElementById('macro_name_input').value.trim();
            const code = document.getElementById('macro_code_input').value;
            if (name && code) {
                const res = await Bridge.saveMacro(name, code);
                if (res.status === 'success') {
                    ConsoleManager.append(`Macro ${name} saved`, "success");
                    await App.reloadData();
                }
            }
        };

        document.getElementById('btn_macro_inject').onclick = () => {
            const code = document.getElementById('macro_code_input').value;
            if (code) {
                EditorManager.injectMacro(code);
                ConsoleManager.append("Macro injected", "info");
            }
        };
    },

    renderList(macros) {
        this.macrosData = macros || {};
        const grid = document.getElementById('macro_grid');
        if (!grid) return;
        grid.innerHTML = '';

        Object.entries(this.macrosData).forEach(([name, code]) => {
            const card = document.createElement('div');
            card.className = 'macro-card';

            const nameSpan = document.createElement('span');
            nameSpan.className = 'macro-item-name';
            nameSpan.textContent = name;

            const actions = document.createElement('div');
            actions.className = 'macro-item-actions';

            const runBtn = document.createElement('button');
            runBtn.className = 'run-direct-btn';
            runBtn.title = 'Execute Direct';
            runBtn.innerHTML = '<svg width="10" height="10"><use href="#icon-play"></use></svg>';

            const delBtn = document.createElement('button');
            delBtn.className = 'delete-macro-btn';
            delBtn.title = 'Delete';
            delBtn.innerHTML = '<svg width="11" height="11"><use href="#icon-trash"></use></svg>';

            actions.appendChild(runBtn);
            actions.appendChild(delBtn);
            card.appendChild(nameSpan);
            card.appendChild(actions);

            card.onclick = (e) => {
                if (e.target.tagName !== 'BUTTON') {
                    document.getElementById('macro_name_input').value = name;
                    document.getElementById('macro_code_input').value = code;
                    document.querySelectorAll('.macro-card').forEach(c => c.classList.remove('active-macro'));
                    card.classList.add('active-macro');
                }
            };

            runBtn.onclick = (e) => { e.stopPropagation(); this.executeDirect(name); };
            delBtn.onclick = (e) => { e.stopPropagation(); this.confirmDelete(name); };

            grid.appendChild(card);
        });
    },

    async executeDirect(name) {
        if (Bridge.isSystemProcessing) return;
        ConsoleManager.append(`Direct execution: ${name}`, "info");
        const isDry = document.getElementById('check_dry_run').checked;
        const res = await Bridge.executePipeline(`RUN "${name}" ;`, isDry);
        App.handleResult(res);
    },

    confirmDelete(name) {
        const modal = document.getElementById('app_modal');
        modal.innerHTML = `
            <div class="modal-box">
                <h3>Delete Macro?</h3>
                <p>Are you sure you want to delete <b>${name}</b> permanently?</p>
                <div class="modal-actions">
                    <button class="primary-btn" id="btn_modal_cancel">CANCEL</button>
                    <button class="primary-btn danger-variant" id="btn_modal_confirm">DELETE</button>
                </div>
            </div>
        `;
        modal.style.display = 'flex';

        document.getElementById('btn_modal_cancel').onclick = () => { modal.style.display = 'none'; };
        document.getElementById('btn_modal_confirm').onclick = () => this.deleteActual(name);
    },

    async deleteActual(name) {
        document.getElementById('app_modal').style.display = 'none';
        const res = await Bridge.deleteMacro(name);
        if (res.status === 'success') {
            ConsoleManager.append(`Macro ${name} deleted`, "info");
            await App.reloadData();
        }
    }
};