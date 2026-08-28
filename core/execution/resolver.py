import os
from typing import Optional
from core.models.structures import CommandModel, PathModel
from core.paths import Paths

class PathResolver:
    @staticmethod
    def resolve_physical(path_object: PathModel, relative_key: str):
        clean_key = Paths.clean(relative_key).lstrip("/")

        if not path_object or path_object.is_cloud:
            return clean_key

        if os.path.isabs(relative_key) or (len(relative_key) > 1 and relative_key[1] == ":"):
            return Paths.clean(os.path.normpath(relative_key))

        absolute_base = Paths.get_full_physical_path(path_object)
        return Paths.join(absolute_base, clean_key)

    @staticmethod
    def calculate_destination_key(source_key, base_path, destination_object: Optional[PathModel], command: CommandModel):
        if not destination_object:
            return None

        clean_source = Paths.clean(source_key)
        clean_base = Paths.clean(base_path or "")

        if command.is_flat:
            relative_result = os.path.basename(clean_source.rstrip("/"))
        else:
            if not clean_base:
                relative_result = clean_source
            else:
                source_cmp = clean_source.lower() if os.name == 'nt' else clean_source
                base_cmp = clean_base.lower() if os.name == 'nt' else clean_base

                if source_cmp.startswith(base_cmp):
                    relative_result = clean_source[len(base_cmp):].lstrip("/")
                    if not relative_result:
                        relative_result = os.path.basename(clean_source.rstrip("/"))
                else:
                    relative_result = os.path.basename(clean_source.rstrip("/"))

        dest_prefix = destination_object.prefix if destination_object.is_cloud else ""

        return Paths.join(dest_prefix or "", relative_result).lstrip("/")

    @staticmethod
    def detect_protocol(source_object: PathModel, destination_object: Optional[PathModel]):
        if not destination_object:
            return "SINGLE"

        protocol_tags = {
            "S3": "S",
            "LOCAL": "L"
        }

        source_tag = protocol_tags.get(source_object.protocol, "L")
        dest_tag = protocol_tags.get(destination_object.protocol, "L")

        return f"{source_tag}2{dest_tag}"

    @staticmethod
    def resolve_base_path(path_object: PathModel):
        if path_object.is_cloud:
            return path_object.prefix or ""

        full_path = Paths.clean(Paths.get_full_physical_path(path_object))
        if path_object.is_directory and not full_path.endswith("/"):
            full_path += "/"
        return full_path

    @staticmethod
    def format_identifier(raw_path, path_object: Optional[PathModel]):
        clean_resource = Paths.clean(raw_path).lstrip("/")
        if not path_object:
            return clean_resource

        if path_object.protocol == "S3":
            bucket = path_object.bucket or ""
            return f"s3://{bucket}/{clean_resource}"

        if path_object.protocol == "LOCAL":
            return f"local://{clean_resource}"

        return clean_resource