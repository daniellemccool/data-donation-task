---
adr_id: "0002"
comments:
    - author: Danielle McCool
      comment: "1"
      date: "2026-03-13 13:30:02"
links:
    precedes: []
    succeeds: []
status: accepted
date: 2026-03-13
tags:
    - bridge
    - iframe
    - postmessage
title: Bridge abstraction with swappable implementations
---

## <a name="question"></a> Context and Problem Statement

The workflow runs inside an iframe on the Eyra Next platform. It must send commands (render page, donate data, end flow) to the host and receive responses. During development there is no host iframe. How should the workflow communicate with its host?

## <a name="options"></a> Considered Options
1. <a name="option-1"></a> Direct postMessage calls from workflow code
2. <a name="option-2"></a> Bridge abstraction with LiveBridge and FakeBridge implementations
3. <a name="option-3"></a> Shared state via window globals

## <a name="criteria"></a> Decision Drivers

* The workflow must run in two contexts: inside an Eyra Next iframe (production) and standalone in a browser tab (development)
* Workflow logic should not need to know which transport is active
* The design is inherited from Eyra and worth preserving for upstream compatibility

## <a name="outcome"></a> Decision Outcome
We decided for [Option 2](#option-2) because: A bridge abstraction with swappable implementations is Eyra's design: LiveBridge uses postMessage for production (iframe to host), FakeBridge provides console-based mock for development; ScriptHostComponent accepts a Bridge prop, so the transport is injected at composition time without changing workflow logic.

### Consequences

* Good: Development uses FakeBridge with console logging — no Eyra Next instance required
* Good: Workflow logic is decoupled from the transport mechanism
* Good: The same Python generator yields commands regardless of which bridge is active

## More Information

See [python-architecture/AD0005](../python-architecture/AD0005-python-generator-protocol-for-workflow-orchestration.md) for the Python side of this communication channel.

## <a name="comments"></a> Comments
<a name="comment-1"></a>1. (2026-03-13 13:30:02) Danielle McCool: marked decision as decided
