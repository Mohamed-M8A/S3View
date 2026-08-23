import os
import math
import hashlib
from datetime import datetime
from core.models import CommandModel, TaskResponse
from core.ops.composite_ops.delta_ops import DeltaOps
from core.execution.operations import BasicOps
from core.paths import Paths

MAX_MULTIPART_PARTS = 10000

def execute_logic(connection_manager, command_model: CommandModel, plugin_instance):
    execution_results = {"files": [], "errors": [], "total_size": 0, "count": 0}
    source_object = command_model.src
    destination_object = command_model.dst
    status_label = plugin_instance.manifest.get("reporting", {}).get("exec_status", "PATCHED")

    if source_object.is_cloud or not destination_object.is_cloud:
        return {"error": "The DELTA engine only supports Local-to-Cloud differential transfers."}

    absolute_source_path = Paths.get_full_physical_path(source_object)
    if not os.path.isfile(absolute_source_path):
        return {"error": f"Source file not found: {absolute_source_path}"}

    source_file_size = os.path.getsize(absolute_source_path)
    chunk_size_megabytes = command_model.chunk_size or 8
    chunk_size_bytes = chunk_size_megabytes * 1024 * 1024

    expected_part_count = math.ceil(source_file_size / chunk_size_bytes) if source_file_size else 0
    if expected_part_count > MAX_MULTIPART_PARTS:
        return {"error": f"DELTA_CHUNK_TOO_SMALL: chunk size {chunk_size_megabytes}MB would need {expected_part_count} parts, S3 allows at most {MAX_MULTIPART_PARTS}."}

    registry_identifier, registry_file_path = DeltaOps.get_registry_info(source_object, source_file_size)
    existing_hashes = DeltaOps.load_hashes(registry_file_path, chunk_size_megabytes, registry_identifier, expected_file_size=source_file_size)

    target_object_key = destination_object.prefix
    if destination_object.content_only or target_object_key.endswith("/"):
        target_object_key = Paths.join(target_object_key, os.path.basename(absolute_source_path))

    multipart_upload_id = None
    try:
        s3_extra_arguments = BasicOps.build_s3_extra_args(command_model)
        multipart_upload_id = BasicOps.s3_init_multipart(connection_manager, destination_object.bucket, target_object_key, extra_args=s3_extra_arguments)

        calculated_new_hashes = []
        completed_upload_parts = []

        with open(absolute_source_path, "rb") as source_file_stream:
            current_part_number = 1
            while True:
                chunk_binary_data = source_file_stream.read(chunk_size_bytes)
                if not chunk_binary_data:
                    break

                current_chunk_hash = hashlib.sha256(chunk_binary_data).digest()
                calculated_new_hashes.append(current_chunk_hash)

                is_hash_identical = (current_part_number <= len(existing_hashes) and current_chunk_hash == existing_hashes[current_part_number - 1])

                if is_hash_identical:
                    try:
                        start_range = (current_part_number - 1) * chunk_size_bytes
                        end_range = start_range + len(chunk_binary_data) - 1
                        byte_range_string = f"{start_range}-{end_range}"
                        copy_part_response = BasicOps.s3_copy_part(
                            connection_manager, destination_object.bucket, target_object_key, multipart_upload_id,
                            current_part_number, destination_object.bucket, target_object_key, byte_range_string
                        )
                        completed_upload_parts.append({"ETag": copy_part_response["CopyPartResult"]["ETag"], "PartNumber": current_part_number})
                    except Exception:
                        upload_response = BasicOps.s3_upload_part(connection_manager, destination_object.bucket, target_object_key, multipart_upload_id, current_part_number, chunk_binary_data)
                        completed_upload_parts.append({"ETag": upload_response["ETag"], "PartNumber": current_part_number})
                else:
                    upload_response = BasicOps.s3_upload_part(connection_manager, destination_object.bucket, target_object_key, multipart_upload_id, current_part_number, chunk_binary_data)
                    completed_upload_parts.append({"ETag": upload_response["ETag"], "PartNumber": current_part_number})

                current_part_number += 1

        BasicOps.s3_complete_multipart(connection_manager, destination_object.bucket, target_object_key, multipart_upload_id, completed_upload_parts)
        DeltaOps.save_registry(registry_file_path, registry_identifier, source_file_size, chunk_size_megabytes, calculated_new_hashes)

        execution_results["files"].append(TaskResponse(
            status=status_label,
            src=absolute_source_path,
            dst=f"s3://{destination_object.bucket}/{target_object_key}",
            size=source_file_size,
            date=datetime.now().strftime("%H:%M:%S")
        ))
        execution_results["total_size"], execution_results["count"] = source_file_size, 1

    except Exception as error:
        if multipart_upload_id:
            BasicOps.s3_abort_multipart(connection_manager, destination_object.bucket, target_object_key, multipart_upload_id)
        execution_results["errors"].append(str(error))

    return execution_results

def simulate_logic(connection_manager, command_model, plugin_instance):
    from core.execution import ExecutionEngine
    return ExecutionEngine.run_smart_task(connection_manager, command_model, None, plugin_instance, is_simulation=True)
