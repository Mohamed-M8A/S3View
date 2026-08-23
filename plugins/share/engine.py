import os
from datetime import datetime
from core.models import TaskResponse
from core.execution.operations import BasicOps
from core.paths import Paths

def worker(connection_manager, execution_context, command_model):
    source_key = execution_context["source_key"]
    bucket_name = command_model.src.bucket
    expiration_time = command_model.expires or 3600
    
    generated_url = BasicOps.s3_share(connection_manager, bucket_name, source_key, expiration_time)
    
    return TaskResponse(
        status="SHARED",
        src=f"s3://{bucket_name}/{source_key}",
        dst=generated_url,
        size=execution_context["item"].size,
        date=datetime.now().strftime("%H:%M:%S")
    )

def execute_logic(connection_manager, command_model, plugin_instance):
    from core.execution import ExecutionEngine
    if not command_model.src.is_cloud:
        return {"files": [], "errors": ["Link generation is only available for cloud-hosted S3 objects."], "total_size": 0, "count": 0}
    
    execution_results = ExecutionEngine.run_smart_task(connection_manager, command_model, worker, plugin_instance)
    
    if execution_results["files"]:
        timestamp_string = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file_path = Paths.resource_path(f"Reports/SHARES/SharedLinks_{timestamp_string}.txt")
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
        with open(output_file_path, "w", encoding="utf-8") as links_file:
            for item in execution_results["files"]:
                links_file.write(f"OBJECT: {item.src}\nURL: {item.dst}\n{'-'*30}\n")
                
    return execution_results

def simulate_logic(connection_manager, command_model, plugin_instance):
    from core.execution import ExecutionEngine
    return ExecutionEngine.run_smart_task(connection_manager, command_model, None, plugin_instance, is_simulation=True)