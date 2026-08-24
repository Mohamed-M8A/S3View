import os
import sys
import re
import hashlib
import mimetypes
from datetime import datetime, timezone
from core.models.structures import PathModel, MetadataModel


class Paths:

    @staticmethod
    def get_root_path():
        if getattr(sys, "frozen", False):
            path = os.path.dirname(os.path.abspath(sys.executable))
        else:
            current_file_path = os.path.abspath(__file__)
            path = os.path.dirname(os.path.dirname(current_file_path))

        return Paths.clean(path)


    @staticmethod
    def clean(raw_text):
        if not raw_text:
            return ""

        normalized_text = str(raw_text).strip().strip('"').strip("'").replace("\\", "/")
        normalized_text = re.sub(r"(?<!:)//+", "/", normalized_text)

        return normalized_text


    @staticmethod
    def resource_path(relative_path):
        if not relative_path:
            return ""

        root_directory = Paths.get_root_path()
        absolute_physical_path = os.path.normpath(os.path.join(root_directory, relative_path))

        return Paths.clean(absolute_physical_path)


    @staticmethod
    def resolve_local_scope(payload):
        root_directory = Paths.get_root_path()
        sandbox_base = os.path.abspath(os.path.join(root_directory, "LOCAL"))
        
        target_physical_path = os.path.abspath(
            os.path.join(sandbox_base, payload.lstrip("/\\"))
        )

        try:
            is_within_scope = os.path.commonpath([sandbox_base, target_physical_path]) == sandbox_base
        except ValueError:
            is_within_scope = False

        if not is_within_scope:
            raise Exception(f"FS_SECURITY_ERROR: Path '{target_physical_path}' escapes sandbox scope.")

        return Paths.clean(target_physical_path)


    @staticmethod
    def split_container_payload(payload):
        sanitized_payload = payload.lstrip("/")
        payload_segments = sanitized_payload.split("/", 1)

        container_name = payload_segments[0]
        object_prefix = payload_segments[1] if len(payload_segments) > 1 else ""

        if object_prefix and payload.endswith("/") and not object_prefix.endswith("/"):
            object_prefix += "/"

        return container_name, object_prefix


    @staticmethod
    def analyze(raw_path):
        normalized_input_path = Paths.clean(raw_path)
        detected_protocol = "EXTERNAL"
        is_cloud_resource = False
        virtual_payload = normalized_input_path

        if normalized_input_path.startswith(("s3://", "s3:/")):
            detected_protocol = "S3"
            is_cloud_resource = True
            virtual_payload = normalized_input_path.split(":", 1)[1].lstrip("/")

        elif normalized_input_path.startswith(("local://", "local:/")):
            detected_protocol = "LOCAL"
            virtual_payload = normalized_input_path.split(":", 1)[1].lstrip("/")

        path_model_instance = PathModel(
            payload=virtual_payload, 
            is_cloud=is_cloud_resource, 
            protocol=detected_protocol
        )
        
        if detected_protocol == "S3":
            path_model_instance.bucket, path_model_instance.prefix = Paths.split_container_payload(virtual_payload)
            
        return path_model_instance


    @staticmethod
    def get_full_physical_path(path_object: PathModel):
        if path_object.protocol == "LOCAL":
            return Paths.resolve_local_scope(path_object.payload)

        return Paths.clean(os.path.abspath(path_object.payload))


    @staticmethod
    def get_local_metadata(full_physical_path):
        try:
            filesystem_stats = os.stat(full_physical_path)
            guessed_mime_type, _ = mimetypes.guess_type(full_physical_path)

            return MetadataModel(
                key=Paths.clean(full_physical_path),
                size=filesystem_stats.st_size,
                last_mod=datetime.fromtimestamp(filesystem_stats.st_mtime, tz=timezone.utc),
                tier="LOCAL",
                content_type=guessed_mime_type or "application/octet-stream",
                is_cloud=False
            )

        except OSError as exception_context:
            raise Exception(f"FS_METADATA_ERROR: Failed to read resource metadata -> {str(exception_context)}")


    @staticmethod
    def get_registry_identifier(path_object: PathModel):
        if path_object.is_cloud:
            return None

        canonical_path_string = str(path_object.payload).replace("\\", "/").strip("/")

        return hashlib.md5(canonical_path_string.encode('utf-8')).hexdigest()


    @staticmethod
    def join(*path_segments):
        cleaned_segments = [
            str(segment).strip("/").replace("\\", "/") 
            for segment in path_segments 
            if segment
        ]

        return "/".join(cleaned_segments)

    @staticmethod
    def resolve_local_path(relative_key):
        clean_key = Paths.clean(relative_key).lstrip("/")
        root_path = Paths.get_root_path()
        return Paths.join(root_path, clean_key)