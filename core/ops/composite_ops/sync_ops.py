import os
from core.paths import Paths
from core.models.structures import MetadataModel, PathModel
from core.ops.storage_ops.s3.integrity import compute_expected_etag, is_multipart_etag, normalize_etag

class SyncOps:
    @staticmethod
    def get_destination_map(connection_manager, destination_object: PathModel, depth_limit=None):
        resource_map = {}
        
        if destination_object.is_cloud:
            bucket_name = destination_object.bucket
            prefix = destination_object.prefix or ""
            base_prefix = prefix if prefix.endswith("/") else prefix + "/"
            
            paginator = connection_manager.s3_client.get_paginator("list_objects_v2")
            operation_params = {"Bucket": bucket_name, "Prefix": prefix}
            
            if depth_limit == 1: 
                operation_params["Delimiter"] = "/"
            
            for page in paginator.paginate(**operation_params):
                for obj in page.get("Contents", []):
                    object_key = obj["Key"]
                    if object_key.endswith('/'): 
                        continue
                    
                    relative_key = object_key[len(base_prefix):].lstrip("/") if prefix else object_key
                    resource_map[relative_key] = MetadataModel(
                        key=object_key, 
                        size=obj["Size"], 
                        last_mod=obj["LastModified"], 
                        is_cloud=True,
                        etag=normalize_etag(obj.get("ETag"))
                    )
        else:
            physical_root = Paths.get_full_physical_path(destination_object)
            if os.path.exists(physical_root):
                root_norm = Paths.clean(physical_root).rstrip("/")
                base_depth = root_norm.count("/")
                
                for root, directories, files in os.walk(root_norm):
                    current_root = Paths.clean(root)
                    current_depth = current_root.count("/") - base_depth
                    
                    if depth_limit is not None and current_depth >= depth_limit:
                        directories.clear()
                        continue
                        
                    for filename in files:
                        full_physical_path = Paths.join(current_root, filename)
                        relative_key = os.path.relpath(full_physical_path, root_norm).replace("\\", "/")
                        
                        metadata = Paths.get_local_metadata(full_physical_path)
                        resource_map[relative_key] = metadata
                        
        return resource_map

    @staticmethod
    def should_sync(source_item, destination_metadata, verify_hash=False, source_full_path=None,
                     base_chunksize=None, multipart_threshold=None):
        if source_item.size != destination_metadata.size:
            return True

        if verify_hash and source_full_path and destination_metadata.etag:
            if not is_multipart_etag(destination_metadata.etag):
                local_etag = compute_expected_etag(
                    source_full_path,
                    base_chunksize or (8 * 1024 * 1024),
                    multipart_threshold or (8 * 1024 * 1024),
                    file_size=source_item.size
                )
                return local_etag != destination_metadata.etag

        if source_item.last_mod > destination_metadata.last_mod:
            return True

        return False
