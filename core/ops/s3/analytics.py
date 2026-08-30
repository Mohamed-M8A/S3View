class AnalyticsOps:

    @staticmethod
    def s3_set_inventory_configuration(manager, bucket_name, inventory_id, destination_bucket_arn, frequency="Daily"):
        return manager.s3_client.put_bucket_inventory_configuration(
            Bucket=bucket_name,
            Id=inventory_id,
            InventoryConfiguration={
                "Destination": {
                    "S3BucketDestination": {
                        "Bucket": destination_bucket_arn,
                        "Format": "CSV",
                    }
                },
                "IsEnabled": True,
                "Id": inventory_id,
                "IncludedObjectVersions": "Current",
                "Schedule": {"Frequency": frequency},
            },
        )

    @staticmethod
    def s3_get_inventory_configuration(manager, bucket_name, inventory_id):
        return manager.s3_client.get_bucket_inventory_configuration(
            Bucket=bucket_name, Id=inventory_id
        )

    @staticmethod
    def s3_delete_inventory_configuration(manager, bucket_name, inventory_id):
        return manager.s3_client.delete_bucket_inventory_configuration(
            Bucket=bucket_name, Id=inventory_id
        )

    @staticmethod
    def s3_set_analytics_configuration(manager, bucket_name, analytics_id, destination_bucket_arn, prefix=""):
        return manager.s3_client.put_bucket_analytics_configuration(
            Bucket=bucket_name,
            Id=analytics_id,
            AnalyticsConfiguration={
                "Id": analytics_id,
                "Filter": {"Prefix": prefix},
                "StorageClassAnalysis": {
                    "DataExport": {
                        "OutputSchemaVersion": "V_1",
                        "Destination": {
                            "S3BucketDestination": {
                                "Bucket": destination_bucket_arn,
                                "Format": "CSV",
                            }
                        },
                    }
                },
            },
        )

    @staticmethod
    def s3_get_analytics_configuration(manager, bucket_name, analytics_id):
        return manager.s3_client.get_bucket_analytics_configuration(
            Bucket=bucket_name, Id=analytics_id
        )

    @staticmethod
    def s3_delete_analytics_configuration(manager, bucket_name, analytics_id):
        return manager.s3_client.delete_bucket_analytics_configuration(
            Bucket=bucket_name, Id=analytics_id
        )

    @staticmethod
    def s3_set_metrics_configuration(manager, bucket_name, metrics_id, prefix=""):
        return manager.s3_client.put_bucket_metrics_configuration(
            Bucket=bucket_name,
            Id=metrics_id,
            MetricsConfiguration={"Id": metrics_id, "Filter": {"Prefix": prefix}},
        )

    @staticmethod
    def s3_get_metrics_configuration(manager, bucket_name, metrics_id):
        return manager.s3_client.get_bucket_metrics_configuration(
            Bucket=bucket_name, Id=metrics_id
        )

    @staticmethod
    def s3_delete_metrics_configuration(manager, bucket_name, metrics_id):
        return manager.s3_client.delete_bucket_metrics_configuration(
            Bucket=bucket_name, Id=metrics_id
        )

    @staticmethod
    def s3_set_intelligent_tiering_configuration(manager, bucket_name, config_id, prefix="", archive_days=90):
        return manager.s3_client.put_bucket_intelligent_tiering_configuration(
            Bucket=bucket_name,
            Id=config_id,
            IntelligentTieringConfiguration={
                "Id": config_id,
                "Filter": {"Prefix": prefix},
                "Status": "Enabled",
                "Tierings": [
                    {"Days": archive_days, "AccessTier": "ARCHIVE_ACCESS"}
                ],
            },
        )

    @staticmethod
    def s3_get_intelligent_tiering_configuration(manager, bucket_name, config_id):
        return manager.s3_client.get_bucket_intelligent_tiering_configuration(
            Bucket=bucket_name, Id=config_id
        )

    @staticmethod
    def s3_delete_intelligent_tiering_configuration(manager, bucket_name, config_id):
        return manager.s3_client.delete_bucket_intelligent_tiering_configuration(
            Bucket=bucket_name, Id=config_id
        )
