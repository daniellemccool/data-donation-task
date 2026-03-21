# Archive Member Caching and Extraction Resolution

**Date:** 2026-03-21
**ADR:** extraction/AD0006 (open → decided by this spec)
**Scope:** Eliminate cascading errors for expected-missing DDP files, improve extraction resolution, reduce redundant zip I/O

## Problem

`extract_file_from_zip()` opens the zip and iterates the full namelist on every call. For Facebook (25+ tables), the zip is opened 25+ times. When a file isn't found, it produces a 4-error cascade per missing file: FileNotFoundInZipError → JSONDecodeError×2 → platform KeyError. A single Facebook extraction produces 31K lines of browser console output.

Additionally, the current "first regex suffix match in zip order" resolution has produced wrong-file extractions in practice. Some platforms (Facebook) work around this by specifying partial paths, but the behavior is accidental and fragile.

## Decision

### 1. Validation caches the archive inventory

`ValidateInput` stores the full namelist during its existing zip walk in `validate_zip()`. No new zip opens.

```python
# validate.py
@dataclass
class ValidateInput:
    ...
    # Full zip member paths cached during validation. Internal only —
    # must not appear in logs, host milestones, or donation payloads.
    archive_members: list[str] = field(default_factory=list, repr=False)
```

`validate_zip()` stores the raw `zf.namelist()` result (full member paths like `facebook-user-2026/your_facebook_activity/messages/inbox/contact_123/photo.jpg`) on the `ValidateInput` before returning. This is separate from the existing `paths` variable which stores basenames only (`Path(f).name`) for `infer_ddp_category()`. Both are needed — basenames for category matching, full paths for member resolution.

### 2. Deterministic member resolution

`extract_file_from_zip()` replaces "first regex suffix match in zip order" with an explicit resolution rule:

1. **Exact path match** — if the requested name exactly matches a member path, use it.
2. **Suffix match** — otherwise, find all members whose path ends with the requested name.
3. **0 suffix matches** → not found.
4. **1 suffix match** → use it.
5. **Multiple suffix matches** → ambiguous. Log a warning, count an error. Do not silently pick one.

This makes ambiguity visible instead of silently extracting the wrong file.

### 3. ZipArchiveReader helper

A reader object encapsulates the zip path, cached archive members, and error counter. Platform code uses it instead of calling `extract_file_from_zip` directly.

```python
# extraction_helpers.py
class ZipArchiveReader:
    """Reads files from a zip archive using cached member inventory.

    Encapsulates the zip path, archive member list (from validation),
    and error counter. Provides json() and csv() methods that combine
    extraction + parsing + found/not-found signaling.
    """

    def __init__(self, zip_path: str, archive_members: list[str], errors: Counter):
        self.zip_path = zip_path
        self.archive_members = archive_members
        self.errors = errors

    def resolve_member(self, filename: str) -> str | None:
        """Resolve a filename to an archive member path.

        Resolution rule:
        1. Exact path match → use it.
        2. Suffix matches → if exactly 1, use it.
        3. 0 suffix matches → return None (not found).
        4. Multiple suffix matches → return None, log warning,
           increment errors["AmbiguousMemberMatch"].
        """
        ...

    def json(self, filename: str) -> JsonExtractionResult:
        """Extract and parse a JSON file.

        Returns JsonExtractionResult(found=False, data={}) if member
        not in archive. Skips read_json_from_bytes entirely when not found.
        """
        ...

    def json_all(self, pattern: str) -> list[JsonExtractionResult]:
        """Extract and parse all JSON files matching a regex pattern.

        Used for paginated exports (post_comments_1.json, _2.json, etc.)
        and multi-file patterns. Returns a list of results for each
        matching member. Empty list if no matches.
        """
        ...

    def csv(self, filename: str) -> CsvExtractionResult:
        """Extract and parse a CSV file.

        Returns CsvExtractionResult(found=False, data=pd.DataFrame())
        if member not in archive.
        """
        ...

    def raw(self, filename: str) -> RawExtractionResult:
        """Extract raw bytes.

        Returns RawExtractionResult(found=False, data=io.BytesIO())
        if member not in archive. Used for HTML (Chrome bookmarks),
        text files (WhatsApp), and .js files (X platform — caller
        applies bytesio_to_listdict for JS prefix stripping).
        """
        ...
```

### 4. Extraction result types

```python
@dataclass
class JsonExtractionResult:
    found: bool
    data: dict | list   # {} when not found
    member_path: str | None = None

@dataclass
class CsvExtractionResult:
    found: bool
    data: pd.DataFrame  # empty DataFrame when not found
    member_path: str | None = None

@dataclass
class RawExtractionResult:
    found: bool
    data: io.BytesIO    # empty BytesIO when not found
    member_path: str | None = None
```

### 5. Platform code pattern

Platform extraction functions create a reader from the validation object:

