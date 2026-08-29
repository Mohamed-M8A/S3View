// ============================================================
// MACROS.JS
// Kept standalone: self-contained macro CRUD feature (list, save,
// inject, delete) not tightly coupled to any other module besides
// Bridge/ConsoleManager/EditorManager, which are all global singletons.
// ============================================================

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

    // FIX: previously built via a template-literal innerHTML string that
    // inserted `name` unescaped, so a macro named e.g.
    // `<img src=x onerror=...>` would execute inside the modal. Now the
    // whole modal is built with safe DOM APIs and `name` is only ever
    // set via textContent.
    confirmDelete(name) {
        const modal = document.getElementById('app_modal');
        modal.innerHTML = '';

        const box = document.createElement('div');
        box.className = 'modal-box';

        const heading = document.createElement('h3');
        heading.textContent = 'Delete Macro?';

        const para = document.createElement('p');
        para.append('Are you sure you want to delete ');
        const bold = document.createElement('b');
        bold.textContent = name;
        para.append(bold);
        para.append(' permanently?');

        const actions = document.createElement('div');
        actions.className = 'modal-actions';

        const cancelBtn = document.createElement('button');
        cancelBtn.className = 'primary-btn';
        cancelBtn.id = 'btn_modal_cancel';
        cancelBtn.textContent = 'CANCEL';

        const confirmBtn = document.createElement('button');
        confirmBtn.className = 'primary-btn danger-variant';
        confirmBtn.id = 'btn_modal_confirm';
        confirmBtn.textContent = 'DELETE';

        actions.appendChild(cancelBtn);
        actions.appendChild(confirmBtn);
        box.appendChild(heading);
        box.appendChild(para);
        box.appendChild(actions);
        modal.appendChild(box);
        modal.style.display = 'flex';

        cancelBtn.onclick = () => { modal.style.display = 'none'; };
        confirmBtn.onclick = () => this.deleteActual(name);
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
