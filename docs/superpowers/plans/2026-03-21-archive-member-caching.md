# Archive Member Caching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate cascading errors for expected-missing DDP files by caching the archive member list during validation and providing a ZipArchiveReader helper with found/not-found signaling.

**Architecture:** `ValidateInput` stores the full zip namelist during validation. `ZipArchiveReader` in extraction_helpers provides `json()`, `json_all()`, `csv()`, `raw()` methods with result types that signal found/not-found. Platform extraction functions use the reader instead of calling `extract_file_from_zip` directly. Missing files produce 0 errors.

**Tech Stack:** Python 3.11+, pytest, zipfile, dataclasses, Counter

---

## File Structure

### New types in existing files
| Location | What |
|---|---|
| `port/helpers/validate.py` | `archive_members` field on `ValidateInput` |
| `port/helpers/extraction_helpers.py` | `ZipArchiveReader` class, `JsonExtractionResult`, `CsvExtractionResult`, `RawExtractionResult` dataclasses |

### Modified files
| File | Changes |
|---|---|
| `port/helpers/validate.py` | Add `archive_members` field, store namelist in `validate_zip()` |
| `port/helpers/extraction_helpers.py` | Add reader class + result types, add empty-bytes guard to `read_json_from_bytes` |
| `port/platforms/instagram.py` | Use `ZipArchiveReader`, skip absent files |
| `port/platforms/facebook.py` | Same |
| `port/platforms/youtube.py` | Same |
| `port/platforms/linkedin.py` | Same (CSV-based) |
| `port/platforms/netflix.py` | Same (CSV-based) |
| `port/platforms/chatgpt.py` | Same |
| `port/platforms/chrome.py` | Same (JSON + HTML) |
| `port/platforms/tiktok.py` | Minimal — single JSON load |
| `port/platforms/x.py` | Same (JS files via raw()) |
| `port/platforms/whatsapp.py` | No change — doesn't use extract_file_from_zip (spec lists it as modified but grep confirms 0 calls) |

### Test files
| File | What |
|---|---|
| `tests/test_zip_archive_reader.py` | Reader tests: resolve_member, json, csv, raw, json_all, ambiguous matches |
| `tests/test_validate.py` | archive_members population, repr exclusion |

---

## Task 1: Add archive_members to ValidateInput and validate_zip (TDD)

**Files:**
- Modify: `packages/python/port/helpers/validate.py`
- Create: `packages/python/tests/test_validate.py`

- [ ] **Step 1: Write failing tests**

Create `packages/python/tests/test_validate.py`:

```python
"""Tests for ValidateInput archive_members caching."""
import sys
import zipfile
from unittest.mock import MagicMock

sys.modules["js"] = MagicMock()

from port.helpers.validate import ValidateInput, validate_zip, DDPCategory, DDPFiletype, Language, StatusCode


class TestArchiveMembers:
    def test_validate_zip_populates_archive_members(self, tmp_path):
        """validate_zip stores full member paths on ValidateInput."""
        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("data/following.json", '{}')
            zf.writestr("data/posts.json", '{}')

        categories = [DDPCategory(
            id="test", ddp_filetype=DDPFiletype.JSON,
            language=Language.EN, known_files=["following.json", "posts.json"]
        )]
        result = validate_zip(categories, str(zip_path))
        assert "data/following.json" in result.archive_members
        assert "data/posts.json" in result.archive_members

    def test_archive_members_excluded_from_repr(self, tmp_path):
        """archive_members must not appear in repr (PII safety)."""
        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("messages/inbox/contact_name_123/photo.jpg", b"")
            zf.writestr("following.json", '{}')

        categories = [DDPCategory(
            id="test", ddp_filetype=DDPFiletype.JSON,
            language=Language.EN, known_files=["following.json"]
        )]
        result = validate_zip(categories, str(zip_path))
        assert "contact_name_123" not in repr(result)

    def test_archive_members_empty_on_bad_zip(self, tmp_path):
        """archive_members stays empty if zip is invalid."""
        bad_path = tmp_path / "bad.zip"
        bad_path.write_bytes(b"not a zip")

        categories = [DDPCategory(
            id="test", ddp_filetype=DDPFiletype.JSON,
            language=Language.EN, known_files=["file.json"]
        )]
        result = validate_zip(categories, str(bad_path))
        assert result.archive_members == []

    def test_archive_members_default_empty(self):
        """archive_members defaults to empty list."""
        status_codes = [StatusCode(id=0, description="OK")]
        categories = [DDPCategory(
            id="test", ddp_filetype=DDPFiletype.JSON,
            language=Language.EN, known_files=["file.json"]
        )]
        v = ValidateInput(status_codes, categories)
        assert v.archive_members == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/python && poetry run pytest tests/test_validate.py -v`
