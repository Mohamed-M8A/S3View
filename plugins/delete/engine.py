from core.models import TaskResponse
from core.execution import ExecutionEngine
from core.execution.operations import BasicOps
from core.pipeline.scan import UniversalScanner
from core.execution.resolver import PathResolver

def worker(connection_manager, execution_context, command_model):
    source_physical_path = execution_context["source_key"]
    BasicOps.loc_del(source_physical_path)
    return True

def execute_logic(connection_manager, command_model, plugin_instance):
    source_object = command_model.src
    reporting_config = plugin_instance.manifest.get("reporting", {})
    execution_status = reporting_config.get("exec_status", "DELETED")
    
    results = {"files": [], "errors": [], "total_size": 0, "count": 0}
    scan_statistics = {"total_size": 0, "count": 0}
    
    inventory = UniversalScanner.scan(connection_manager, source_object, command_model, scan_statistics)
    if not inventory:
        return results

    if source_object.is_cloud:
        protocol = source_object.protocol
        bucket = source_object.bucket
        keys = [item.key for item in inventory]
        
        batch_size = 1000
        
        for i in range(0, len(keys), batch_size):
            chunk = keys[i:i + batch_size]
            try:
                if protocol == "S3":
                    BasicOps.s3_del_batch(connection_manager, bucket, chunk)
                
                for item in inventory[i:i + batch_size]:
                    results["files"].append(TaskResponse(
                        status=execution_status,
                        src=PathResolver.format_identifier(item.key, source_object),
                        size=item.size,
                        tier=item.tier
                    ))
            except Exception as exc:
                results["errors"].append(f"CLOUD_DELETE_ERROR ({protocol}): {str(exc)}")
        
        results["total_size"] = scan_statistics["total_size"]
        results["count"] = scan_statistics["count"]
    else:
        execution_output = ExecutionEngine.run_smart_task(
            connection_manager, 
            command_model, 
            worker, 
            plugin_instance, 
            prebuilt_inventory=inventory
        )
        results.update(execution_output)

    return results

def simulate_logic(connection_manager, command_model, plugin_instance):
    return ExecutionEngine.run_smart_task(connection_manager, command_model, None, plugin_instance, is_simulation=True)