import os
import json
import sys
import importlib
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

class PluginEntity:
    def __init__(self, folder_path: str):
        self.folder_path = folder_path
        self.manifest = {}
        self.view = {}
        self.cached_plugin_module = None
        self.load_configurations()

    def load_configurations(self):
        manifest_file_path = os.path.join(self.folder_path, "manifest.json")
        if os.path.exists(manifest_file_path):
            try:
                with open(manifest_file_path, "r", encoding="utf-8") as f:
                    self.manifest = json.load(f)
                self.view = self.manifest.get("view", {})
            except Exception as e:
                logger.warning(f"Failed to parse manifest.json in {self.folder_path}: {e}")

    @property
    def action_name(self) -> str:
        return self.manifest.get("behavior", {}).get("action_name", "unknown")

    @property
    def syntax_color(self) -> str:
        return self.view.get("syntax_color", "#cccccc")

    @property
    def supports_simulation(self) -> bool:
        return self.manifest.get("behavior", {}).get("supports_simulation", True)

    @property
    def requires_src(self) -> bool:
        return self.manifest.get("behavior", {}).get("requires_src", True)

    @property
    def requires_dst(self) -> bool:
        return self.manifest.get("behavior", {}).get("requires_dst", True)

    @property
    def all_keywords(self) -> List[str]:
        return [
            str(keyword)
            for group in self.manifest.get("triggers", [])
            for keyword in group.get("keywords", [])
        ]

    def get_trigger_configuration(self, raw_keyword: str) -> Dict[str, Any]:
        for group in self.manifest.get("triggers", []):
            if raw_keyword in [str(k) for k in group.get("keywords", [])]:
                return group
        return {}

    def get_parser_method_name(self) -> str:
        return self.manifest.get("behavior", {}).get("parser_method", "parse_unary")

    def get_plugin_module(self, force_reload: bool = False):
        if self.cached_plugin_module and not force_reload:
            return self.cached_plugin_module
        folder_name = os.path.basename(self.folder_path)
        module_import_path = f"plugins.{folder_name}.engine"
        try:
            if force_reload and module_import_path in sys.modules:
                self.cached_plugin_module = importlib.reload(sys.modules[module_import_path])
            else:
                self.cached_plugin_module = importlib.import_module(module_import_path)
            return self.cached_plugin_module
        except Exception as e:
            logger.error(f"Error loading module for action '{self.action_name}': {e}")
            return None

    def execute(self, connection_manager, command_model):
        target_module = self.get_plugin_module()
        if not target_module:
            return {"error": f"Logic engine for '{self.action_name}' could not be loaded."}
        if hasattr(target_module, "execute_logic"):
            return target_module.execute_logic(connection_manager, command_model, self)
        if hasattr(target_module, "worker"):
            from core.execution import ExecutionEngine
            return ExecutionEngine.run_smart_task(
                connection_manager, command_model, target_module.worker, self, is_simulation=False
            )
        return {"error": f"Entry point not found in '{self.action_name}' engine."}

    def simulate(self, connection_manager, command_model):
        target_module = self.get_plugin_module()
        if not target_module:
            return {"error": f"Logic engine for '{self.action_name}' could not be loaded."}
        if hasattr(target_module, "simulate_logic"):
            return target_module.simulate_logic(connection_manager, command_model, self)
        if hasattr(target_module, "worker"):
            from core.execution import ExecutionEngine
            return ExecutionEngine.run_smart_task(
                connection_manager, command_model, None, self, is_simulation=True
            )
        return {"error": f"Simulation entry point not found in '{self.action_name}'."}