from datetime import datetime
from core.execution.operations import BasicOps
from core.models import TaskResponse

def execute_logic(connection_manager, command_model, plugin_instance):
    reporting_config = plugin_instance.manifest.get("reporting", {})
    execution_status = reporting_config.get("exec_status", "FOUND")

    results = {"files": [], "errors": [], "total_size": 0, "count": 0}

    try:
        bucket_inventory = BasicOps.s3_list_buckets(connection_manager)
        for bucket in bucket_inventory:
            results["files"].append(TaskResponse(
                status=execution_status,
                src=f"s3://{bucket['Name']}",
                date=bucket["CreationDate"]
            ))
        results["count"] = len(bucket_inventory)
    except Exception as exc:
        results["errors"].append(f"BUCKET_LIST_FAILED: {str(exc)}")

    return results

def simulate_logic(connection_manager, command_model, plugin_instance):
    return execute_logic(connection_manager, command_model, plugin_instance)
