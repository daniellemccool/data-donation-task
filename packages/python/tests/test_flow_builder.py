"""Tests for FlowBuilder.start_flow() — all six flow paths."""
import json
import sys
from unittest.mock import MagicMock, patch

sys.modules["js"] = MagicMock()

import pytest
from port.helpers.flow_builder import FlowBuilder
from port.helpers.uploads import FileTooLargeError
from port.api.commands import CommandUIRender, CommandSystemDonate
import port.api.props as props
import port.api.d3i_props as d3i_props
from port.helpers.validate import ValidateInput


class StubFlow(FlowBuilder):
    """Concrete FlowBuilder for testing."""

    def __init__(self, session_id="test-session", validation_status=0, tables=None):
        super().__init__(session_id, "TestPlatform")
        self._validation_status = validation_status
        self._tables = tables if tables is not None else [
            d3i_props.PropsUIPromptConsentFormTableViz(
                id="test_table",
                data_frame=__import__("pandas").DataFrame({"col": [1, 2]}),
                title=props.Translatable({"en": "Test", "nl": "Test"}),
            )
        ]

    def validate_file(self, file):
        v = MagicMock(spec=ValidateInput)
        v.get_status_code_id.return_value = self._validation_status
        return v

    def extract_data(self, file, validation):
        return self._tables


def make_payload(type_name, **attrs):
    p = MagicMock()
    p.__type__ = type_name
    for k, v in attrs.items():
        setattr(p, k, v)
    return p


class TestHappyPath:
    """User uploads valid file → extraction has data → consents → donates."""

    @patch("port.helpers.flow_builder.uploads.check_file_safety")
    @patch("port.helpers.flow_builder.uploads.materialize_file", return_value="/tmp/test.zip")
    def test_happy_path_yields_donate(self, mock_mat, mock_safety):
        flow = StubFlow()
        gen = flow.start_flow()

        # Step 1: file prompt
        cmd = next(gen)
        assert isinstance(cmd, CommandUIRender)

        # Step 2: user uploads file (PayloadFile)
        file_payload = make_payload("PayloadFile", value=MagicMock())
        cmd = gen.send(file_payload)
        # Should be consent form
        assert isinstance(cmd, CommandUIRender)

        # Step 3: user consents (PayloadJSON)
        consent_payload = make_payload("PayloadJSON", value='{"data": "test"}')
        cmd = gen.send(consent_payload)
        # Should be donate command
        assert isinstance(cmd, CommandSystemDonate)
        assert cmd.key == "test-session-testplatform"

        # Generator should continue (waiting for donate result)
        # Send back PayloadVoid (fire-and-forget success)
        with pytest.raises(StopIteration):
            gen.send(make_payload("PayloadVoid"))


class TestRetryPath:
    """User uploads invalid file → retries → uploads valid file → succeeds."""

    @patch("port.helpers.flow_builder.uploads.check_file_safety")
    @patch("port.helpers.flow_builder.uploads.materialize_file", return_value="/tmp/test.zip")
    def test_retry_loops_back(self, mock_mat, mock_safety):
        call_count = [0]
        flow = StubFlow()

        def varying_validate(file):
            call_count[0] += 1
            v = MagicMock(spec=ValidateInput)
            v.get_status_code_id.return_value = 1 if call_count[0] == 1 else 0
            return v

        flow.validate_file = varying_validate

        gen = flow.start_flow()

        # File prompt
        cmd = next(gen)
        assert isinstance(cmd, CommandUIRender)

        # Upload invalid file
        cmd = gen.send(make_payload("PayloadString", value="/tmp/bad.zip"))
        # Should be retry prompt
        assert isinstance(cmd, CommandUIRender)

        # User clicks "Try again" (PayloadTrue)
        cmd = gen.send(make_payload("PayloadTrue"))
        # Should loop back to file prompt
        assert isinstance(cmd, CommandUIRender)

        # Upload valid file
        cmd = gen.send(make_payload("PayloadString", value="/tmp/good.zip"))
        # Should be consent form
        assert isinstance(cmd, CommandUIRender)


