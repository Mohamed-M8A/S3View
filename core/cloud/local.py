from core import config


class LocalManager:
    def __init__(self):
        self.http_logs = []

        full_data = config.get_credentials()

        try:
            self.workers = int(full_data.get("LOCAL_WORKERS", 4))
        except (ValueError, TypeError):
            self.workers = 4

        if self.workers < 1:
            self.workers = 1

        self.task_timeout = full_data.get("TASK_TIMEOUT_SECONDS", 300)
        self.http_log_max_entries = full_data.get("HTTP_LOG_MAX_ENTRIES", 1000)
