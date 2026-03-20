# PII-Safe Logging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent PII leakage through the log forwarding bridge while maintaining flow observability via a dedicated `port.bridge` logger.

**Architecture:** LogForwardingHandler moves from `port` to `port.bridge` (leaf logger, propagate=False). Only FlowBuilder and script.py write PII-free milestones to bridge_logger. Extraction helpers get an `errors: Counter` parameter to bubble up error counts. ExtractionResult dataclass wraps tables + error counts. Content enumeration uses a non-propagating logger.

**Tech Stack:** Python 3.11+, pytest, collections.Counter, logging module

---

## File Structure

### New files
| File | Responsibility |
|------|---------------|
| `packages/python/tests/test_logging_boundary.py` | Tests that bridge logger forwards, other loggers don't |

### Modified files
| File | Changes |
|------|---------|
| `port/main.py` | Handler scope `port` → `port.bridge`, add `propagate = False` |
| `port/api/d3i_props.py` | Add `ExtractionResult` dataclass |
| `port/helpers/extraction_helpers.py` | Add `errors` param to `extract_file_from_zip`, `_read_json`, `read_json_from_bytes`, `epoch_to_iso`; non-propagating content logger |
| `port/helpers/flow_builder.py` | Add `bridge_logger`, flow milestones, handle `ExtractionResult`, Netflix generator support |
| `port/script.py` | Add `bridge_logger` for platform start and study complete |
| `port/platforms/instagram.py` | `extraction()` returns `ExtractionResult`, passes `errors` counter to helpers |
| `port/platforms/facebook.py` | Same |
| `port/platforms/tiktok.py` | Same |
| `port/platforms/youtube.py` | Same |
| `port/platforms/linkedin.py` | Same |
| `port/platforms/netflix.py` | Same (plus generator return) |
| `port/platforms/chatgpt.py` | Same |
| `port/platforms/whatsapp.py` | Same |
| `port/platforms/x.py` | Same |
| `tests/test_main_queue.py` | Logger scope `port` → `port.bridge` |
| `tests/test_flow_builder.py` | Update for `ExtractionResult` return type |

---

## Task 1: Add ExtractionResult dataclass and logging boundary tests (TDD)

**Files:**
- Modify: `packages/python/port/api/d3i_props.py`
- Create: `packages/python/tests/test_logging_boundary.py`

- [ ] **Step 1: Write failing test for ExtractionResult**

Append to an existing test file or create a new one. Since ExtractionResult is a simple dataclass, test it inline with the logging boundary tests.

Create `packages/python/tests/test_logging_boundary.py`:

```python
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
        # Attach a handler to port (simulating someone widening scope)
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
        from collections import Counter
        from port.helpers.extraction_helpers import extract_file_from_zip

        # Create a zip with one file
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

        # Should not raise — errors defaults to None
        result = extract_file_from_zip(str(zip_path), "nonexistent.json")
        assert result.getvalue() == b""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/python && poetry run pytest tests/test_logging_boundary.py -v`
Expected: FAIL — `ExtractionResult` does not exist yet

- [ ] **Step 3: Add ExtractionResult to d3i_props.py**

Add at the end of `packages/python/port/api/d3i_props.py`:

```python
from collections import Counter

@dataclass
class ExtractionResult:
    """Result of a platform extraction: tables for consent + aggregated error counts.

    The errors Counter contains type-name keys (e.g. "FileNotFoundInZipError": 3).
    These counts are safe to forward via the bridge logger. Raw exception messages
    are never included — they stay in local __name__ logger output only.
    """
    tables: list[PropsUIPromptConsentFormTableViz]
    errors: Counter[str]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/python && poetry run pytest tests/test_logging_boundary.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add port/api/d3i_props.py tests/test_logging_boundary.py
git commit -m "feat: add ExtractionResult dataclass and logging boundary tests"
```

---

## Task 2: Change handler scope to port.bridge in main.py

**Files:**
- Modify: `packages/python/port/main.py`
- Modify: `packages/python/tests/test_main_queue.py`

- [ ] **Step 1: Update main.py add_log_handler**

In `packages/python/port/main.py`, replace `add_log_handler`:

