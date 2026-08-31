from dataclasses import dataclass
from typing import Optional, Callable


@dataclass(frozen=True)
class ProviderSpec:
    id: str
    display_name: str
    default_region: str
    region_required: bool
    addressing_style: str
    signature_version: str
    supports_batch_delete: bool
    max_batch_delete_keys: int
    endpoint_builder: Optional[Callable[[str, str], Optional[str]]] = None

    def build_endpoint(self, explicit_endpoint, region, account_id):
        if explicit_endpoint:
            cleaned = explicit_endpoint.strip()
            if cleaned:
                return cleaned if cleaned.startswith(("http://", "https://")) else f"https://{cleaned}"
        if self.endpoint_builder:
            return self.endpoint_builder(region, account_id)
        return None


def _aws_endpoint(region, account_id):
    resolved_region = region or "us-east-1"
    if resolved_region == "us-east-1":
        return "https://s3.amazonaws.com"
    return f"https://s3.{resolved_region}.amazonaws.com"


def _r2_endpoint(region, account_id):
    if not account_id:
        return None
    return f"https://{account_id}.r2.cloudflarestorage.com"


def _b2_endpoint(region, account_id):
    if not region:
        return None
    return f"https://s3.{region}.backblazeb2.com"


def _wasabi_endpoint(region, account_id):
    resolved_region = region or "us-east-1"
    if resolved_region == "us-east-1":
        return "https://s3.wasabisys.com"
    return f"https://s3.{resolved_region}.wasabisys.com"


def _digitalocean_endpoint(region, account_id):
    if not region:
        return None
    return f"https://{region}.digitaloceanspaces.com"


def _gcp_endpoint(region, account_id):
    return "https://storage.googleapis.com"


def _linode_endpoint(region, account_id):
    if not region:
        return None
    return f"https://{region}.linodeobjects.com"


def _vultr_endpoint(region, account_id):
    if not region:
        return None
    return f"https://{region}.vultrobjects.com"


def _ibm_endpoint(region, account_id):
    if not region:
        return None
    return f"https://s3.{region}.cloud-object-storage.appdomain.cloud"


def _oci_endpoint(region, account_id):
    if not region or not account_id:
        return None
    return f"https://{account_id}.compat.objectstorage.{region}.oraclecloud.com"


def _alibaba_endpoint(region, account_id):
    if not region:
        return None
    return f"https://s3.oss-{region}.aliyuncs.com"


def _scaleway_endpoint(region, account_id):
    if not region:
        return None
    return f"https://s3.{region}.scw.cloud"


def _ovhcloud_endpoint(region, account_id):
    if not region:
        return None
    return f"https://s3.{region}.io.cloud.ovh.net"


def _hetzner_endpoint(region, account_id):
    if not region:
        return None
    return f"https://{region}.your-objectstorage.com"


AWS = ProviderSpec(
    id="AWS",
    display_name="Amazon Web Services S3",
    default_region="us-east-1",
    region_required=True,
    addressing_style="virtual",
    signature_version="s3v4",
    supports_batch_delete=True,
    max_batch_delete_keys=1000,
    endpoint_builder=_aws_endpoint
)

R2 = ProviderSpec(
    id="R2",
    display_name="Cloudflare R2",
    default_region="auto",
    region_required=False,
    addressing_style="path",
    signature_version="s3v4",
    supports_batch_delete=True,
    max_batch_delete_keys=1000,
    endpoint_builder=_r2_endpoint
)

B2 = ProviderSpec(
    id="B2",
    display_name="Backblaze B2",
    default_region="",
    region_required=True,
    addressing_style="path",
    signature_version="s3v4",
    supports_batch_delete=True,
    max_batch_delete_keys=1000,
    endpoint_builder=_b2_endpoint
)

WASABI = ProviderSpec(
    id="Wasabi",
    display_name="Wasabi Hot Cloud Storage",
    default_region="us-east-1",
    region_required=True,
    addressing_style="path",
    signature_version="s3v4",
    supports_batch_delete=True,
    max_batch_delete_keys=1000,
    endpoint_builder=_wasabi_endpoint
)

DIGITALOCEAN = ProviderSpec(
    id="DigitalOcean",
    display_name="DigitalOcean Spaces",
    default_region="",
    region_required=True,
    addressing_style="virtual",
    signature_version="s3v4",
    supports_batch_delete=True,
    max_batch_delete_keys=1000,
    endpoint_builder=_digitalocean_endpoint
)

MINIO = ProviderSpec(
    id="Minio",
    display_name="MinIO",
    default_region="us-east-1",
    region_required=False,
    addressing_style="path",
    signature_version="s3v4",
    supports_batch_delete=True,
    max_batch_delete_keys=1000,
    endpoint_builder=None
)

GCP = ProviderSpec(
    id="GCP",
    display_name="Google Cloud Storage",
    default_region="",
    region_required=False,
    addressing_style="path",
    signature_version="s3v4",
    supports_batch_delete=True,
    max_batch_delete_keys=1000,
    endpoint_builder=_gcp_endpoint
)

LINODE = ProviderSpec(
    id="Linode",
    display_name="Linode Object Storage",
    default_region="",
    region_required=True,
    addressing_style="virtual",
    signature_version="s3v4",
    supports_batch_delete=True,
    max_batch_delete_keys=1000,
    endpoint_builder=_linode_endpoint
)

VULTR = ProviderSpec(
    id="Vultr",
    display_name="Vultr Object Storage",
    default_region="",
    region_required=True,
    addressing_style="virtual",
    signature_version="s3v4",
    supports_batch_delete=True,
    max_batch_delete_keys=1000,
    endpoint_builder=_vultr_endpoint
)

