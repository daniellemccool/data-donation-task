---
adr_id: "0006"
comments:
    - author: Danielle McCool
      comment: "1"
      date: "2026-03-16 17:27:31"
links:
    precedes: []
    succeeds: []
status: open
tags:
    - extraction
    - flowbuilder
    - consolidation
    - donation-flows
title: Consolidate donation_flows and platforms into single extraction architecture
---

## <a name="question"></a> Context and Problem Statement

Two parallel extraction systems exist: donation_flows/ (data-driven entries pattern from what-if — active in script.py) and platforms/ (FlowBuilder template method with DDP_CATEGORIES — d3i-infra standard but unwired). Each has strengths the other lacks. donation_flows/ has superior data completeness (180 vs 26 tables for Facebook) and helper-based UI construction aligned with python-architecture/AD0003. platforms/ has FlowBuilder (extraction/AD0001) and DDP_CATEGORIES validation (extraction/AD0002). Neither system satisfies both ADRs. How should these be consolidated?

## <a name="options"></a> Considered Options
1. <a name="option-1"></a> FlowBuilder control flow + data-driven extraction + DDP_CATEGORIES validation
2. <a name="option-2"></a> Keep donation_flows/ pattern with DDP_CATEGORIES validation bolted on
3. <a name="option-3"></a> Keep both systems — let researchers choose

## <a name="criteria"></a> Decision Drivers
Feldspar alignment: FlowBuilder.start_flow() mirrors eyra's expected generator protocol — the retry/consent/donation control flow should be framework-level, not per-script
Researcher usability: researchers add platforms by writing extraction logic, not UI boilerplate — the data-driven entries pattern (donation_flows/) lets a researcher define a table in 3 lines vs 15+ lines of PropsUI construction (platforms/)
ADR compliance: extraction/AD0001 requires FlowBuilder; python-architecture/AD0003 requires helper-based UI construction — the consolidated system must satisfy both
Data completeness: donation_flows/ extracts 180 Facebook tables vs 26 in platforms/ — a consolidation must not lose coverage
Validation robustness: DDP_CATEGORIES (platforms/) validates against known file lists with threshold matching; donation_flows/ uses simple pattern matching (has_file_in_zip) which accepts invalid DDPs
Retry flow correctness: FlowBuilder.start_flow() has a bug at line 76 — yields retry prompt but never checks the response, so retries skip back to consent instead of re-prompting for file
Error observability: donation_flows/ uses logging.exception() with full traceback and structured DataFrame export; platforms/ uses logger.error() without traceback and no export mechanism
Code maintainability: donation_flows/ is 59 lines per platform (data-driven); platforms/ is 1000+ lines per platform (hand-written extraction functions)
### Pros and Cons

**FlowBuilder control flow + data-driven extraction + DDP_CATEGORIES validation**
* Good, because satisfies both extraction/AD0001 (FlowBuilder) and python-architecture/AD0003 (helper-based UI)
* Good, because preserves 180-table data completeness from donation_flows/ entries pattern
* Good, because adopts DDP_CATEGORIES validation from platforms/ replacing weak pattern matching
* Good, because researchers add platforms via entries dict (3 lines per table) not PropsUI boilerplate
* Good, because FlowBuilder.start_flow() centralizes retry/consent/donation — aligned with feldspar generator protocol
* Neutral, because requires fixing FlowBuilder retry bug (line 76) and wiring structured logging into FlowBuilder
* Bad, because requires migrating 5 platforms from donation_flows/ entries format into FlowBuilder subclasses with DDP_CATEGORIES
* Bad, because the 5 extra platforms in platforms/ (ChatGPT, LinkedIn, Netflix, WhatsApp, X) need their hand-written extraction functions converted to entries format or kept as-is

**Keep donation_flows/ pattern with DDP_CATEGORIES validation bolted on**
* Good, because minimal migration — donation_flows/ already works and is wired to script.py
* Good, because preserves data-driven entries pattern and helper-based UI construction
* Good, because adding DDP_CATEGORIES to donation_flows/ validation is straightforward
* Bad, because violates extraction/AD0001 — no FlowBuilder, control flow stays in script.py
* Bad, because script.py orchestration is not aligned with feldspar's generator protocol expectations
* Bad, because the 5 extra platforms (ChatGPT, LinkedIn, Netflix, WhatsApp, X) only exist in platforms/ and would need rewriting
* Bad, because retry/consent/donation flow duplicated per-script instead of centralized

**Keep both systems — let researchers choose**
* Good, because no migration work needed
* Bad, because two parallel architectures confuse contributors and violate ADR intent
* Bad, because bug fixes and flow improvements must be applied in two places
* Bad, because new researchers don't know which pattern to follow


## <a name="comments"></a> Comments
<a name="comment-1"></a>1. (2026-03-16 17:27:31) Danielle McCool: More Information:
This decision supersedes the current state where donation_flows/ (from what-if, commit 4f4c0d88 by Kasper Welbers, 2025-07-01) is active and platforms/FlowBuilder (d3i-infra standard) is unwired. Related: extraction/AD0001 (FlowBuilder), extraction/AD0002 (DDP_CATEGORIES), python-architecture/AD0003 (helper-based UI). FlowBuilder retry bug: platforms/flow_builder.py line 76 yields retry prompt without checking response.
