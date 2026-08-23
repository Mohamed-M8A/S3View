from core.execution.operations import BasicOps
from core.models import TaskResponse

def worker(connection_manager, execution_context, command_model):
    source_key = execution_context["source_key"]
    bucket_name = command_model.src.bucket
    target_tier = command_model.tier or command_model.extra_metadata.get("target_tier", "STANDARD")
    
    s3_operation_arguments = {"StorageClass": target_tier, "MetadataDirective": "COPY"}
    
    BasicOps.c2c(
        connection_manager, 
        bucket_name, 
        source_key, 
        bucket_name, 
        source_key, 
        extra_args=s3_operation_arguments
    )
    
    return True

def execute_logic(connection_manager, command_model, plugin_instance):
    from core.execution import ExecutionEngine
    if not command_model.src.is_cloud:
        return {"files": [], "errors": ["S3 Storage Tiers are not supported on local filesystem paths."], "total_size": 0, "count": 0}
    return ExecutionEngine.run_smart_task(connection_manager, command_model, worker, plugin_instance, is_simulation=False)

def simulate_logic(connection_manager, command_model, plugin_instance):
    from core.execution import ExecutionEngine
    if not command_model.src.is_cloud:
        return {"files": [], "errors": ["S3 Storage Tiers are not supported on local filesystem paths."], "total_size": 0, "count": 0}
    return ExecutionEngine.run_smart_task(connection_manager, command_model, None, plugin_instance, is_simulation=True)