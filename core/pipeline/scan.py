import os
from botocore.exceptions import ClientError
from .shield import Shield
from core.filter import FilterEngine
from core.paths import Paths
from core.report import Reporting
from core.models import MetadataModel, PathModel


class UniversalScanner:

    @staticmethod
    def scan(connection_manager, path_object: PathModel, command, statistics):
        protected_list = Shield.load_protected_list()

        if path_object.is_cloud:
            root_prefix = (path_object.prefix or "").lstrip("/")
            root_identifier = f"{path_object.bucket}/{root_prefix}"
        else:
            physical_root = Paths.get_full_physical_path(path_object)
            root_identifier = Paths.clean(physical_root)

        if command.action != "list":
            if not Shield.is_allowed({"payload": root_identifier}, command.exclusions, protected_list, protocol=path_object.protocol):
                raise RuntimeError(
                    f"SHIELD_BLOCKED: Refusing to operate on '{root_identifier}' -- it is a drive root, "
                    f"filesystem root, or a protected system directory. This is a deliberate safety guard, "
                    f"not an empty-result. Point the command at a specific subdirectory instead."
                )

        if path_object.protocol == "S3":
            return UniversalScanner._scan_s3_storage(connection_manager, path_object, command, statistics, protected_list)
        
        if path_object.protocol == "LOCAL":
            return UniversalScanner._scan_local_filesystem(path_object, command, statistics, protected_list)

        return []


    @staticmethod
    def _scan_s3_storage(manager, path_object: PathModel, command, statistics, protected_list):
        inventory = []
        target_bucket = path_object.bucket
        raw_prefix = path_object.prefix or ""
        target_prefix = raw_prefix.lstrip("/")
        is_recursive_mode = path_object.is_directory or target_prefix == ""
        needs_mime_resolution = FilterEngine.requires_mime_resolution(getattr(command, "compiled_logic", None))

        try:
            paginator = manager.s3_client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=target_bucket, Prefix=target_prefix):
                if 'Contents' not in page:
                    continue

                for obj in page['Contents']:
                    if command.limit and len(inventory) >= command.limit:
                        return inventory

                    object_key = obj['Key']
                    if not is_recursive_mode:
                        if object_key != target_prefix:
                            continue
                    else:
                        if object_key == target_prefix:
                            continue

                    if is_recursive_mode and command.depth is not None:
                        relative_path = object_key[len(target_prefix):].lstrip("/")
                        if relative_path and relative_path.count("/") > command.depth:
                            continue

                    full_id = f"{target_bucket}/{object_key}"
                    if not Shield.is_allowed({"payload": full_id}, command.exclusions, protected_list, protocol="S3"):
                        continue

                    resolved_content_type = "application/octet-stream"
                    if needs_mime_resolution:
                        try:
                            head_response = manager.s3_client.head_object(Bucket=target_bucket, Key=object_key)
                            resolved_content_type = head_response.get("ContentType", resolved_content_type)
                        except ClientError as head_exc:
                            Reporting.save_error_log(f"S3_HEAD_ERROR: {target_bucket}/{object_key}", str(head_exc))

                    metadata = MetadataModel(
                        key=object_key,
                        size=obj['Size'],
                        last_mod=obj['LastModified'],
                        tier=obj.get('StorageClass', 'STANDARD'),
                        content_type=resolved_content_type,
                        is_cloud=True
                    )

                    if FilterEngine.should_process_compiled(command.compiled_logic, metadata, command.logic_inversion, statistics["total_size"], statistics["count"]):
                        inventory.append(metadata)
                        statistics["total_size"] += metadata.size
                        statistics["count"] += 1

        except ClientError as exc:
            error_msg = f"S3_SCAN_ERROR: {target_bucket}/{target_prefix} :: {str(exc)}"
            Reporting.save_error_log(f"S3_SCAN_ERROR: {target_bucket}/{target_prefix}", str(exc))
            raise RuntimeError(error_msg) from exc

        return inventory


    @staticmethod
    def _scan_local_filesystem(path_object: PathModel, command, statistics, protected_list):
        inventory = []
        physical_root = Paths.get_full_physical_path(path_object)
        is_folder_intent = path_object.is_directory

        if not is_folder_intent:
            if os.path.isfile(physical_root):
                cleaned_file_path = Paths.clean(physical_root)
                if Shield.is_allowed({"payload": cleaned_file_path}, command.exclusions, protected_list, protocol="LOCAL"):
                    try:
                        metadata = Paths.get_local_metadata(cleaned_file_path)
                    except (OSError, PermissionError) as exc:
                        Reporting.save_error_log(cleaned_file_path, str(exc))
                        return inventory

                    if FilterEngine.should_process_compiled(command.compiled_logic, metadata, command.logic_inversion, statistics["total_size"], statistics["count"]):
                        inventory.append(metadata)
                        statistics["total_size"] += metadata.size
                        statistics["count"] += 1
            return inventory

        if not os.path.isdir(physical_root):
            return inventory

        cleaned_root = Paths.clean(physical_root)
        base_directory = cleaned_root.rstrip("/")
        if not base_directory or (len(base_directory) == 2 and base_directory[1] == ":"):
            base_directory = cleaned_root
        base_depth = base_directory.count("/")

        for root, directories, files in os.walk(base_directory, topdown=True):
            current_directory = Paths.clean(root)
            current_depth = current_directory.count("/") - base_depth

            if command.depth is not None and current_depth > command.depth:
                directories[:] = []
                continue

            directories[:] = [
                d for d in directories 
                if Shield.is_allowed({"payload": Paths.join(current_directory, d)}, command.exclusions, protected_list, protocol="LOCAL")
            ]

            for filename in files:
                if command.limit and len(inventory) >= command.limit:
                    return inventory

                full_file_path = Paths.join(current_directory, filename)
                if not Shield.is_allowed({"payload": full_file_path}, command.exclusions, protected_list, protocol="LOCAL"):
                    continue

                try:
                    metadata = Paths.get_local_metadata(full_file_path)
                except (OSError, PermissionError) as exc:
                    Reporting.save_error_log(full_file_path, str(exc))
                    continue

                if FilterEngine.should_process_compiled(command.compiled_logic, metadata, command.logic_inversion, statistics["total_size"], statistics["count"]):
                    inventory.append(metadata)
                    statistics["total_size"] += metadata.size
                    statistics["count"] += 1

        return inventory