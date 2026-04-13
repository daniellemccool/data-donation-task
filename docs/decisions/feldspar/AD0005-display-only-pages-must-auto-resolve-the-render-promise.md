---
adr_id: "0005"
comments:
    - author: Danielle McCool
      comment: "1"
      date: "2026-04-13 09:54:44"
links:
    precedes: []
    succeeds:
        - "0004"
status: decided
tags:
    - end-page
    - completion
    - render-promise
    - host-integration
title: Display-only pages must auto-resolve the render promise
---

## <a name="question"></a> Context and Problem Statement

The EndPage component renders a 'Thank you' message with no buttons or user interaction. Like all pages, it receives a resolve callback from ReactEngine.renderPage() — but unlike interactive pages, nothing ever calls it. This creates a silent break in the generator protocol: Python hangs at `yield render_end_page()`, StopIteration never fires, ScriptWrapper never produces CommandSystemExit, and the host never marks the task complete (no checkmark). How should display-only pages handle the render promise?

## <a name="options"></a> Considered Options
1. <a name="option-1"></a> Auto-resolve in the component via useEffect
2. <a name="option-2"></a> Special-case EndPage in CommandRouter to skip the UI promise
3. <a name="option-3"></a> Send CommandSystemExit explicitly instead of rendering EndPage

## <a name="criteria"></a> Decision Drivers
AD0004 documents generator exhaustion as the termination mechanism — but exhaustion requires the final yield to return, which requires the render promise to resolve
Commit 142f46ad replaced `yield ph.exit()` with `yield CommandUIRender(PropsUIPageEnd())` to fix a spinner — correctly showing a Thank You page, but inadvertently blocking the completion signal
The host (mono) requires CommandSystemExit via the bridge to mark the crew task as complete and render finished_view (the checkmark); no other signal triggers this
Upstream eyra/feldspar never renders an end page — the script returns and StopIteration fires directly — so this is a D3I-specific issue
### Pros and Cons

**Auto-resolve in the component via useEffect**
* Good, because the EndPage stays visible while the exit signal propagates — solving both the spinner problem and the completion signal problem
* Good, because it requires a single useEffect addition to end_page.tsx — minimal change
* Good, because it makes AD0004's documented flow actually work as described
* Good, because other display-only pages added in future would follow the same pattern
* Neutral, because developers must remember to auto-resolve any future display-only page

**Special-case EndPage in CommandRouter to skip the UI promise**
* Good, because no change to the React component
* Bad, because it adds page-type awareness to CommandRouter which currently treats all CommandUIRender uniformly
* Bad, because it violates separation of concerns — the router should not know about page semantics

**Send CommandSystemExit explicitly instead of rendering EndPage**
* Good, because the completion signal is sent immediately
* Bad, because the UI stays on the last platform's consent form (the original spinner problem from commit 142f46ad)
* Bad, because it reverses the fix that motivated the EndPage approach
* Bad, because it contradicts AD0004 which chose generator exhaustion over explicit exit


## <a name="outcome"></a> Decision Outcome
We decided for [Option 1](#option-1) because: This is the minimal change that preserves both behaviors: the Thank You page renders (solving the spinner that motivated commit 142f46ad) and the generator exhausts naturally (sending CommandSystemExit to the host, restoring the checkmark). The full completion chain becomes: script.py yields PropsUIPageEnd → ReactEngine creates render promise → EndPage renders and auto-resolves → promise resolves with PayloadVoid → Python advances past yield → generator returns → StopIteration → ScriptWrapper returns CommandSystemExit → CommandRouter sends via bridge → mono feldspar_app.js receives exit → waitForDonationsAndExit → pushEvent to LiveView → tool_view publishes :tool_completed → crew task marked complete → finished_view (checkmark) rendered. Consequence: any future display-only page component must also auto-resolve; this is a component-level responsibility, not a framework-level one.

## <a name="comments"></a> Comments
<a name="comment-1"></a>1. (2026-04-13 09:54:44) Danielle McCool: marked decision as decided
