# PII-Safe Logging for Multi-Module Extraction Architecture

**Date:** 2026-03-20
**Status:** Proposed revision to `2026-03-20-pii-safe-logging-design.md`
**ADR:** python-architecture/AD0009 (exception safety), python-architecture/AD0008 (log forwarding scope)
**Scope:** Redesign log forwarding to prevent PII leakage while preserving minimal flow observability

## Context

The current implementation forwards Python logs from the `port` logger tree to mono via `CommandSystemLog` and `/api/feldspar/log`.

This is not theoretical. The observed browser logs in `~/logs/ddt6.log` and `~/logs/ddt7.log` show concrete forwarding of:

- `port.helpers.uploads: PayloadFile: wrote 64247155 bytes to /tmp/facebook-3y-download-2026-03-10.zip`
- `port.helpers.validate: Detected DDP category: json_en`
- `port.helpers.extraction_helpers: File not found: who_you_ve_followed.json: File not found in zip`
- `port.platforms.facebook: Exception caught: 'following_v3'`

The same run produces repeated `POST https://next.eyra.co/api/feldspar/log 429` responses, confirming the current design creates both a privacy problem and a rate-limit problem.

### Exposure paths confirmed

1. **Explicit logger calls in Python code**

   These are currently forwarded automatically because the handler is attached to `port`, not to a dedicated safe logger. The observed examples include:

   - shared infrastructure: `port.helpers.uploads`, `port.helpers.validate`
   - shared extraction helpers: `port.helpers.extraction_helpers`
   - platform code: `port.platforms.facebook`

   This is the main active exposure path in the current fork.

2. **High-volume helper diagnostics**

   `extraction_helpers` emits many per-file and per-error logs. In `ddt7.log`, repeated helper errors alone are enough to drive `/api/feldspar/log` into `429` responses. Even when a given message is not directly identifying, this volume is operationally unsafe.

3. **Framework-level uncaught exception path**

   AD0009 is still correct: uncaught Python exceptions must not be allowed to escape to the JS-side logging path without consent. That remains an upstream/framework risk to track with Eyra.

   For this spec, the design must not rely on JS-side truncation, bridge behavior, or current worker implementation details as a privacy control.

## What we need from logging

- **Flow milestones:** a small number of PII-free status messages, forwarded immediately
- **Extraction summary:** aggregated error counts only, never raw exception text
- **Local diagnostics:** full messages can remain local to the browser/runtime for debugging, but they must not cross the bridge automatically

## Decision

### 1. Use a dedicated bridge logger

Forwarded logs must come only from `port.bridge`.

`ScriptWrapper.add_log_handler()` changes from `port` to `port.bridge`:

```python
def add_log_handler(self, logger_name: str = "port.bridge") -> None:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    handler = LogForwardingHandler(self.queue)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
    logger.addHandler(handler)
```

Two requirements matter here:

- `logger_name` must be `port.bridge`, not `port`
- `logger.propagate = False` must be set so a future parent handler cannot accidentally re-forward bridge messages or duplicate them

### 2. Reserve `port.bridge` for a tiny safe vocabulary

Only `script.py` and `FlowBuilder` may log to `port.bridge`.

Platform modules and helper modules keep using `logging.getLogger(__name__)`, but those logs remain local-only.

Bridge messages must never include:

- participant-provided content
- DDP file names or internal paths
- local filesystem paths
- raw exception strings
- traceback text
- donation keys or session-derived identifiers

### 3. Keep flow milestones, but make them privacy-safe

Allowed examples:

```text
Starting platform: LinkedIn
[LinkedIn] File received: 161016 bytes, PayloadFile
[LinkedIn] Validation: valid (json_en)
[LinkedIn] Extraction complete: 5 tables, 127 rows; errors: none
[LinkedIn] Consent form shown
[LinkedIn] Consent: accepted
[LinkedIn] Donation started: payload size=418771 bytes
[LinkedIn] Donation result: success
Study complete
```

Not allowed:

- `key=sess-123-linkedin`
- `/tmp/facebook-3y-download-2026-03-10.zip`
- `who_you_ve_followed.json`
- `"Exception caught: 'following_v3'"`

