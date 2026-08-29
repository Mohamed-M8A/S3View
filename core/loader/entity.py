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
        if not os.path.exists(manifest_file_path):
            return

        try:
            with open(manifest_file_path, "r", encoding="utf-8") as f:
                raw_manifest = json.load(f)
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in {manifest_file_path}: {e}")
            return
        except Exception as e:
            logger.warning(f"Failed to read manifest.json in {self.folder_path}: {e}")
            return

        validation_errors = PluginEntity._validate_manifest_structure(raw_manifest)
        if validation_errors:
            plugin_label = raw_manifest.get("plugin_id", os.path.basename(self.folder_path)) if isinstance(raw_manifest, dict) else os.path.basename(self.folder_path)
            combined_message = "; ".join(validation_errors)
            for error in validation_errors:
                logger.warning(f"manifest.json for plugin '{plugin_label}' ({manifest_file_path}) is invalid: {error}")
            try:

                from core.report import Reporting
                Reporting.save_error_log(
                    f"manifest.json for plugin '{plugin_label}' ({manifest_file_path}) is invalid: {combined_message}",
                    "PLUGIN_MANIFEST_VALIDATION"
                )
            except Exception:
                pass 
            return

        self.manifest = raw_manifest
        self.view = self.manifest.get("view", {})

    @staticmethod
    def _validate_manifest_structure(manifest: Any) -> List[str]:
        """Returns a list of human-readable validation error strings. An
        empty list means the manifest is structurally sound enough to load.
        This intentionally does NOT require every optional key (e.g. 'view',
        'version') -- only the fields the rest of the system actually reads
        and would otherwise fail on confusingly (see core/loader/entity.py's
        action_name/get_parser_method_name/all_keywords properties, and
        core/interpreter/builder.py's _compile_to_pipeline)."""
        errors: List[str] = []

        if not isinstance(manifest, dict):
            return [f"expected a JSON object at the top level, got {type(manifest).__name__}"]

        behavior = manifest.get("behavior")
        if not isinstance(behavior, dict):
            errors.append("missing or invalid 'behavior' object")
        else:
            action_name = behavior.get("action_name")
            if not isinstance(action_name, str) or not action_name.strip():
                errors.append("'behavior.action_name' must be a non-empty string")

            parser_method = behavior.get("parser_method")
            if not isinstance(parser_method, str) or not parser_method.strip():
                errors.append("'behavior.parser_method' must be a non-empty string")

        triggers = manifest.get("triggers")
        if not isinstance(triggers, list) or not triggers:
            errors.append("'triggers' must be a non-empty list")
        else:
            for i, group in enumerate(triggers):
                if not isinstance(group, dict):
                    errors.append(f"triggers[{i}] must be an object")
                    continue
                keywords = group.get("keywords")
                if not isinstance(keywords, list) or not keywords or not all(isinstance(k, str) and k.strip() for k in keywords):
                    errors.append(f"triggers[{i}].keywords must be a non-empty list of non-empty strings")

        return errors

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