Expected: FAIL — `archive_members` not on `ValidateInput`

- [ ] **Step 3: Implement**

In `validate.py`, add field to `ValidateInput`:
```python
    # Full zip member paths cached during validation. Internal only —
    # must not appear in logs, host milestones, or donation payloads.
    archive_members: list[str] = field(default_factory=list, repr=False)
```

In `validate_zip()`, store the namelist:
```python
    try:
        paths = []
        with zipfile.ZipFile(path_to_zip, "r") as zf:
            all_members = zf.namelist()
            for f in all_members:
                p = Path(f)
                content_logger.debug("Found: %s in zip", p.name)
                paths.append(p.name)
            validate.archive_members = all_members
        validate.infer_ddp_category(paths)
    except zipfile.BadZipFile:
        validate.set_current_status_code_by_id(1)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/python && poetry run pytest tests/test_validate.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Run all tests**

Run: `pnpm test`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add packages/python/port/helpers/validate.py packages/python/tests/test_validate.py
git commit -m "feat: cache archive_members on ValidateInput during validation"
```

---

## Task 2: Implement ZipArchiveReader with result types (TDD)

**Files:**
- Modify: `packages/python/port/helpers/extraction_helpers.py`
- Create: `packages/python/tests/test_zip_archive_reader.py`

- [ ] **Step 1: Write failing tests**

Create `packages/python/tests/test_zip_archive_reader.py`:

