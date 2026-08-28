import os
import json
import webview
from core.utils import CoreUtils

class S3ViewAPI:
    def __init__(self):
        from core.main import boot_system
        boot_system()

    def get_app_data(self):
        from .bridge.macros import MacroHandler
        from .bridge.settings import SettingsHandler
        from core.loader import PluginLoader
        
        config_data = SettingsHandler.get_all_config()
        plugin_loader = PluginLoader()
        plugin_loader.discover_plugins()
        
        available_statuses = ["FOUND", "ERROR", "SKIPPED"]
        for plugin in plugin_loader.plugins.values():
            execution_status = plugin.manifest.get("reporting", {}).get("exec_status")
            simulation_status = plugin.manifest.get("reporting", {}).get("sim_status")
            if execution_status:
                available_statuses.append(execution_status)
            if simulation_status:
                available_statuses.append(simulation_status)

        return {
            "settings": config_data.get("settings", {}),
            "credentials": config_data.get("credentials", {}),
            "macros": MacroHandler.load_all(),
            "plugins_metadata": SettingsHandler.get_plugins_data(),
            "available_statuses": list(set(available_statuses)),
            "commands_script": SettingsHandler.read_workspace_file("Commands.view"),
            "protected_list": SettingsHandler.read_workspace_file("Protected.vshield")
        }

    def list_reports(self):
        json_directory = CoreUtils.resource_path("Reports/JSON")
        if not os.path.exists(json_directory):
            return []
        
        files = [f for f in os.listdir(json_directory) if f.endswith(".s3vr")]
        files.sort(key=lambda x: os.path.getmtime(os.path.join(json_directory, x)), reverse=True)
        return files

    def get_report(self, filename):
        file_path = CoreUtils.resource_path(f"Reports/JSON/{filename}")
        try:
            with open(file_path, "r", encoding="utf-8") as file_stream:
                return json.load(file_stream)
        except Exception:
            return {"error": "Failed to read the requested report."}

    def save_workspace(self, payload):
        from .bridge.settings import SettingsHandler
        return SettingsHandler.save_workspace(payload)

    def save_macro(self, name, code):
        from .bridge.macros import MacroHandler
        return MacroHandler.save(name, code)

    def delete_macro(self, name):
        from .bridge.macros import MacroHandler
        return MacroHandler.delete(name)

    def run_pipeline(self, script_content, is_dry_run):
        from .bridge.executor import PipelineHandler
        return PipelineHandler.execute(script_content, is_dry_run)

    def open_reports_folder(self):
        from .bridge.executor import PipelineHandler
        return PipelineHandler.open_reports()

    def view_latest_report(self):
        from .bridge.executor import PipelineHandler
        return PipelineHandler.show_latest()

def launch_gui(debug_mode=True):
    index_html_path = os.path.abspath(CoreUtils.resource_path("gui/web_ui/index.html"))
    
    if not os.path.exists(index_html_path):
        return

    api = S3ViewAPI()
    window = webview.create_window(
        title="S3View Enterprise Cloud Manager",
        url=index_html_path,
        js_api=api,
        width=1400,
        height=900,
        background_color="#000000"
    )

    webview.start(debug=debug_mode)