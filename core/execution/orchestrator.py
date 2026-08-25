import concurrent.futures
from core.models.structures import CommandModel, TaskResponse
from .resolver import PathResolver

DEFAULT_LOCAL_WORKERS = 4
DEFAULT_TASK_TIMEOUT = 300

class TaskOrchestrator:

    @staticmethod
    def _generate_telemetry_response(status, resource_item, source_key, destination_key, source_object, destination_object, error="-"):
        return TaskResponse(
            status=status,
            src=PathResolver.format_identifier(source_key, source_object) if source_object else "-",
            dst=PathResolver.format_identifier(destination_key, destination_object) if (destination_key and destination_object) else "-",
            size=resource_item.size if resource_item else 0,
            date=resource_item.last_mod if resource_item else "N/A",
            tier=getattr(resource_item, "tier", "STANDARD") if resource_item else "N/A",
            error=error
        )


    @staticmethod
    def process_batch(connection_manager, inventory, command: CommandModel, worker_function, manifest, is_simulation=False):
        batch_results = {"files": [], "errors": [], "total_size": 0, "count": 0}
        source_object, destination_object = command.src, command.dst
        behavior_config = manifest.get("behavior", {})
        reporting_config = manifest.get("reporting", {})

        manager_default_timeout = getattr(connection_manager, "task_timeout", DEFAULT_TASK_TIMEOUT) if connection_manager is not None else DEFAULT_TASK_TIMEOUT
        manifest_timeout = behavior_config.get("task_timeout", manager_default_timeout)
        task_timeout = command.task_timeout if command.task_timeout is not None else manifest_timeout

        protocol_type = PathResolver.detect_protocol(source_object, destination_object) if source_object else "SINGLE"
        source_base_path = PathResolver.resolve_base_path(source_object) if source_object else ""

        if is_simulation:
            for item in inventory:
                target_key = PathResolver.calculate_destination_key(item.key, source_base_path, destination_object, command)
                
                response = TaskOrchestrator._generate_telemetry_response(
                    reporting_config.get("sim_status", "WILL PROCESS"),
                    item, 
                    item.key, 
                    target_key, 
                    source_object, 
                    destination_object,
                    error="WILL_PROCESS"
                )
                
                batch_results["files"].append(response)
                batch_results["total_size"] += item.size
                batch_results["count"] += 1

            return batch_results

        manager_default_workers = getattr(connection_manager, "workers", DEFAULT_LOCAL_WORKERS) if connection_manager is not None else DEFAULT_LOCAL_WORKERS
        worker_count = command.workers if command.workers is not None else manager_default_workers

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=worker_count)
        future_tasks = {}
        timed_out = False

        try:
            for item in inventory:
                target_key = PathResolver.calculate_destination_key(item.key, source_base_path, destination_object, command)
                
                task_context = {
                    "protocol": protocol_type,
                    "source_key": PathResolver.resolve_physical(source_object, item.key) if source_object else item.key,
                    "destination_key": PathResolver.resolve_physical(destination_object, target_key) if destination_object else None,
                    "logical_source_key": item.key,
                    "logical_destination_key": target_key,
                    "item": item,
                    "status_text": reporting_config.get("exec_status", "success")
                }
                
                future = executor.submit(
                    TaskOrchestrator._execute_safe_task, 
                    worker_function, 
                    connection_manager, 
                    task_context, 
                    command, 
                    source_object, 
                    destination_object
                )
                
                future_tasks[future] = task_context

            try:
                for future in concurrent.futures.as_completed(future_tasks, timeout=task_timeout):
                    task_result = future.result()
                    
                    if task_result.error == "-":
                        batch_results["files"].append(task_result)
                        batch_results["total_size"] += task_result.size
                        batch_results["count"] += 1
                    else:
                        batch_results["errors"].append(task_result.error)

            except concurrent.futures.TimeoutError:
                timed_out = True
                for pending_future, context in future_tasks.items():
                    if not pending_future.done():
                        pending_future.cancel()
                        error_source = PathResolver.format_identifier(context["logical_source_key"], source_object)
                        batch_results["errors"].append(
                            f"TIMEOUT_ERROR: Task for '{error_source}' exceeded {task_timeout}s and was cancelled."
                        )

        except KeyboardInterrupt:
            executor.shutdown(wait=False, cancel_futures=True)
            raise

        finally:
            executor.shutdown(wait=not timed_out)

        if not timed_out and protocol_type == "L2L" and behavior_config.get("prune_empty_source_dirs", False) and source_base_path:
            TaskOrchestrator._prune_empty_directories(source_base_path)

        return batch_results

    @staticmethod
    def _prune_empty_directories(root_path):
        import os
        if not os.path.isdir(root_path):
            return
        for current_dir, _, _ in os.walk(root_path, topdown=False):
            try:
                if not os.listdir(current_dir):
                    os.rmdir(current_dir)
            except OSError:
                pass


    @staticmethod
    def _execute_safe_task(worker_function, connection_manager, context, command, source_object, destination_object):
        try:
            worker_output = worker_function(connection_manager, context, command)

            if isinstance(worker_output, TaskResponse):
                worker_output.src = PathResolver.format_identifier(context["logical_source_key"], source_object)
                
                if worker_output.dst and worker_output.dst != "-":
                    worker_output.dst = PathResolver.format_identifier(context["logical_destination_key"], destination_object)
                
                return worker_output

            return TaskOrchestrator._generate_telemetry_response(
                context["status_text"],
                context["item"],
                context["logical_source_key"],
                context["logical_destination_key"],
                source_object,
                destination_object,
                error="-"
            )

        except Exception as exc:
            error_source = PathResolver.format_identifier(context["logical_source_key"], source_object)
            return TaskResponse.failure(src=error_source, error_msg=str(exc))