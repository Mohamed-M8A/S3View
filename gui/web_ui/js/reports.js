const ReportsManager = {
    allRows: [],
    filteredRows: [],
    currentPage: 1,
    PAGE_SIZE: 100,
    sortCol: null,
    sortDir: 1,
    hiddenCols: new Set(),
    loaded: false,
    dom: {},

    COLS: [
        { key: 'status', label: 'STATUS', render: r => `<span class="status-tag" style="color:${ReportsManager.resolveColor(r.status)};border-color:${ReportsManager.resolveColor(r.status)}">${r.status}</span>` },
        { key: 'path', label: 'OBJECT PATH', cls: 'path-cell', render: r => `<span title="${ReportsManager.esc(r.path)}">${ReportsManager.esc(r.path)}</span>` },
        { key: 'size', label: 'SIZE', cls: 'size-col', render: r => ReportsManager.formatSize(r.size) },
        { key: 'date', label: 'TIMESTAMP', cls: 'date-col', render: r => ReportsManager.esc(r.date) },
        { key: 'tier', label: 'TIER', cls: 'tier-col', render: r => ReportsManager.esc(r.tier) }
    ],

    init() {
        this.cacheDom();
        this.bindEvents();
    },

    cacheDom() {
        this.dom = {
            fileSelect: document.getElementById('reports_file_select'),
            refreshBtn: document.getElementById('btn_reports_refresh'),
            dashboard: document.getElementById('reports_dashboard'),
            insights: document.getElementById('reports_insights'),
            controls: document.getElementById('reports_controls'),
            tableContainer: document.getElementById('reports_table_container'),
            emptyState: document.getElementById('reports_empty_state'),
            tbody: document.getElementById('reports_table_body'),
            theadRow: document.getElementById('reports_thead_row'),
            fPath: document.getElementById('reports_f_path'),
            fOp: document.getElementById('reports_f_op'),
            opMenu: document.getElementById('reports_op_menu'),
            fExt: document.getElementById('reports_f_ext'),
            fStart: document.getElementById('reports_f_date_start'),
            fEnd: document.getElementById('reports_f_date_end'),
            countVal: document.getElementById('reports_count_val'),
            volVal: document.getElementById('reports_vol_val'),
            errVal: document.getElementById('reports_err_val'),
            fileVal: document.getElementById('reports_file_val'),
            insExt: document.getElementById('reports_ins_ext'),
            insLargest: document.getElementById('reports_ins_largest'),
            insAvg: document.getElementById('reports_ins_avg'),
            insLatest: document.getElementById('reports_ins_latest')
        };
    },

    bindEvents() {
        this.dom.refreshBtn.onclick = () => this.loadFileList();

        this.dom.fileSelect.onchange = () => {
            const filename = this.dom.fileSelect.value;
            if (filename) this.loadReport(filename);
        };

        this.dom.fPath.addEventListener('input', () => this.applyFilters());
        this.dom.fExt.addEventListener('input', () => this.applyFilters());
        this.dom.fStart.addEventListener('change', () => this.applyFilters());
        this.dom.fEnd.addEventListener('change', () => this.applyFilters());

        this.dom.fOp.onclick = (e) => {
            e.stopPropagation();
            const open = this.dom.opMenu.style.display === 'block';
            this.closeAllCombos();
            this.dom.opMenu.style.display = open ? 'none' : 'block';
        };

        this.dom.opMenu.querySelectorAll('.combo-option').forEach(opt => {
            opt.onclick = () => {
                this.dom.fOp.value = opt.textContent;
                this.dom.fOp.dataset.val = opt.dataset.value;
                this.closeAllCombos();
                this.applyFilters();
            };
        });

        document.addEventListener('click', () => this.closeAllCombos());

        document.getElementById('btn_reports_reset').onclick = () => this.resetFilters();
        document.getElementById('btn_reports_export').onclick = () => this.exportCSV();

        document.querySelectorAll('#view_reports .toggle-btn').forEach(btn => {
            btn.onclick = () => this.toggleColumn(parseInt(btn.dataset.colIdx), btn);
        });

        document.querySelectorAll('#reports_table_container .btn-prev').forEach(b => b.onclick = () => this.changePage(-1));
        document.querySelectorAll('#reports_table_container .btn-next').forEach(b => b.onclick = () => this.changePage(1));
        document.querySelectorAll('#reports_table_container .f-goto-page').forEach(i => {
            i.onkeydown = (e) => { if (e.key === 'Enter') this.gotoPage(i.value); };
        });
    },

    closeAllCombos() {
        document.querySelectorAll('#view_reports .combo-dropdown').forEach(d => d.style.display = 'none');
    },

    async onShow() {
        if (!this.loaded) {
            this.loaded = true;
            await this.loadFileList();
        }
    },

    async loadFileList() {
        const files = await Bridge.listSavedReports();
        this.dom.fileSelect.innerHTML = '<option value="">Select report file...</option>';
        if (Array.isArray(files)) {
            files.forEach(f => {
                const opt = document.createElement('option');
                opt.value = f;
                opt.textContent = f;
                this.dom.fileSelect.appendChild(opt);
            });
        }
    },

    async loadReport(filename) {
        const report = await Bridge.getReportContent(filename);
        if (!report || report.error) {
            ConsoleManager.append(report && report.error ? report.error : 'Failed to load report', 'error');
            return;
        }
        this.dom.fileVal.textContent = filename;
        this.loadData(report);
    },

    loadData(json) {
        this.allRows = [];
        const keysMap = {
            archived: 'ARCHIVED',
            synced: 'SYNCED',
            moved: 'MOVED',
            deleted: 'DELETED',
            uploaded: 'UPLOADED',
            downloaded: 'DOWNLOADED',
            copied: 'COPIED',
            files: 'FOUND',
            skipped: 'SKIPPED',
            errors: 'ERROR'
        };

        Object.keys(json).forEach(stepKey => {
            const data = json[stepKey];
            if (typeof data !== 'object' || data === null) return;

            Object.entries(keysMap).forEach(([jsonKey, label]) => {
                if (Array.isArray(data[jsonKey])) {
                    data[jsonKey].forEach(o => {
                        this.allRows.push({
                            status: label,
                            path: typeof o === 'string' ? o : (o.key || o.path || 'N/A'),
                            size: typeof o === 'object' ? (o.size || 0) : 0,
                            date: typeof o === 'object' ? (o.last_mod || o.date || 'N/A') : 'N/A',
                            tier: typeof o === 'object' ? (o.StorageClass || o.tier || 'STD') : 'N/A',
                            step: stepKey.toUpperCase()
                        });
                    });
                }
            });
        });

        if (this.allRows.length === 0) {
            this.dom.dashboard.classList.add('hidden');
            this.dom.insights.classList.add('hidden');
            this.dom.controls.classList.add('hidden');
            this.dom.tableContainer.classList.add('hidden');
            this.dom.emptyState.classList.remove('hidden');
            return;
        }

        this.dom.emptyState.classList.add('hidden');
        this.dom.dashboard.classList.remove('hidden');
        this.dom.insights.classList.remove('hidden');
        this.dom.controls.classList.remove('hidden');
        this.dom.tableContainer.classList.remove('hidden');

        this.filteredRows = [...this.allRows];
        this.currentPage = 1;
        this.buildHeader();
        this.renderPage();
        this.updateStats(this.filteredRows);
    },

    resolveColor(status) {
        const s = status.toLowerCase();
        const variants = [s, s.replace(/d$/, ''), s.replace(/ed$/, ''), s.replace(/s$/, '')];
        const colors = (window.UI && UI.pluginColors) ? UI.pluginColors : {};
        for (const v of variants) {
            if (colors[v]) return colors[v];
        }
        const fallback = { found: '#3b82f6', skipped: '#666666', error: '#ff3333' };
        return fallback[s] || '#888888';
    },

    buildHeader() {
        this.dom.theadRow.innerHTML = '';
        this.COLS.forEach((col, idx) => {
            const th = document.createElement('th');
            th.id = `reports_th_${idx}`;
            if (this.hiddenCols.has(idx)) th.classList.add('hidden-col');
            if (col.key === this.sortCol) th.classList.add(this.sortDir === 1 ? 'sorted-asc' : 'sorted-desc');
            const label = document.createElement('span');
            label.className = 'th-label';
            label.innerHTML = `${col.label}<span class="sort-arrow"></span>`;
            label.onclick = () => this.doSort(col.key, th);
            th.appendChild(label);
            this.dom.theadRow.appendChild(th);
        });
    },

    doSort(col, th) {
        if (this.sortCol === col) this.sortDir *= -1;
        else {
            this.sortCol = col;
            this.sortDir = 1;
        }
        this.dom.theadRow.querySelectorAll('th').forEach(t => t.classList.remove('sorted-asc', 'sorted-desc'));
        th.classList.add(this.sortDir === 1 ? 'sorted-asc' : 'sorted-desc');
        this.filteredRows.sort((a, b) => col === 'size'
            ? ((parseInt(a.size) || 0) - (parseInt(b.size) || 0)) * this.sortDir
            : String(a[col] || '').localeCompare(String(b[col] || '')) * this.sortDir);
        this.currentPage = 1;
        this.renderPage();
    },

    toggleColumn(idx, btn) {
        if (this.hiddenCols.has(idx)) {
            this.hiddenCols.delete(idx);
            btn.classList.add('active');
            document.getElementById(`reports_th_${idx}`).classList.remove('hidden-col');
        } else {
            this.hiddenCols.add(idx);
            btn.classList.remove('active');
            document.getElementById(`reports_th_${idx}`).classList.add('hidden-col');
        }
        this.renderPage();
    },

    renderPage() {
        const total = this.filteredRows.length;
        const pages = Math.max(1, Math.ceil(total / this.PAGE_SIZE));
        if (this.currentPage > pages) this.currentPage = pages;
        if (this.currentPage < 1) this.currentPage = 1;

        const slice = this.filteredRows.slice((this.currentPage - 1) * this.PAGE_SIZE, this.currentPage * this.PAGE_SIZE);
        this.dom.tbody.innerHTML = slice.length === 0
            ? `<tr><td colspan="${this.COLS.length}"><div class="empty-state">No records match filters</div></td></tr>`
            : slice.map(r => `<tr>${this.COLS.map((c, idx) => `<td class="${c.cls || ''} ${this.hiddenCols.has(idx) ? 'hidden-col' : ''}">${c.render(r)}</td>`).join('')}</tr>`).join('');

        document.querySelectorAll('#reports_table_container .page-info').forEach(el => el.textContent = `PAGE ${this.currentPage} / ${pages} (${total} ITEMS)`);
        document.querySelectorAll('#reports_table_container .btn-prev').forEach(b => b.disabled = this.currentPage <= 1);
        document.querySelectorAll('#reports_table_container .btn-next').forEach(b => b.disabled = this.currentPage >= pages);
        document.querySelectorAll('#reports_table_container .f-goto-page').forEach(i => {
            i.value = this.currentPage;
            i.max = pages;
        });

        document.querySelectorAll('#reports_table_container .page-numbers-container').forEach(container => {
            container.innerHTML = '';
            let start = Math.max(1, this.currentPage - 2);
            let end = Math.min(pages, start + 4);
            if (end - start < 4) start = Math.max(1, end - 4);
            for (let i = start; i <= end; i++) {
                const b = document.createElement('button');
                b.textContent = i;
                b.className = i === this.currentPage ? 'page-num-btn active' : 'page-num-btn';
                b.onclick = () => { this.currentPage = i; this.renderPage(); };
                container.appendChild(b);
            }
        });
    },

    changePage(d) {
        this.currentPage += d;
        this.renderPage();
    },

    gotoPage(val) {
        const p = parseInt(val);
        const pages = Math.max(1, Math.ceil(this.filteredRows.length / this.PAGE_SIZE));
        if (p && p >= 1 && p <= pages) {
            this.currentPage = p;
            this.renderPage();
        } else {
            document.querySelectorAll('#reports_table_container .f-goto-page').forEach(i => i.value = this.currentPage);
        }
    },

    applyFilters() {
        const q = (this.dom.fPath.value || '').toLowerCase();
        const op = this.dom.fOp.dataset.val || '';
        const ext = (this.dom.fExt.value || '').toLowerCase().trim();

        this.filteredRows = this.allRows.filter(r => {
            if (q && !r.path.toLowerCase().includes(q)) return false;
            if (op && r.status !== op) return false;
            if (ext && !r.path.toLowerCase().endsWith(ext)) return false;
            if (this.dom.fStart.value && new Date(r.date) < new Date(this.dom.fStart.value)) return false;
            if (this.dom.fEnd.value && new Date(r.date) > new Date(this.dom.fEnd.value + 'T23:59:59')) return false;
            return true;
        });

        this.currentPage = 1;
        this.renderPage();
        this.updateStats(this.filteredRows);
    },

    resetFilters() {
        this.dom.fPath.value = '';
        this.dom.fOp.value = '';
        this.dom.fOp.dataset.val = '';
        this.dom.fExt.value = '';
        this.dom.fStart.value = '';
        this.dom.fEnd.value = '';
        this.filteredRows = [...this.allRows];
        this.currentPage = 1;
        this.sortCol = null;
        this.sortDir = 1;
        this.buildHeader();
        this.renderPage();
        this.updateStats(this.filteredRows);
    },

    updateStats(rows) {
        const totalSize = rows.reduce((s, r) => s + (parseInt(r.size) || 0), 0);
        const errCount = rows.filter(r => r.status === 'ERROR').length;
        this.dom.volVal.textContent = this.formatSize(totalSize);
        this.dom.countVal.textContent = rows.length;
        this.dom.errVal.textContent = errCount;

        if (rows.length === 0) {
            [this.dom.insExt, this.dom.insLargest, this.dom.insAvg, this.dom.insLatest].forEach(el => el.textContent = '—');
            return;
        }

        const extCount = {};
        rows.forEach(r => {
            const parts = r.path.split('.');
            if (parts.length > 1) {
                const e = parts.pop().toLowerCase();
                extCount[e] = (extCount[e] || 0) + 1;
            }
        });
        const topExt = Object.entries(extCount).sort((a, b) => b[1] - a[1])[0];

        const largest = rows.reduce((m, r) => (parseInt(r.size) || 0) > (parseInt(m.size) || 0) ? r : m, rows[0]);
        const avg = totalSize / rows.length;

        const validDates = rows.map(r => new Date(r.date)).filter(d => !isNaN(d));
        const latest = validDates.length ? new Date(Math.max(...validDates)) : null;

        this.dom.insExt.textContent = topExt ? `.${topExt[0]} (${topExt[1]})` : '—';
        this.dom.insLargest.textContent = this.formatSize(largest.size);
        this.dom.insAvg.textContent = this.formatSize(avg);
        this.dom.insLatest.textContent = latest ? latest.toLocaleString() : 'N/A';
    },

    exportCSV() {
        if (this.filteredRows.length === 0) {
            ConsoleManager.append('No data to export', 'error');
            return;
        }
        const headers = ['status', 'path', 'size', 'date', 'tier', 'step'];
        const csvEscape = v => `"${String(v).replace(/"/g, '""')}"`;
        const lines = [headers.join(',')];
        this.filteredRows.forEach(r => lines.push(headers.map(h => csvEscape(r[h])).join(',')));
        const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `S3View_Export_${Date.now()}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    },

    formatSize(b) {
        if (!b || b === 0) return '0 B';
        const u = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(b) / Math.log(1024));
        return (b / Math.pow(1024, i)).toFixed(2) + ' ' + u[i];
    },

    esc(s) {
        return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
};
