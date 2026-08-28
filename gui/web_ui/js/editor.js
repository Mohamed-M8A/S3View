function s3vInjectBaseStyles() {
    if (document.getElementById('s3v-editor-base-style')) return;
    const style = document.createElement('style');
    style.id = 's3v-editor-base-style';
    style.textContent = `
.s3v-editor-wrap{display:flex;width:100%;height:100%;overflow:auto;background:var(--bg-black);font-family:var(--font-mono);font-size:13px;line-height:20px;box-sizing:border-box}
.s3v-gutter{flex:0 0 auto;padding:8px 10px 8px 14px;text-align:right;color:var(--text-primary);opacity:0.45;user-select:none;border-right:1px solid var(--border);background:var(--bg-black)}
.s3v-gnum{height:20px;line-height:20px}
.s3v-content{flex:1 1 auto;padding:8px 14px;color:var(--text-primary);white-space:pre;outline:none;caret-color:var(--accent);min-height:100%}
.s3v-line{height:20px;line-height:20px;white-space:pre}
.tok-keyword-control{color:#BB86FC;font-weight:bold}
.tok-keyword-direction{color:#BB86FC;font-weight:bold}
.tok-keyword-property{color:#4FC3F7}
.tok-storage-class{color:#03DAC6}
.tok-operator-logic{color:#F97316;font-weight:bold}
.tok-brackets{color:#FFD54F}
.tok-delimiter{color:inherit}
.tok-str{color:#A5D6A7}
.tok-str-esc{color:inherit}
.tok-number-value{color:#FFD54F}
.tok-comment-grey{color:#666666;font-style:italic}
`;
    document.head.appendChild(style);
}

function s3vTokenizeLine(line, rules) {
    const out = [];
    let i = 0;
    const n = line.length;
    while (i < n) {
        if (line[i] === '"') {
            out.push({ t: '"', c: 'str' });
            i++;
            let buf = '';
            while (i < n && line[i] !== '"') {
                if (line[i] === '\\' && i + 1 < n) {
                    if (buf) { out.push({ t: buf, c: 'str' }); buf = ''; }
                    out.push({ t: line.substr(i, 2), c: 'str-esc' });
                    i += 2;
                    continue;
                }
                buf += line[i];
                i++;
            }
            if (buf) out.push({ t: buf, c: 'str' });
            if (i < n) { out.push({ t: '"', c: 'str' }); i++; }
            continue;
        }
        let matched = false;
        for (let k = 0; k < rules.length; k++) {
            const r = rules[k];
            r.re.lastIndex = i;
            const m = r.re.exec(line);
            if (m && m.index === i && m[0].length > 0) {
                out.push({ t: m[0], c: r.cls });
                i += m[0].length;
                matched = true;
                break;
            }
        }
        if (!matched) {
            out.push({ t: line[i], c: null });
            i++;
        }
    }
    return out;
}

