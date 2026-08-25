import os

from core.ops.storage_ops.local.local_ops import LocalOps
from core.ops.storage_ops.s3.integrity import (
    compute_expected_etag,
    is_encrypted,
    is_multipart_etag,
    normalize_etag,
    verify_etag,
    verify_size,
)


class IoOps:

    @staticmethod
    def s2s(manager, source_bucket, source_key, destination_bucket, destination_key, extra_args=None):
        source_head = manager.s3_client.head_object(Bucket=source_bucket, Key=source_key)

        response = manager.s3_client.copy_object(
            CopySource={"Bucket": source_bucket, "Key": source_key},
            Bucket=destination_bucket,
            Key=destination_key,
            **(extra_args or {})
        )

        context_label = f"s3://{destination_bucket}/{destination_key}"
        source_etag = normalize_etag(source_head.get("ETag"))

        if not is_encrypted(extra_args) and source_etag and not is_multipart_etag(source_etag):
            destination_etag = response.get("CopyObjectResult", {}).get("ETag")
            verify_etag(source_etag, destination_etag, context_label)
        else:
            destination_head = manager.s3_client.head_object(Bucket=destination_bucket, Key=destination_key)
            verify_size(source_head.get("ContentLength"), destination_head.get("ContentLength"), context_label)

        return response

    @staticmethod
    def s2l(manager, source_bucket, source_key, local_destination):
        LocalOps.ensure_directory(local_destination)
        source_head = manager.s3_client.head_object(Bucket=source_bucket, Key=source_key)

        download_result = manager.s3_client.download_file(
            source_bucket,
            source_key,
            local_destination,
            Config=manager.transfer_config
        )

        encryption_probe = {
            "ServerSideEncryption": source_head.get("ServerSideEncryption"),
            "SSECustomerAlgorithm": source_head.get("SSECustomerAlgorithm"),
        }
        source_etag = normalize_etag(source_head.get("ETag"))

        if not is_encrypted(encryption_probe) and source_etag and not is_multipart_etag(source_etag):
            local_hash = compute_expected_etag(
                local_destination,
                manager.transfer_config.multipart_chunksize,
                manager.transfer_config.multipart_threshold,
                file_size=source_head.get("ContentLength")
            )
            verify_etag(local_hash, source_etag, local_destination)
        else:
            verify_size(source_head.get("ContentLength"), os.path.getsize(local_destination), local_destination)

        return download_result

    @staticmethod
    def l2s(manager, local_source, destination_bucket, destination_key, extra_args=None):
        expected_etag = None
        if not is_encrypted(extra_args):
            expected_etag = compute_expected_etag(
                local_source,
                manager.transfer_config.multipart_chunksize,
                manager.transfer_config.multipart_threshold
            )

        upload_result = manager.s3_client.upload_file(
            local_source,
            destination_bucket,
            destination_key,
            ExtraArgs=(extra_args or {}),
            Config=manager.transfer_config
        )

        if expected_etag is not None:
            destination_head = manager.s3_client.head_object(Bucket=destination_bucket, Key=destination_key)
            if not is_encrypted(destination_head):
                verify_etag(expected_etag, destination_head.get("ETag"), f"s3://{destination_bucket}/{destination_key}")

        return upload_result

    @staticmethod
    def copy_folder(manager, source_bucket, source_prefix, destination_bucket, destination_prefix, extra_args=None):
        paginator = manager.s3_client.get_paginator("list_objects_v2")
        results = []
        for page in paginator.paginate(Bucket=source_bucket, Prefix=source_prefix):
            for obj in page.get("Contents", []):
                relative_key = obj["Key"][len(source_prefix):].lstrip("/")
                dest_key = f"{destination_prefix.rstrip('/')}/{relative_key}" if relative_key else destination_prefix
                result = IoOps.s2s(manager, source_bucket, obj["Key"], destination_bucket, dest_key, extra_args)
                results.append(result)
        return results

    @staticmethod
    def s3_del(manager, bucket_name, object_key):
        return manager.s3_client.delete_object(Bucket=bucket_name, Key=object_key)

    @staticmethod
    def _chunk_keys(keys_list, chunk_size):
        for start_index in range(0, len(keys_list), chunk_size):
            yield keys_list[start_index:start_index + chunk_size]

    @staticmethod
    def s3_del_batch(manager, bucket_name, keys_list):
        if not keys_list:
            return {"Deleted": [], "Errors": []}

        provider = getattr(manager, "provider", None)
        max_batch_keys = getattr(provider, "max_batch_delete_keys", 1000) or 1000
        batch_supported = getattr(provider, "supports_batch_delete", True)

        aggregated_result = {"Deleted": [], "Errors": []}

        if batch_supported:
            try:
                for chunk in IoOps._chunk_keys(keys_list, max_batch_keys):
                    delete_payload = {"Objects": [{"Key": key} for key in chunk]}
                    response = manager.s3_client.delete_objects(Bucket=bucket_name, Delete=delete_payload)
                    aggregated_result["Deleted"].extend(response.get("Deleted", []))
                    aggregated_result["Errors"].extend(response.get("Errors", []))
                return aggregated_result
            except Exception:
                pass

        for key in keys_list:
            try:
                manager.s3_client.delete_object(Bucket=bucket_name, Key=key)
                aggregated_result["Deleted"].append({"Key": key})
            except Exception as exc:
                aggregated_result["Errors"].append({"Key": key, "Message": str(exc)})

        return aggregated_result

    @staticmethod
    def s3_init_multipart(manager, bucket_name, object_key, extra_args=None):
        response = manager.s3_client.create_multipart_upload(
            Bucket=bucket_name, Key=object_key, **(extra_args or {})
        )
        return response.get("UploadId")

    @staticmethod
    def s3_upload_part(manager, bucket_name, object_key, upload_id, part_number, body_content):
        return manager.s3_client.upload_part(
            Bucket=bucket_name,
            Key=object_key,
            UploadId=upload_id,
            PartNumber=part_number,
            Body=body_content
        )

    @staticmethod
    def s3_copy_part(manager, bucket_name, object_key, upload_id, part_number, src_bucket, src_key, byte_range):
        copy_source = {"Bucket": src_bucket, "Key": src_key}
        return manager.s3_client.upload_part_copy(
            Bucket=bucket_name,
            Key=object_key,
            UploadId=upload_id,
            PartNumber=part_number,
            CopySource=copy_source,
            CopySourceRange=f"bytes={byte_range}"
        )

    @staticmethod
    def s3_complete_multipart(manager, bucket_name, object_key, upload_id, parts_list):
        return manager.s3_client.complete_multipart_upload(
            Bucket=bucket_name,
            Key=object_key,
            UploadId=upload_id,
            MultipartUpload={"Parts": parts_list}
        )

    @staticmethod
    def s3_abort_multipart(manager, bucket_name, object_key, upload_id):
        return manager.s3_client.abort_multipart_upload(
            Bucket=bucket_name, Key=object_key, UploadId=upload_id
        )

    @staticmethod
    def s3_list_multipart_uploads(manager, bucket_name):
        response = manager.s3_client.list_multipart_uploads(Bucket=bucket_name)
        return response.get("Uploads", [])

    @staticmethod
    def s3_list_parts(manager, bucket_name, object_key, upload_id):
        response = manager.s3_client.list_parts(
            Bucket=bucket_name, Key=object_key, UploadId=upload_id
        )
        return response.get("Parts", [])
