"""
core/paths.py -- resolves raw path strings the user types into structured
PathModel objects (local filesystem paths and S3 bucket/prefix paths), and
provides related filesystem/metadata helpers used across the codebase.

Path semantics fixed in this file (2026-08-30 session):
- A path's trailing "/" is the ONLY signal for whether it is a file or a
  folder. There is deliberately no disk lookup (os.path.isdir) to "smartly"
  reclassify a path some other way -- a path with no trailing slash always
  means "a file with this exact name"; if no such file exists, that is a
  normal, expected not-found result, not a cue to guess the user meant a
  directory instead. This was a real, confirmed bug: os.path.isdir() was
  silently upgrading file-intent paths to folder-intent whenever a folder
  of that name happened to exist on disk.
- That trailing-slash intent has to be captured from the raw input BEFORE
  os.path.abspath()/os.path.normpath() run, because both silently strip
  trailing separators (e.g. abspath("/tmp/x/") == "/tmp/x"). Checking
  endswith("/") only *after* calling abspath() would always return False,
  since the very thing being checked for was already destroyed -- this was
  the root cause of local folder detection being broken entirely at one
  point during today's fixes, and is why the slash is captured up front
  here and re-applied to the absolute path afterward.
- resolve_local_path() was added because it did not exist before, despite
  being called by the archive/media plugins for their default output path
  -- every call to it was crashing with AttributeError.
"""

import os
import sys
import re
import hashlib
import mimetypes
from datetime import datetime, timezone
from core.models import PathModel, MetadataModel


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
        detected_protocol = "LOCAL"
        is_cloud_resource = False
        virtual_payload = normalized_input_path

        if normalized_input_path.startswith(("s3://", "s3:/")):
            detected_protocol = "S3"
            is_cloud_resource = True
            virtual_payload = normalized_input_path.split(":", 1)[1].lstrip("/")

        elif normalized_input_path.startswith(("local://", "local:/")):
            detected_protocol = "LOCAL"
            virtual_payload = normalized_input_path.split(":", 1)[1].lstrip("/")

        user_specified_directory = virtual_payload.endswith("/")

        if not is_cloud_resource:
            virtual_payload = Paths.clean(os.path.abspath(virtual_payload))
            if user_specified_directory and not virtual_payload.endswith("/"):
                virtual_payload += "/"

        is_directory_flag = virtual_payload.endswith("/")

        path_model_instance = PathModel(
            payload=virtual_payload, 
            is_cloud=is_cloud_resource, 
            is_directory=is_directory_flag,
            protocol=detected_protocol
        )
        
        if detected_protocol == "S3":
            path_model_instance.bucket, path_model_instance.prefix = Paths.split_container_payload(virtual_payload)

        return path_model_instance


    @staticmethod
    def resolve_local_path(relative_or_filename):
        if not relative_or_filename:
            return ""
        return Paths.clean(os.path.abspath(relative_or_filename))


    @staticmethod
    def get_full_physical_path(path_object: PathModel):
        if not path_object.is_cloud:
            return Paths.clean(os.path.abspath(path_object.payload))

        return Paths.clean(path_object.payload)


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
        segments = [str(segment) for segment in path_segments if segment]
        if not segments:
            return ""

        is_absolute = segments[0].replace("\\", "/").startswith("/")

        cleaned_segments = [
            segment.strip("/").replace("\\", "/")
            for segment in segments
        ]
        cleaned_segments = [s for s in cleaned_segments if s]

        joined = "/".join(cleaned_segments)
        return f"/{joined}" if is_absolute else joined


    @staticmethod
    def apply_custom_domain(url, custom_domain):
        if not custom_domain:
            return url
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(url)
        domain_text = custom_domain if "://" in custom_domain else f"https://{custom_domain}"
        parsed_domain = urlparse(domain_text)
        return urlunparse(parsed._replace(scheme=parsed_domain.scheme, netloc=parsed_domain.netloc))