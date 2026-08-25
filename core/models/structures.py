from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict
from datetime import datetime

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
    bucket: Optional[str] = None
    prefix: Optional[str] = None
    protocol: str = "LOCAL"

    def __post_init__(self):
        if self.is_cloud and self.payload and not self.bucket:
            from core.paths import Paths
            if self.protocol == "S3":
                self.bucket, self.prefix = Paths.split_container_payload(self.payload)

    def get_full_identifier(self) -> str:
        if not self.is_cloud: return self.payload

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
        return bool(self.src)

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
    error: Optional[str] = None
    metadata: Optional[dict] = None

    @classmethod
    def success(cls, src: str, dst: str = "-", size: int = 0, tier: str = "STANDARD"):
        return cls(status="success", src=src, dst=dst, size=size, tier=tier)

    @classmethod
    def failure(cls, src: str, error_msg: str):
        return cls(status="error", src=src, error=error_msg)