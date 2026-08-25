import os
from datetime import datetime, timedelta, timezone
from core.models import TaskResponse
from core.execution.operations import BasicOps
from core.paths import Paths
import core.config as config


def worker(connection_manager, execution_context, command_model):
    source_key = execution_context["source_key"]
    bucket_name = command_model.src.bucket
    expiration_time = command_model.expires or 3600

    raw_url = BasicOps.s3_share(connection_manager, bucket_name, source_key, expiration_time)
    custom_domain = command_model.extra_metadata.get("_custom_domain", "")
    final_url = Paths.apply_custom_domain(raw_url, custom_domain)
    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=expiration_time)).isoformat()

    return TaskResponse(
        status="SHARED",
        src=f"s3://{bucket_name}/{source_key}",
        dst=final_url,
        size=execution_context["item"].size,
        date=datetime.now().strftime("%H:%M:%S"),
        metadata={"key": source_key, "original_url": raw_url, "expires_at": expires_at, "expires_in_seconds": expiration_time}
    )


def execute_logic(connection_manager, command_model, plugin_instance):
    from core.execution import ExecutionEngine
    from plugins.share import formatter

    if not command_model.src.is_cloud:
        return {"files": [], "errors": ["Link generation is only available for cloud-hosted S3 objects."], "total_size": 0, "count": 0}

    settings = config.load_config()
    command_model.extra_metadata["_custom_domain"] = settings.get("CUSTOM_DOMAIN", "")
    include_original = settings.get("SHARE_INCLUDE_ORIGINAL_URL", False)

    execution_results = ExecutionEngine.run_smart_task(connection_manager, command_model, worker, plugin_instance)

    if execution_results["files"]:
        bucket_name = command_model.src.bucket
        custom_domain = settings.get("CUSTOM_DOMAIN", "")
        payload = formatter.build_payload(execution_results["files"], bucket_name, custom_domain, include_original)

        timestamp_string = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Paths.resource_path("Reports/SHARES")
        os.makedirs(output_dir, exist_ok=True)

        if settings.get("SHARE_FORMAT_HTML", True):
            formatter.write_html(payload, os.path.join(output_dir, f"Share_{timestamp_string}.html"))
        if settings.get("SHARE_FORMAT_JSON", False):
            formatter.write_json(payload, os.path.join(output_dir, f"Share_{timestamp_string}.json"))
        if settings.get("SHARE_FORMAT_TXT", False):
            formatter.write_txt(payload, os.path.join(output_dir, f"Share_{timestamp_string}.txt"))

    return execution_results


def simulate_logic(connection_manager, command_model, plugin_instance):
    from core.execution import ExecutionEngine
    return ExecutionEngine.run_smart_task(connection_manager, command_model, None, plugin_instance, is_simulation=True)
