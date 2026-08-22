from core.ops.storage_ops.local.local_ops import LocalOps


class IoOps:

    @staticmethod
    def s2s(manager, source_bucket, source_key, destination_bucket, destination_key, extra_args=None):
        copy_source = {"Bucket": source_bucket, "Key": source_key}
        return manager.s3_client.copy_object(
            CopySource=copy_source,
            Bucket=destination_bucket,
            Key=destination_key,
            **(extra_args or {})
        )

    @staticmethod
    def s2l(manager, source_bucket, source_key, local_destination):
        LocalOps.ensure_directory(local_destination)
        return manager.s3_client.download_file(
            source_bucket,
            source_key,
            local_destination,
            Config=manager.transfer_config
        )

    @staticmethod
    def l2s(manager, local_source, destination_bucket, destination_key, extra_args=None):
        return manager.s3_client.upload_file(
            local_source,
            destination_bucket,
            destination_key,
            ExtraArgs=(extra_args or {}),
            Config=manager.transfer_config
        )

    @staticmethod
    def copy_folder(manager, source_bucket, source_prefix, destination_bucket, destination_prefix, extra_args=None):
        paginator = manager.s3_client.get_paginator("list_objects_v2")
        results = []
        for page in paginator.paginate(Bucket=source_bucket, Prefix=source_prefix):
            for obj in page.get("Contents", []):
                relative_key = obj["Key"][len(source_prefix):].lstrip("/")
                dest_key = f"{destination_prefix.rstrip('/')}/{relative_key}" if relative_key else destination_prefix
                copy_source = {"Bucket": source_bucket, "Key": obj["Key"]}
                result = manager.s3_client.copy_object(
                    CopySource=copy_source,
                    Bucket=destination_bucket,
                    Key=dest_key,
                    **(extra_args or {})
                )
                results.append(result)
        return results

    @staticmethod
    def s3_del(manager, bucket_name, object_key):
        return manager.s3_client.delete_object(Bucket=bucket_name, Key=object_key)

    @staticmethod
    def s3_del_batch(manager, bucket_name, keys_list):
        delete_payload = {"Objects": [{"Key": key} for key in keys_list]}
        return manager.s3_client.delete_objects(Bucket=bucket_name, Delete=delete_payload)

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