```python
def add_log_handler(self, logger_name: str = "port.bridge") -> None:
    """Attach a handler to the named logger that forwards log records as CommandSystemLog commands."""
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    handler = LogForwardingHandler(self.queue)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
    logger.addHandler(handler)
```

Changes from current:
- Default `"port"` → `"port.bridge"`
- Added `logger.propagate = False`
- Handler level stays `logging.INFO` (already set)

- [ ] **Step 2: Update test_main_queue.py logger scope**

In `packages/python/tests/test_main_queue.py`, replace all `"port"` logger references with `"port.bridge"`:

1. `clean_port_script_logger` fixture: `logging.getLogger("port")` → `logging.getLogger("port.bridge")`
2. `test_log_commands_returned_before_script_command`: `logging.getLogger("port")` → `logging.getLogger("port.bridge")`
3. `test_add_log_handler_wires_logger`: `logging.getLogger("port")` → `logging.getLogger("port.bridge")`
4. `test_log_command_flow_integration`: `logging.getLogger("port")` → `logging.getLogger("port.bridge")`
5. `test_start_function_creates_wrapper_with_log_handler`: `logging.getLogger("port")` → `logging.getLogger("port.bridge")`

- [ ] **Step 3: Run all tests**

Run: `cd packages/python && poetry run pytest -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add port/main.py tests/test_main_queue.py
git commit -m "feat: narrow log forwarding scope from port to port.bridge (PII safety)"
```

---

## Task 3: Add error counting to extraction_helpers and validate.py

**Files:**
- Modify: `packages/python/port/helpers/extraction_helpers.py`
- Modify: `packages/python/port/helpers/validate.py`

This task adds the optional `errors: Counter[str] | None = None` parameter to helper functions that swallow errors, and converts all content enumeration (zip namelist iteration) to use non-propagating loggers.

- [ ] **Step 1: Add content_logger and errors parameter to extraction_helpers.py**

At the top of the file, after the existing `logger = logging.getLogger(__name__)`, add:

```python
# Non-propagating logger for zip content enumeration.
# Contains PII (contact names in file paths). Inert by default —
# a developer must explicitly attach a handler in a debug session.
content_logger = logging.getLogger(f"{__name__}.content")
content_logger.propagate = False
content_logger.addHandler(logging.NullHandler())
```

- [ ] **Step 2: Update json_dumper content logging (line 157)**

In `json_dumper()` (~line 133), change line 157:
```python
logger.debug("Contained in zip: %s", f)
```
to:
```python
content_logger.debug("Contained in zip: %s", f)
```

- [ ] **Step 3: Update extract_file_from_zip**

Change the zip content log at line 344:
```python
logger.debug("Contained in zip: %s", f)
```
to:
```python
content_logger.debug("Contained in zip: %s", f)
```

Add `errors: Counter[str] | None = None` parameter and increment in except blocks:

For `extract_file_from_zip` at line ~314:
```python
def extract_file_from_zip(zfile: str, file_to_extract: str, errors: Counter | None = None) -> io.BytesIO:
```

In the except blocks:
```python
    except zipfile.BadZipFile as e:
        logger.error("BadZipFile:  %s", e)
        if errors is not None:
            errors["BadZipFile"] += 1
    except FileNotFoundInZipError as e:
        logger.error("File not found:  %s: %s", file_to_extract, e)
        if errors is not None:
            errors["FileNotFoundInZipError"] += 1
    except Exception as e:
        logger.error("Exception was caught:  %s", e)
        if errors is not None:
            errors["Exception"] += 1
```

- [ ] **Step 4: Update _read_json**

Add `errors: Counter[str] | None = None` parameter to `_read_json`:

```python
def _read_json(json_input, json_reader, errors: Counter | None = None):
```

In the except blocks:
```python
        except json.JSONDecodeError:
            logger.error("Cannot decode json with encoding: %s", encoding)
            if errors is not None:
                errors["JSONDecodeError"] += 1
        except TypeError as e:
            logger.error("%s, could not convert json bytes", e)
            if errors is not None:
                errors["TypeError"] += 1
            break
        except Exception as e:
            logger.error("%s, could not convert json bytes", e)
            if errors is not None:
                errors["Exception"] += 1
            break
```

