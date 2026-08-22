import os
import tempfile
import uuid

from ..ops.storage_ops import (
    LocalOps,
    S3IoOps, 
    S3BucketOps, 
    S3ObjectOps, 
    S3AnalyticsOps
)
from ..ops.composite_ops.archive_ops import ArchiveOps
from ..ops.composite_ops.delta_ops import DeltaOps
from ..ops.composite_ops.macro_ops import MacroOps
from ..ops.composite_ops.media_ops import MediaOps
from ..ops.composite_ops.sync_ops import SyncOps


class _ProviderDelegationMeta(type):
    def __getattr__(cls, name):
        for provider_class in cls._PROVIDER_CLASSES:
            if hasattr(provider_class, name):
                return getattr(provider_class, name)
        raise AttributeError(f"'{cls.__name__}' has no provider method '{name}'")


class BasicOps(
    ArchiveOps,
    DeltaOps,
    MacroOps,
    MediaOps,
    SyncOps,
    metaclass=_ProviderDelegationMeta
):
    _PROVIDER_CLASSES = (
        LocalOps,
        S3IoOps, 
        S3BucketOps, 
        S3ObjectOps, 
        S3AnalyticsOps
    )

    TRANSFER_MATRIX = {
        ("LOCAL", "LOCAL"): "_route_l2l",
        ("S3", "S3"): "_route_s2s",
        ("S3", "LOCAL"): "_route_s2l",
        ("LOCAL", "S3"): "_route_l2s",
    }

    SUPPORTED_PROTOCOLS = {"LOCAL", "S3"}

    @classmethod
    def resolve_provider_method(cls, name):
        for provider_class in cls._PROVIDER_CLASSES:
            if hasattr(provider_class, name):
                return getattr(provider_class, name)
        return None

    @classmethod
    def transfer(cls, manager, src_protocol, dst_protocol, source_ref, destination_ref, extra_args=None, move_mode=False):
        if src_protocol not in cls.SUPPORTED_PROTOCOLS or dst_protocol not in cls.SUPPORTED_PROTOCOLS:
            raise Exception(f"CV_ROUTER_ERROR: Unsupported transfer protocols: {src_protocol} -> {dst_protocol}")

        handler_name = cls.TRANSFER_MATRIX.get((src_protocol, dst_protocol))

        if handler_name:
            handler = getattr(cls, handler_name)
            result = handler(manager, source_ref, destination_ref, extra_args, move_mode)
        else:
            result = cls._route_relay(manager, src_protocol, dst_protocol, source_ref, destination_ref, extra_args)

        if move_mode and result and result.status == "success":
            cls.remove(src_protocol, manager, source_ref)

        return result

    @classmethod
    def _route_l2l(cls, manager, source_ref, destination_ref, extra_args, move_mode):
        return cls.l2l(source_ref, destination_ref, move_mode=move_mode)

    @classmethod
    def _route_s2s(cls, manager, source_ref, destination_ref, extra_args, move_mode):
        return cls.s2s(
            manager, 
            source_ref["bucket"], 
            source_ref["key"], 
            destination_ref["bucket"], 
            destination_ref["key"], 
            extra_args
        )

    @classmethod
    def _route_s2l(cls, manager, source_ref, destination_ref, extra_args, move_mode):
        return cls.s2l(manager, source_ref["bucket"], source_ref["key"], destination_ref)

    @classmethod
    def _route_l2s(cls, manager, source_ref, destination_ref, extra_args, move_mode):
        return cls.l2s(manager, source_ref, destination_ref["bucket"], destination_ref["key"], extra_args)

    @classmethod
    def _route_relay(cls, manager, src_protocol, dst_protocol, source_ref, destination_ref, extra_args):
        temp_directory = tempfile.gettempdir()
        relay_path = os.path.join(temp_directory, f"s3v_relay_{uuid.uuid4().hex}")
        try:
            cls.transfer(manager, src_protocol, "LOCAL", source_ref, relay_path, extra_args, False)
            return cls.transfer(manager, "LOCAL", dst_protocol, relay_path, destination_ref, extra_args, False)
        finally:
            if os.path.exists(relay_path):
                cls.loc_del(relay_path)

    @classmethod
    def remove(cls, protocol, manager, resource_ref):
        if protocol == "LOCAL":
            return cls.loc_del(resource_ref)
        if protocol == "S3":
            return cls.s3_del(manager, resource_ref["bucket"], resource_ref["key"])
        raise Exception(f"CV_ROUTER_ERROR: Protocol '{protocol}' not supported for deletion.")

    @classmethod
    def remove_batch(cls, protocol, manager, resource_refs):
        if protocol == "S3":
            return cls.s3_del_batch(manager, resource_refs["bucket"], resource_refs["keys"])
        raise Exception(f"CV_ROUTER_ERROR: Protocol '{protocol}' not supported for batch deletion.")