function s3vCreateEditor(container) {
    container.innerHTML = '';
    container.classList.add('s3v-editor-wrap');

    const gutter = document.createElement('div');
    gutter.className = 's3v-gutter';
    const content = document.createElement('div');
    content.className = 's3v-content';
    content.contentEditable = 'true';
    content.spellcheck = false;

    container.appendChild(gutter);
    container.appendChild(content);

    const state = { undoStack: [], redoStack: [] };
    let debounceTimer = null;

    function textLenBefore(node, offset) {
        if (node.nodeType === 3) return offset;
        let sum = 0;
        for (let i = 0; i < offset && i < node.childNodes.length; i++) sum += node.childNodes[i].textContent.length;
        return sum;
    }

    function nodeOffsetWithin(line, node, off) {
        if (node === line) return textLenBefore(line, off);
        let total = 0;
        let found = false;
        function walk(n) {
            if (found) return;
            if (n === node) { total += textLenBefore(n, off); found = true; return; }
            if (n.nodeType === 3) { total += n.textContent.length; }
            else { for (const c of n.childNodes) { walk(c); if (found) return; } }
        }
        for (const c of line.childNodes) { walk(c); if (found) break; }
        return total;
    }

    function getCaretOffset() {
        const sel = window.getSelection();
        if (!sel.rangeCount) return 0;
        const range = sel.getRangeAt(0);
        if (!content.contains(range.startContainer)) return 0;
        let offset = 0;
        const lines = content.children;
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            if (line === range.startContainer || line.contains(range.startContainer)) {
                return offset + nodeOffsetWithin(line, range.startContainer, range.startOffset);
            }
            offset += line.textContent.length + 1;
        }
        return offset;
    }

    function placeCaretInLine(line, offset) {
        const sel = window.getSelection();
        const range = document.createRange();
        let remaining = offset;
        let placed = false;
        function walk(n) {
            if (placed) return;
            if (n.nodeType === 3) {
                const len = n.textContent.length;
                if (remaining <= len) { range.setStart(n, remaining); placed = true; return; }
                remaining -= len;
            } else if (n.nodeName === 'BR') {
                if (remaining <= 0) { range.setStartBefore(n); placed = true; }
            } else {
                for (const c of n.childNodes) { walk(c); if (placed) return; }
            }
        }
        walk(line);
        if (!placed) { range.selectNodeContents(line); range.collapse(false); }
        else { range.collapse(true); }
        sel.removeAllRanges();
        sel.addRange(range);
    }

    function setCaretOffset(target) {
        const lines = content.children;
        let remaining = target;
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            const len = line.textContent.length;
            if (remaining <= len) { placeCaretInLine(line, remaining); return; }
            remaining -= len + 1;
        }
        if (lines.length) placeCaretInLine(lines[lines.length - 1], lines[lines.length - 1].textContent.length);
    }

    function getValue() {
        return Array.from(content.children).map(l => l.textContent).join('\n');
    }

    function buildLineDOM(text) {
        const div = document.createElement('div');
        div.className = 's3v-line';
        if (text.length === 0) { div.appendChild(document.createElement('br')); return div; }
        const tokens = s3vTokenizeLine(text, EditorManager._rules);
        tokens.forEach(tok => {
            if (tok.c) {
                const span = document.createElement('span');
                span.className = 'tok-' + tok.c;
                span.textContent = tok.t;
                div.appendChild(span);
            } else {
                div.appendChild(document.createTextNode(tok.t));
            }
        });
        return div;
    }

    function updateGutter(n) {
        if (gutter.childElementCount === n) return;
        let html = '';
        for (let i = 1; i <= n; i++) html += '<div class="s3v-gnum">' + i + '</div>';
        gutter.innerHTML = html;
    }

    function render(text, caretOffset) {
        content.innerHTML = '';
        const lines = text.split('\n');
        lines.forEach(l => content.appendChild(buildLineDOM(l)));
        updateGutter(lines.length);
        if (caretOffset != null) setCaretOffset(caretOffset);
    }

    function pushUndo(text, caret) {
        const last = state.undoStack[state.undoStack.length - 1];
        if (last && last.text === text) return;
        state.undoStack.push({ text: text, caret: caret });
        if (state.undoStack.length > 200) state.undoStack.shift();
        state.redoStack.length = 0;
    }

    function scheduleUndoPush(text, caret) {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => pushUndo(text, caret), 300);
    }

    function undo() {
        if (state.undoStack.length < 2) return;
        const cur = state.undoStack.pop();
        state.redoStack.push(cur);
        const prev = state.undoStack[state.undoStack.length - 1];
        render(prev.text, prev.caret);
    }

    function redo() {
        if (!state.redoStack.length) return;
        const next = state.redoStack.pop();
        state.undoStack.push(next);
        render(next.text, next.caret);
    }

    content.addEventListener('input', () => {
        const caret = getCaretOffset();
        const text = getValue();
        render(text, caret);
        scheduleUndoPush(text, caret);
    });

    content.addEventListener('keydown', (e) => {
        if (e.key === 'Tab') {
            e.preventDefault();
            document.execCommand('insertText', false, '    ');
        } else if ((e.ctrlKey || e.metaKey) && !e.shiftKey && (e.key === 'z' || e.key === 'Z')) {
            e.preventDefault();
            undo();
        } else if ((e.ctrlKey || e.metaKey) && ((e.key === 'y' || e.key === 'Y') || (e.shiftKey && (e.key === 'z' || e.key === 'Z')))) {
            e.preventDefault();
            redo();
        }
    });

    function setValue(text) {
        render(text || '', 0);
        state.undoStack = [{ text: text || '', caret: 0 }];
        state.redoStack = [];
    }

    function refresh() {
        const t = getValue();
        render(t);
    }

    function scrollToEnd() {
        container.scrollTop = container.scrollHeight;
    }

    return {
        getValue: getValue,
        setValue: setValue,
        refresh: refresh,
        layout: function () {},
        focus: function () { content.focus(); },
        scrollToEnd: scrollToEnd
    };
}

