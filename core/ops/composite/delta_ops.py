import os
import struct
import math
from core.paths import Paths
from core.report import Reporting

HASH_ENTRY_SIZE = 32


class DeltaOps:
    @staticmethod
    def get_registry_info(source_object):
        registry_id = Paths.get_registry_identifier(source_object)
        registry_filename = f"{registry_id}.fhr"

        physical_path = Paths.resource_path(f"_sys/registry/{registry_filename}")
        return registry_id, physical_path

    @staticmethod
    def load_hashes(registry_path, expected_chunk_size_mb, expected_path_hash, expected_file_size=None):
        if not os.path.exists(registry_path):
            return []

        stored_hashes = []
        try:
            with open(registry_path, "rb") as file_stream:
                header_data = file_stream.read(64)

                if len(header_data) < 64:
                    return []

                if header_data[0:3] != b"FHR":
                    return []

                stored_chunk_size_mb = struct.unpack(">H", header_data[3:5])[0]
                if stored_chunk_size_mb != expected_chunk_size_mb:
                    return []

                stored_file_size = struct.unpack(">Q", header_data[5:17][-8:])[0]

                stored_path_hash = header_data[17:49].rstrip(b"\x00").decode("ascii", errors="ignore")
                if stored_path_hash != expected_path_hash:
                    return []

                while True:
                    binary_hash = file_stream.read(HASH_ENTRY_SIZE)
                    if not binary_hash:
                        break
                    if len(binary_hash) != HASH_ENTRY_SIZE:
                        Reporting.save_error_log(
                            f"Truncated hash entry in registry '{registry_path}'.",
                            "DELTA_REGISTRY_TRUNCATED"
                        )
                        return []
                    stored_hashes.append(binary_hash)

                reference_size = expected_file_size if expected_file_size is not None else stored_file_size
                chunk_size_bytes = stored_chunk_size_mb * 1024 * 1024
                expected_part_count = max(1, math.ceil(reference_size / chunk_size_bytes)) if reference_size else 0

                if expected_part_count and len(stored_hashes) != expected_part_count:
                    Reporting.save_error_log(
                        f"Registry '{registry_path}' has {len(stored_hashes)} parts, expected {expected_part_count}.",
                        "DELTA_REGISTRY_PART_COUNT_MISMATCH"
                    )
                    return []

        except Exception as exc:
            Reporting.save_error_log(str(exc), "DELTA_HASH_LOAD_FAILURE")
            return []

        return stored_hashes

    @staticmethod
    def save_registry(registry_path, registry_id, file_size, chunk_size_mb, hash_list):
        os.makedirs(os.path.dirname(registry_path), exist_ok=True)

        try:
            with open(registry_path, "wb") as file_stream:
                magic_bytes = b"FHR"
                packed_chunk_size = struct.pack(">H", chunk_size_mb)
                packed_size = struct.pack(">Q", file_size).rjust(12, b"\x00")
                packed_path_id = registry_id.encode('ascii')[:32].ljust(32, b'\x00')
                reserved_padding = b"\x00" * 15

                header_block = (
                    magic_bytes + packed_chunk_size +
                    packed_size + packed_path_id + reserved_padding
                )

                file_stream.write(header_block)

                for file_hash in hash_list:
                    file_stream.write(file_hash)

        except Exception as exc:
            Reporting.save_error_log(str(exc), "DELTA_REGISTRY_SAVE_FAILURE")