```python
"""Tests for ZipArchiveReader — member resolution, extraction, result types."""
import sys
import io
import json
import zipfile
from collections import Counter
from unittest.mock import MagicMock

sys.modules["js"] = MagicMock()

import pytest
import pandas as pd
from port.helpers.extraction_helpers import (
    ZipArchiveReader,
    JsonExtractionResult,
    CsvExtractionResult,
    RawExtractionResult,
)


@pytest.fixture
def sample_zip(tmp_path):
    """Create a zip with known structure for testing."""
    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("data/following.json", json.dumps({"relationships_following": []}))
        zf.writestr("data/nested/following.json", json.dumps({"other": "data"}))
        zf.writestr("data/foo_following.json", json.dumps({"wrong": "file"}))
        zf.writestr("ratings.csv", "Title,Rating\nMovie A,5\nMovie B,3\n")
        zf.writestr("Bookmarks.html", "<html><body><a href='http://example.com'>Example</a></body></html>")
        zf.writestr("post_comments_1.json", json.dumps([{"comment": "one"}]))
        zf.writestr("post_comments_2.json", json.dumps([{"comment": "two"}]))
    members = [
        "data/following.json", "data/nested/following.json",
        "data/foo_following.json", "ratings.csv", "Bookmarks.html",
        "post_comments_1.json", "post_comments_2.json",
    ]
    return str(zip_path), members


class TestResolveMember:
    def test_exact_match(self, sample_zip):
        path, members = sample_zip
        reader = ZipArchiveReader(path, members, Counter())
        assert reader.resolve_member("data/following.json") == "data/following.json"

    def test_suffix_match_unique(self, sample_zip):
        path, members = sample_zip
        reader = ZipArchiveReader(path, members, Counter())
        assert reader.resolve_member("ratings.csv") == "ratings.csv"

    def test_suffix_match_path_boundary(self, sample_zip):
        """foo_following.json must NOT match following.json."""
        path, members = sample_zip
        # Remove the nested match to isolate the path-boundary test
        filtered = [m for m in members if m != "data/nested/following.json"]
        reader = ZipArchiveReader(path, filtered, Counter())
        result = reader.resolve_member("following.json")
        assert result == "data/following.json"
        # foo_following.json should NOT have matched

    def test_no_match_returns_none(self, sample_zip):
        path, members = sample_zip
        reader = ZipArchiveReader(path, members, Counter())
        assert reader.resolve_member("nonexistent.json") is None

    def test_ambiguous_match_returns_none_and_counts_error(self, sample_zip):
        """Multiple path-boundary matches → None + AmbiguousMemberMatch."""
        path, members = sample_zip
        errors = Counter()
        reader = ZipArchiveReader(path, members, errors)
        # "following.json" matches both data/following.json and data/nested/following.json
        result = reader.resolve_member("following.json")
        assert result is None
        assert errors["AmbiguousMemberMatch"] == 1

    def test_exact_match_wins_over_suffix(self, tmp_path):
        """When a file exists at top level AND nested, exact match wins."""
        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("ratings.csv", "a,b\n1,2\n")
            zf.writestr("data/ratings.csv", "c,d\n3,4\n")
        members = ["ratings.csv", "data/ratings.csv"]
        reader = ZipArchiveReader(str(zip_path), members, Counter())
        assert reader.resolve_member("ratings.csv") == "ratings.csv"


class TestJsonExtraction:
    def test_found(self, sample_zip):
        path, members = sample_zip
        reader = ZipArchiveReader(path, members, Counter())
        result = reader.json("data/following.json")
        assert result.found is True
        assert result.data == {"relationships_following": []}
        assert result.member_path == "data/following.json"

    def test_not_found(self, sample_zip):
        path, members = sample_zip
        errors = Counter()
        reader = ZipArchiveReader(path, errors=errors, archive_members=members)
        result = reader.json("nonexistent.json")
        assert result.found is False
        assert result.data == {}
        assert result.member_path is None
        assert errors.get("FileNotFoundInZipError", 0) == 0  # NOT an error

    def test_malformed_json(self, tmp_path):
        zip_path = tmp_path / "bad.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("bad.json", "not valid json {{{")
        errors = Counter()
        reader = ZipArchiveReader(str(zip_path), ["bad.json"], errors)
        result = reader.json("bad.json")
        assert result.found is True
        assert result.data == {}
        assert errors["JSONDecodeError"] > 0


class TestCsvExtraction:
    def test_found(self, sample_zip):
        path, members = sample_zip
        reader = ZipArchiveReader(path, members, Counter())
        result = reader.csv("ratings.csv")
        assert result.found is True
        assert isinstance(result.data, pd.DataFrame)
        assert len(result.data) == 2

    def test_not_found(self, sample_zip):
        path, members = sample_zip
        reader = ZipArchiveReader(path, members, Counter())
        result = reader.csv("nonexistent.csv")
        assert result.found is False
        assert result.data.empty


class TestRawExtraction:
    def test_found(self, sample_zip):
        path, members = sample_zip
        reader = ZipArchiveReader(path, members, Counter())
        result = reader.raw("Bookmarks.html")
        assert result.found is True
        assert b"Example" in result.data.read()

    def test_not_found(self, sample_zip):
        path, members = sample_zip
        reader = ZipArchiveReader(path, members, Counter())
        result = reader.raw("nonexistent.html")
        assert result.found is False
        assert result.data.getvalue() == b""


class TestJsonAll:
    def test_matches_multiple(self, sample_zip):
        path, members = sample_zip
        reader = ZipArchiveReader(path, members, Counter())
        results = reader.json_all(r"post_comments_\d+\.json$")
        assert len(results) == 2
        assert all(r.found for r in results)

    def test_sorted_lexicographically(self, sample_zip):
        path, members = sample_zip
        reader = ZipArchiveReader(path, members, Counter())
        results = reader.json_all(r"post_comments_\d+\.json$")
        paths = [r.member_path for r in results]
        assert paths == sorted(paths)

    def test_no_matches(self, sample_zip):
        path, members = sample_zip
        reader = ZipArchiveReader(path, members, Counter())
        results = reader.json_all(r"nonexistent_\d+\.json$")
        assert results == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/python && poetry run pytest tests/test_zip_archive_reader.py -v`
