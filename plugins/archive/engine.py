import os
import uuid
import zipfile
from core.models import CommandModel, TaskResponse, BatchResult
from core.pipeline.scan import UniversalScanner
from core.ops.composite.archive import ArchiveOps
from core.execution.resolver import PathResolver
from core.execution.operations import BasicOps
from core.paths import Paths
from datetime import datetime

def execute_logic(connection_manager, command_model: CommandModel, plugin_instance):
    execution_results = BatchResult()
    source_object = command_model.src
    destination_object = command_model.dst

    compression_level = command_model.level if command_model.level is not None else 6
    target_extension = command_model.extra_metadata.get("target_extension", "zip")
    content_mime_type = command_model.extra_metadata.get("content_type", "application/zip")
    status_label = plugin_instance.manifest.get("reporting", {}).get("exec_status", "ARCHIVED")

    scanning_statistics = {"total_size": 0, "count": 0}
    try:
        inventory_list = UniversalScanner.scan(connection_manager, source_object, command_model, scanning_statistics)
    except Exception as exc:
        execution_results["errors"].append(str(exc))
        return execution_results

    if not inventory_list:
        return execution_results

    if not ArchiveOps.validate_space(scanning_statistics["total_size"]):
        execution_results["errors"].append("Insufficient disk space in system vault for archiving.")
        return execution_results

    temporary_zip_path = ArchiveOps.create_temp_archive()
    vault_storage_path = ArchiveOps.get_vault_path()
    source_base_directory = PathResolver.resolve_base_path(source_object)

    try:
        with zipfile.ZipFile(temporary_zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=compression_level) as archive_file:
            for item in inventory_list:
                unique_temporary_name = f"item_{uuid.uuid4().hex[:6]}"
                item_temporary_path = Paths.join(vault_storage_path, unique_temporary_name)

                if source_object.is_cloud:
                    BasicOps.s2l(connection_manager, source_object.bucket, item.key, item_temporary_path)
                    internal_archive_path = item.key[len(source_base_directory):].lstrip("/") if source_base_directory else item.key
                else:
                    BasicOps.l2l(item.key, item_temporary_path, move_mode=False)
                    internal_archive_path = os.path.relpath(item.key, source_base_directory).replace("\\", "/")

                if os.path.exists(item_temporary_path):
                    archive_file.write(item_temporary_path, internal_archive_path)
                    os.remove(item_temporary_path)

        if destination_object:
            if destination_object.is_cloud:
                final_key = destination_object.prefix.rstrip("/")
                if not final_key.endswith(f".{target_extension}"):
                    final_key += f".{target_extension}"

                s3_upload_arguments = BasicOps.build_s3_extra_args(command_model)
                s3_upload_arguments.update({"ContentType": content_mime_type})

                BasicOps.l2s(connection_manager, temporary_zip_path, destination_object.bucket, final_key, extra_args=s3_upload_arguments)
                final_output_path = f"s3://{destination_object.bucket}/{final_key}"
            else:
                absolute_destination = Paths.get_full_physical_path(destination_object)
                if not absolute_destination.endswith(f".{target_extension}"):
                    absolute_destination += f".{target_extension}"
                final_output_path = ArchiveOps.finalize_zip(temporary_zip_path, absolute_destination)
        else:
            default_filename = source_object.payload.rstrip("/").split("/")[-1] + f".{target_extension}"
            final_output_path = ArchiveOps.finalize_zip(temporary_zip_path, Paths.resolve_local_path(default_filename))

        summary_response = TaskResponse(
            status=status_label,
            src=source_object.payload,
            dst=final_output_path,
            size=scanning_statistics["total_size"],
            date=datetime.now().strftime("%H:%M:%S")
        )
        execution_results["files"].append(summary_response)
        execution_results["total_size"] = scanning_statistics["total_size"]
        execution_results["count"] = 1

    except Exception as error:
        execution_results["errors"].append(str(error))
    finally:
        if os.path.exists(temporary_zip_path):
            os.remove(temporary_zip_path)

    return execution_results

def simulate_logic(connection_manager, command_model, plugin_instance):
    from core.execution import ExecutionEngine
    return ExecutionEngine.run_smart_task(connection_manager, command_model, None, plugin_instance, is_simulation=True)
