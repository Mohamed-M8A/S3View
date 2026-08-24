import os
from core.models import CommandModel, TaskResponse
from core.execution import ExecutionEngine
from core.execution.resolver import PathResolver
from core.execution.operations import BasicOps
from core.pipeline.scan import UniversalScanner
from core.ops.composite_ops.sync_ops import SyncOps
from core.paths import Paths

def worker(connection_manager, execution_context, command_model):
    protocol = execution_context["protocol"]
    source_path = execution_context["source_key"]
    destination_path = execution_context["destination_key"]
    item_metadata = execution_context["item"]
    status_label = execution_context["status_text"]

    s3_extra_arguments = BasicOps.build_s3_extra_args(command_model)

    try:
        if protocol == "S2S":
            BasicOps.s2s(connection_manager, command_model.src.bucket, source_path, command_model.dst.bucket, destination_path, extra_args=s3_extra_arguments)
        elif protocol == "S2L":
            local_dest = Paths.resolve_local_path(destination_path) if command_model.dst.protocol == "LOCAL" else destination_path
            BasicOps.s2l(connection_manager, command_model.src.bucket, source_path, local_dest)
        elif protocol == "L2S":
            BasicOps.l2s(connection_manager, source_path, command_model.dst.bucket, destination_path, extra_args=s3_extra_arguments)
        elif protocol == "L2L":
            local_dest = Paths.resolve_local_path(destination_path) if command_model.dst.protocol == "LOCAL" else destination_path
            BasicOps.l2l(source_path, local_dest, move_mode=False)

        return True
    except Exception as error:
        return TaskResponse.failure(src=source_path, error_msg=str(error))

def execute_logic(connection_manager, command_model: CommandModel, plugin_instance, is_simulation=False):
    execution_results = {"files": [], "errors": [], "total_size": 0, "count": 0}
    source_object = command_model.src
    destination_object = command_model.dst

    source_inventory = UniversalScanner.scan(connection_manager, source_object, command_model, {"total_size": 0, "count": 0})
    destination_inventory_map = SyncOps.get_destination_map(connection_manager, destination_object, command_model.depth)
    source_base_directory = PathResolver.resolve_base_path(source_object)

    sync_queue = []
    active_source_keys = set()

    for item in source_inventory:
        if source_object.is_cloud:
            relative_path = item.key[len(source_base_directory):].lstrip("/") if source_base_directory else item.key
        else:
            relative_path = os.path.relpath(item.key, source_base_directory).replace("\\", "/")

        active_source_keys.add(relative_path)

        if relative_path not in destination_inventory_map or SyncOps.should_sync(item, destination_inventory_map[relative_path]):
            if is_simulation:
                full_source_path = PathResolver.format_identifier(item.key, source_object)
                full_dest_path = PathResolver.format_identifier(relative_path, destination_object)
                execution_results["files"].append(TaskResponse(status="WILL SYNC", src=full_source_path, dst=full_dest_path, size=item.size))
                execution_results["total_size"] += item.size
                execution_results["count"] += 1
            else:
                sync_queue.append(item)

    if command_model.extra_metadata.get("purge"):
        for relative_path, destination_metadata in destination_inventory_map.items():
            if relative_path not in active_source_keys:
                if is_simulation:
                    execution_results["files"].append(TaskResponse(status="WILL PURGE", src=destination_metadata.key, size=destination_metadata.size))
                else:
                    try:
                        if destination_object.is_cloud:
                            BasicOps.s3_del(connection_manager, destination_object.bucket, destination_metadata.key)
                        else:
                            BasicOps.loc_del(destination_metadata.key)
                        execution_results["files"].append(TaskResponse(status="PURGED", src=destination_metadata.key, size=destination_metadata.size))
                    except Exception as error:
                        execution_results["errors"].append(f"Purge Failure: {destination_metadata.key} - {str(error)}")

    if not is_simulation and sync_queue:
        batch_output = ExecutionEngine.run_smart_task(connection_manager, command_model, worker, plugin_instance, False, prebuilt_inventory=sync_queue)
        execution_results["files"].extend(batch_output["files"])
        execution_results["errors"].extend(batch_output["errors"])
        execution_results["total_size"] += batch_output["total_size"]
        execution_results["count"] += batch_output["count"]

    return execution_results

def simulate_logic(connection_manager, command_model: CommandModel, plugin_instance):
    return execute_logic(connection_manager, command_model, plugin_instance, is_simulation=True)