- [ ] **Step 5: Update read_json_from_bytes**

Add `errors` parameter and pass through to `_read_json`:

```python
def read_json_from_bytes(json_bytes: io.BytesIO, errors: Counter | None = None) -> dict[Any, Any] | list[Any]:
```

In the body:
```python
    try:
        b = json_bytes.read()
        out = _read_json(b, _json_reader_bytes, errors=errors)
    except Exception as e:
        logger.error("%s, could not convert json bytes", e)
        if errors is not None:
            errors["Exception"] += 1
```

- [ ] **Step 6: Update epoch_to_iso**

Add `errors` parameter:

```python
def epoch_to_iso(epoch_timestamp, errors: Counter | None = None) -> str:
```

In the except block:
```python
    except (OverflowError, OSError, ValueError, TypeError) as e:
        logger.error("Could not convert epoch time timestamp, %s", e)
        if errors is not None:
            errors["TimestampParseError"] += 1
```

- [ ] **Step 7: Update read_csv_from_bytes**

Add `errors` parameter (line ~509):

```python
def read_csv_from_bytes(json_bytes: io.BytesIO, errors: Counter | None = None) -> list[dict[Any, Any]]:
```

In the except block:
```python
    except Exception as e:
        logger.error("%s, could not convert csv bytes", e)
        if errors is not None:
            errors["CSVDecodeError"] += 1
```

- [ ] **Step 8: Add Counter import at top of file**

Add `from collections import Counter` to the imports.

- [ ] **Step 9: Update validate.py content logger**

In `packages/python/port/helpers/validate.py`, after `logger = logging.getLogger(__name__)` (line 15), add:

```python
content_logger = logging.getLogger(f"{__name__}.content")
content_logger.propagate = False
content_logger.addHandler(logging.NullHandler())
```

Change line 236:
```python
logger.debug("Found: %s in zip", p.name)
```
to:
```python
content_logger.debug("Found: %s in zip", p.name)
```

- [ ] **Step 10: Run all tests**

Run: `cd packages/python && poetry run pytest -v`
Expected: All tests PASS (errors parameter is optional, so existing callers unaffected)

- [ ] **Step 11: Commit**

```bash
git add port/helpers/extraction_helpers.py port/helpers/validate.py
git commit -m "feat: add error counting to extraction helpers, non-propagating content loggers"
```

---

## Task 4: Update platform extraction functions to return ExtractionResult

**Files:**
- Modify: All 9 platform files in `packages/python/port/platforms/`

Each platform's `extraction()` function and `extract_data()` method needs to:
1. Create a `Counter` and pass it to helper calls
2. Return `ExtractionResult(tables, errors)` instead of bare table list

- [ ] **Step 1: Update instagram.py**

Import at top:
```python
from collections import Counter
from port.api.d3i_props import ExtractionResult
```

In `extraction()`, add `errors = Counter()` at the start. Pass `errors=errors` to each `eh.extract_file_from_zip()` call, each `eh.read_json_from_bytes()` call, and each `eh.epoch_to_iso()` call where applicable. Add error counting to the platform-level except blocks:

```python
    except Exception as e:
        logger.error("Exception caught: %s", e)
        errors["Exception"] += 1
```

Change the return:
```python
    return ExtractionResult(
        tables=[table for table in tables if not table.data_frame.empty],
        errors=errors,
    )
```

Update `extract_data` to match:
```python
    def extract_data(self, file_value, validation):
        return extraction(file_value)
```
(No change needed — `extraction()` now returns `ExtractionResult` directly.)

- [ ] **Step 2: Update facebook.py** — same pattern

- [ ] **Step 3: Update tiktok.py** — same pattern

- [ ] **Step 4: Update youtube.py** — same pattern

- [ ] **Step 5: Update linkedin.py** — same pattern

- [ ] **Step 6: Update netflix.py** — same pattern, but `extract_data` is a generator:

```python
def extract_data(self, file, validation):
    selected_user = ""
    users = extract_users(file)
    if len(users) == 1:
        selected_user = users[0]
        return extraction(file, selected_user)
    elif len(users) > 1:
        ...
        selection = yield ph.render_page(empty_text, radio_prompt)
        selected_user = selection.value
        return extraction(file, selected_user)
```

