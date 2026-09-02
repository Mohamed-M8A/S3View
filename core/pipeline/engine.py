import os
from core.paths import Paths
from core.config import load_config
from core.loader import PluginLoader
from core.report import Reporting
from core.cloud.s3 import S3Manager
from core.cloud.local import LocalManager


class PipelineEngine:

    _plugin_loader = None


    @staticmethod
    def _get_plugin_loader():
        if PipelineEngine._plugin_loader is None:
            loader = PluginLoader()
            loader.discover_plugins()
            PipelineEngine._plugin_loader = loader

        return PipelineEngine._plugin_loader


    @staticmethod
    def init_environment():
        required_folders = [
            "WORKSPACE", "WORKSPACE/CONFIG",
            "reports/html", "reports/tsv", "reports/json", 
            "reports/sqlite", "reports/duckdb", "reports/logs", 
            "reports/shares", "reports/network", "_sys/registry", "_sys/.vault"
        ]
        
        for folder in required_folders:
            os.makedirs(Paths.resource_path(folder), exist_ok=True)
        
        load_config()
        
        core_files = {
            "WORKSPACE/Commands.view": "// S3View Execution Script\n",
            "WORKSPACE/Protected.vshield": "// S3View Protection List\n",
        }
        
        for file_path, header_text in core_files.items():
            full_physical_path = Paths.resource_path(file_path)
            if not os.path.exists(full_physical_path):
                with open(full_physical_path, "w", encoding="utf-8-sig") as file_handle:
                    file_handle.write(header_text)


    @staticmethod
    def cleanup_vault():
        try:
            vault_path = Paths.resource_path("_sys/.vault")

            if os.path.exists(vault_path):
                for temp_filename in os.listdir(vault_path):
                    file_physical_path = Paths.join(vault_path, temp_filename)
                    if os.path.isfile(file_physical_path): 
                        os.remove(file_physical_path)

        except Exception as exc:
            Reporting.save_error_log(str(exc), "VAULT_CLEANUP_FAILURE")


    @staticmethod
    def _dispatch_task(action_name, command_model, connection_manager, is_dry_run):
        plugin_loader = PipelineEngine._get_plugin_loader()
        target_plugin = plugin_loader.get_plugin_by_action(action_name)
        
        if not target_plugin:
            return {"error": f"EXECUTION_ERROR: Command '{action_name}' is not recognized."}
        
        try:
            if is_dry_run:
                if target_plugin.supports_simulation: 
                    return target_plugin.simulate(connection_manager, command_model)
                return {"error": f"SIMULATION_ERROR: Action '{action_name}' does not support Dry-run mode."}
            
            return target_plugin.execute(connection_manager, command_model)

        except Exception as exc:
            return {"error": f"RUNTIME_CRASH: {str(exc)}"}


    @staticmethod
    def execute_pipeline(task_pipeline, is_dry_run, is_cli_mode):
        pipeline_results = {}
        active_managers = {}
        all_network_logs = []
        needed_protocols = set()
        plugin_loader = PipelineEngine._get_plugin_loader()

        def _plugin_requires_s3(action_name):
            plugin = plugin_loader.get_plugin_by_action(action_name)
            return bool(plugin and plugin.manifest.get("behavior", {}).get("requires_s3"))

        for task in task_pipeline:
            cmd_data = task["data"]
            if cmd_data.src:
                needed_protocols.add(cmd_data.src.protocol)
            if cmd_data.dst:
                needed_protocols.add(cmd_data.dst.protocol)
            if _plugin_requires_s3(task["action"]):
                needed_protocols.add("S3")

        if "S3" in needed_protocols:
            active_managers["S3"] = S3Manager()

        active_managers["LOCAL"] = LocalManager()

        for step_index, task in enumerate(task_pipeline, 1):
            action = task["action"]
            command_data = task["data"]
            step_identifier = f"Step_{step_index}_{action}"
            
            is_s3_involved = (command_data.src and command_data.src.protocol == "S3") or \
                             (command_data.dst and command_data.dst.protocol == "S3") or \
                             _plugin_requires_s3(action)

            if is_s3_involved:
                current_manager = active_managers.get("S3")
            else:
                current_manager = active_managers.get("LOCAL")

            if is_cli_mode:
                print(f" -> STEP #{step_index}: {action.upper()} processing started...")
            
            try:
                execution_result = PipelineEngine._dispatch_task(action, command_data, current_manager, is_dry_run)
                pipeline_results[step_identifier] = execution_result

                step_failed = "error" in execution_result or bool(execution_result.get("errors"))

                if is_cli_mode:
                    if step_failed:
                        processed_count = execution_result.get("count", 0)
                        failure_count = len(execution_result.get("errors", [])) or 1
                        first_error = execution_result.get("error") or (execution_result.get("errors") or ["Unknown error"])[0]
                        print(f"    [!] STEP #{step_index}: FAILED. {failure_count} error(s), {processed_count} item(s) processed. First error: {first_error}")
                    else:
                        processed_count = execution_result.get("count", 0)
                        execution_status = "SIMULATED" if is_dry_run else "COMPLETED"
                        print(f"    [OK] STEP #{step_index}: {execution_status}. {processed_count} items processed.")
                        
            except Exception as exc:
                error_message = f"STEP #{step_index}: FAILED. Context: {str(exc)}"
                Reporting.save_error_log(str(exc), f"PIPELINE_STEP_{step_index}")
                if is_cli_mode: 
                    print(f"    [!] {error_message}")
                pipeline_results[step_identifier] = {"error": error_message}
        
        for manager_instance in active_managers.values():
            if manager_instance and hasattr(manager_instance, "http_logs"):
                all_network_logs.extend(manager_instance.http_logs)

        had_failures = any(
            ("error" in step_result) or bool(step_result.get("errors"))
            for step_result in pipeline_results.values()
        )

        return {
            "results": pipeline_results,
            "network_logs": all_network_logs,
            "had_failures": had_failures
        }