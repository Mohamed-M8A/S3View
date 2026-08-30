from typing import Any, Dict
from core.execution.operations import BasicOps


def worker(
    connection_manager: Any,
    execution_context: Dict[str, Any],
    command_model: Any
) -> bool:
    protocol = execution_context["protocol"]
    source_path = execution_context["source_key"]
    destination_path = execution_context["destination_key"]
    item_metadata = execution_context.get("item")

    s3_extra_args = {}

    tier = getattr(command_model, "tier", None)
    if tier:
        s3_extra_args["StorageClass"] = tier

    if protocol in ("L2S", "S2S"):
        content_type = getattr(item_metadata, "content_type", "application/octet-stream")
        s3_extra_args["ContentType"] = content_type

    if protocol == "S2S":
        BasicOps.s2s(
            connection_manager,
            command_model.src.bucket,
            source_path,
            command_model.dst.bucket,
            destination_path,
            extra_args=s3_extra_args
        )
    elif protocol == "S2L":
        BasicOps.s2l(
            connection_manager,
            command_model.src.bucket,
            source_path,
            destination_path
        )
    elif protocol == "L2S":
        BasicOps.l2s(
            connection_manager,
            source_path,
            command_model.dst.bucket,
            destination_path,
            extra_args=s3_extra_args
        )
    elif protocol == "L2L":
        BasicOps.l2l(
            source_path,
            destination_path,
            move_mode=False
        )

    return True
