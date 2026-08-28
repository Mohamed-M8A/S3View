import os
import json
from core import config
from core.utils import CoreUtils
from core.loader import PluginLoader

class SettingsHandler:
    @staticmethod
    def get_all_config():
        try:
            configuration_data = config.load_config()
            return {
                "settings": {str(key): value for key, value in configuration_data.items() if key in config.DEFAULT_SETTINGS},
                "credentials": {str(key): value for key, value in configuration_data.items() if key in config.DEFAULT_CREDS}
            }
        except Exception:
            return {"settings": {}, "credentials": {}}

    @staticmethod
    def get_plugins_data():
        plugin_loader = PluginLoader()
        plugin_loader.discover_plugins()
        metadata_list = []
        
        for action_name, plugin_instance in plugin_loader.plugins.items():
            reporting_config = plugin_instance.manifest.get("reporting", {})
            metadata_list.append({
                "action": str(action_name),
                "color": str(plugin_instance.syntax_color),
                "keywords": plugin_instance.all_keywords,
                "hint": str(plugin_instance.view.get("hint", "")),
                "description": str(plugin_instance.view.get("description", "")),
                "exec_status": str(reporting_config.get("exec_status", action_name.upper())),
                "sim_status": str(reporting_config.get("sim_status", f"WILL {action_name.upper()}"))
            })
        return metadata_list

    @staticmethod
    def read_workspace_file(filename):
        absolute_file_path = CoreUtils.resource_path(f"WORKSPACE/{filename}")
        if os.path.exists(absolute_file_path):
            try:
                with open(absolute_file_path, "r", encoding="utf-8-sig") as file_stream:
                    return file_stream.read()
            except Exception:
                return ""
        return ""

    @staticmethod
    def save_workspace(payload):
        try:
            if "settings" in payload or "credentials" in payload:
                current_configuration = config.load_config()
                if "settings" in payload:
                    current_configuration.update(payload["settings"])
                if "credentials" in payload:
                    current_configuration.update(payload["credentials"])
                config.save_config(current_configuration)
            
            if payload.get("commands") is not None:
                commands_path = CoreUtils.resource_path("WORKSPACE/Commands.view")
                with open(commands_path, "w", encoding="utf-8-sig") as commands_file:
                    commands_file.write(payload["commands"])
            
            if payload.get("protected") is not None:
                protected_path = CoreUtils.resource_path("WORKSPACE/Protected.vshield")
                with open(protected_path, "w", encoding="utf-8-sig") as protected_file:
                    protected_file.write(payload["protected"])
            
            return {"status": "success"}
        except Exception as error:
            return {"status": "error", "message": str(error)}