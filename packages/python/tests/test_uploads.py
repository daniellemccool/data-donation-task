"""Tests for file materialization and safety checks."""
import os
import sys
import pytest
from unittest.mock import MagicMock

# Mock js module before any port imports
sys.modules["js"] = MagicMock()

from port.helpers.uploads import (
    materialize_file,
    check_file_safety,
    FileTooLargeError,
    ChunkedExportError,
    MAX_FILE_SIZE_BYTES,
)


class TestMaterializeFile:
    def test_payload_string_returns_path(self):
        """PayloadString: value is returned as-is (it's already a path)."""
        payload = MagicMock()
        payload.__type__ = "PayloadString"
        payload.value = "/some/path/file.zip"
        assert materialize_file(payload) == "/some/path/file.zip"

    def test_payload_file_writes_to_tmp(self, tmp_path):
        """PayloadFile: contents are written to /tmp and path is returned."""
        content = b"fake zip content"
        adapter = MagicMock()
        adapter.name = "test.zip"
        adapter.read.return_value = content
        adapter.size = len(content)

        payload = MagicMock()
        payload.__type__ = "PayloadFile"
        payload.value = adapter

        result = materialize_file(payload)
        assert result == "/tmp/test.zip"
        assert os.path.exists(result)
        with open(result, "rb") as f:
            assert f.read() == content

        # Cleanup
        os.unlink(result)

    def test_unknown_type_raises_type_error(self):
        """Unknown payload type raises TypeError."""
        payload = MagicMock()
        payload.__type__ = "PayloadJSON"
        with pytest.raises(TypeError, match="Unsupported payload type"):
            materialize_file(payload)


class TestCheckFileSafety:
    def test_normal_file_passes(self, tmp_path):
        """Normal-sized file passes safety check."""
        f = tmp_path / "ok.zip"
        f.write_bytes(b"x" * 100)
        check_file_safety(str(f))  # Should not raise

    def test_too_large_raises(self, tmp_path):
        """File exceeding MAX_FILE_SIZE_BYTES raises FileTooLargeError."""
        f = tmp_path / "big.zip"
        f.write_bytes(b"")  # Create empty file

        # Mock os.path.getsize to avoid creating a 2GB file
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "os.path.getsize",
                lambda p: MAX_FILE_SIZE_BYTES + 1,
            )
            with pytest.raises(FileTooLargeError):
                check_file_safety(str(f))

    def test_exact_sentinel_raises_chunked_export(self, tmp_path):
        """File exactly at sentinel size raises ChunkedExportError."""
        f = tmp_path / "chunked.zip"
        f.write_bytes(b"")

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "os.path.getsize",
                lambda p: MAX_FILE_SIZE_BYTES,
            )
            with pytest.raises(ChunkedExportError):
                check_file_safety(str(f))
