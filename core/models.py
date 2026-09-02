"""
core/models.py -- every structured (dataclass) representation used across
the pipeline: parsed command metadata, resolved paths, per-item scan
results, per-task execution outcomes, and per-batch execution outcomes.

BatchResult (added 2026-08-30 session): the result of running one plugin
action over a batch of items (a whole scan's worth of files, or a single
account-level operation). It replaces the ad-hoc dict
{"files": [], "errors": [], "total_size": 0, "count": 0} that used to be
hand-built independently in 13 different places across the codebase --
which is exactly how a real bug slipped in: one code path checked "error"
(singular) while every producer only ever set "errors" (plural), so
failures were silently reported as successes. A dataclass with named
fields makes that whole class of bug a hard AttributeError instead of a
silent typo.

BatchResult keeps dict-style .get()/[]/["x"]=/.update() access working on
purpose, so call sites did not all have to be rewritten in the same pass --
each of the 13 producers/consumers was migrated to it one file at a time
and tested after each step, rather than in one large, high-risk change.
`error` (singular) is set only for a whole-batch fatal failure, e.g. the
initial scan/listing itself raised before any item could be processed.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class MetadataPackage:
    exclusions: List[str] = field(default_factory=list)
    logic: Optional[str] = None
    logic_inversion: bool = False
    limit: Optional[int] = None
    depth: Optional[int] = None
    tier: Optional[str] = None
    expires: Optional[int] = None
    level: Optional[int] = None
    chunk_size: Optional[int] = None
    is_flat: bool = False
    workers: Optional[int] = None
    task_timeout: Optional[int] = None
    extra_metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PathModel:
    payload: str
    is_cloud: bool
    is_directory: bool = False
    bucket: Optional[str] = None
    prefix: Optional[str] = None
    protocol: str = "LOCAL"

    def __post_init__(self):
        if self.is_cloud and self.payload and not self.bucket:
            from core.paths import Paths
            if self.protocol == "S3":
                self.bucket, self.prefix = Paths.split_container_payload(self.payload)

    def get_full_identifier(self) -> str:
        if not self.is_cloud: 
            return self.payload

        prefix_clean = self.prefix.lstrip('/') if self.prefix else ""

        if self.protocol == "S3":
            return f"s3://{self.bucket}/{prefix_clean}"

        return self.payload

@dataclass
class CommandModel:
    action: str
    src: PathModel
    dst: Optional[PathModel] = None
    logic: Optional[str] = None
    logic_inversion: bool = False
    compiled_logic: Optional[Any] = None
    limit: Optional[int] = None
    depth: Optional[int] = None
    tier: Optional[str] = None
    expires: Optional[int] = None
    level: Optional[int] = None
    chunk_size: Optional[int] = None
    exclusions: List[str] = field(default_factory=list)
    is_mirror: bool = False
    is_flat: bool = False
    trigger_mode: str = ""
    extra_metadata: dict = field(default_factory=dict)
    workers: Optional[int] = None
    task_timeout: Optional[int] = None

    def is_valid(self) -> bool:
        if not self.src:
            return False
        return bool(self.src.payload) and bool(self.src.payload.strip())

@dataclass
class MetadataModel:
    key: str
    size: int
    last_mod: datetime
    tier: str = "STANDARD"
    content_type: str = "application/octet-stream"
    is_cloud: bool = False
    etag: Optional[str] = None

@dataclass
class TaskResponse:
    status: str
    src: str
    dst: str = "-"
    size: int = 0
    date: Any = "N/A"
    tier: str = "STANDARD"
    error: Optional[str] = "-"
    metadata: Optional[dict] = None

    @classmethod
    def success(cls, src: str, dst: str = "-", size: int = 0, tier: str = "STANDARD"):
        return cls(status="success", src=src, dst=dst, size=size, tier=tier)

    @classmethod
    def failure(cls, src: str, error_msg: str):
        return cls(status="error", src=src, error=error_msg)


@dataclass
class BatchResult:
    files: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    skipped: list = field(default_factory=list)
    total_size: int = 0
    count: int = 0
    error: Optional[str] = None

    def get(self, key, default=None):
        return getattr(self, key, default) if hasattr(self, key) else default

    def __getitem__(self, key):
        if not hasattr(self, key):
            raise KeyError(key)
        return getattr(self, key)

    def __contains__(self, key):
        if key == "error":
            return self.error is not None
        return hasattr(self, key)

    def __setitem__(self, key, value):
        if not hasattr(self, key):
            raise KeyError(key)
        setattr(self, key, value)

    def update(self, other):
        source = other.__dict__ if isinstance(other, BatchResult) else other
        for key, value in source.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def add_file(self, task_response):
        self.files.append(task_response)
        if isinstance(task_response.size, (int, float)):
            self.total_size += task_response.size
        self.count += 1

    def add_error(self, message):
        self.errors.append(message)

    def add_skipped(self, task_response):
        self.skipped.append(task_response)

    @classmethod
    def fatal(cls, error_message: str):
        return cls(error=error_message)