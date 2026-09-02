class BucketOps:

    @staticmethod
    def _clean_bucket_name(bucket_name):
        return str(bucket_name).strip()

    @staticmethod
    def s3_create_bucket(manager, bucket_name):
        clean_name = BucketOps._clean_bucket_name(bucket_name)
        region = manager.s3_client.meta.region_name
        provider = getattr(manager, "provider", None)
        provider_id = getattr(provider, "id", "")

        if provider_id in ("R2",) or region == "us-east-1":
            return manager.s3_client.create_bucket(Bucket=clean_name)

        return manager.s3_client.create_bucket(
            Bucket=clean_name,
            CreateBucketConfiguration={'LocationConstraint': region}
        )

    @staticmethod
    def s3_delete_bucket(manager, bucket_name, force=False):
        clean_name = BucketOps._clean_bucket_name(bucket_name)
        if force:
            from .io import IoOps
            paginator = manager.s3_client.get_paginator("list_object_versions")
            for page in paginator.paginate(Bucket=clean_name):
                objects_to_delete = []
                for version in page.get("Versions", []):
                    objects_to_delete.append({"Key": version["Key"], "VersionId": version["VersionId"]})
                for marker in page.get("DeleteMarkers", []):
                    objects_to_delete.append({"Key": marker["Key"], "VersionId": marker["VersionId"]})
                for chunk in IoOps._chunk_keys(objects_to_delete, 1000):
                    manager.s3_client.delete_objects(
                        Bucket=clean_name, Delete={"Objects": chunk}
                    )
        return manager.s3_client.delete_bucket(Bucket=clean_name)

    @staticmethod
    def s3_list_buckets(manager):
        response = manager.s3_client.list_buckets()
        return response.get("Buckets", [])

    @staticmethod
    def s3_bucket_exists(manager, bucket_name):
        clean_name = BucketOps._clean_bucket_name(bucket_name)
        try:
            manager.s3_client.head_bucket(Bucket=clean_name)
            return True
        except Exception:
            return False

    @staticmethod
    def s3_get_bucket_location(manager, bucket_name):
        return manager.s3_client.get_bucket_location(Bucket=bucket_name)

    @staticmethod
    def s3_toggle_versioning(manager, bucket_name, enabled=True):
        status = "Enabled" if enabled else "Suspended"
        return manager.s3_client.put_bucket_versioning(
            Bucket=bucket_name, VersioningConfiguration={"Status": status}
        )

    @staticmethod
    def s3_get_bucket_versioning(manager, bucket_name):
        return manager.s3_client.get_bucket_versioning(Bucket=bucket_name)

    @staticmethod
    def s3_list_versions(manager, bucket_name, prefix=""):
        return manager.s3_client.list_object_versions(
            Bucket=bucket_name, Prefix=prefix
        )

    @staticmethod
    def s3_set_encryption(manager, bucket_name, algorithm="AES256"):
        encryption_rule = {"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": algorithm}}
        return manager.s3_client.put_bucket_encryption(
            Bucket=bucket_name,
            ServerSideEncryptionConfiguration={"Rules": [encryption_rule]}
        )

    @staticmethod
    def s3_get_bucket_encryption(manager, bucket_name):
        return manager.s3_client.get_bucket_encryption(Bucket=bucket_name)

    @staticmethod
    def s3_delete_bucket_encryption(manager, bucket_name):
        return manager.s3_client.delete_bucket_encryption(Bucket=bucket_name)

    @staticmethod
    def s3_set_policy(manager, bucket_name, policy_json):
        return manager.s3_client.put_bucket_policy(Bucket=bucket_name, Policy=policy_json)

    @staticmethod
    def s3_get_bucket_policy(manager, bucket_name):
        return manager.s3_client.get_bucket_policy(Bucket=bucket_name)

    @staticmethod
    def s3_delete_bucket_policy(manager, bucket_name):
        return manager.s3_client.delete_bucket_policy(Bucket=bucket_name)

    @staticmethod
    def s3_get_bucket_acl(manager, bucket_name):
        return manager.s3_client.get_bucket_acl(Bucket=bucket_name)

    @staticmethod
    def s3_set_bucket_acl(manager, bucket_name, acl="private"):
        return manager.s3_client.put_bucket_acl(Bucket=bucket_name, ACL=acl)

    @staticmethod
    def s3_block_public_access(manager, bucket_name, state=True):
        return manager.s3_client.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": state,
                "IgnorePublicAcls": state,
                "BlockPublicPolicy": state,
                "RestrictPublicBuckets": state
            }
        )

    @staticmethod
    def s3_get_public_access_block(manager, bucket_name):
        return manager.s3_client.get_public_access_block(Bucket=bucket_name)

    @staticmethod
    def s3_set_ownership_controls(manager, bucket_name, rule="BucketOwnerEnforced"):
        return manager.s3_client.put_bucket_ownership_controls(
            Bucket=bucket_name,
            OwnershipControls={"Rules": [{"ObjectOwnership": rule}]}
        )

    @staticmethod
    def s3_get_ownership_controls(manager, bucket_name):
        return manager.s3_client.get_bucket_ownership_controls(Bucket=bucket_name)

    @staticmethod
    def s3_set_cors(manager, bucket_name, origins=None, methods=None):
        cors_rule = {
            "AllowedHeaders": ["*"],
            "AllowedMethods": methods or ["GET", "PUT", "POST", "DELETE"],
            "AllowedOrigins": origins or ["*"],
            "MaxAgeSeconds": 3000
        }
        return manager.s3_client.put_bucket_cors(Bucket=bucket_name, CORSConfiguration={"CORSRules": [cors_rule]})

    @staticmethod
    def s3_get_bucket_cors(manager, bucket_name):
        return manager.s3_client.get_bucket_cors(Bucket=bucket_name)

    @staticmethod
    def s3_delete_bucket_cors(manager, bucket_name):
        return manager.s3_client.delete_bucket_cors(Bucket=bucket_name)

    @staticmethod
    def s3_set_lifecycle(manager, bucket_name, rules_list):
        return manager.s3_client.put_bucket_lifecycle_configuration(
            Bucket=bucket_name, LifecycleConfiguration={"Rules": rules_list}
        )

    @staticmethod
    def s3_get_bucket_lifecycle(manager, bucket_name):
        return manager.s3_client.get_bucket_lifecycle_configuration(Bucket=bucket_name)

    @staticmethod
    def s3_delete_bucket_lifecycle(manager, bucket_name):
        return manager.s3_client.delete_bucket_lifecycle(Bucket=bucket_name)

    @staticmethod
    def s3_set_notifications(manager, bucket_name, config):
        return manager.s3_client.put_bucket_notification_configuration(
            Bucket=bucket_name, NotificationConfiguration=config
        )

    @staticmethod
    def s3_get_bucket_notifications(manager, bucket_name):
        return manager.s3_client.get_bucket_notification_configuration(Bucket=bucket_name)

    @staticmethod
    def s3_set_object_lock(manager, bucket_name, mode="COMPLIANCE", days=30):
        return manager.s3_client.put_object_lock_configuration(
            Bucket=bucket_name,
            ObjectLockConfiguration={
                "ObjectLockEnabled": "Enabled",
                "Rule": {"DefaultRetention": {"Mode": mode, "Days": days}},
            },
        )

    @staticmethod
    def s3_get_object_lock_configuration(manager, bucket_name):
        return manager.s3_client.get_object_lock_configuration(Bucket=bucket_name)

    @staticmethod
    def s3_set_replication(manager, bucket_name, role_arn, destination_bucket_arn, prefix=""):
        replication_config = {
            "Role": role_arn,
            "Rules": [
                {
                    "Status": "Enabled",
                    "Priority": 1,
                    "Filter": {"Prefix": prefix},
                    "Destination": {"Bucket": destination_bucket_arn},
                }
            ],
        }
        return manager.s3_client.put_bucket_replication(
            Bucket=bucket_name, ReplicationConfiguration=replication_config
        )

    @staticmethod
    def s3_get_replication(manager, bucket_name):
        return manager.s3_client.get_bucket_replication(Bucket=bucket_name)

    @staticmethod
    def s3_delete_replication(manager, bucket_name):
        return manager.s3_client.delete_bucket_replication(Bucket=bucket_name)

    @staticmethod
    def s3_set_logging(manager, bucket_name, target_bucket, target_prefix=""):
        return manager.s3_client.put_bucket_logging(
            Bucket=bucket_name,
            BucketLoggingStatus={
                "LoggingEnabled": {
                    "TargetBucket": target_bucket,
                    "TargetPrefix": target_prefix,
                }
            },
        )

    @staticmethod
    def s3_get_bucket_logging(manager, bucket_name):
        return manager.s3_client.get_bucket_logging(Bucket=bucket_name)

    @staticmethod
    def s3_set_transfer_acceleration(manager, bucket_name, enabled=True):
        status = "Enabled" if enabled else "Suspended"
        return manager.s3_client.put_bucket_accelerate_configuration(
            Bucket=bucket_name, AccelerateConfiguration={"Status": status}
        )

    @staticmethod
    def s3_get_transfer_acceleration(manager, bucket_name):
        return manager.s3_client.get_bucket_accelerate_configuration(Bucket=bucket_name)

    @staticmethod
    def s3_set_request_payment(manager, bucket_name, requester_pays=True):
        payer = "Requester" if requester_pays else "BucketOwner"
        return manager.s3_client.put_bucket_request_payment(
            Bucket=bucket_name, RequestPaymentConfiguration={"Payer": payer}
        )

    @staticmethod
    def s3_get_request_payment(manager, bucket_name):
        return manager.s3_client.get_bucket_request_payment(Bucket=bucket_name)

    @staticmethod
    def s3_enable_static_website(manager, bucket_name, index="index.html", error="error.html"):
        return manager.s3_client.put_bucket_website(
            Bucket=bucket_name,
            WebsiteConfiguration={
                "ErrorDocument": {"Key": error},
                "IndexDocument": {"Suffix": index},
            },
        )

    @staticmethod
    def s3_get_bucket_website(manager, bucket_name):
        return manager.s3_client.get_bucket_website(Bucket=bucket_name)

    @staticmethod
    def s3_delete_bucket_website(manager, bucket_name):
        return manager.s3_client.delete_bucket_website(Bucket=bucket_name)