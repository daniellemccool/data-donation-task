---
adr_id: "0006"
comments:
    - author: Danielle McCool
      comment: "1"
      date: "2026-03-20 15:29:51"
links:
    precedes: []
    succeeds: []
status: open
tags:
    - extraction-helpers
    - ddp-compatibility
    - error-handling
title: Handle expected-missing DDP files without error cascades
---

## <a name="question"></a> Context and Problem Statement

extract_file_from_zip() treats a missing file as an exception — logging an error and returning empty bytes. Downstream helpers then try to parse the empty bytes (2 more errors) and platform code catches the empty result (1 more error). This produces 4 error log lines per missing file. For platforms like Facebook where DDPs vary by version — language — and download options — dozens of files are routinely absent. A single Facebook extraction produces 31K lines of diagnostic noise in the browser console and 559+ TimestampParseError counts. How should extraction helpers distinguish expected-missing files from actual errors?

## <a name="options"></a> Considered Options
1. <a name="option-1"></a> Return a sentinel from extract_file_from_zip for missing files — callers skip without cascading
2. <a name="option-2"></a> Pre-filter DDP_CATEGORIES against the zip namelist before extraction
3. <a name="option-3"></a> Keep current behavior but downgrade missing-file logs to DEBUG

## <a name="criteria"></a> Decision Drivers
DDPs vary across platform versions — languages — and download time ranges — many files in DDP_CATEGORIES will not be present in any given DDP
The current cascade (FileNotFound → empty BytesIO → JSONDecodeError × 2 → KeyError) produces ~4 error lines per missing file
Error counts in ExtractionResult become inflated with expected absences — making real errors hard to spot
Facebook 3-year DDP produced 31K lines of Pyodide stderr and 559 TimestampParseError counts
Researchers configuring which tables to extract need to know which files actually failed vs which were simply absent
### Pros and Cons

**Return a sentinel from extract_file_from_zip for missing files — callers skip without cascading**
* Good, because eliminates the cascade at the source
* Good, because callers can distinguish missing from corrupt
* Neutral, because requires updating all platform extraction functions to check the sentinel

**Pre-filter DDP_CATEGORIES against the zip namelist before extraction**
* Good, because only attempts extraction on files known to exist
* Good, because eliminates all missing-file errors at once
* Neutral, because requires a new step between validation and extraction

**Keep current behavior but downgrade missing-file logs to DEBUG**
* Good, because minimal code change
* Bad, because the cascade still happens — just quieter
* Bad, because error counts remain inflated


## <a name="comments"></a> Comments
<a name="comment-1"></a>1. (2026-03-20 15:29:51) Danielle McCool: Evidence from ddt11.log (2026-03-20 testing on Eyra mono): Facebook 755MB DDP produced 23 tables and 20159 rows but also 31K lines of Pyodide stderr from the error cascade. Error counts: JSONDecodeError×10 KeyError×3 TimestampParseError×559. The 559 timestamp errors are from epoch_to_iso receiving empty strings — these originate from rows extracted from files that DO exist but have empty timestamp fields. The JSONDecodeError×10 and KeyError×3 are from the missing-file cascade: extract_file_from_zip returns empty BytesIO → read_json_from_bytes tries utf8 then utf-8-sig (2 errors) → platform catches empty result (1 error). Instagram 1.2MB DDP: only 1 table extracted out of 9 possible with 28 errors (TimestampParseError×7 JSONDecodeError×14 KeyError×6 TypeError×1). The cascade pattern is in extraction_helpers.py:extract_file_from_zip (returns empty BytesIO on FileNotFoundInZipError) → _read_json (tries multiple encodings on empty bytes) → platform extraction function (catches KeyError on empty dict). Each platform defines DDP_CATEGORIES with known_files that represent ALL possible files across ALL versions and languages of a platform export. A real DDP will only contain a subset. The pre-filter approach (Option 2) would let FlowBuilder check which DDP_CATEGORIES files actually exist in the zip before calling extract_data — platforms would only attempt extraction on files known to be present.
