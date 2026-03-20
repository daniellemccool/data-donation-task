# PII-Safe Logging for Multi-Module Extraction Architecture

**Date:** 2026-03-20
**ADR:** python-architecture/AD0009 (exception safety), python-architecture/AD0008 (log forwarding scope)
**Scope:** Redesign log forwarding to prevent PII leakage while providing flow observability

## Context

The log forwarding system (PR #663 in eyra/feldspar) forwards Python log messages to mono via `CommandSystemLog` → HTTP POST to `/api/feldspar/log` → AppSignal. In Eyra's single-file model, the handler is scoped to `port.script` — the only file that exists. Our multi-module architecture (script.py → FlowBuilder → platforms → helpers) widened this to `port`, which captured extraction_helpers ERROR logs containing file paths with PII (contact names in Facebook DDP directory structure) and triggered 429 rate limiting on mono.

### PII exposure paths identified

1. **Explicit logger calls:** `logger.error("Exception caught: %s", e)` where `e` contains participant data (Python exceptions routinely include the offending input in their message). Present in extraction_helpers and all 9 platform files. These are researcher/developer-written calls.

2. **Uncaught exceptions (Eyra framework-level):** In eyra/feldspar develop, uncaught Python exceptions propagate to Pyodide → JS worker → `worker_engine.ts` logs via `LogForwarder` → `bridge.sendLogs()` → mono. Full stack trace forwarded without consent. Our fork mitigates this at the Python level via ScriptWrapper's `except Exception` catch (AD0009). **Remaining risk:** If Pyodide itself throws (out-of-memory, WebAssembly trap, or Pyodide glue code error that bypasses Python's exception mechanism), `py_worker.js` catches it and `worker_engine.ts` forwards `error.toString()` and the stack trace via the JS-side `LogForwarder`. This JS-level path is outside our control — it's in feldspar's framework code. Reported to Eyra on 2026-03-20.

3. **Debug-level zip enumeration:** `extraction_helpers.extract_file_from_zip()` logs every file in the zip at DEBUG level. A Facebook DDP contains thousands of files with paths like `messages/inbox/contactname_12345/videos/file.mp4`. Currently blocked by INFO handler level, but this protection is fragile — any handler level change would expose them.

### What we need from logging

- **Flow milestones:** Where the participant is in the process, sent as they happen (not batched). Critical because the iframe may crash before end-of-flow, and we need to know how far they got.
- **Extraction error summary:** Per-error-type counts after extraction completes. Not individual error messages (which may contain PII).
- **Local diagnostics:** Full error messages in browser console for developer debugging. Never forwarded.

### Supersedes extraction consolidation spec logging decision

The extraction consolidation spec (2026-03-17) changed `add_log_handler()` from `port.script` to `port`. This design supersedes that decision — the scope changes to `port.bridge` instead. The `port` scope was the correct intent (capture logs from the multi-module architecture) but the wrong mechanism (captured everything including PII-containing diagnostic logs).

## Decision

### Two-logger architecture

**`port.bridge`** — dedicated logger for messages safe to forward to the host platform. `LogForwardingHandler` attaches only to this logger. Only FlowBuilder and script.py write to it. Messages on this logger are designed to be PII-free.

**`__name__` loggers** (e.g. `port.helpers.extraction_helpers`, `port.platforms.facebook`) — standard Python loggers for local diagnostic output. These appear in the browser console but are never forwarded because no handler is attached to them or their parents that forwards to the bridge.

### Implementation: LogForwardingHandler scope

```python
# main.py
def add_log_handler(self, logger_name: str = "port.bridge") -> None:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    handler = LogForwardingHandler(self.queue)
    handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
    logger.addHandler(handler)
```

The handler attaches to `port.bridge`, not `port`. No propagation issues — `port.bridge` is a leaf logger with no children.

### Implementation: Bridge logger usage

FlowBuilder and script.py import and use the bridge logger:

```python
# In flow_builder.py and script.py
bridge_logger = logging.getLogger("port.bridge")
```

The existing `logger = logging.getLogger(__name__)` stays for local diagnostics.

### Implementation: Non-propagating content logger