Expected: FAIL — `ZipArchiveReader` does not exist

- [ ] **Step 3: Implement ZipArchiveReader and result types**

Add to `packages/python/port/helpers/extraction_helpers.py` (after existing code):

```python
@dataclass
class JsonExtractionResult:
    """Result of extracting and parsing a JSON file from a zip."""
    found: bool
    data: dict | list  # {} when not found
    member_path: str | None = None

@dataclass
class CsvExtractionResult:
    """Result of extracting and parsing a CSV file from a zip."""
    found: bool
    data: pd.DataFrame  # empty DataFrame when not found
    member_path: str | None = None

@dataclass
class RawExtractionResult:
    """Result of extracting raw bytes from a zip."""
    found: bool
    data: io.BytesIO  # empty BytesIO when not found
    member_path: str | None = None


class ZipArchiveReader:
    """Reads files from a zip archive using cached member inventory.

    Encapsulates the zip path, archive member list (from validation),
    and error counter. Provides json()/csv()/raw() methods with
    found/not-found signaling to eliminate cascading errors for
    expected-missing files.
    """

    def __init__(self, zip_path: str, archive_members: list[str], errors: Counter):
        self.zip_path = zip_path
        self.archive_members = archive_members
        self.errors = errors

    def resolve_member(self, filename: str) -> str | None:
        """Resolve a filename to an archive member path.

        Resolution rule:
        1. Exact path match → use it.
        2. Path-boundary suffix match (member.endswith("/" + filename)) → if exactly 1, use it.
        3. 0 matches → return None.
        4. Multiple matches → return None, log warning, increment errors["AmbiguousMemberMatch"].
        """
        # 1. Exact match
        if filename in self.archive_members:
            return filename

        # 2. Path-boundary suffix match
        matches = [m for m in self.archive_members if m.endswith("/" + filename)]

        if len(matches) == 1:
            return matches[0]
        elif len(matches) == 0:
            return None
        else:
            logger.warning("Ambiguous member match: '%s' matched %d members in archive", filename, len(matches))
            self.errors["AmbiguousMemberMatch"] += 1
            return None

    def _read_member_bytes(self, member_path: str) -> io.BytesIO:
        """Read a specific member from the zip by exact path."""
        try:
            with zipfile.ZipFile(self.zip_path, "r") as zf:
                return io.BytesIO(zf.read(member_path))
        except Exception as e:
            logger.error("Error reading zip member %s: %s", member_path, type(e).__name__)
            self.errors[type(e).__name__] += 1
            return io.BytesIO()

    def json(self, filename: str) -> JsonExtractionResult:
        """Extract and parse a JSON file."""
        member = self.resolve_member(filename)
        if member is None:
            return JsonExtractionResult(found=False, data={})

        b = self._read_member_bytes(member)
        raw = b.read()
        if not raw:
            return JsonExtractionResult(found=True, data={}, member_path=member)

        data = _read_json(raw, _json_reader_bytes, errors=self.errors)
        return JsonExtractionResult(found=True, data=data, member_path=member)

    def json_all(self, pattern: str) -> list[JsonExtractionResult]:
        """Extract and parse all JSON files matching a regex pattern.

        Returns results sorted lexicographically by member path.
        """
        matches = sorted(m for m in self.archive_members if re.search(pattern, m))
        results = []
        for member in matches:
            b = self._read_member_bytes(member)
            raw = b.read()
            if not raw:
                results.append(JsonExtractionResult(found=True, data={}, member_path=member))
                continue
            data = _read_json(raw, _json_reader_bytes, errors=self.errors)
            results.append(JsonExtractionResult(found=True, data=data, member_path=member))
        return results

    def csv(self, filename: str) -> CsvExtractionResult:
        """Extract and parse a CSV file."""
        member = self.resolve_member(filename)
        if member is None:
            return CsvExtractionResult(found=False, data=pd.DataFrame())

        b = self._read_member_bytes(member)
        if not b.getvalue():
            return CsvExtractionResult(found=True, data=pd.DataFrame(), member_path=member)

        df = read_csv_from_bytes_to_df(b)
        return CsvExtractionResult(found=True, data=df, member_path=member)

    def raw(self, filename: str) -> RawExtractionResult:
        """Extract raw bytes from a zip member."""
        member = self.resolve_member(filename)
        if member is None:
            return RawExtractionResult(found=False, data=io.BytesIO())

        b = self._read_member_bytes(member)
        return RawExtractionResult(found=True, data=b, member_path=member)
```

