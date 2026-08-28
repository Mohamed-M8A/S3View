class ObjectOps:

    @staticmethod
    def s3_share(manager, bucket_name, object_key, expires_in_seconds):
        return manager.s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": object_key},
            ExpiresIn=expires_in_seconds
        )

    @staticmethod
    def s3_delete_objects_batch(manager, bucket_name, keys_list, quiet=False):
        from core.ops.s3.io_ops import IoOps
        return IoOps.s3_del_batch(manager, bucket_name, keys_list)

    @staticmethod
    def s3_generate_upload_url(manager, bucket_name, object_key, expires_in_seconds=3600, conditions=None):
        return manager.s3_client.generate_presigned_post(
            Bucket=bucket_name,
            Key=object_key,
            Conditions=conditions,
            ExpiresIn=expires_in_seconds
        )

    @staticmethod
    def s3_exists(manager, bucket_name, object_key):
        try:
            manager.s3_client.head_object(Bucket=bucket_name, Key=object_key)
            return True
        except Exception:
            return False

    @staticmethod
    def s3_list_objects(manager, bucket_name, prefix="", recursive=True):
        paginator = manager.s3_client.get_paginator("list_objects_v2")
        operation_params = {"Bucket": bucket_name, "Prefix": prefix}
        if not recursive:
            operation_params["Delimiter"] = "/"

        discovered_items = []
        for page in paginator.paginate(**operation_params):
            for item in page.get("Contents", []):
                discovered_items.append(item)
        return discovered_items

    @staticmethod
    def s3_get_folder_stats(manager, bucket_name, prefix=""):
        objects = ObjectOps.s3_list_objects(manager, bucket_name, prefix=prefix, recursive=True)
        total_bytes = sum(obj.get("Size", 0) for obj in objects)
        return {"total_bytes": total_bytes, "file_count": len(objects)}

    @staticmethod
    def s3_get_object(manager, bucket_name, object_key):
        response = manager.s3_client.get_object(Bucket=bucket_name, Key=object_key)
        return response["Body"].read()

    @staticmethod
    def s3_put_object(manager, bucket_name, object_key, body_content, extra_args=None):
        return manager.s3_client.put_object(
            Bucket=bucket_name, Key=object_key, Body=body_content, **(extra_args or {})
        )

    @staticmethod
    def s3_head_object(manager, bucket_name, object_key):
        return manager.s3_client.head_object(Bucket=bucket_name, Key=object_key)

    @staticmethod
    def s3_set_tags(manager, bucket_name, object_key=None, tags_dictionary=None):
        tags_dictionary = tags_dictionary or {}
        formatted_tags = [{"Key": k, "Value": str(v)} for k, v in tags_dictionary.items()]

        if object_key:
            return manager.s3_client.put_object_tagging(
                Bucket=bucket_name, Key=object_key, Tagging={"TagSet": formatted_tags}
            )
        return manager.s3_client.put_bucket_tagging(
            Bucket=bucket_name, Tagging={"TagSet": formatted_tags}
        )

    @staticmethod
    def s3_get_tags(manager, bucket_name, object_key=None):
        if object_key:
            return manager.s3_client.get_object_tagging(Bucket=bucket_name, Key=object_key)
        return manager.s3_client.get_bucket_tagging(Bucket=bucket_name)

    @staticmethod
    def s3_delete_tags(manager, bucket_name, object_key=None):
        if object_key:
            return manager.s3_client.delete_object_tagging(Bucket=bucket_name, Key=object_key)
        return manager.s3_client.delete_bucket_tagging(Bucket=bucket_name)

    @staticmethod
    def s3_change_storage_class(manager, bucket_name, object_key, target_tier="INTELLIGENT_TIERING"):
        copy_source = {"Bucket": bucket_name, "Key": object_key}
        return manager.s3_client.copy_object(
            Bucket=bucket_name,
            Key=object_key,
            CopySource=copy_source,
            StorageClass=target_tier,
            MetadataDirective="REPLACE"
        )

    @staticmethod
    def s3_set_metadata(manager, bucket_name, object_key, metadata_dict):
        copy_source = {"Bucket": bucket_name, "Key": object_key}
        return manager.s3_client.copy_object(
            Bucket=bucket_name,
            Key=object_key,
            CopySource=copy_source,
            Metadata=metadata_dict,
            MetadataDirective="REPLACE"
        )

    @staticmethod
    def s3_restore_object(manager, bucket_name, object_key, days=7, retrieval_tier="Standard"):
        return manager.s3_client.restore_object(
            Bucket=bucket_name,
            Key=object_key,
            RestoreRequest={
                "Days": days,
                "GlacierJobParameters": {"Tier": retrieval_tier}
            }
        )

    @staticmethod
    def s3_get_object_acl(manager, bucket_name, object_key):
        return manager.s3_client.get_object_acl(Bucket=bucket_name, Key=object_key)

    @staticmethod
    def s3_set_object_acl(manager, bucket_name, object_key, acl="private"):
        return manager.s3_client.put_object_acl(Bucket=bucket_name, Key=object_key, ACL=acl)

    @staticmethod
    def s3_get_object_legal_hold(manager, bucket_name, object_key):
        return manager.s3_client.get_object_legal_hold(Bucket=bucket_name, Key=object_key)

    @staticmethod
    def s3_set_object_legal_hold(manager, bucket_name, object_key, status="ON"):
        return manager.s3_client.put_object_legal_hold(
            Bucket=bucket_name, Key=object_key, LegalHold={"Status": status}
        )

    @staticmethod
    def s3_get_object_retention(manager, bucket_name, object_key):
        return manager.s3_client.get_object_retention(Bucket=bucket_name, Key=object_key)

    @staticmethod
    def s3_set_object_retention(manager, bucket_name, object_key, mode="GOVERNANCE", retain_until=None):
        return manager.s3_client.put_object_retention(
            Bucket=bucket_name,
            Key=object_key,
            Retention={"Mode": mode, "RetainUntilDate": retain_until}
        )

    @staticmethod
    def s3_select_content(manager, bucket_name, object_key, sql_expression, is_csv=True):
        input_serialization = {"CSV": {"FileHeaderInfo": "USE"}} if is_csv else {"JSON": {"Type": "DOCUMENT"}}
        response = manager.s3_client.select_object_content(
            Bucket=bucket_name,
            Key=object_key,
            ExpressionType="SQL",
            Expression=sql_expression,
            InputSerialization=input_serialization,
            OutputSerialization={"JSON": {}}
        )

        records = []
        for event in response["Payload"]:
            if "Records" in event:
                records.append(event["Records"]["Payload"].decode("utf-8"))
        return "".join(records)