```python
# In extraction_helpers.py
content_logger = logging.getLogger("port.helpers.extraction_helpers.content")
content_logger.propagate = False
content_logger.addHandler(logging.NullHandler())
```

Replace `logger.debug("Contained in zip: %s", f)` with `content_logger.debug(...)`. This logger produces zero output unless a developer explicitly attaches a handler. Setting `propagate = False` means even if someone attaches a forwarding handler to `port` or `port.helpers`, these messages never reach it.

## Flow Milestones

All emitted by FlowBuilder via `bridge_logger.info()` at each step of `start_flow()`:

```
[LinkedIn] File received: 161016 bytes, PayloadFile
[LinkedIn] Validation: valid (json_en)
[LinkedIn] Extraction complete: 5 tables, 127 rows; errors: none
[LinkedIn] Consent form shown
[LinkedIn] Consent: accepted
[LinkedIn] Donation started: key=sess-123-linkedin, size=418771
[LinkedIn] Donation result: success
```

And by script.py:
```
Starting platform: LinkedIn
Study complete
```

### What is NOT logged to the bridge

- File paths from DDP contents
- Raw exception messages
- Individual extraction errors
- Any string derived from participant data

## ExtractionResult Dataclass

`extract_data()` return type changes from `list[PropsUIPromptConsentFormTableViz]` to:

```python
from collections import Counter

@dataclass
class ExtractionResult:
    tables: list[PropsUIPromptConsentFormTableViz]
    errors: Counter[str]  # e.g. Counter({"FileNotFound": 8, "JSONDecodeError": 4})
```

Uses `Counter` rather than bare `dict` — the `errors[type(e).__name__] += 1` pattern is cleaner and less error-prone across 9 platform implementations.

This lives in `port/api/d3i_props.py` (alongside the table types it references).

### Platform extraction function changes

Each platform's `extraction()` function changes to collect error counts. The existing pattern:

```python
# Current: individual errors logged, empty DataFrame returned
try:
    items = d["following_v3"]
    ...
except Exception as e:
    logger.error("Exception caught: %s", e)
return out  # empty DataFrame
```

Becomes:

```python
# New: errors counted, still logged locally, returned in result
errors: dict[str, int] = {}
...
try:
    items = d["following_v3"]
    ...
except KeyError as e:
    logger.error("Exception caught: %s", e)  # local diagnostic, unchanged
    errors["KeyError"] = errors.get("KeyError", 0) + 1
except Exception as e:
    logger.error("Exception caught: %s", e)
    errors["Exception"] = errors.get("Exception", 0) + 1

return ExtractionResult(
    tables=[t for t in tables if not t.data_frame.empty],
    errors=errors,
)
```

### Netflix generator edge case

Netflix's `extract_data()` uses `yield` for a profile selection radio prompt (multiple Netflix profiles in one DDP). This makes it a generator, not a regular function — it cannot simply `return ExtractionResult(...)`.

**Resolution:** FlowBuilder detects generator returns and handles them with `yield from`, same as the old FlowBuilder did (the removed `isinstance(self.table_list, Generator)` check). The extraction result is obtained via `StopIteration.value` when the generator exhausts:

```python
# step 6: Extract
raw_result = self.extract_data(path, validation)
if isinstance(raw_result, Generator):
    result = yield from raw_result
else:
    result = raw_result
```

Netflix's `extract_data()` would `yield` for the radio prompt, then `return ExtractionResult(...)` at the end. All other platforms return `ExtractionResult` directly.

### WhatsApp extraction pattern note

WhatsApp's `extraction()` receives a pre-parsed DataFrame rather than a zip path. The error-counting pattern still applies but typical exceptions differ (DataFrame column `KeyError` rather than `FileNotFoundError` or `JSONDecodeError`). The platform implementation should use error type names that reflect the actual failures, not copy the zip-based example verbatim.

### FlowBuilder changes

