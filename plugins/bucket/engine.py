# ==================================================================================
# S3 INFRASTRUCTURE MANAGEMENT ENGINE (PROVISIONING & DISCOVERY)
# ------------------------------------------------------------------------------
# STRATEGY: 
# This engine operates on the "Fast Lane" by using 'execute_logic' instead of a 
# standard 'worker'. It bypasses the resource-scanning phase to perform 
# direct bucket-level operations (Create, List, Purge) using manifest-driven 
# behavior flags.
# ------------------------------------------------------------------------------
# ARCHITECTURE:
# 1. Mode Dispatching: Dynamically branches into specific logic paths based 
#    on the 'mode' flag (create/list/purge) injected by the Interpreter.
# 2. Infrastructure Inventory: In 'list' mode, it maps raw cloud responses 
#    directly into standardized TaskResponse objects for consistent reporting.
# 3. Forced Removal: Implements recursive bucket purging (metadata + objects) 
#    when the 'purge' mode is triggered, ensuring clean de-provisioning.
# 4. Telemetry Integration: Synchronizes with the plugin manifest to retrieve 
#    execution and simulation status labels dynamically.
# ==================================================================================

from datetime import datetime
from core.execution.operations import BasicOps
from core.models import TaskResponse

def execute_logic(connection_manager, command_model, plugin_instance):
    operation_mode = command_model.extra_metadata.get("mode", "create")
    target_name = command_model.src.payload.strip("/")
    
    reporting_config = plugin_instance.manifest.get("reporting", {})
    execution_status = reporting_config.get("exec_status", "SUCCESS")
    
    results = {"files": [], "errors": [], "total_size": 0, "count": 0}

    try:
        if operation_mode == "list":
            bucket_inventory = BasicOps.s3_list_buckets(connection_manager)
            for bucket in bucket_inventory:
                results["files"].append(TaskResponse(
                    status="FOUND", 
                    src=f"s3://{bucket['Name']}", 
                    date=bucket['CreationDate']
                ))
            results["count"] = len(bucket_inventory)

        elif operation_mode == "create":
            BasicOps.s3_create_bucket(connection_manager, target_name)
            results["files"].append(TaskResponse(
                status="CREATED", 
                src=f"s3://{target_name}", 
                date=datetime.now()
            ))
            results["count"] = 1

        elif operation_mode == "purge":
            BasicOps.s3_delete_bucket(connection_manager, target_name, force=True)
            results["files"].append(TaskResponse(
                status="PURGED", 
                src=f"s3://{target_name}", 
                date=datetime.now()
            ))
            results["count"] = 1

    except Exception as exc:
        results["errors"].append(f"BUCKET_OPERATION_FAILED: {str(exc)}")
        
    return results

def simulate_logic(connection_manager, command_model, plugin_instance):
    operation_mode = command_model.extra_metadata.get("mode", "create")
    reporting_config = plugin_instance.manifest.get("reporting", {})
    simulation_status = reporting_config.get("sim_status", "WILL PROCESS")
    
    target_path = f"s3://{command_model.src.payload.strip('/')}"
    
    return {
        "files": [TaskResponse(status=simulation_status, src=target_path, date=datetime.now())],
        "errors": [],
        "total_size": 0,
        "count": 1
    }