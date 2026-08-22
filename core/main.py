import os
from core import pipeline
from core.config import get_credentials, save_config
from core.interpreter import CommandsParser
from core.report import Reporting
from core.paths import Paths

def boot_system():
    pipeline.init_environment()

def run_logic_pipeline(is_cli=True, override_dry_run=None):
    try:
        settings = get_credentials()
    except Exception as e:
        err = f"BOOTSTRAP_FAILURE: {str(e)}"
        Reporting.save_error_log(str(e), "BOOTSTRAP_FAILURE")
        return {"error": err}

    if is_cli and (not settings.get("ACCESS_KEY") or not settings.get("SECRET_KEY")):
        print("\n[!] S3View: REQUIRED CREDENTIALS MISSING")
        settings["ACCOUNT_ID"] = input(" > Enter Account ID (Optional): ").strip()
        settings["ACCESS_KEY"] = input(" > Enter Access Key: ").strip()
        settings["SECRET_KEY"] = input(" > Enter Secret Key: ").strip()
        settings["S3_ENDPOINT"] = input(" > Enter S3 Endpoint (Optional): ").strip()
        
        try:
            save_config(settings)
            print("[+] Credentials successfully stored and secured.\n")
        except Exception as e:
            print(f"[-] Failed to save credentials: {e}")

    is_dry = override_dry_run if override_dry_run is not None else settings.get("DRY_RUN", False)
    vault_cleanup_enabled = settings.get("VAULT_CLEANUP", True)
    path = Paths.resource_path("WORKSPACE/Commands.view")

    if not os.path.exists(path):
        err = "FILE_NOT_FOUND: Commands.view could not be located in WORKSPACE."
        return {"error": err}

    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            script = f.read().strip()
    except Exception as e:
        err = f"READ_ERROR: Failed to read Commands.view -> {str(e)}"
        return {"error": err}

    try:
        pipeline_commands = CommandsParser.get_pipeline_commands(script)
        if not pipeline_commands: 
            err_msg = "INTERPRETER_WARNING: The script contains no valid commands to execute."
            return {"error": err_msg}
    except Exception as e:
        err_msg = f"SYNTAX_ERROR: {str(e)}"
        Reporting.save_error_log(str(e), "PIPELINE_INIT")
        return {"error": err_msg}

    try:
        if is_cli:
            mode_str = "YES" if is_dry else "NO"
            print(f"[*] Starting execution... (Dry Run: {mode_str})")
            print(f"[*] Found {len(pipeline_commands)} tasks to execute.")

        try:
            pipeline_output = pipeline.execute_pipeline(pipeline_commands, settings, is_dry, is_cli)
            results = pipeline_output.get("results", {})
            network_logs = pipeline_output.get("network_logs", [])
        except Exception as e:
            err_msg = f"EXECUTION_CRASH: {str(e)}"
            Reporting.save_error_log(str(e), "PIPELINE_EXECUTION_FATAL")
            return {"error": err_msg}

        if settings.get("REPORT_NETWORK", False) and not is_dry and network_logs:
            Reporting.save_network_report(network_logs)

        if settings.get("ENABLE_REPORTS", True):
            if is_dry: 
                Reporting.save_simulation_report(results)
            else: 
                Reporting.save_execution_report(results)

            if is_cli: 
                print("[+] TASK COMPLETED SUCCESSFULLY.")

        return {"results": results, "network_logs": network_logs}
    finally:
        if vault_cleanup_enabled:
            pipeline.cleanup_vault()