Add `from dataclasses import dataclass` to imports if not already present.

**Also add empty-bytes guard to `read_json_from_bytes`** as a defensive improvement for any remaining direct callers during transition:

```python
def read_json_from_bytes(json_bytes: io.BytesIO, errors: Counter | None = None) -> dict[Any, Any] | list[Any]:
    out: dict[Any, Any] | list[Any] = {}
    try:
        b = json_bytes.read()
        if not b:
            return out  # empty bytes → empty result, no parse attempt
        out = _read_json(b, _json_reader_bytes, errors=errors)
    ...
```

**Note:** `ZipArchiveReader.json()` calls `_read_json()` directly (bypassing `read_json_from_bytes`) for efficiency — it already has raw bytes, not a BytesIO wrapper. `_read_json`'s docstring says "should not be used directly" but this is intentional reuse within the same module. Update the docstring to reflect its dual-use status.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/python && poetry run pytest tests/test_zip_archive_reader.py -v`
Expected: All tests PASS

- [ ] **Step 5: Run all tests + Pyright**

Run: `pnpm test && cd packages/python && npx pyright port/helpers/extraction_helpers.py`
Expected: All tests PASS, 0 Pyright errors

- [ ] **Step 6: Commit**

```bash
git add packages/python/port/helpers/extraction_helpers.py packages/python/tests/test_zip_archive_reader.py
git commit -m "feat: add ZipArchiveReader with result types and deterministic member resolution"
```

---

## Task 3: Migrate Instagram to ZipArchiveReader

**Files:**
- Modify: `packages/python/port/platforms/instagram.py`

This is the most complex platform (12 tables, multi-file patterns). The pattern established here applies to all other platforms.

- [ ] **Step 1: Update extraction() signature and create reader**

Change `extraction(instagram_zip: str)` to `extraction(instagram_zip: str, validation)` and create the reader:

```python
def extraction(instagram_zip: str, validation) -> ExtractionResult:
    errors = Counter()
    reader = eh.ZipArchiveReader(instagram_zip, validation.archive_members, errors)
```

Update `extract_data()`:
```python
def extract_data(self, file_value, validation):
    return extraction(file_value, validation)
```

- [ ] **Step 2: Convert per-table extraction functions**

For each table builder function, replace the `eh.extract_file_from_zip` + `eh.read_json_from_bytes` pattern with `reader.json()`. Example for `followers_to_df`:

Before:
```python
def followers_to_df(instagram_zip: str, errors: Counter) -> pd.DataFrame:
    b = eh.extract_file_from_zip(instagram_zip, "followers_1.json", errors=errors)
    data = eh.read_json_from_bytes(b, errors=errors)
    ...
```

After:
```python
def followers_to_df(reader: eh.ZipArchiveReader, errors: Counter) -> pd.DataFrame:
    result = reader.json("followers_1.json")
    if not result.found:
        return pd.DataFrame()
    data = result.data
    ...
```

Apply this pattern to ALL per-table functions. For `post_comments_to_df`, use `reader.json_all()`:

```python
def post_comments_to_df(reader: eh.ZipArchiveReader, errors: Counter) -> pd.DataFrame:
    results = reader.json_all(r"(^|/)post_comments(?:_\d+)?\.json$")
    if not results:
        return pd.DataFrame()
    datapoints = []
    for result in results:
        ...  # parse each result.data
```

