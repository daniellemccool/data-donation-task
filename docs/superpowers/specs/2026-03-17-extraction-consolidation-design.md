# Extraction Consolidation Design

**Date:** 2026-03-17
**ADR:** python-architecture/AD0006
**Scope:** Consolidate donation_flows/ and platforms/ into a single FlowBuilder-based extraction architecture

## Context

Two parallel extraction systems exist in this fork:

- **platforms/** (d3i-infra standard): FlowBuilder template method pattern with DDP_CATEGORIES validation. 9 platform implementations. Designed by trbKnl (Niek de Schipper) in April 2025 as "a standardized way of building up data donation flows." Used in dd-vu-2026 with 7 production platforms.
- **donation_flows/** (what-if origin): Data-driven entries pattern from Kasper Welbers' what-if project, copy-pasted in commit 4f4c0d88. 180 Facebook tables in ~59 lines via auto-generated entries. Active in script.py; FlowBuilder unwired.

Neither system alone satisfies all ADRs. This design consolidates on FlowBuilder as the standard, fixes its gaps, and removes donation_flows/.

## Decision

**FlowBuilder is the standard.** Realize Niek's original goal: FlowBuilder owns the per-platform flow, script.py owns study-level orchestration.

**donation_flows/ is removed.** It's Kasper's what-if innovation — could become a plug-in pattern someday, but the template repo standardizes on FlowBuilder + platforms/.

**Data minimization drives architecture.** The template ships a library of common extraction functions per platform. Researchers select which tables to include in their study. The auto-extraction approach (180 tables) conflicts with the project's data minimization principle.

## Architectural Layers

```
main.py / ScriptWrapper
  Framework boundary: generator bridge, PayloadFile→AsyncFileAdapter, exception capture
  (UI construction delegated to port_helpers)

  └── script.py / process()
        Study orchestration: platform list, VITE_PLATFORM filtering, sequencing, end-of-study flow

        └── platforms/*.py
              Platform bindings: subclass FlowBuilder, define validate_file() and extract_data()

              └── helpers/flow_builder.py
                    Shared per-platform orchestration:
                    file→materialize→safety→validate→retry→extract→consent→donate

                    ├── helpers/uploads.py         File materialization, safety checks, temp-file policy
                    ├── helpers/validate.py         DDP validation (unchanged)
                    ├── helpers/port_helpers.py     UI/page construction, donate-result handling
                    └── helpers/extraction_helpers.py  Parsing utilities (unchanged)
```

**Dependency rule:** Each layer only calls downward. FlowBuilder never reaches up to script.py. Helpers never reach up to FlowBuilder.

**ADR alignment:**
- AD0001 (layered architecture): FlowBuilder is shared helper-layer infrastructure, not a platform module
- AD0003 (UI through port_helpers): all page construction goes through port_helpers.py, including error pages
- AD0005 (generator protocol): FlowBuilder.start_flow() is a generator; script.py uses `yield from`

## FlowBuilder Changes

FlowBuilder moves from `platforms/flow_builder.py` to `helpers/flow_builder.py` (per AD0001 — it's shared infrastructure, not a platform binding).

### Type annotation change

`FlowBuilder.__init__` changes `session_id: int` to `session_id: str` to match script.py's contract and dd-vu-2026's usage.

### Interface contract

`validate_file(path)` and `extract_data(path, validation)` receive a **file path string** (from `materialize_file()`), not a file object. This is consistent with the current d3i-infra platform implementations. The materialization step in start_flow() ensures all platform code works with paths regardless of whether the browser delivered PayloadFile or PayloadString.

### start_flow() Rewrite

The 11-step per-platform flow with explicit control flow rules:

- `continue` — retry upload only
- `break` — successful extraction, proceed to consent
- `return` — every terminal path (skip, safety error, invalid+no retry, no data, donate failure, successful completion)

All informational pages (no_data, safety_error, donate_failure) are awaited (`_ = yield ...`) so the participant sees them before the flow moves on.

```
1.  Render file prompt → receive payload
2.  Materialize upload to path via uploads.materialize_file(file_result)
    - PayloadFile → write to /tmp, return path
    - PayloadString → return existing path directly
3.  Safety check via uploads.check_file_safety(path)
    - On error → render safety error page (awaited), return
4.  Validate via self.validate_file(path) (DDP_CATEGORIES)
5.  If invalid → render retry prompt → check result
    - PayloadTrue → continue (loop back to step 1)
    - Else → return
6.  Extract via self.extract_data(path, validation)
7.  If no tables → render "no relevant data" page (awaited) → return
8.  Render consent form
9.  Donate with per-platform key: f"{session_id}-{platform_name.lower()}"
10. Inspect donate result via ph.handle_donate_result(result)
    - On failure → render donate failure page (awaited), return
11. Return (script.py handles next platform or end page)
```

FlowBuilder does not yield `ph.exit()` or `CommandSystemExit`. Exit is handled by ScriptWrapper: when the generator exhausts (StopIteration), ScriptWrapper automatically returns `CommandSystemExit(0, "End of script")`. script.py yields the end page and then returns; the generator protocol handles termination.

### Behavior Changes

- **Donate key format:** Changes from `f"{self.session_id}"` to `f"{self.session_id}-{self.platform_name.lower()}"`. This is required for multi-platform studies (avoids key collision). Single-platform builds will produce keys like `"abc123-facebook"` instead of `"abc123"`. Downstream data pipelines that expect plain session_id keys will need updating.
- **Empty extraction:** Currently (line 81), an empty table list still shows the consent form. After this change, an empty extraction renders a "no relevant data found" page and skips donation. This is intentional — showing an empty consent form is confusing UX. The no-data page explicitly tells the participant what happened.

### Bug Fixes

- **Retry result capture** (current line 76): yield now captures result, checks `__type__`, breaks on decline. Previously the result was discarded.
- **PayloadFile support** (current line 60): replaced PayloadString check with materialize_file() which handles both types for backward compatibility.

### Unchanged

- `_initialize_ui_text()` — stays as-is
- `generate_file_prompt()`, `generate_retry_prompt()`, `generate_review_data_prompt()` — stay as overridable methods
- `validate_file()` and `extract_data()` — stay abstract

## script.py Rewrite

Replaces both `d3i_example_script.py` and eyra's example `script.py`. Synthesizes dd-vu-2026's proven study orchestration pattern with FlowBuilder delegation via `yield from`. dd-vu-2026 proved the orchestration logic (multi-platform sequencing, filtering, safety checks, donation handling). FlowBuilder proved the template method pattern. The `yield from` delegation is the new element that connects them — this combination has not been deployed in production but follows directly from both proven components.

**Responsibilities:**
- Define the platform list (which FlowBuilder subclasses to run)
- VITE_PLATFORM filtering (single-platform builds)
- Multi-platform sequencing: `yield from flow.start_flow()` per platform
- End page: `yield ph.render_end_page()`

**Does NOT:**
- Handle files, validation, retry, consent, or donation (FlowBuilder owns that)
- Construct raw PropsUI objects (port_helpers only)
- Handle errors (main.py/ScriptWrapper owns that)

Approximate shape (~35 lines of logic):

```python
def process(session_id: str, platform: str | None = None):
    all_platforms = [
        ("LinkedIn",  linkedin.LinkedInFlow(session_id)),
        ("Instagram", instagram.InstagramFlow(session_id)),
        ("Facebook",  facebook.FacebookFlow(session_id)),
        ("YouTube",   youtube.YouTubeFlow(session_id)),
        ("TikTok",    tiktok.TikTokFlow(session_id)),
        ("Netflix",   netflix.NetflixFlow(session_id)),
        ("ChatGPT",   chatgpt.ChatGPTFlow(session_id)),
        ("WhatsApp",  whatsapp.WhatsAppFlow(session_id)),
        ("X",         x.XFlow(session_id)),
    ]

    platforms = filter_platforms(all_platforms, platform)

    for platform_name, flow in platforms:
        logger.info("Starting platform: %s", platform_name)
        yield from flow.start_flow()

    yield ph.render_end_page()
```

**Exit protocol:** After `render_end_page()`, `process()` returns. The generator exhausts. ScriptWrapper catches StopIteration and returns `CommandSystemExit(0, "End of script")`. The host (mono) receives the exit command and handles the transition. script.py never yields CommandSystemExit directly.

## New and Modified Helpers

### New: helpers/uploads.py

File materialization and safety checks.

```python
MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024 * 1024
CHUNKED_EXPORT_SENTINEL_BYTES = MAX_FILE_SIZE_BYTES  # same value, distinct intent

def materialize_file(file_result) -> str:
    """Convert PayloadFile or PayloadString to a file path.

    file_result.__type__ == "PayloadFile": write file_result.value
    (AsyncFileAdapter) contents to /tmp, return path.
    file_result.__type__ == "PayloadString": return file_result.value directly.
    Anything else: raise TypeError.

    Note: /tmp is emscripten in-memory FS — files persist for worker
    lifetime and are freed when the WebWorker terminates. No cleanup needed.
    Materialization doubles memory usage of the file (original + copy).
    See project_worker_memory_hang.md for broader browser memory concerns.
    """

def check_file_safety(path: str) -> None:
    """Raise FileTooLargeError or ChunkedExportError if file is unsafe.

    Checks: >MAX_FILE_SIZE_BYTES (too large),
    exactly CHUNKED_EXPORT_SENTINEL_BYTES (split export sentinel).
    """

class FileTooLargeError(Exception): ...
class ChunkedExportError(Exception): ...
```

### Additions to helpers/port_helpers.py

UI construction helpers (use existing factory-supported types):

```python
def render_end_page():
    """Render study completion page. Uses top-level PropsUIPageEnd.
    Returns CommandUIRender wrapping PropsUIPageEnd."""

def render_no_data_page(platform_name: str):
    """Render 'no relevant data found' with acknowledge button.
    Uses standard render_page() + PropsUIPromptConfirm.
    Caller should yield and await response before returning."""

def render_safety_error_page(platform_name: str, error: Exception):
    """Render file safety error.
    Uses PropsUIPageError as a custom body component inside
    PropsUIPageDataSubmission, rendered by the registered ErrorPageFactory.
    Note: PropsUIPageError is dispatched through the factory pattern
    (ErrorPageFactory checks __type__), not as a top-level page type.
    Caller should yield and await response before returning."""

def render_donate_failure_page(platform_name: str):
    """Render donation failure.
    Uses PropsUIPageError as a custom body component inside
    PropsUIPageDataSubmission, rendered by the registered ErrorPageFactory.
    Caller should yield and await response before returning."""
```

Protocol helper (bridge-result interpretation, not UI construction):

```python
def handle_donate_result(result) -> bool:
    """Inspect donate result. Returns True on success, False on failure.

    PayloadResponse(success=True) → True
    PayloadResponse(success=False) → False
    PayloadVoid / None → True (legacy fire-and-forget)
    Anything else → log warning, return False
    """
```

### Unchanged

- `helpers/validate.py` — DDP validation
- `helpers/extraction_helpers.py` — parsing utilities

## main.py Changes

**Logging:**
- Change `add_log_handler()` default from `"port.script"` to `"port"` to capture all port package loggers (FlowBuilder, platforms, helpers)
- Add formatter with logger name: `"%(name)s: %(message)s"` so forwarded messages retain source context

**error_flow() AD0003 violation:**
- Flagged for future cleanup. Lines 26-41 construct raw PropsUI objects. Should be refactored to use port_helpers when the error donation system is properly built. Not in scope for this design.

## File Changes

### New files
- `helpers/uploads.py` — file materialization + safety checks
- `tests/test_uploads.py` — materialize_file (PayloadFile + PayloadString + TypeError), check_file_safety (normal, too large, chunked export)
- `tests/test_flow_builder.py` — start_flow paths: happy, retry, skip, no-data, safety error, donate failure
- `tests/test_port_helpers.py` — new helper function tests

### Moved files
- `platforms/flow_builder.py` → `helpers/flow_builder.py`

### Modified files
- `helpers/flow_builder.py` — rewritten start_flow() (11 steps), bug fixes, correct control flow, session_id type annotation `int` → `str`
- `helpers/port_helpers.py` — add render_end_page(), render_no_data_page(), render_safety_error_page(), render_donate_failure_page(), handle_donate_result()
- `script.py` — rewritten as study orchestrator (new imports from port.platforms.*, all 9 platforms listed, filtering, `yield from`, end page)
- `main.py` — logger attachment scope (`"port.script"` → `"port"`) and formatter
- `platforms/facebook.py` — update FlowBuilder import to `port.helpers.flow_builder`
- `platforms/instagram.py` — update FlowBuilder import
- `platforms/tiktok.py` — update FlowBuilder import
- `platforms/youtube.py` — update FlowBuilder import
- `platforms/linkedin.py` — update FlowBuilder import
- `platforms/netflix.py` — update FlowBuilder import
- `platforms/chatgpt.py` — update FlowBuilder import
- `platforms/whatsapp.py` — update FlowBuilder import
- `platforms/x.py` — update FlowBuilder import
- `tests/test_main_queue.py` — update logger scope assumption from `port.script` to `port`

### Deleted files
- `platforms/flow_builder.py` (old location, after move)
- `d3i_example_script.py` — replaced by new script.py
- `donation_flows/` — entire directory (facebook.py, instagram.py, youtube.py, tiktok.py, twitter.py)
- `helpers/parsers.py` — donation_flows dependency
- `helpers/entries_data.py` — donation_flows dependency
- `helpers/donation_flow.py` — donation_flows dependency
- `helpers/readers.py` — only imported by parsers.py and donation_flows/; orphaned after deletion
- `helpers/Structure_extractor_libraries/` — entire directory (6 files); imports from parsers.py which is deleted; part of what-if's structure donation tooling, not part of the runtime extraction architecture

### Not changed
- `helpers/validate.py`
- `helpers/extraction_helpers.py`
- `api/props.py`, `api/d3i_props.py`, `api/commands.py`, `api/file_utils.py`, `api/logging.py`
- All TypeScript/React files (out of scope)

## ADR Updates

- **python-architecture/AD0006**: Status from `open` to `decided`. Option 1 selected (FlowBuilder as standard). Option text updated to match final design.

## Out of Scope

- Adding new platforms or extraction tables
- The entries_data.py generation tooling (what-if's researcher workflow)
- Mono compatibility audit (Phase 5)
- TypeScript/React changes
- main.py error_flow() AD0003 violation (deferred to error donation system redesign)
- Worker memory/hang issues (tracked in project_worker_memory_hang.md)

## Design Principles

1. **Data minimization** — template ships common extractions; researchers select what they need
2. **FlowBuilder is the standard** — realizes Niek's goal of standardized data donation flows
3. **Factory-first UI** — all custom UI types use the PromptFactory registration pattern per feldspar README
4. **Infrastructure in helpers/** — FlowBuilder orchestrates, helpers do the work
5. **script.py is orchestration-only** — no file handling, no raw props, no error handling
6. **return for terminal paths** — clean control flow in start_flow()
