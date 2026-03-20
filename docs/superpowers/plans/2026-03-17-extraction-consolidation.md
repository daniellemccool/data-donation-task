# Extraction Consolidation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate donation_flows/ and platforms/ into a single FlowBuilder-based extraction architecture, moving FlowBuilder to helpers/, rewriting script.py as a study orchestrator, and adding file materialization support.

**Architecture:** FlowBuilder moves from platforms/ to helpers/ (shared infrastructure per AD0001). script.py becomes a thin orchestrator that delegates to FlowBuilder subclasses via `yield from`. New helpers/uploads.py handles PayloadFile materialization and safety checks. donation_flows/ and its dependencies are removed.

**Tech Stack:** Python 3.11+, pytest, pandas, Pyodide (browser runtime)

### Intentional behavior changes from current code

1. **Log donation removed:** Current script.py donates a `{session_id}-log` DataFrame at end of flow via a `DataFrameHandler`. This is dropped — the `LogForwardingHandler` in main.py replaces this with real-time log forwarding to the host via `CommandSystemLog`. The old approach was a legacy holdover from before log forwarding existed.

2. **Interactive platform selection removed:** Current script.py shows a radio button prompt if no `platform` parameter is set. The new script.py runs all platforms when no filter is set. Single-platform builds use `VITE_PLATFORM` env var to filter. This matches dd-vu-2026's proven pattern.

3. **Empty extraction skips consent:** Current FlowBuilder shows an empty consent form when extraction returns nothing. New behavior: shows a "no relevant data found" page and skips donation. This is better UX per the spec.

4. **Error pages use PropsUIPromptConfirm, not PropsUIPageError:** The spec mentions using `PropsUIPageError` through the factory pattern. In practice, `PropsUIPageError` only has a `message` string with no user-actionable button. The plan uses `PropsUIPromptConfirm` inside `PropsUIPageDataSubmission` to give participants a "Continue" button. This is a pragmatic deviation — the factory pattern can be adopted later when the error donation system is redesigned.

5. **`ph.exit()` no longer called by FlowBuilder:** Exit is handled by ScriptWrapper's StopIteration catch, not by yielding `CommandSystemExit`. Verified: `command_router.ts:29-31` does NOT resolve for CommandSystemExit — yielding it would hang the generator forever.

6. **Double-encoded decline JSON fixed:** Current code does `json.dumps('{"status": "data_submission declined"}')` (double-encoding). New code does `json.dumps({"status": "data_submission declined"})` (proper dict).

### Protocol notes (verified against feldspar source)