- [ ] **Step 3: Update extraction() table list to pass reader**

Change all calls from `followers_to_df(instagram_zip, errors)` to `followers_to_df(reader, errors)`.

- [ ] **Step 4: Run tests + Pyright**

Run: `pnpm test && cd packages/python && npx pyright port/platforms/instagram.py`
Expected: All tests PASS, 0 Pyright errors

- [ ] **Step 5: Commit**

```bash
git add packages/python/port/platforms/instagram.py
git commit -m "feat: migrate Instagram to ZipArchiveReader — 0 errors for missing files"
```

---

## Task 4: Migrate Facebook to ZipArchiveReader

**Files:**
- Modify: `packages/python/port/platforms/facebook.py`

Same pattern as Instagram. Facebook has 29 `extract_file_from_zip` calls and paginated files (likes_and_reactions_1.json, _2.json).

- [ ] **Step 1: Update extraction() and per-table functions**

Same pattern as Task 3. For paginated files like `likes_and_reactions_to_df`, use `reader.json_all()`.

Note: Some Facebook extractions use partial paths (e.g. `"facebook_news/your_locations.json"`, `"notifications/notifications.json"`, `"logged_information/search/your_search_history.json"`, `"preferences/feed/controls.json"`, `"comments_and_reactions/comments.json"`). These are exact-ish paths that will match via the suffix rule. Verify they resolve correctly.

- [ ] **Step 2: Run tests + Pyright**

Run: `pnpm test && cd packages/python && npx pyright port/platforms/facebook.py`
Expected: All tests PASS, 0 Pyright errors

- [ ] **Step 3: Commit**

```bash
git add packages/python/port/platforms/facebook.py
git commit -m "feat: migrate Facebook to ZipArchiveReader — 0 errors for missing files"
```

---

## Task 5: Migrate remaining JSON-based platforms

**Files:**
- Modify: `packages/python/port/platforms/chatgpt.py` (1 extract call)
- Modify: `packages/python/port/platforms/chrome.py` (3 extract calls + HTML)
- Modify: `packages/python/port/platforms/tiktok.py` (1 extract call via _load_user_data)

Same pattern. Chrome uses `reader.raw()` for `Bookmarks.html`. TikTok's `_load_user_data` tries two filenames — use `reader.json()` for each and take the first found.

- [ ] **Step 1: Update all three platforms**

- [ ] **Step 2: Run tests + Pyright**

Run: `pnpm test && cd packages/python && npx pyright port/platforms/chatgpt.py port/platforms/chrome.py port/platforms/tiktok.py`
Expected: All tests PASS, 0 Pyright errors

- [ ] **Step 3: Commit**

```bash
git add packages/python/port/platforms/chatgpt.py packages/python/port/platforms/chrome.py packages/python/port/platforms/tiktok.py
git commit -m "feat: migrate ChatGPT, Chrome, TikTok to ZipArchiveReader"
```

---

## Task 6: Migrate CSV-based platforms (LinkedIn, Netflix)

**Files:**
- Modify: `packages/python/port/platforms/linkedin.py` (8 extract calls, all CSV)
- Modify: `packages/python/port/platforms/netflix.py` (3 extract calls, CSV)

LinkedIn uses `reader.csv()`. Netflix needs the reader passed through `extraction()` → `netflix_to_df()` → `keep_user()`. Netflix's `extract_users()` also needs the reader (or its own zip read for Profiles.csv).

- [ ] **Step 1: Update LinkedIn**

LinkedIn's `strip_notes()` helper processes raw CSV bytes before parsing. Use `reader.raw()` → `strip_notes()` → `read_csv_from_bytes_to_df()` for files that need note stripping (Connections.csv).

- [ ] **Step 2: Update Netflix**

Netflix has a multi-step flow in `extract_data()`: `extract_users()` → optional UI yield → `extraction()`. Both need the reader.

Update `extract_users` to accept a reader:
```python
def extract_users(reader: eh.ZipArchiveReader) -> list[str]:
    """Extract all profile names from Profiles.csv."""
    result = reader.csv("Profiles.csv")
    if not result.found:
        # Fallback to ViewingActivity.csv
        result = reader.csv("ViewingActivity.csv")
    ...
```

