import threading
import math
import boto3
from datetime import datetime
from urllib.parse import urlparse
from boto3.s3.transfer import TransferConfig
from botocore.config import Config as BotoConfig
from core import config

class S3Manager:
    def __init__(self):
        self.http_logs = []
        self._logs_lock = threading.Lock()

        full_data = config.get_credentials()
        
        self.task_timeout = full_data.get("TASK_TIMEOUT_SECONDS", 300)
        self.http_log_max_entries = full_data.get("HTTP_LOG_MAX_ENTRIES", 1000)

        chunk_size_mb = 5
        ram_limit = full_data.get("RAM_LIMIT_MB", 200)
        buffer_ram = full_data.get("BUFFER_RAM_MB", 40)
        max_workers_limit = full_data.get("MAX_WORKERS", 15)
        
        self.workers = self._calculate_workers(max_workers_limit, ram_limit, chunk_size_mb, buffer_ram)

        access_key = str(full_data.get("ACCESS_KEY", "")).strip()
        secret_key = str(full_data.get("SECRET_KEY", "")).strip()
        
        if not access_key or not secret_key:
            raise Exception("S3_AUTH_ERROR: Access Key or Secret Key is missing in credentials.json.")

        target_url = self._format_endpoint_url(
            full_data.get("S3_ENDPOINT", ""), 
            full_data.get("ACCOUNT_ID", "")
        )
        
        if not target_url:
            raise Exception("S3_AUTH_ERROR: S3_ENDPOINT or ACCOUNT_ID must be provided.")

        s3_config = BotoConfig(
            retries={'max_attempts': 10, 'mode': 'standard'},
            connect_timeout=15,
            read_timeout=15,
            signature_version='s3v4',
            s3={'addressing_style': 'path'}
        )

        self.s3_client = boto3.client(
            service_name="s3",
            endpoint_url=target_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="auto",
            config=s3_config
        )

        self.s3_client.meta.events.register('before-send.s3.*', self._intercept_request)

        chunk_bytes = chunk_size_mb * 1024 * 1024
        self.transfer_config = TransferConfig(
            multipart_threshold=chunk_bytes * 2,
            multipart_chunksize=chunk_bytes,
            max_concurrency=self.workers,
            use_threads=True
        )

    def _calculate_workers(self, max_limit, ram_mb, chunk_mb, buffer_mb):
        available_ram = max(10, ram_mb - buffer_mb)
        safe_concurrency = math.floor(available_ram / chunk_mb)
        return min(max_limit, max(2, safe_concurrency))

    def _format_endpoint_url(self, endpoint, account_id):
        if endpoint:
            return endpoint if endpoint.startswith(("http://", "https://")) else f"https://{endpoint}"
        if account_id:
            return f"https://{account_id}.r2.cloudflarestorage.com"
        return None

    def _intercept_request(self, request, **kwargs):
        try:
            headers = dict(request.headers.items())
            if "Authorization" in headers:
                headers["Authorization"] = "MASKED"
            
            parsed = urlparse(request.url)
            entry = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "method": request.method,
                "host": parsed.netloc,
                "path": parsed.path,
                "headers": headers,
            }
            
            with self._logs_lock:
                self.http_logs.append(entry)
                if len(self.http_logs) > self.http_log_max_entries:
                    self.http_logs.pop(0)
        except:
            pass