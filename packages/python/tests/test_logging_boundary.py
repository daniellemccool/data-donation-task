"""Tests for PII-safe logging boundary.

Verifies that only port.bridge logs are forwarded via LogForwardingHandler,
and that other port.* loggers stay local.
"""
import sys
import logging
from collections import Counter
from unittest.mock import MagicMock

sys.modules["js"] = MagicMock()

import pytest
from port.api.d3i_props import ExtractionResult, PropsUIPromptConsentFormTableViz
from port.api.logging import LogForwardingHandler
from port.api import props
import pandas as pd


class TestExtractionResult:
    def test_basic_construction(self):
        tables = [
            PropsUIPromptConsentFormTableViz(
                id="test",
                data_frame=pd.DataFrame({"a": [1]}),
                title=props.Translatable({"en": "T", "nl": "T"}),
            )
        ]
        errors = Counter({"FileNotFound": 3, "JSONDecodeError": 2})
        result = ExtractionResult(tables=tables, errors=errors)
        assert len(result.tables) == 1
        assert result.errors["FileNotFound"] == 3

    def test_empty_errors(self):
        result = ExtractionResult(tables=[], errors=Counter())
        assert not result.errors
        assert not result.tables

    def test_default_errors(self):
        """errors defaults to empty Counter if not provided."""
        result = ExtractionResult(tables=[])
        assert isinstance(result.errors, Counter)
        assert not result.errors


class TestLoggingBoundary:
    """Verify that LogForwardingHandler only captures port.bridge logs."""

    @pytest.fixture(autouse=True)
    def setup_bridge_logger(self):
        """Set up port.bridge logger with handler, clean up after."""
        self.queue = []
        self.bridge_logger = logging.getLogger("port.bridge")
        self.bridge_logger.propagate = False
        self.handler = LogForwardingHandler(self.queue)
        self.handler.setLevel(logging.INFO)
        self.bridge_logger.addHandler(self.handler)
        self.bridge_logger.setLevel(logging.DEBUG)
        yield
        self.bridge_logger.removeHandler(self.handler)
        self.bridge_logger.propagate = True

    def test_bridge_logger_forwards(self):
        """Messages to port.bridge are forwarded."""
        self.bridge_logger.info("test message")
        assert len(self.queue) == 1
        assert self.queue[0]["message"] == "test message"

    def test_platform_logger_not_forwarded(self):
        """Messages to port.platforms.facebook are NOT forwarded."""
        fb_logger = logging.getLogger("port.platforms.facebook")
        fb_logger.error("Exception caught: sensitive data")
        assert len(self.queue) == 0

    def test_helpers_logger_not_forwarded(self):
        """Messages to port.helpers.uploads are NOT forwarded."""
        uploads_logger = logging.getLogger("port.helpers.uploads")
        uploads_logger.info("PayloadFile: wrote 64MB to /tmp/sensitive-name.zip")
        assert len(self.queue) == 0

    def test_extraction_helpers_not_forwarded(self):
        """Messages to port.helpers.extraction_helpers are NOT forwarded."""
        eh_logger = logging.getLogger("port.helpers.extraction_helpers")
        eh_logger.error("File not found: contact_name.json")
        assert len(self.queue) == 0

    def test_bridge_propagate_false(self):
        """port.bridge has propagate=False so parent handlers can't duplicate."""
        assert self.bridge_logger.propagate is False

    def test_content_logger_not_forwarded_even_with_parent_handler(self):
        """Content logger stays silent even if a handler is on port."""
        port_logger = logging.getLogger("port")
        spy_queue = []
        spy_handler = LogForwardingHandler(spy_queue)
        port_logger.addHandler(spy_handler)

        content_logger = logging.getLogger("port.helpers.extraction_helpers.content")
        content_logger.propagate = False
        content_logger.addHandler(logging.NullHandler())
        content_logger.debug("Contained in zip: messages/inbox/mothersname_123/photo.jpg")

        assert len(spy_queue) == 0
        port_logger.removeHandler(spy_handler)


class TestHelperErrorCounting:
    """Verify helper functions increment the errors Counter when provided."""

    def test_extract_file_from_zip_counts_file_not_found(self, tmp_path):
        """extract_file_from_zip increments errors when file not in zip."""
        import zipfile
        from port.helpers.extraction_helpers import extract_file_from_zip

        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("existing.json", '{"key": "value"}')

        errors = Counter()
        extract_file_from_zip(str(zip_path), "nonexistent.json", errors=errors)
        assert errors["FileNotFoundInZipError"] == 1

    def test_errors_none_does_not_crash(self, tmp_path):
        """extract_file_from_zip works without errors parameter (backward compat)."""
        import zipfile
        from port.helpers.extraction_helpers import extract_file_from_zip

        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("existing.json", '{"key": "value"}')

        result = extract_file_from_zip(str(zip_path), "nonexistent.json")
        assert result.getvalue() == b""
