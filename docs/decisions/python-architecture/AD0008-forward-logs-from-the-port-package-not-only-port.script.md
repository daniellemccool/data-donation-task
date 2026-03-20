---
adr_id: "0008"
comments:
    - author: Danielle McCool
      comment: "1"
      date: "2026-03-17 13:24:09"
    - author: Danielle McCool
      comment: "2"
      date: "2026-03-17 13:24:09"
    - author: Danielle McCool
      comment: "3"
      date: "2026-03-20 15:36:09"
links:
    precedes: []
    revised by:
        - "0010"
    succeeds: []
status: decided
tags:
    - logging
    - observability
    - bridge
title: Forward logs from the port package not only port.script
---

## <a name="question"></a> Context and Problem Statement

The LogForwardingHandler in main.py forwards Python log records to the TypeScript bridge as CommandSystemLog. Currently it attaches only to the port.script logger. After the extraction consolidation (AD0006) shared logic moves into helpers/ and platforms/ which use their own module-level loggers (port.helpers.flow_builder, port.platforms.facebook, etc.). These logs are not forwarded. What logger scope should the forwarding handler attach to?

## <a name="options"></a> Considered Options
1. <a name="option-1"></a> Attach to port root logger
2. <a name="option-2"></a> Keep port.script only
3. <a name="option-3"></a> Attach to each module logger individually

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


## <a name="outcome"></a> Decision Outcome
We decided for [Option 1](#option-1) because: The layered architecture (AD0001) distributes logic across helpers/ and platforms/. Attaching to port captures everything without per-module registration. A formatter with '%(name)s: %(message)s' preserves source context so logs from different modules are distinguishable. This is an observability-policy change: more logs will be forwarded than before.

## <a name="comments"></a> Comments
<a name="comment-3"></a>3. (2026-03-20 15:36:09) Danielle McCool: Superseded: AD0008 was revised by AD0010 (port.bridge scope) which was then superseded by AD0011 (explicit CommandSystemLog yields). The port-wide forwarding approach proved unsafe — it forwarded PII-containing extraction errors to mono.