The `extraction()` function returns `ExtractionResult`. The generator `return` sends it via `StopIteration.value`.

- [ ] **Step 7: Update chatgpt.py** — same pattern

- [ ] **Step 8: Update whatsapp.py** — same pattern (note: different extraction input type)

- [ ] **Step 9: Update x.py** — same pattern

- [ ] **Step 10: Run all tests**

Run: `cd packages/python && poetry run pytest -v`
Expected: All tests PASS

- [ ] **Step 11: Commit**

```bash
git add port/platforms/
git commit -m "feat: platform extractions return ExtractionResult with error counts"
```

---

## Task 5: Add bridge_logger milestones to FlowBuilder and script.py

**Files:**
- Modify: `packages/python/port/helpers/flow_builder.py`
- Modify: `packages/python/port/script.py`
- Modify: `packages/python/tests/test_flow_builder.py`

- [ ] **Step 1: Update flow_builder.py**

Add bridge_logger import and ExtractionResult handling:

```python
from collections.abc import Generator

bridge_logger = logging.getLogger("port.bridge")
```

Update `start_flow()` with milestones and ExtractionResult handling. Replace the existing logger calls with bridge_logger calls where messages are PII-safe, keep local logger for diagnostics:

```python
def start_flow(self):
    while True:
        # 1. Render file prompt
        logger.info("Prompt for file for %s", self.platform_name)
        file_prompt = self.generate_file_prompt()
        file_result = yield ph.render_page(self.UI_TEXT["submit_file_header"], file_prompt)

        # Skip
        if file_result.__type__ not in ("PayloadFile", "PayloadString"):
            logger.info("Skipped at file selection for %s", self.platform_name)
            return

        # 2. Materialize
        path = uploads.materialize_file(file_result)
        # Bridge milestone: file received (size + type only, no path)
        file_size = getattr(file_result.value, 'size', None) if file_result.__type__ == "PayloadFile" else None
        bridge_logger.info("[%s] File received: %s bytes, %s",
                          self.platform_name,
                          file_size or "unknown",
                          file_result.__type__)

        # 3. Safety check
        try:
            uploads.check_file_safety(path)
        except (uploads.FileTooLargeError, uploads.ChunkedExportError) as e:
            logger.error("Safety check failed for %s: %s", self.platform_name, e)
            bridge_logger.info("[%s] Safety check failed: %s", self.platform_name, type(e).__name__)
            _ = yield ph.render_safety_error_page(self.platform_name, e)
            return

        # 4. Validate
        validation = self.validate_file(path)
        status = validation.get_status_code_id()
        category = getattr(validation, 'current_ddp_category', None)
        category_id = getattr(category, 'id', 'unknown') if category else 'unknown'

        if status == 0:
            bridge_logger.info("[%s] Validation: valid (%s)", self.platform_name, category_id)
        else:
            bridge_logger.info("[%s] Validation: invalid", self.platform_name)

        # 5. If invalid → retry
        if status != 0:
            logger.info("Invalid %s file; prompting retry", self.platform_name)
            retry_prompt = self.generate_retry_prompt()
            retry_result = yield ph.render_page(self.UI_TEXT["retry_header"], retry_prompt)
            if retry_result.__type__ == "PayloadTrue":
                continue
            return

        # 6. Extract
        logger.info("Extracting data for %s", self.platform_name)
        raw_result = self.extract_data(path, validation)
        if isinstance(raw_result, Generator):
            result = yield from raw_result
        else:
            result = raw_result

        # 7. Log extraction summary via bridge
        total_rows = sum(len(t.data_frame) for t in result.tables)
        if result.errors:
            error_summary = ", ".join(f"{k}×{v}" for k, v in result.errors.items())
            bridge_logger.info("[%s] Extraction complete: %d tables, %d rows; errors: %s",
                              self.platform_name, len(result.tables), total_rows, error_summary)
        else:
            bridge_logger.info("[%s] Extraction complete: %d tables, %d rows; errors: none",
                              self.platform_name, len(result.tables), total_rows)

        # 8. If no tables → no-data page
        if not result.tables:
            logger.info("No data extracted for %s", self.platform_name)
            _ = yield ph.render_no_data_page(self.platform_name)
            return

        break

    # 9. Render consent form
    bridge_logger.info("[%s] Consent form shown", self.platform_name)
    review_data_prompt = self.generate_review_data_prompt(result.tables)
    consent_result = yield ph.render_page(self.UI_TEXT["review_data_header"], review_data_prompt)

    # 10. Donate
    if consent_result.__type__ == "PayloadJSON":
        reviewed_data = consent_result.value
        bridge_logger.info("[%s] Consent: accepted", self.platform_name)
    elif consent_result.__type__ == "PayloadFalse":
        reviewed_data = json.dumps({"status": "data_submission declined"})
        bridge_logger.info("[%s] Consent: declined", self.platform_name)
    else:
        return

    donate_key = f"{self.session_id}-{self.platform_name.lower()}"
    bridge_logger.info("[%s] Donation started: payload size=%d bytes",
                      self.platform_name, len(reviewed_data))
    donate_result = yield ph.donate(donate_key, reviewed_data)

    # 11. Inspect donate result
    if not ph.handle_donate_result(donate_result):
        logger.error("Donation failed for %s", self.platform_name)
        bridge_logger.info("[%s] Donation result: failed", self.platform_name)
        _ = yield ph.render_donate_failure_page(self.platform_name)
        return

    bridge_logger.info("[%s] Donation result: success", self.platform_name)
```