class TestSkipPath:
    """User skips file selection (not PayloadFile or PayloadString)."""

    def test_skip_returns_immediately(self):
        flow = StubFlow()
        gen = flow.start_flow()

        # File prompt
        cmd = next(gen)
        assert isinstance(cmd, CommandUIRender)

        # User skips (PayloadFalse or similar)
        with pytest.raises(StopIteration):
            gen.send(make_payload("PayloadFalse"))


class TestNoDataPath:
    """Valid file but extraction returns empty table list."""

    @patch("port.helpers.flow_builder.uploads.check_file_safety")
    @patch("port.helpers.flow_builder.uploads.materialize_file", return_value="/tmp/test.zip")
    def test_no_data_shows_page_then_returns(self, mock_mat, mock_safety):
        flow = StubFlow(tables=[])
        gen = flow.start_flow()

        # File prompt
        cmd = next(gen)
        assert isinstance(cmd, CommandUIRender)

        # Upload valid file
        cmd = gen.send(make_payload("PayloadString", value="/tmp/empty.zip"))
        # Should be no-data page
        assert isinstance(cmd, CommandUIRender)

        # User acknowledges no-data page
        with pytest.raises(StopIteration):
            gen.send(make_payload("PayloadTrue"))


class TestSafetyErrorPath:
    """File fails safety check."""

    @patch("port.helpers.flow_builder.uploads.check_file_safety", side_effect=FileTooLargeError("too big"))
    @patch("port.helpers.flow_builder.uploads.materialize_file", return_value="/tmp/test.zip")
    def test_safety_error_shows_page_then_returns(self, mock_mat, mock_safety):
        flow = StubFlow()
        gen = flow.start_flow()

        # File prompt
        cmd = next(gen)
        assert isinstance(cmd, CommandUIRender)

        # Upload file that fails safety
        cmd = gen.send(make_payload("PayloadFile", value=MagicMock()))
        # Should be safety error page
        assert isinstance(cmd, CommandUIRender)

        # User acknowledges
        with pytest.raises(StopIteration):
            gen.send(make_payload("PayloadTrue"))


class TestDonateFailurePath:
    """Donation fails after consent."""

    @patch("port.helpers.flow_builder.ph.handle_donate_result", return_value=False)
    @patch("port.helpers.flow_builder.uploads.check_file_safety")
    @patch("port.helpers.flow_builder.uploads.materialize_file", return_value="/tmp/test.zip")
    def test_donate_failure_shows_page_then_returns(self, mock_mat, mock_safety, mock_handle):
        flow = StubFlow()
        gen = flow.start_flow()

        # File prompt
        cmd = next(gen)

        # Upload valid file
        cmd = gen.send(make_payload("PayloadString", value="/tmp/test.zip"))
        # Consent form
        assert isinstance(cmd, CommandUIRender)

        # User consents
        cmd = gen.send(make_payload("PayloadJSON", value='{"data": "test"}'))
        # Donate command
        assert isinstance(cmd, CommandSystemDonate)

        # Donate result comes back — send it to gen
        cmd = gen.send(make_payload("PayloadResponse", success=False))
        # Should be donate failure page
        assert isinstance(cmd, CommandUIRender)

        # User acknowledges
        with pytest.raises(StopIteration):
            gen.send(make_payload("PayloadTrue"))


class TestSessionIdType:
    def test_session_id_accepts_string(self):
        """FlowBuilder.__init__ should accept str for session_id."""
        flow = StubFlow(session_id="abc-123")
        assert flow.session_id == "abc-123"


class TestDonateKeyFormat:
    @patch("port.helpers.flow_builder.uploads.check_file_safety")
    @patch("port.helpers.flow_builder.uploads.materialize_file", return_value="/tmp/test.zip")
    def test_donate_key_includes_platform(self, mock_mat, mock_safety):
        """Donate key should be '{session_id}-{platform_name.lower()}'."""
        flow = StubFlow(session_id="sess-42")
        gen = flow.start_flow()
        next(gen)  # file prompt
        gen.send(make_payload("PayloadString", value="/tmp/test.zip"))  # consent form
        cmd = gen.send(make_payload("PayloadJSON", value="{}"))  # donate
        assert cmd.key == "sess-42-testplatform"
