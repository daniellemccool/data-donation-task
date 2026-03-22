"""File materialization and safety checks.

Converts browser file payloads to filesystem paths and validates
file sizes before extraction processing.
"""
import logging
import os

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024 * 1024  # 2 GiB
CHUNKED_EXPORT_SENTINEL_BYTES = MAX_FILE_SIZE_BYTES  # same value, distinct intent


class FileTooLargeError(Exception):
    """Raised when a file exceeds MAX_FILE_SIZE_BYTES."""


class ChunkedExportError(Exception):
    """Raised when a file is exactly CHUNKED_EXPORT_SENTINEL_BYTES (split export sentinel)."""


def materialize_file(file_result) -> str:
    """Convert PayloadFile or PayloadString to a file path.

    PayloadFile: write file_result.value (AsyncFileAdapter) contents to /tmp, return path.
    PayloadString: return file_result.value directly (already a WORKERFS path).
    Anything else: raise TypeError.

    Note: /tmp is emscripten in-memory FS — files persist for worker
    lifetime and are freed when the WebWorker terminates. No cleanup needed.
    """
    if file_result.__type__ == "PayloadString":
        return file_result.value

    if file_result.__type__ == "PayloadFile":
        adapter = file_result.value
        file_path = f"/tmp/{adapter.name}"
        with open(file_path, "wb") as f:
            f.write(adapter.read())
        logger.info("PayloadFile: wrote %d bytes to %s", adapter.size, file_path)
        return file_path

    raise TypeError(f"Unsupported payload type: {file_result.__type__}")


def check_file_safety(path: str) -> None:
    """Raise FileTooLargeError or ChunkedExportError if file is unsafe.

    Checks: >MAX_FILE_SIZE_BYTES (too large),
    exactly CHUNKED_EXPORT_SENTINEL_BYTES (split export sentinel).
    """
    size = os.path.getsize(path)
    if size == CHUNKED_EXPORT_SENTINEL_BYTES:
        raise ChunkedExportError(
            f"File is exactly {CHUNKED_EXPORT_SENTINEL_BYTES} bytes — likely a chunked export sentinel"
        )
    if size > MAX_FILE_SIZE_BYTES:
        raise FileTooLargeError(
            f"File is {size} bytes, exceeding limit of {MAX_FILE_SIZE_BYTES} bytes"
        )
