import hashlib
import os

MAX_PARTS = 10000
MAX_SINGLE_UPLOAD_SIZE = 5 * 1024 * 1024 * 1024
MIN_UPLOAD_CHUNKSIZE = 5 * 1024 * 1024


class IntegrityError(Exception):
    pass


def predict_effective_chunksize(base_chunksize, file_size):
    chunksize = base_chunksize
    if file_size is not None:
        num_parts = int(-(-file_size // chunksize))
        while num_parts > MAX_PARTS:
            chunksize *= 2
            num_parts = int(-(-file_size // chunksize))

    if chunksize > MAX_SINGLE_UPLOAD_SIZE:
        return MAX_SINGLE_UPLOAD_SIZE
    if chunksize < MIN_UPLOAD_CHUNKSIZE:
        return MIN_UPLOAD_CHUNKSIZE
    return chunksize


def _md5_of_range(file_path, start, length):
    hasher = hashlib.md5()
    with open(file_path, "rb") as file_handle:
        file_handle.seek(start)
        remaining = length
        while remaining > 0:
            block = file_handle.read(min(1024 * 1024, remaining))
            if not block:
                break
            hasher.update(block)
            remaining -= len(block)
    return hasher.digest()


def compute_expected_etag(file_path, base_chunksize, multipart_threshold, file_size=None):
    size = file_size if file_size is not None else os.path.getsize(file_path)

    if size <= multipart_threshold:
        binary_digest = _md5_of_range(file_path, 0, size)
        return binary_digest.hex()

    effective_chunksize = predict_effective_chunksize(base_chunksize, size)

    part_digests = []
    offset = 0
    while offset < size:
        part_length = min(effective_chunksize, size - offset)
        part_digests.append(_md5_of_range(file_path, offset, part_length))
        offset += part_length

    combined_hex = hashlib.md5(b"".join(part_digests)).hexdigest()
    return f"{combined_hex}-{len(part_digests)}"


def is_multipart_etag(etag):
    if not etag:
        return False
    return "-" in str(etag).strip('"')


def is_encrypted(probe):
    if not probe:
        return False
    return bool(probe.get("ServerSideEncryption") or probe.get("SSECustomerAlgorithm"))


def normalize_etag(raw_etag):
    if raw_etag is None:
        return None
    return str(raw_etag).strip('"')


def verify_etag(expected_etag, actual_etag, context_label):
    normalized_actual = normalize_etag(actual_etag)
    if expected_etag == normalized_actual:
        return True

    if is_multipart_etag(normalized_actual) and is_multipart_etag(expected_etag):
        expected_parts = expected_etag.split("-")[1]
        actual_parts = normalized_actual.split("-")[1]
        
        if expected_parts != actual_parts:
            return True

    raise IntegrityError(
        f"INTEGRITY_MISMATCH: '{context_label}' expected ETag '{expected_etag}' but got '{normalized_actual}'."
    )


def verify_size(expected_size, actual_size, context_label):
    if expected_size != actual_size:
        raise IntegrityError(
            f"INTEGRITY_SIZE_MISMATCH: '{context_label}' expected {expected_size} bytes but got {actual_size} bytes."
        )