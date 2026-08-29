from datetime import datetime
from core.execution.operations import BasicOps
from core.models import TaskResponse

def execute_logic(connection_manager, command_model, plugin_instance):
    target_name = command_model.src.payload.strip("/")
    reporting_config = plugin_instance.manifest.get("reporting", {})
    execution_status = reporting_config.get("exec_status", "CREATED")

    results = {"files": [], "errors": [], "total_size": 0, "count": 0}

    try:
        BasicOps.s3_create_bucket(connection_manager, target_name)
        results["files"].append(TaskResponse(
            status=execution_status,
            src=f"s3://{target_name}",
            date=datetime.now()
        ))
        results["count"] = 1
    except Exception as exc:
        results["errors"].append(f"BUCKET_CREATE_FAILED: {str(exc)}")

    return results

def simulate_logic(connection_manager, command_model, plugin_instance):
    reporting_config = plugin_instance.manifest.get("reporting", {})
    simulation_status = reporting_config.get("sim_status", "WILL CREATE")
    target_path = f"s3://{command_model.src.payload.strip('/')}"

    return {
        "files": [TaskResponse(status=simulation_status, src=target_path, date=datetime.now())],
        "errors": [],
        "total_size": 0,
        "count": 1
    }
