---
adr_id: "0003"
comments:
    - author: Danielle McCool
      comment: "1"
      date: "2026-03-13 13:33:16"
links:
    precedes: []
    succeeds:
        - "0001"
status: accepted
date: 2026-03-13
tags:
    - ui-construction
    - helpers
    - script
title: All UI page construction through port_helpers
---

## <a name="question"></a> Context and Problem Statement

PropsUI* objects can be constructed anywhere in the Python code. With 7 platforms and multiple flow types, page construction is being duplicated. Should script.py and platform flows construct pages directly from PropsUI* objects, or should all page construction go through helper functions?

## <a name="options"></a> Considered Options
1. <a name="option-1"></a> Construct PropsUI* objects wherever needed — no restriction
2. <a name="option-2"></a> Centralize all page construction in port_helpers.py as generate_*() functions
3. <a name="option-3"></a> Use builder classes with a fluent interface

## <a name="criteria"></a> Decision Drivers

* With 7 platforms, direct PropsUI* construction would be duplicated across every platform's flow
* script.py should describe the study flow at a high level ("what"), not concern itself with prop assembly ("how")
* A single location for page construction makes it easy to audit, fix, or extend all pages at once

## <a name="outcome"></a> Decision Outcome
We decided for [Option 2](#option-2) because: Centralizing page construction in port_helpers.py separates what-to-show (script.py, flow logic) from how-to-build-it (port_helpers), prevents duplicated page construction across 7 platforms, and creates a single place to audit and fix page structure.

### Consequences

* Good: script.py reads as a high-level description of the study flow
* Good: All page variants are visible in one file — easy to audit consistency across platforms
* Bad: port_helpers.py can become a "dumping ground" if the rule is applied without discipline to organising the helpers

### Confirmation

Code review: any `PropsUIPrompt*()` or `PropsUIPage()` constructor call in `script.py` or platform files is a violation. These should only appear in `port_helpers.py`.

### Evidence of violation

The `feat/facebook-ddp-error-handling` branch's `donation_failed_flow()` constructs 3 pages from raw `PropsUIPromptText`, `PropsUIPromptTextArea`, and `PropsUIDataSubmissionButtons` directly in `script.py`.

## More Information

See [extraction/AD0001](../extraction/AD0001-flowbuilder-template-for-per-platform-extraction-flows.md) — FlowBuilder lives in helpers/ and uses port_helpers for page construction.

## <a name="comments"></a> Comments
<a name="comment-1"></a>1. (2026-03-13 13:33:16) Danielle McCool: marked decision as decided
