---
adr_id: "0003"
comments:
    - author: Danielle McCool
      comment: "1"
      date: "2026-03-13 13:41:56"
links:
    precedes: []
    succeeds: []
status: accepted
date: 2026-03-13
tags:
    - column-naming
    - consent-ui
    - dutch
title: Dutch column names in consent UI
---

## <a name="question"></a> Context and Problem Statement

DataFrame column headers are shown directly to participants in the consent UI, without passing through any translation layer. The study participants are Dutch speakers. What language should column names use?

## <a name="options"></a> Considered Options
1. <a name="option-1"></a> English column names throughout
2. <a name="option-2"></a> Dutch column names throughout
3. <a name="option-3"></a> Bilingual via Translatable wrapper

## <a name="criteria"></a> Decision Drivers

* The consent UI renders DataFrame column names verbatim — there is no interpolated translation step
* Study participants are Dutch speakers; English column names would be opaque to them
* `Translatable` is designed for UI strings, not DataFrame column headers; adapting it would add complexity without generalizable benefit

## <a name="outcome"></a> Decision Outcome
We decided for [Option 2](#option-2) because: Columns are rendered directly as DataFrame column names without a translation infrastructure, so Dutch is required for participant comprehension; Translatable wrapping would require framework changes not justified for column headers alone.

### Consequences

* Good: Column headers are immediately readable to participants without any additional rendering layer
* Good: Each platform's `*_to_df()` extractor is the single place where column naming is controlled — consistent, auditable
* Bad: This is a study-specific policy; any future study with non-Dutch participants would need a different approach
* Bad: English-named source fields must be renamed via `.rename(columns={...})` — cannot use source field names directly

### Confirmation

Code review: any `pd.DataFrame(columns=[...])` or similar construction using English column names that will appear in the consent UI is a violation. Always check for a subsequent `.rename(columns={...})` call — the policy applies to the final column names shown, not intermediate ones.

## <a name="comments"></a> Comments
<a name="comment-1"></a>1. (2026-03-13 13:41:56) Danielle McCool: marked decision as decided