- **Donate returns PayloadResponse on eyra/develop (production).** As of Feb 2026, `command_router.ts` on eyra/feldspar `develop` awaits the bridge result for CommandSystemDonate and returns `PayloadResponse { value: { success, key, status, error? } }`. The LiveBridge tracks pending donations and resolves when mono sends DonateSuccess/DonateError. Non-donate system commands still get PayloadVoid. The FakeBridge (dev mode) returns void. Our local feldspar copy is on an older version (fire-and-forget), so handle_donate_result() must handle both: PayloadResponse (production, checked first) and PayloadVoid/None (dev mode, backward-compat).
- **PropsUIPromptConfirm is a registered feldspar factory** (`ConfirmFactory` in feldspar's prompt factory registry). PropsUIPageError renders but has no button. Using PropsUIPromptConfirm for error pages is correct.
- **PropsUIPromptRetry, PropsUIPromptConsentFormViz, PropsUIPromptFileInputMultiple** are d3i-specific custom types, not in upstream feldspar. They require custom factory registration in data-collector.
- **No TypeScript code references Python file paths.** py_worker.js loads `port-0.0.0-py3-none-any.whl` and calls `port.start()`. Deleting donation_flows/ and d3i_example_script.py is safe from the JS side.

---

## File Structure

### New files
| File | Responsibility |
|------|---------------|
| `packages/python/port/helpers/uploads.py` | File materialization (PayloadFile→path), safety checks |
| `packages/python/tests/test_uploads.py` | Tests for materialize_file and check_file_safety |
| `packages/python/tests/test_flow_builder.py` | Tests for start_flow paths (happy, retry, skip, no-data, safety, donate fail) |
| `packages/python/tests/test_port_helpers.py` | Tests for new port_helpers functions |

### Moved files
| From | To | Reason |
|------|-----|--------|
| `port/platforms/flow_builder.py` | `port/helpers/flow_builder.py` | AD0001: shared infrastructure lives in helpers/ |

### Modified files
| File | Changes |
|------|---------|
| `port/helpers/flow_builder.py` | Rewritten start_flow() (11 steps), session_id: int→str, donate key format, empty extraction handling |
| `port/helpers/port_helpers.py` | Add render_end_page(), render_no_data_page(), render_safety_error_page(), render_donate_failure_page(), handle_donate_result() |
| `port/script.py` | Complete rewrite as study orchestrator (~35 lines) |
| `port/main.py` | Logger scope "port.script"→"port", add formatter |
| `port/platforms/instagram.py` | Update import from `port.platforms.flow_builder` → `port.helpers.flow_builder` |
| `port/platforms/facebook.py` | Update import |
| `port/platforms/tiktok.py` | Update import |
| `port/platforms/youtube.py` | Update import |
| `port/platforms/linkedin.py` | Update import |
| `port/platforms/netflix.py` | Update import |
| `port/platforms/chatgpt.py` | Update import |
| `port/platforms/whatsapp.py` | Update import |
| `port/platforms/x.py` | Update import |
| `packages/python/tests/test_main_queue.py` | Update logger scope "port.script"→"port" |

### Deleted files
| File | Reason |
|------|--------|
| `port/platforms/flow_builder.py` | Moved to helpers/ |
| `port/d3i_example_script.py` | Replaced by new script.py |
| `port/donation_flows/` (entire dir) | Replaced by FlowBuilder + platforms/ |
| `port/helpers/parsers.py` | donation_flows dependency, orphaned |
| `port/helpers/entries_data.py` | donation_flows dependency, orphaned |
| `port/helpers/donation_flow.py` | donation_flows dependency, orphaned |
| `port/helpers/readers.py` | Only imported by parsers.py, orphaned |
| `port/helpers/Structure_extractor_libraries/` (entire dir) | Imports from parsers.py, orphaned |

---

## Task 1: Create helpers/uploads.py with tests (TDD)

**Files:**
- Create: `packages/python/port/helpers/uploads.py`
- Create: `packages/python/tests/test_uploads.py`

- [ ] **Step 1: Write failing tests for uploads module**

Create `packages/python/tests/test_uploads.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/python && poetry run pytest tests/test_uploads.py -v`
Expected: FAIL — `port.helpers.uploads` module does not exist

- [ ] **Step 3: Implement uploads.py**

Create `packages/python/port/helpers/uploads.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/python && poetry run pytest tests/test_uploads.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add packages/python/port/helpers/uploads.py packages/python/tests/test_uploads.py
git commit -m "feat: add helpers/uploads.py for file materialization and safety checks"
```

---

## Task 2: Add new port_helpers functions with tests (TDD)

**Files:**
- Modify: `packages/python/port/helpers/port_helpers.py`
- Create: `packages/python/tests/test_port_helpers.py`

- [ ] **Step 1: Write failing tests for new port_helpers functions**

Create `packages/python/tests/test_port_helpers.py`:

```python
"""Tests for new port_helpers functions."""
import sys
from unittest.mock import MagicMock

sys.modules["js"] = MagicMock()

import port.helpers.port_helpers as ph
from port.api.commands import CommandUIRender


class TestRenderEndPage:
    def test_returns_command_ui_render(self):
        result = ph.render_end_page()
        assert isinstance(result, CommandUIRender)

    def test_page_type_is_end(self):
        result = ph.render_end_page()
        d = result.toDict()
        assert d["page"]["__type__"] == "PropsUIPageEnd"


class TestRenderNoDataPage:
    def test_returns_command_ui_render(self):
        result = ph.render_no_data_page("Instagram")
        assert isinstance(result, CommandUIRender)

    def test_page_type_is_data_submission(self):
        result = ph.render_no_data_page("Instagram")
        d = result.toDict()
        assert d["page"]["__type__"] == "PropsUIPageDataSubmission"


class TestRenderSafetyErrorPage:
    def test_returns_command_ui_render(self):
        error = ValueError("test error")
        result = ph.render_safety_error_page("Facebook", error)
        assert isinstance(result, CommandUIRender)

    def test_page_type_is_data_submission(self):
        error = ValueError("test error")
        result = ph.render_safety_error_page("Facebook", error)
        d = result.toDict()
        assert d["page"]["__type__"] == "PropsUIPageDataSubmission"


class TestRenderDonateFailurePage:
    def test_returns_command_ui_render(self):
        result = ph.render_donate_failure_page("YouTube")
        assert isinstance(result, CommandUIRender)

    def test_page_type_is_data_submission(self):
        result = ph.render_donate_failure_page("YouTube")
        d = result.toDict()
        assert d["page"]["__type__"] == "PropsUIPageDataSubmission"


class TestHandleDonateResult:
    def test_success_response(self):
        """PayloadResponse with value.success=True → True."""
        result = MagicMock()
        result.__type__ = "PayloadResponse"
        result.value = MagicMock(success=True, key="k", status=200)
        assert ph.handle_donate_result(result) is True

    def test_failure_response(self):
        """PayloadResponse with value.success=False → False."""
        result = MagicMock()
        result.__type__ = "PayloadResponse"
        result.value = MagicMock(success=False, key="k", status=500, error="server error")
        assert ph.handle_donate_result(result) is False

    def test_payload_void_is_success(self):
        """PayloadVoid (dev mode / backward-compat) → True."""
        result = MagicMock()
        result.__type__ = "PayloadVoid"
        assert ph.handle_donate_result(result) is True

    def test_none_is_success(self):
        """None (legacy fire-and-forget) → True."""
        assert ph.handle_donate_result(None) is True

    def test_unknown_type_is_failure(self):
        result = MagicMock()
        result.__type__ = "PayloadWeird"
        assert ph.handle_donate_result(result) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/python && poetry run pytest tests/test_port_helpers.py -v`
Expected: FAIL — functions do not exist yet

- [ ] **Step 3: Add new functions to port_helpers.py**

Append to `packages/python/port/helpers/port_helpers.py` (after the existing `generate_questionnaire()` function):

```python
import logging

_logger = logging.getLogger(__name__)


def render_end_page() -> CommandUIRender:
    """Render study completion page."""
    return CommandUIRender(props.PropsUIPageEnd())


def render_no_data_page(platform_name: str) -> CommandUIRender:
    """Render 'no relevant data found' with acknowledge button.

    Caller should yield and await response before returning.
    """
    header = props.PropsUIHeader(
        props.Translatable({
            "en": f"No data found",
            "nl": f"Geen gegevens gevonden",
        })
    )
    body = props.PropsUIPromptConfirm(
        text=props.Translatable({
            "en": f"Unfortunately, no relevant data was found in your {platform_name} file.",
            "nl": f"Helaas zijn er geen relevante gegevens gevonden in uw {platform_name} bestand.",
        }),
        ok=props.Translatable({"en": "Continue", "nl": "Doorgaan"}),
        cancel=props.Translatable({"en": "Continue", "nl": "Doorgaan"}),
    )
    page = props.PropsUIPageDataSubmission(platform_name, header, body)
    return CommandUIRender(page)


def render_safety_error_page(platform_name: str, error: Exception) -> CommandUIRender:
    """Render file safety error page.

    Caller should yield and await response before returning.
    """
    header = props.PropsUIHeader(
        props.Translatable({
            "en": "File cannot be processed",
            "nl": "Bestand kan niet worden verwerkt",
        })
    )
    body = props.PropsUIPromptConfirm(
        text=props.Translatable({
            "en": f"Your {platform_name} file could not be processed: {error}",
            "nl": f"Uw {platform_name} bestand kon niet worden verwerkt: {error}",
        }),
        ok=props.Translatable({"en": "Continue", "nl": "Doorgaan"}),
        cancel=props.Translatable({"en": "Continue", "nl": "Doorgaan"}),
    )
    page = props.PropsUIPageDataSubmission(platform_name, header, body)
    return CommandUIRender(page)


def render_donate_failure_page(platform_name: str) -> CommandUIRender:
    """Render donation failure page.

    Caller should yield and await response before returning.
    """
    header = props.PropsUIHeader(
        props.Translatable({
            "en": "Data submission failed",
            "nl": "Gegevensinzending mislukt",
        })
    )
    body = props.PropsUIPromptConfirm(
        text=props.Translatable({
            "en": f"Unfortunately, your {platform_name} data could not be submitted. Please try again later.",
            "nl": f"Helaas konden uw {platform_name} gegevens niet worden ingediend. Probeer het later opnieuw.",
        }),
        ok=props.Translatable({"en": "Continue", "nl": "Doorgaan"}),
        cancel=props.Translatable({"en": "Continue", "nl": "Doorgaan"}),
    )
    page = props.PropsUIPageDataSubmission(platform_name, header, body)
    return CommandUIRender(page)


def handle_donate_result(result) -> bool:
    """Inspect donate result. Returns True on success, False on failure.

    eyra/feldspar develop (Feb 2026+) returns PayloadResponse for
    CommandSystemDonate with value.success indicating outcome. Older
    feldspar and FakeBridge (dev mode) return PayloadVoid (fire-and-forget).

    PayloadResponse → check value.success (production path, checked first)
    PayloadVoid / None → True (dev mode / backward-compat)
    Anything else → log warning, return False
    """
    if result is None:
        return True

    result_type = getattr(result, "__type__", None)

    if result_type == "PayloadResponse":
        # value is { success: bool, key: str, status: int, error?: str }
        return bool(result.value.success)

    if result_type == "PayloadVoid":
        return True

    _logger.warning("Unexpected donate result type: %s", result_type)
    return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/python && poetry run pytest tests/test_port_helpers.py -v`
Expected: All 11 tests PASS

- [ ] **Step 5: Commit**

```bash
git add packages/python/port/helpers/port_helpers.py packages/python/tests/test_port_helpers.py
git commit -m "feat: add render_end_page, render_no_data_page, safety/donate error pages, handle_donate_result to port_helpers"
```

---

## Task 3: Move FlowBuilder to helpers/ and update all platform imports

**Files:**
- Move: `packages/python/port/platforms/flow_builder.py` → `packages/python/port/helpers/flow_builder.py`
- Modify: `packages/python/port/platforms/instagram.py`
- Modify: `packages/python/port/platforms/facebook.py`
- Modify: `packages/python/port/platforms/tiktok.py`
- Modify: `packages/python/port/platforms/youtube.py`
- Modify: `packages/python/port/platforms/linkedin.py`
- Modify: `packages/python/port/platforms/netflix.py`
- Modify: `packages/python/port/platforms/chatgpt.py`
- Modify: `packages/python/port/platforms/whatsapp.py`
- Modify: `packages/python/port/platforms/x.py`

- [ ] **Step 1: Move flow_builder.py to helpers/ using git mv**

```bash
git mv packages/python/port/platforms/flow_builder.py packages/python/port/helpers/flow_builder.py
```

- [ ] **Step 2: Update import in every platform file**

In each of the 9 platform files, change:
```python
from port.platforms.flow_builder import FlowBuilder
```
to:
```python
from port.helpers.flow_builder import FlowBuilder
```

Files to update (all in `packages/python/port/platforms/`):
- `instagram.py`
- `facebook.py`
- `tiktok.py`
- `youtube.py`
- `linkedin.py`
- `netflix.py`
- `chatgpt.py`
- `whatsapp.py`
- `x.py`

- [ ] **Step 3: Run existing tests to verify nothing broke**

Run: `cd packages/python && poetry run pytest -v`
Expected: All existing tests PASS

- [ ] **Step 4: Commit**

```bash
git add packages/python/port/helpers/flow_builder.py packages/python/port/platforms/
git commit -m "refactor: move FlowBuilder from platforms/ to helpers/ (AD0001)"
```

---

## Task 4: Rewrite FlowBuilder.start_flow() with tests (TDD)

**Files:**
- Modify: `packages/python/port/helpers/flow_builder.py`
- Create: `packages/python/tests/test_flow_builder.py`

- [ ] **Step 1: Write failing tests for the new start_flow()**

Create `packages/python/tests/test_flow_builder.py`:

```python
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


def drive_generator(gen, responses):
    """Drive a generator with a sequence of responses, collecting yielded commands."""
    commands = []
    try:
        cmd = next(gen)
        commands.append(cmd)
        for resp in responses:
            cmd = gen.send(resp)
            commands.append(cmd)
    except StopIteration:
        pass
    return commands


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

        # Generator should be exhausted
        with pytest.raises(StopIteration):
            next(gen)


class TestRetryPath:
    """User uploads invalid file → retries → uploads valid file → succeeds."""

    @patch("port.helpers.flow_builder.uploads.check_file_safety")
    @patch("port.helpers.flow_builder.uploads.materialize_file", return_value="/tmp/test.zip")
    def test_retry_loops_back(self, mock_mat, mock_safety):
        # First call: invalid, second call: valid
        call_count = [0]
        original_validate = StubFlow.validate_file

        flow = StubFlow()

        def varying_validate(self_inner, file):
            call_count[0] += 1
            v = MagicMock(spec=ValidateInput)
            v.get_status_code_id.return_value = 1 if call_count[0] == 1 else 0
            return v

        flow.validate_file = lambda f: varying_validate(flow, f)

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/python && poetry run pytest tests/test_flow_builder.py -v`
Expected: FAIL — flow_builder doesn't import uploads, doesn't have new behavior

- [ ] **Step 3: Rewrite flow_builder.py**

Replace the contents of `packages/python/port/helpers/flow_builder.py`:

```python
"""FlowBuilder — shared per-platform donation flow orchestration.

Subclass this to implement a platform-specific donation flow.
Override validate_file() and extract_data(). Call start_flow()
as a generator from script.py via `yield from`.
"""
from abc import abstractmethod
import json
import logging

import port.api.props as props
import port.api.d3i_props as d3i_props
import port.helpers.port_helpers as ph
import port.helpers.validate as validate
import port.helpers.uploads as uploads

logger = logging.getLogger(__name__)


class FlowBuilder:
    def __init__(self, session_id: str, platform_name: str):
        self.session_id = session_id
        self.platform_name = platform_name
        self._initialize_ui_text()

    def _initialize_ui_text(self):
        """Initialize UI text based on platform name."""
        self.UI_TEXT = {
            "submit_file_header": props.Translatable({
                "en": f"Select your {self.platform_name} file",
                "nl": f"Selecteer uw {self.platform_name} bestand",
            }),
            "review_data_header": props.Translatable({
                "en": f"Your {self.platform_name} data",
                "nl": f"Uw {self.platform_name} gegevens",
            }),
            "retry_header": props.Translatable({
                "en": "Try again",
                "nl": "Probeer opnieuw",
            }),
            "review_data_description": props.Translatable({
                "en": f"Below you will find a curated selection of {self.platform_name} data.",
                "nl": f"Hieronder vindt u een zorgvuldig samengestelde selectie van {self.platform_name} gegevens.",
            }),
        }

    def start_flow(self):
        """Main per-platform flow: file→materialize→safety→validate→retry→extract→consent→donate.

        This is a generator. script.py calls it via `yield from flow.start_flow()`.
        Control flow rules:
        - continue: retry upload only
        - break: successful extraction, proceed to consent
        - return: every terminal path
        """
        while True:
            # 1. Render file prompt → receive payload
            logger.info("Prompt for file for %s", self.platform_name)
            file_prompt = self.generate_file_prompt()
            file_result = yield ph.render_page(self.UI_TEXT["submit_file_header"], file_prompt)

            # Skip: user didn't select a file
            if file_result.__type__ not in ("PayloadFile", "PayloadString"):
                logger.info("Skipped at file selection for %s", self.platform_name)
                return

            # 2. Materialize upload to path
            path = uploads.materialize_file(file_result)

            # 3. Safety check
            try:
                uploads.check_file_safety(path)
            except (uploads.FileTooLargeError, uploads.ChunkedExportError) as e:
                logger.error("Safety check failed for %s: %s", self.platform_name, e)
                _ = yield ph.render_safety_error_page(self.platform_name, e)
                return

            # 4. Validate
            validation = self.validate_file(path)

            # 5. If invalid → retry prompt
            if validation.get_status_code_id() != 0:
                logger.info("Invalid %s file; prompting retry", self.platform_name)
                retry_prompt = self.generate_retry_prompt()
                retry_result = yield ph.render_page(self.UI_TEXT["retry_header"], retry_prompt)
                if retry_result.__type__ == "PayloadTrue":
                    continue  # loop back to step 1
                return  # user declined retry

            # 6. Extract
            logger.info("Extracting data for %s", self.platform_name)
            table_list = self.extract_data(path, validation)

            # 7. If no tables → no-data page
            if not table_list:
                logger.info("No data extracted for %s", self.platform_name)
                _ = yield ph.render_no_data_page(self.platform_name)
                return

            break  # proceed to consent

        # 8. Render consent form
        logger.info("Prompting consent for %s", self.platform_name)
        review_data_prompt = self.generate_review_data_prompt(table_list)
        consent_result = yield ph.render_page(self.UI_TEXT["review_data_header"], review_data_prompt)

        # 9. Donate with per-platform key
        if consent_result.__type__ == "PayloadJSON":
            reviewed_data = consent_result.value
        elif consent_result.__type__ == "PayloadFalse":
            reviewed_data = json.dumps({"status": "data_submission declined"})
        else:
            return

        donate_key = f"{self.session_id}-{self.platform_name.lower()}"
        donate_result = yield ph.donate(donate_key, reviewed_data)

        # 10. Inspect donate result
        if not ph.handle_donate_result(donate_result):
            logger.error("Donation failed for %s", self.platform_name)
            _ = yield ph.render_donate_failure_page(self.platform_name)
            return

        # 11. Return (script.py handles next platform or end page)

    # Methods to be overridden by platform-specific implementations
    def generate_file_prompt(self):
        """Generate platform-specific file prompt."""
        return ph.generate_file_prompt("application/zip")

    @abstractmethod
    def validate_file(self, file: str) -> validate.ValidateInput:
        """Validate the file according to platform-specific rules."""
        raise NotImplementedError("Must be implemented by subclass")

    @abstractmethod
    def extract_data(self, file: str, validation: validate.ValidateInput) -> list[d3i_props.PropsUIPromptConsentFormTableViz]:
        """Extract data from file using platform-specific logic."""
        raise NotImplementedError("Must be implemented by subclass")

    def generate_retry_prompt(self):
        """Generate platform-specific retry prompt."""
        return ph.generate_retry_prompt(self.platform_name)

    def generate_review_data_prompt(self, table_list):
        """Generate platform-specific review data prompt."""
        return ph.generate_review_data_prompt(
            description=self.UI_TEXT["review_data_description"],
            table_list=table_list,
        )
```

- [ ] **Step 4: Run all tests**

Run: `cd packages/python && poetry run pytest -v`
Expected: All tests PASS (test_flow_builder.py + existing tests)

- [ ] **Step 5: Commit**

```bash
git add packages/python/port/helpers/flow_builder.py packages/python/tests/test_flow_builder.py
git commit -m "feat: rewrite FlowBuilder.start_flow() with 11-step flow, safety checks, donate key format"
```

---

## Task 5: Update platform Flow classes for new FlowBuilder interface

**Files:**
- Modify: `packages/python/port/platforms/instagram.py`
- Modify: `packages/python/port/platforms/facebook.py`
- Modify: all other 7 platform files

The new FlowBuilder changes:
1. `session_id: int` → `session_id: str` — platform `__init__` calls need updating
2. `table_list` is no longer stored as `self.table_list` — it's passed directly to `generate_review_data_prompt(table_list)`
3. `extract_data()` must NOT be a generator anymore (the `isinstance(self.table_list, Generator)` check is removed)

- [ ] **Step 1: Update InstagramFlow and FacebookFlow type annotations**

In `packages/python/port/platforms/instagram.py`, change:
```python
class InstagramFlow(FlowBuilder):
    def __init__(self, session_id: int):
```
to:
```python
class InstagramFlow(FlowBuilder):
    def __init__(self, session_id: str):
```

Same change in `packages/python/port/platforms/facebook.py`.

Repeat for all 9 platform files. The `__init__` parameter type annotation for `session_id` changes from `int` to `str` in every platform Flow class.

- [ ] **Step 2: Run all tests**

Run: `cd packages/python && poetry run pytest -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add packages/python/port/platforms/
git commit -m "fix: update platform Flow classes for str session_id"
```

---

## Task 6: Rewrite script.py as study orchestrator

**Files:**
- Modify: `packages/python/port/script.py`

- [ ] **Step 1: Rewrite script.py**

Replace `packages/python/port/script.py` with:

```python
"""Study orchestration — platform list, filtering, sequencing.

This module defines which platforms are included in the study and
delegates per-platform flows to FlowBuilder subclasses via `yield from`.
"""
import logging

import port.helpers.port_helpers as ph
import port.platforms.linkedin as linkedin
import port.platforms.instagram as instagram
import port.platforms.facebook as facebook
import port.platforms.youtube as youtube
import port.platforms.tiktok as tiktok
import port.platforms.netflix as netflix
import port.platforms.chatgpt as chatgpt
import port.platforms.whatsapp as whatsapp
import port.platforms.x as x

logger = logging.getLogger(__name__)


def process(session_id: str, platform: str | None = None):
    """Run the data donation study.

    Args:
        session_id: Unique session identifier (from host).
        platform: If set (via VITE_PLATFORM), run only this platform.
    """
    all_platforms = [
        ("LinkedIn", linkedin.LinkedInFlow(session_id)),
        ("Instagram", instagram.InstagramFlow(session_id)),
        ("Facebook", facebook.FacebookFlow(session_id)),
        ("YouTube", youtube.YouTubeFlow(session_id)),
        ("TikTok", tiktok.TikTokFlow(session_id)),
        ("Netflix", netflix.NetflixFlow(session_id)),
        ("ChatGPT", chatgpt.ChatGPTFlow(session_id)),
        ("WhatsApp", whatsapp.WhatsAppFlow(session_id)),
        ("X", x.XFlow(session_id)),
    ]

    platforms = filter_platforms(all_platforms, platform)

    for platform_name, flow in platforms:
        logger.info("Starting platform: %s", platform_name)
        yield from flow.start_flow()

    yield ph.render_end_page()


def filter_platforms(all_platforms, platform_filter):
    """Filter platform list by VITE_PLATFORM value.

    If platform_filter is None or empty, return all platforms.
    Otherwise return only the matching platform (case-insensitive).
    """
    if not platform_filter:
        return all_platforms
    return [
        (name, flow) for name, flow in all_platforms
        if name.lower() == platform_filter.lower()
    ]
```

- [ ] **Step 2: Run all tests**

Run: `cd packages/python && poetry run pytest -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add packages/python/port/script.py
git commit -m "feat: rewrite script.py as study orchestrator with yield-from delegation"
```

---

## Task 7: Update main.py logger scope and formatter

**Files:**
- Modify: `packages/python/port/main.py`
- Modify: `packages/python/tests/test_main_queue.py`

- [ ] **Step 1: Update main.py logger scope**

In `packages/python/port/main.py`, change `add_log_handler`:

```python
def add_log_handler(self, logger_name: str = "port") -> None:
    """Attach a handler to the named logger that forwards log records as CommandSystemLog commands."""
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    handler = LogForwardingHandler(self.queue)
    handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
    logger.addHandler(handler)
```

- [ ] **Step 2: Update test_main_queue.py logger scope**

In `packages/python/tests/test_main_queue.py`, replace all occurrences of `"port.script"` with `"port"`:

1. In `clean_port_script_logger` fixture:
   ```python
   logger = logging.getLogger("port")
   ```

2. In `test_log_commands_returned_before_script_command`:
   ```python
   logger = logging.getLogger("port")
   ```

3. In `test_add_log_handler_wires_logger`:
   ```python
   logger = logging.getLogger("port")
   ```

4. In `test_log_command_flow_integration`:
   ```python
   logger = logging.getLogger("port")
   ```

5. In `test_start_function_creates_wrapper_with_log_handler`:
   ```python
   logger = logging.getLogger("port")
   ```

- [ ] **Step 3: Run all tests**

Run: `cd packages/python && poetry run pytest -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add packages/python/port/main.py packages/python/tests/test_main_queue.py
git commit -m "feat: widen logger scope from port.script to port, add formatter"
```

---

## Task 8: Delete donation_flows/ and orphaned helpers

**Files:**
- Delete: `packages/python/port/donation_flows/` (entire directory)
- Delete: `packages/python/port/d3i_example_script.py`
- Delete: `packages/python/port/helpers/parsers.py`
- Delete: `packages/python/port/helpers/entries_data.py`
- Delete: `packages/python/port/helpers/donation_flow.py`
- Delete: `packages/python/port/helpers/readers.py`
- Delete: `packages/python/port/helpers/Structure_extractor_libraries/` (entire directory)

- [ ] **Step 1: Delete donation_flows/ directory**

```bash
rm -r packages/python/port/donation_flows/
```

- [ ] **Step 2: Delete d3i_example_script.py**

```bash
rm packages/python/port/d3i_example_script.py
```

- [ ] **Step 3: Delete orphaned helpers**

```bash
rm packages/python/port/helpers/parsers.py
rm packages/python/port/helpers/entries_data.py
rm packages/python/port/helpers/donation_flow.py
rm packages/python/port/helpers/readers.py
rm -r packages/python/port/helpers/Structure_extractor_libraries/
```

- [ ] **Step 4: Run all tests**

Run: `cd packages/python && poetry run pytest -v`
Expected: All tests PASS (nothing should depend on deleted files)

- [ ] **Step 5: Commit**

```bash
git add -A packages/python/port/donation_flows/ packages/python/port/d3i_example_script.py packages/python/port/helpers/parsers.py packages/python/port/helpers/entries_data.py packages/python/port/helpers/donation_flow.py packages/python/port/helpers/readers.py packages/python/port/helpers/Structure_extractor_libraries/
git commit -m "chore: remove donation_flows/ and orphaned helpers (parsers, entries_data, donation_flow, readers, Structure_extractor_libraries)"
```

---

## Task 9: Update ADR AD0006 status

**Files:**
- Modify: ADR file for python-architecture/AD0006

- [ ] **Step 1: Locate the ADR file**

```bash
find docs/decisions -name "*AD0006*" -o -name "*0006*" 2>/dev/null
```

Or check `docs/decisions/python-architecture/` for the AD0006 file.

- [ ] **Step 2: Update ADR status using adg**

Use `adg decide` to update the ADR status from `open` to `decided`, selecting Option 1 (FlowBuilder as standard).

```bash
adg decide docs/decisions/python-architecture/AD0006*.md --option 1
```

Note: All ADR content must flow through `adg` — never edit ADR files directly (per feedback_adr_adg_only.md).

- [ ] **Step 3: Commit**

```bash
git add docs/decisions/
git commit -m "docs: mark AD0006 as decided — FlowBuilder is the standard"
```

---

## Task 10: Final verification

- [ ] **Step 1: Run full test suite**

```bash
cd packages/python && poetry run pytest -v
```
Expected: All tests PASS

- [ ] **Step 2: Try a build**

```bash
pnpm run build
```
Expected: Build completes successfully

- [ ] **Step 3: Verify no stale imports**

```bash
cd packages/python && grep -r "donation_flows" port/ --include="*.py" || echo "No stale donation_flows imports"
grep -r "from port.platforms.flow_builder" port/ --include="*.py" || echo "No stale flow_builder imports"
grep -r "port.helpers.parsers\|port.helpers.readers\|port.helpers.entries_data\|port.helpers.donation_flow" port/ --include="*.py" || echo "No stale helper imports"
```
Expected: No matches (all old imports removed)