Also update the `extract_data` abstract method signature:

```python
@abstractmethod
def extract_data(self, file: str, validation: validate.ValidateInput) -> d3i_props.ExtractionResult:
    """Extract data from file using platform-specific logic."""
    raise NotImplementedError("Must be implemented by subclass")
```

- [ ] **Step 2: Update script.py**

Add bridge_logger:
```python
bridge_logger = logging.getLogger("port.bridge")
```

Update `process()`:
```python
    for platform_name, flow in platforms:
        bridge_logger.info("Starting platform: %s", platform_name)
        yield from flow.start_flow()

    bridge_logger.info("Study complete")
    yield ph.render_end_page()
```

Remove the existing `logger.info("Starting platform: %s")` line (replaced by bridge_logger).

- [ ] **Step 3: Update test_flow_builder.py**

Update `StubFlow.extract_data` to return `ExtractionResult`:

```python
from port.api.d3i_props import ExtractionResult
from collections import Counter

class StubFlow(FlowBuilder):
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
        v.current_ddp_category = MagicMock(id="json_en")
        return v

    def extract_data(self, file, validation):
        return ExtractionResult(tables=self._tables, errors=Counter())
```

Update `TestNoDataPath` to use empty ExtractionResult:
```python
flow = StubFlow(tables=[])
```
This already works since StubFlow wraps the tables in ExtractionResult.

- [ ] **Step 4: Run all tests**

Run: `cd packages/python && poetry run pytest -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add port/helpers/flow_builder.py port/script.py tests/test_flow_builder.py
git commit -m "feat: add bridge_logger milestones to FlowBuilder and script.py"
```

---

## Task 6: Final verification

- [ ] **Step 1: Run full test suite**

```bash
cd packages/python && poetry run pytest -v
```
Expected: All tests PASS

- [ ] **Step 2: Verify no port.* loggers write to bridge**

```bash
cd packages/python && grep -rn "bridge_logger" port/ --include="*.py" | grep -v "flow_builder\|script\.py\|__pycache__"
```
Expected: No matches — only flow_builder.py and script.py use bridge_logger

- [ ] **Step 3: Verify content_logger is non-propagating**

```bash
cd packages/python && grep -n "content_logger" port/helpers/extraction_helpers.py
```
Expected: Shows content_logger definition with propagate=False and usage in zip enumeration

- [ ] **Step 4: Verify bridge messages contain no paths, keys, or exception text**

Review bridge_logger.info calls in flow_builder.py — none should include:
- File paths (no `path` variable in message)
- Donate keys (no `donate_key` variable in message)
- Exception messages (only `type(e).__name__`, not `str(e)`)
- DDP filenames