```python
def extraction(instagram_zip: str, validation: ValidateInput) -> ExtractionResult:
    errors = Counter()
    reader = eh.ZipArchiveReader(instagram_zip, validation.archive_members, errors)

    # Each table extraction becomes:
    result = reader.json("following.json")
    if not result.found:
        # Expected absence — not an error, skip this table
        following_df = pd.DataFrame()
    else:
        # Parse the data
        following_df = _parse_following(result.data, errors)

    ...
```

Per-table helper functions receive parsed data, not zip paths:

```python
def _parse_following(data: dict | list, errors: Counter) -> pd.DataFrame:
    """Parse following data from the JSON structure."""
    out = pd.DataFrame()
    try:
        items = data["relationships_following"]
        ...
    except KeyError as e:
        # This is a REAL error — file existed but had unexpected structure
        logger.error("Exception caught: %s", e)
        errors[type(e).__name__] += 1
    return out
```

### 6. Cascade outcomes

| Scenario | Before (4 errors) | After |
|---|---|---|
| File missing | FileNotFound + JSONDecode×2 + KeyError | 0 errors, table skipped |
| File present, valid JSON | 0 errors | 0 errors |
| File present, malformed JSON | JSONDecode (may count twice due to encoding retries) | JSONDecode counted once per encoding attempt (real error) |
| File present, unexpected schema | KeyError (real) | KeyError (real, counted) |
| Ambiguous filename match | Silently extracts wrong file | Warning + error count, no extraction |

### 7. Malformed JSON counting

The current `_read_json()` tries two encodings (utf8, utf-8-sig) and increments JSONDecodeError for each failure. For a truly malformed file, this produces 2 error counts. This is the correct behavior — each encoding attempt is a real parse failure. The error count reflects what was tried, not what the caller expected.

## extract_data() interface change

Platform `extract_data()` currently receives `(path, validation)`. The validation object now carries `archive_members`. No interface change is needed — platforms access `validation.archive_members` to construct the reader.

However, platforms currently don't use the `validation` parameter in their extraction functions — most pass only the zip path to `extraction()`. The change is:

```python
# Before (current):
def extract_data(self, file_value, validation):
    return extraction(file_value)

# After:
def extract_data(self, file_value, validation):
    return extraction(file_value, validation)
```

And `extraction()` receives validation to build the reader.

## File changes

### Modified files
- `port/helpers/validate.py` — `archive_members` field on `ValidateInput`, stored in `validate_zip()`
- `port/helpers/extraction_helpers.py` — `ZipArchiveReader` class, `JsonExtractionResult`/`CsvExtractionResult`/`RawExtractionResult` dataclasses, new `resolve_member()` logic
- `port/platforms/instagram.py` — use `ZipArchiveReader`, refactor per-table functions to receive parsed data
- `port/platforms/facebook.py` — same
- `port/platforms/tiktok.py` — uses `_load_user_data` (single JSON load), minimal change
- `port/platforms/youtube.py` — same pattern
- `port/platforms/linkedin.py` — CSV-based, uses `reader.csv()`
- `port/platforms/netflix.py` — CSV-based, uses `reader.csv()`
- `port/platforms/chatgpt.py` — same pattern
- `port/platforms/whatsapp.py` — unique parsing, uses `reader.raw()` for text files
- `port/platforms/x.py` — JS files (JSON with prefix), may need `reader.raw()` + custom parsing
- `port/platforms/chrome.py` — JSON + HTML, uses both `reader.json()` and `reader.raw()`

### New tests
- `ZipArchiveReader.resolve_member()` — exact match, single suffix match, no match, ambiguous match
- `ZipArchiveReader.json()` — found, not found, malformed
- `ZipArchiveReader.csv()` — found, not found
- `ValidateInput.archive_members` populated by `validate_zip()`
- `ValidateInput.__repr__` excludes `archive_members`
- End-to-end: extraction with missing files produces 0 errors for absent files

### Unchanged
- `port/helpers/flow_builder.py` — unchanged
- `port/main.py` — unchanged
- `port/script.py` — unchanged
- `port/api/` — unchanged

## Backward compatibility

`extract_file_from_zip()` retains its current signature and behavior when `archive_members` is not provided. The new `ZipArchiveReader` is additive — old code continues to work. Migration to the reader is per-platform, not all-or-nothing.

## Security

- `archive_members` contains full zip member paths which may include PII (contact names in Facebook directory structure)
- `repr=False` prevents accidental logging of the field via `ValidateInput.__repr__()`
- The field is internal-only — never included in host milestones (AD0011), donation payloads, or bridge logs
- The content_logger (non-propagating) already handles path logging during validation

## Design principles

1. **Validation discovers, helper resolves, platform parses** — each layer has one job
2. **Expected absence is not an error** — missing files produce 0 errors
3. **Ambiguity is visible** — multiple suffix matches are flagged, not silently resolved
4. **The reader hides plumbing** — platforms write table parsing logic, not zip mechanics
5. **Backward compatible** — old code still works, migration is incremental
