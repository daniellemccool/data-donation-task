---
adr_id: "0001"
comments:
    - author: Danielle McCool
      comment: "1"
      date: "2026-03-13 13:33:16"
links:
    precedes:
        - "0002"
        - "0003"
    succeeds:
        - "0005"
status: accepted
date: 2026-03-13
tags:
    - layering
    - structure
    - imports
title: Layered Python architecture with unidirectional dependencies
---

## <a name="question"></a> Context and Problem Statement

Eyra's Python package is flat: api/, script.py, main.py. This fork has grown to 7 platforms, shared utilities (FlowBuilder, validation), and custom props. The flat structure makes dependency management and testing increasingly difficult. How should the Python package be organized?

## <a name="options"></a> Considered Options
1. <a name="option-1"></a> Keep the flat structure inherited from upstream
2. <a name="option-2"></a> Layer by responsibility with strict unidirectional imports
3. <a name="option-3"></a> Domain-driven organization with one directory per platform

## <a name="criteria"></a> Decision Drivers

* 7 platforms share validation logic, FlowBuilder, and UI construction helpers — a flat structure duplicates these or creates undisciplined cross-imports
* Import direction in a flat package is unenforceable; layers make it auditable
* Per-platform domain directories would prevent sharing helpers across platforms

## <a name="outcome"></a> Decision Outcome
We decided for [Option 2](#option-2) because: Layering by responsibility (api → helpers → platforms/script.py) gives each layer a clear purpose and makes dependency direction enforceable; domain-driven per-platform directories would duplicate shared logic across 7 platforms.

### Consequences

* Good: Each layer has a clear purpose; a new helper that doesn't belong in api/ clearly belongs in helpers/
* Good: Dependency direction is auditable — any upward import (helpers → script.py) is an error
* Bad: Upstream feldspar's flat api/ structure must be reconciled when pulling upstream changes

### Layer definitions

```
port/
  api/        — Protocol types and file utilities; imports only stdlib/third-party. Mirrors upstream.
  helpers/    — Shared logic (FlowBuilder, validation, port_helpers); imports only api/.
  platforms/  — Per-platform extractors; imports helpers/ and api/.
  script.py   — Orchestrator; imports helpers/, api/, calls platforms.
  main.py     — Entry point; imports script.py.
```

## More Information

See [fork-governance/AD0004](../fork-governance/AD0004-three-package-monorepo-with-distinct-modification-policies.md) for the monorepo structure that makes Python its own package.

## <a name="comments"></a> Comments
<a name="comment-1"></a>1. (2026-03-13 13:33:16) Danielle McCool: marked decision as decided
