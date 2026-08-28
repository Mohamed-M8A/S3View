import os
import uuid
from core.models import TaskResponse
from core.execution.operations import BasicOps
from core.ops.composite_ops.media_ops import MediaOps
from core.paths import Paths

def worker(connection_manager, execution_context, command_model):
    source_path = execution_context["source_key"]
    destination_path = execution_context["destination_key"]
    item_metadata = execution_context["item"]

    quality_level = command_model.level or 80
    target_extension = command_model.extra_metadata.get("target_extension")
    target_format = command_model.extra_metadata.get("target_format")

    vault_path = Paths.resource_path("_sys/.vault")
    temporary_input = Paths.join(vault_path, f"input_{uuid.uuid4().hex[:6]}")
    temporary_output = Paths.join(vault_path, f"output_{uuid.uuid4().hex[:6]}.{target_extension}")

    try:
        if command_model.src.is_cloud:
            BasicOps.s2l(connection_manager, command_model.src.bucket, source_path, temporary_input)
        else:
            BasicOps.l2l(source_path, temporary_input, move_mode=False)

        if MediaOps.transform(temporary_input, temporary_output, target_format, quality_level):
            final_filename = f"{os.path.splitext(destination_path or source_path)[0]}.{target_extension}"

            is_destination_cloud = command_model.dst.is_cloud if command_model.dst else command_model.src.is_cloud
            target_bucket = command_model.dst.bucket if command_model.dst else command_model.src.bucket

            if is_destination_cloud:
                BasicOps.l2s(connection_manager, temporary_output, target_bucket, final_filename, extra_args=BasicOps.build_s3_extra_args(command_model))
                result_destination = f"s3://{target_bucket}/{final_filename}"
            else:
                local_destination = Paths.resolve_local_path(final_filename) if not command_model.dst or command_model.dst.protocol == "LOCAL" else final_filename
                BasicOps.l2l(temporary_output, local_destination, move_mode=False)
                result_destination = local_destination

            return TaskResponse(
                status=f"{execution_context['status_text']}({target_format})",
                src=source_path,
                dst=result_destination,
                size=os.path.getsize(temporary_output),
                tier=getattr(item_metadata, "tier", "STANDARD")
            )
        return TaskResponse.failure(src=source_path, error_msg="IMAGE_TRANSFORM_FAILED")
    finally:
        for temporary_file in [temporary_input, temporary_output]:
            if os.path.exists(temporary_file):
                os.remove(temporary_file)