```python
# step 6: Extract
raw_result = self.extract_data(path, validation)
if isinstance(raw_result, Generator):
    result = yield from raw_result
else:
    result = raw_result

# step 7: Log extraction summary via bridge
total_rows = sum(len(t.data_frame) for t in result.tables)
if result.errors:
    error_summary = ", ".join(f"{k}×{v}" for k, v in result.errors.items())
    bridge_logger.info("[%s] Extraction complete: %d tables, %d rows; errors: %s",
                       self.platform_name, len(result.tables), total_rows, error_summary)
else:
    bridge_logger.info("[%s] Extraction complete: %d tables, %d rows; errors: none",
                       self.platform_name, len(result.tables), total_rows)

# step 8: check for empty
if not result.tables:
    ...
```

## File Changes

### Modified files
- `port/main.py` — handler scope `port.bridge` (from `port`)
- `port/helpers/flow_builder.py` — add `bridge_logger`, flow milestone logs, handle `ExtractionResult`
- `port/script.py` — add `bridge_logger` for platform start and study complete
- `port/api/d3i_props.py` — add `ExtractionResult` dataclass
- `port/helpers/extraction_helpers.py` — non-propagating content logger, replace `logger.debug("Contained in zip: ...")` calls. The existing 12+ `logger.error()` calls throughout extraction_helpers are intentionally left unchanged as local-only diagnostics — they use the `__name__` logger which has no bridge handler attached. Their error information reaches the bridge only via the aggregated `ExtractionResult.errors` counts returned by the platform callers.
- `port/platforms/instagram.py` — `extraction()` returns `ExtractionResult` with error counts
- `port/platforms/facebook.py` — same
- `port/platforms/tiktok.py` — same
- `port/platforms/youtube.py` — same
- `port/platforms/linkedin.py` — same
- `port/platforms/netflix.py` — same
- `port/platforms/chatgpt.py` — same
- `port/platforms/whatsapp.py` — same
- `port/platforms/x.py` — same
- `tests/test_main_queue.py` — update logger scope from `port` to `port.bridge`
- `tests/test_flow_builder.py` — update for `ExtractionResult` return type

### New files
- None

### Not changed
- `port/api/logging.py` — `LogForwardingHandler` unchanged
- `port/helpers/validate.py` — unchanged
- `port/helpers/port_helpers.py` — unchanged

## Compatibility with future error donation page

The error donation page (out of scope) will show full error details to the participant and ask for consent to donate. This design is compatible:

- **Automatic path (this design):** Scrubbed error counts forwarded via bridge_logger. Always on, PII-free.
- **Voluntary path (future):** Full error details collected in `ExtractionResult.errors` could be extended to include messages (not just counts) and shown to the participant via a consent UI. The `error_flow()` pattern in main.py already demonstrates this for uncaught exceptions.

The `ExtractionResult` dataclass can be extended with an optional `error_details: list[str]` field when the error donation page is built. These details would never go through bridge_logger — only through the consent-gated donation path.

### Note on error_flow() in main.py

`error_flow()` already shows full tracebacks to the participant and can donate them via `CommandSystemDonate` with participant consent. The traceback text rendered in the UI (`PropsUIPromptText`) may contain PII from exception messages. This is acceptable because: (a) it goes through explicit participant consent ("Would you like to report this error?"), (b) it uses the donation path (`CommandSystemDonate`), not the logging path (`CommandSystemLog`), and (c) the participant can see what they're sharing. This is distinct from the automatic bridge logging path which has no consent gate.

## ADR Updates

- **python-architecture/AD0008**: Update to reflect `port.bridge` scope instead of `port`
- **python-architecture/AD0009**: Already committed — documents ScriptWrapper exception catch as PII safety boundary

## Design Principles

1. **PII never crosses the bridge unsanitized via Python logging** — bridge_logger messages are designed to be PII-free. Remaining risk: Pyodide-level crashes may forward stack traces via the JS-side LogForwarder path (outside our control, reported to Eyra)
2. **Explicit opt-in for bridge forwarding** — code must deliberately use bridge_logger; accidental forwarding is impossible
3. **Local diagnostics preserved** — `__name__` loggers keep full error messages in browser console
4. **Milestones sent as they happen** — immediate forwarding, not batched, because iframe crashes lose buffered data
5. **Error counts, not error messages** — the bridge gets "KeyError×3", not the KeyError's content
6. **Content enumeration isolated** — zip file listing uses non-propagating logger, inert by default
