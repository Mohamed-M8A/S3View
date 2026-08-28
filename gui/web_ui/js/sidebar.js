const SidebarManager = {
    init() {
        this.bindEvents();
    },

    bindEvents() {
        document.getElementById('btn_sidebar_execute').onclick = () => {
            if (window.App) App.executePipeline();
        };

        document.getElementById('btn_nav_reports').onclick = () => Bridge.openReportsFolder();
        document.getElementById('btn_nav_latest').onclick = () => Bridge.showLatestReport();
    }
};
