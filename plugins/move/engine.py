from core.execution.operations import BasicOps
from core.models.structures import TaskResponse


def worker(connection_manager, execution_context, command_model):
    protocol = execution_context["protocol"]
    source_path = execution_context["source_key"]
    destination_path = execution_context["destination_key"]
    item_metadata = execution_context["item"]

    s3_extra_args = {}
    if hasattr(command_model, "tier") and command_model.tier:
        s3_extra_args["StorageClass"] = command_model.tier

    if protocol in ("L2C", "C2C"):
        content_type = getattr(item_metadata, "content_type", "application/octet-stream")
        s3_extra_args["ContentType"] = content_type

    try:
        if protocol == "C2C":
            BasicOps.c2c(
                connection_manager,
                command_model.src.bucket,
                source_path,
                command_model.dst.bucket,
                destination_path,
                extra_args=s3_extra_args
            )
            BasicOps.s3_del(
                connection_manager,
                command_model.src.bucket,
                source_path
            )

        elif protocol == "C2L":
            BasicOps.c2l(
                connection_manager,
                command_model.src.bucket,
                source_path,
                destination_path
            )
            BasicOps.s3_del(
                connection_manager,
                command_model.src.bucket,
                source_path
            )

        elif protocol == "L2C":
            BasicOps.l2c(
                connection_manager,
                source_path,
                command_model.dst.bucket,
                destination_path,
                extra_args=s3_extra_args
            )
            BasicOps.loc_del(source_path)

        elif protocol == "L2L":
            BasicOps.l2l(
                source_path,
                destination_path,
                move_mode=True
            )

        return True

    except Exception as e:
        return TaskResponse.failure(
            src=source_path,
            error_msg=str(e)
        )