Update `netflix_to_df` to use the reader:
```python
def netflix_to_df(reader: eh.ZipArchiveReader, file_name: str, selected_user: str) -> pd.DataFrame:
    result = reader.csv(file_name)
    if not result.found:
        return pd.DataFrame()
    return keep_user(result.data, selected_user)
```

Update `extraction()` signature:
```python
def extraction(reader: eh.ZipArchiveReader, selected_user: str) -> ExtractionResult:
```

Update `extract_data()`:
```python
def extract_data(self, file, validation):
    reader = eh.ZipArchiveReader(file, validation.archive_members, Counter())
    users = extract_users(reader)
    if len(users) == 1:
        return extraction(reader, users[0])
    elif len(users) > 1:
        ...  # UI prompt, then:
        return extraction(reader, selected_user)
```

- [ ] **Step 3: Run tests + Pyright**

Run: `pnpm test && cd packages/python && npx pyright port/platforms/linkedin.py port/platforms/netflix.py`
Expected: All tests PASS, 0 Pyright errors

- [ ] **Step 4: Commit**

```bash
git add packages/python/port/platforms/linkedin.py packages/python/port/platforms/netflix.py
git commit -m "feat: migrate LinkedIn, Netflix to ZipArchiveReader"
```

---

## Task 7: Migrate X platform (JS files)

**Files:**
- Modify: `packages/python/port/platforms/x.py` (10 extract calls)

X uses `.js` files with a JS variable prefix. The existing `bytesio_to_listdict()` function handles this. Use `reader.raw()` → `bytesio_to_listdict()`.

- [ ] **Step 1: Update X**

Replace `eh.extract_file_from_zip(x_zip, "filename.js", errors=errors)` with `reader.raw("filename.js")`, check `result.found`, then pass `result.data` to `bytesio_to_listdict()`.

- [ ] **Step 2: Run tests + Pyright**

Run: `pnpm test && cd packages/python && npx pyright port/platforms/x.py`
Expected: All tests PASS, 0 Pyright errors

- [ ] **Step 3: Commit**

```bash
git add packages/python/port/platforms/x.py
git commit -m "feat: migrate X platform to ZipArchiveReader"
```

---

## Task 8: YouTube (already receives validation)

**Files:**
- Modify: `packages/python/port/platforms/youtube.py` (6 extract calls)

YouTube's `extraction()` already receives `validation`. Convert to reader.

- [ ] **Step 1: Update YouTube**

YouTube uses different filenames for EN vs NL DDPs. The reader's suffix matching handles this — just try the EN name first, then NL.

- [ ] **Step 2: Run tests + Pyright**

Run: `pnpm test && cd packages/python && npx pyright port/platforms/youtube.py`
Expected: All tests PASS, 0 Pyright errors

- [ ] **Step 3: Commit**

```bash
git add packages/python/port/platforms/youtube.py
git commit -m "feat: migrate YouTube to ZipArchiveReader"
```

---

## Task 9: Final verification

- [ ] **Step 1: Run full test suite**

Run: `pnpm test`
Expected: All tests PASS

- [ ] **Step 2: Run Pyright on all files**

Run: `cd packages/python && npx pyright port/platforms/*.py port/helpers/*.py port/api/*.py port/main.py port/script.py`
Expected: 0 errors

- [ ] **Step 3: Verify no remaining direct extract_file_from_zip calls in platforms**

```bash
grep -rn "eh\.extract_file_from_zip" port/platforms/ --include="*.py"
```
Expected: 0 matches (all migrated to reader)

- [ ] **Step 4: Verify WhatsApp unchanged**

WhatsApp doesn't use `extract_file_from_zip` — confirm it's untouched.

- [ ] **Step 5: Manual test with Facebook DDP**

Build and run locally, upload a Facebook DDP. Verify:
- Tables that exist in the DDP show data
- Missing tables are silently skipped (no error cascade in console)
- Extraction summary in bridge milestone shows real errors only