const EditorManager = {
    editors: {},
    isReady: false,
    _rules: [],
    _pluginStyleEl: null,

    init() {
        return new Promise((resolve) => {
            s3vInjectBaseStyles();
            this.editors.commands = s3vCreateEditor(document.getElementById('monaco_commands_container'));
            this.editors.protected = s3vCreateEditor(document.getElementById('monaco_protected_container'));
            this.isReady = true;
            resolve();
        });
    },

    layout() {
        Object.values(this.editors).forEach(e => e.layout());
    },

    registerDynamicLanguage(plugins) {
        if (!plugins) return;
        const pluginRules = plugins.map(p => ({
            re: new RegExp('\\b(' + p.keywords.join('|') + ')\\b', 'iy'),
            cls: 'plugin-' + p.action
        }));

        this._rules = [
            ...pluginRules,
            { re: /\b(where|limit|depth|tier|expires)\b/y, cls: 'keyword-control' },
            { re: /\b(to|\*to)\b/y, cls: 'keyword-direction' },
            { re: /\b(size|sum|count|age|date|sname|ename|type|tier|regex)\b(?=:|[><=])/y, cls: 'keyword-property' },
            { re: /\b(STANDARD|STANDARD_IA|GLACIER|GLACIER_IR|DEEP_ARCHIVE|INTELLIGENT_TIERING|ONEZONE_IA|REDUCED_REDUNDANCY)\b/y, cls: 'storage-class' },
            { re: /[><=]=?|&|!/y, cls: 'operator-logic' },
            { re: /[{}()\[\]]/y, cls: 'brackets' },
            { re: /[;:]/y, cls: 'delimiter' },
            { re: /\b\d+(\.\d+)?(KB|MB|GB|TB|B|D|H|M)?\b/iy, cls: 'number-value' },
            { re: /\/\/.*/y, cls: 'comment-grey' }
        ];

        let css = '';
        plugins.forEach(p => {
            let color = (p.color || '#cccccc').trim().replace('#', '');
            if (color.length === 3) color = color.split('').map(c => c + c).join('');
            css += '.tok-plugin-' + p.action + '{color:#' + color + ';font-weight:bold}';
        });

        if (!this._pluginStyleEl) {
            this._pluginStyleEl = document.createElement('style');
            document.head.appendChild(this._pluginStyleEl);
        }
        this._pluginStyleEl.textContent = css;

        Object.values(this.editors).forEach(e => e.refresh());
    },

    applyTheme(plugins) {
        this.registerDynamicLanguage(plugins);
    },

    getCommandsContent() { return this.editors.commands ? this.editors.commands.getValue() : ""; },
    setCommandsContent(content) { if (this.editors.commands) this.editors.commands.setValue(content || ""); },
    getProtectedContent() { return this.editors.protected ? this.editors.protected.getValue() : ""; },
    setProtectedContent(content) { if (this.editors.protected) this.editors.protected.setValue(content || ""); },

    injectMacro(code) {
        if (!this.editors.commands) return;
        const cur = this.editors.commands.getValue();
        this.editors.commands.setValue(cur ? cur + '\n' + code : code);
        this.editors.commands.scrollToEnd();
        this.editors.commands.focus();
    }
};
