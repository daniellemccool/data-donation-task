---
adr_id: "0010"
comments:
    - author: Danielle McCool
      comment: "1"
      date: "2026-03-20 13:42:06"
    - author: Danielle McCool
      comment: "2"
      date: "2026-03-20 15:36:17"
links:
    precedes: []
    revises:
        - "0008"
    succeeds: []
status: decided
tags:
    - logging
    - observability
    - bridge
    - pii-safety
title: Forward logs from the port package not only port.script (Revised)
---

## <a name="question"></a> Context and Problem Statement
The LogForwardingHandler in main.py forwards Python log records to the TypeScript bridge as CommandSystemLog. Currently it attaches only to the port.script logger. After the extraction consolidation (AD0006) shared logic moves into helpers/ and platforms/ which use their own module-level loggers (port.helpers.flow_builder, port.platforms.facebook, etc.). These logs are not forwarded. What logger scope should the forwarding handler attach to?
AD0008 decided to attach the LogForwardingHandler to the port root logger to capture all module logs. Testing on mono revealed this forwards PII-containing error messages from extraction_helpers and platform modules (file paths with contact names — raw exception text) to mono's /api/feldspar/log endpoint without participant consent. It also caused 429 rate-limiting from error volume. The port scope was the correct intent (observability across modules) but the wrong mechanism (no PII boundary). How should log forwarding be scoped to provide flow observability without forwarding participant data?

## <a name="options"></a> Considered Options
1. <a name="option-1"></a> Attach to port root logger
2. <a name="option-2"></a> Keep port.script only
3. <a name="option-3"></a> Attach to each module logger individually
4. <a name="option-4"></a> Attach to dedicated port.bridge logger — only script.py and FlowBuilder write to it with PII-free messages

## <a name="criteria"></a> Decision Drivers
FlowBuilder and platform modules emit diagnostic logs that are invisible without forwarding
The Pyodide WebWorker has no console — log forwarding is the only observability channel
Eyra upstream attaches to port.script because all their logic is in script.py — our layered architecture distributes logic across helpers/ and platforms/
### Pros and Cons

**Attach to port root logger**
* Good, because captures all logs from script.py, helpers/, and platforms/ automatically
* Good, because new modules in port/ are captured without handler changes
* Good, because preserves Eyra's log forwarding mechanism — just widens scope
* Neutral, because may forward more logs than before — add formatter with logger name for source context

**Keep port.script only**
* Good, because matches Eyra upstream exactly
* Bad, because FlowBuilder and platform logs are silently lost
* Bad, because debugging extraction issues requires adding ad-hoc handlers
Forwarding raw helper/platform error logs exposed PII (contact names in Facebook DDP paths) and caused 429 rate-limiting on mono
The forwarding boundary must be explicit in the code — if you see bridge_logger you know it crosses the iframe
Diagnostic logs (extraction errors with full context) must remain available locally in the browser console
Flow milestones (where the participant is in the process) must be forwarded immediately for crash diagnostics

## <a name="outcome"></a> Decision Outcome
We decided for [Option 4](#option-4) because: A dedicated port.bridge logger creates an explicit PII boundary in the code. Only script.py and FlowBuilder write to it with a controlled vocabulary of PII-free milestone messages. All other module loggers (extraction_helpers — platform modules — uploads — validate) keep using their __name__ loggers for local diagnostics that never cross the bridge. This supersedes AD0008 Option 1 (attach to port root) which was proven unsafe by testing on mono. See docs/superpowers/specs/2026-03-20-pii-safe-logging-design.md for the full design.

## <a name="comments"></a> Comments
<a name="comment-2"></a>2. (2026-03-20 15:36:17) Danielle McCool: Superseded by AD0011: The LogForwardingHandler + port.bridge logger approach was replaced by explicit CommandSystemLog yields from FlowBuilder and script.py. The hidden handler mechanism created a parallel implicit pipeline alongside the JS LogForwarder.