### 4. Aggregate errors where they are currently swallowed

The original spec was too optimistic about platform-level `try/except` blocks.

Today, many failures are swallowed inside shared helpers such as:

- `extract_file_from_zip()`
- `_read_json()` / `read_json_from_bytes()`
- `read_csv_from_bytes()`
- timestamp conversion helpers

If those helpers keep catching exceptions and returning fallback values, platform code will never see the original failure and cannot count it accurately afterward.

Therefore the aggregation boundary must include shared helpers.

## ExtractionResult

`extract_data()` returns:

```python
from collections import Counter
from dataclasses import dataclass

@dataclass
class ExtractionResult:
    tables: list[PropsUIPromptConsentFormTableViz]
    errors: Counter[str]
```

### Error-counting rule

If a helper swallows an error locally, it must increment the shared `Counter` before returning its fallback value.

Example shape:

```python
def extract_file_from_zip(
    zfile: str,
    file_to_extract: str,
    errors: Counter[str] | None = None,
) -> io.BytesIO:
    ...
    except FileNotFoundInZipError as e:
        logger.error("File not found: %s: %s", file_to_extract, e)
        if errors is not None:
            errors["FileNotFoundInZipError"] += 1
```

Platform-level handlers still increment the same counter for failures they catch directly.

This preserves current local diagnostics while making the forwarded summary truthful.

### FlowBuilder summary

FlowBuilder logs only the aggregate:

```python
total_rows = sum(len(t.data_frame) for t in result.tables)

if result.errors:
    error_summary = ", ".join(f"{k}×{v}" for k, v in result.errors.items())
    bridge_logger.info(
        "[%s] Extraction complete: %d tables, %d rows; errors: %s",
        self.platform_name,
        len(result.tables),
        total_rows,
        error_summary,
    )
else:
    bridge_logger.info(
        "[%s] Extraction complete: %d tables, %d rows; errors: none",
        self.platform_name,
        len(result.tables),
        total_rows,
    )
```

## Content enumeration logs

Zip-entry enumeration is especially sensitive because paths can contain names and because the volume is large.

For any helper that enumerates archive contents for debugging, use a dedicated non-propagating logger:

```python
content_logger = logging.getLogger("port.helpers.extraction_helpers.content")
content_logger.propagate = False
content_logger.addHandler(logging.NullHandler())
```

Apply the same pattern to `validate.py` if zip-entry enumeration is kept there.

This is defense in depth. The primary privacy boundary is still that forwarding attaches only to `port.bridge`.

## File impact

### Modified files

- `packages/python/port/main.py`
- `packages/python/port/helpers/flow_builder.py`
- `packages/python/port/script.py`
- `packages/python/port/api/d3i_props.py`
- `packages/python/port/helpers/extraction_helpers.py`
- `packages/python/port/helpers/validate.py`
- `packages/python/port/platforms/*.py`
- `packages/python/tests/test_main_queue.py`
- `packages/python/tests/test_flow_builder.py`

### Unchanged but now protected by scope change

- `packages/python/port/helpers/uploads.py`

Its current info log contains a local path and original filename, which is unsafe to forward. After the scope change it stays local-only.

## Required tests

The design is not complete without regression tests.

1. `port.bridge` logs are forwarded as `CommandSystemLog`
2. `port.platforms.facebook` logs are not forwarded
3. `port.helpers.uploads` logs are not forwarded
4. `port.bridge` has `propagate = False`
5. content loggers do not forward even if a broader parent handler is attached
6. helper-originated failures increment `ExtractionResult.errors`

## Rationale

This is the correct approach for the current problem because it fixes the active exposure path shown in `ddt7.log`:

- it stops forwarding raw helper and platform diagnostics
- it keeps a small observability channel for milestones
- it avoids forwarding exception text and filenames
- it reduces log volume enough to avoid the observed `429` storm

The remaining JS/framework exception path is a separate boundary to track with Eyra, but it is not a reason to keep forwarding the current Python logger tree.