IBM = ProviderSpec(
    id="IBM",
    display_name="IBM Cloud Object Storage",
    default_region="",
    region_required=True,
    addressing_style="path",
    signature_version="s3v4",
    supports_batch_delete=True,
    max_batch_delete_keys=1000,
    endpoint_builder=_ibm_endpoint
)

OCI = ProviderSpec(
    id="OCI",
    display_name="Oracle Cloud Infrastructure Object Storage",
    default_region="",
    region_required=True,
    addressing_style="path",
    signature_version="s3v4",
    supports_batch_delete=True,
    max_batch_delete_keys=1000,
    endpoint_builder=_oci_endpoint
)

ALIBABA = ProviderSpec(
    id="Alibaba",
    display_name="Alibaba Cloud OSS",
    default_region="",
    region_required=True,
    addressing_style="virtual",
    signature_version="s3v4",
    supports_batch_delete=True,
    max_batch_delete_keys=1000,
    endpoint_builder=_alibaba_endpoint
)

SCALEWAY = ProviderSpec(
    id="Scaleway",
    display_name="Scaleway Object Storage",
    default_region="",
    region_required=True,
    addressing_style="virtual",
    signature_version="s3v4",
    supports_batch_delete=True,
    max_batch_delete_keys=1000,
    endpoint_builder=_scaleway_endpoint
)

OVHCLOUD = ProviderSpec(
    id="OVHcloud",
    display_name="OVHcloud Object Storage",
    default_region="",
    region_required=True,
    addressing_style="virtual",
    signature_version="s3v4",
    supports_batch_delete=True,
    max_batch_delete_keys=1000,
    endpoint_builder=_ovhcloud_endpoint
)

HETZNER = ProviderSpec(
    id="Hetzner",
    display_name="Hetzner Object Storage",
    default_region="",
    region_required=True,
    addressing_style="virtual",
    signature_version="s3v4",
    supports_batch_delete=True,
    max_batch_delete_keys=1000,
    endpoint_builder=_hetzner_endpoint
)

OTHER = ProviderSpec(
    id="Other",
    display_name="Other S3 Compatible",
    default_region="us-east-1",
    region_required=False,
    addressing_style="path",
    signature_version="s3v4",
    supports_batch_delete=True,
    max_batch_delete_keys=1000,
    endpoint_builder=None
)

_REGISTRY = {
    AWS.id.upper(): AWS,
    R2.id.upper(): R2,
    B2.id.upper(): B2,
    WASABI.id.upper(): WASABI,
    DIGITALOCEAN.id.upper(): DIGITALOCEAN,
    MINIO.id.upper(): MINIO,
    GCP.id.upper(): GCP,
    LINODE.id.upper(): LINODE,
    VULTR.id.upper(): VULTR,
    IBM.id.upper(): IBM,
    OCI.id.upper(): OCI,
    ALIBABA.id.upper(): ALIBABA,
    SCALEWAY.id.upper(): SCALEWAY,
    OVHCLOUD.id.upper(): OVHCLOUD,
    HETZNER.id.upper(): HETZNER,
    OTHER.id.upper(): OTHER,
}

_ALIASES = {
    "R2": "R2",
    "CLOUDFLARE": "R2",
    "AWS": "AWS",
    "AMAZON": "AWS",
    "B2": "B2",
    "BACKBLAZE": "B2",
    "WASABI": "WASABI",
    "DO": "DIGITALOCEAN",
    "DIGITALOCEAN": "DIGITALOCEAN",
    "SPACES": "DIGITALOCEAN",
    "MINIO": "MINIO",
    "GCP": "GCP",
    "GOOGLE": "GCP",
    "GCS": "GCP",
    "LINODE": "LINODE",
    "VULTR": "VULTR",
    "IBM": "IBM",
    "IBMCOS": "IBM",
    "OCI": "OCI",
    "ORACLE": "OCI",
    "ALIBABA": "ALIBABA",
    "ALIYUN": "ALIBABA",
    "OSS": "ALIBABA",
    "SCALEWAY": "SCALEWAY",
    "OVHCLOUD": "OVHCLOUD",
    "OVH": "OVHCLOUD",
    "HETZNER": "HETZNER",
    "OTHER": "OTHER",
}

_DOMAIN_HINTS = (
    ("r2.cloudflarestorage.com", "R2"),
    ("backblazeb2.com", "B2"),
    ("wasabisys.com", "WASABI"),
    ("digitaloceanspaces.com", "DIGITALOCEAN"),
    ("storage.googleapis.com", "GCP"),
    ("linodeobjects.com", "LINODE"),
    ("vultrobjects.com", "VULTR"),
    ("cloud-object-storage.appdomain.cloud", "IBM"),
    ("compat.objectstorage", "OCI"),
    ("aliyuncs.com", "ALIBABA"),
    ("scw.cloud", "SCALEWAY"),
    ("cloud.ovh", "OVHCLOUD"),
    ("your-objectstorage.com", "HETZNER"),
    ("amazonaws.com", "AWS"),
)


def get_provider(provider_id):
    if not provider_id:
        return OTHER
    normalized = str(provider_id).strip().upper()
    resolved_key = _ALIASES.get(normalized, normalized)
    return _REGISTRY.get(resolved_key, OTHER)


def detect_provider_from_endpoint(endpoint):
    if not endpoint:
        return None
    normalized_endpoint = str(endpoint).strip().lower()
    for domain_hint, provider_key in _DOMAIN_HINTS:
        if domain_hint in normalized_endpoint:
            return _REGISTRY.get(provider_key)
    return None


def resolve_provider(provider_id, endpoint):
    explicit = str(provider_id).strip() if provider_id else ""
    if explicit:
        return get_provider(explicit)

    detected = detect_provider_from_endpoint(endpoint)
    if detected:
        return detected

    return OTHER


def list_providers():
    return list(_REGISTRY.values())
