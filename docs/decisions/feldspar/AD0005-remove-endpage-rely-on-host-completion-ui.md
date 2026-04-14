---
adr_id: "0005"
comments:
    - author: Danielle McCool
      comment: "1"
      date: "2026-04-14 09:00:00"
links:
    precedes: []
    succeeds:
        - "0004"
status: decided
tags:
    - end-page
    - completion
    - host-integration
title: Remove EndPage and rely on host completion UI
---

## <a name="question"></a> Context and Problem Statement

The EndPage component rendered a "Thank you" message after the last platform completed. Like all pages it received a `resolve` callback from `ReactEngine.renderPage()` — but unlike interactive pages, nothing ever called it. This created a silent break in the generator protocol: Python hung at `yield render_end_page()`, StopIteration never fired, ScriptWrapper never produced `CommandSystemExit`, and the host never marked the task complete (no checkmark). How should the workflow signal study completion to the host?

## <a name="options"></a> Considered Options
1. <a name="option-1"></a> Auto-resolve the render promise inside EndPage via useEffect
2. <a name="option-2"></a> Remove EndPage entirely and rely on the host's completion UI
3. <a name="option-3"></a> Yield CommandSystemExit explicitly before rendering EndPage

## <a name="criteria"></a> Decision Drivers
AD0004 documents generator exhaustion as the termination mechanism — but exhaustion requires the final yield to return, which requires the render promise to resolve
Commit 142f46ad replaced `yield ph.exit()` with `yield CommandUIRender(PropsUIPageEnd())` to fix a spinner — correctly showing a Thank You page, but inadvertently blocking the completion signal
The host (mono) requires CommandSystemExit via the bridge to mark the crew task as complete and render finished_view (the checkmark); no other signal triggers this
Mono already renders its own completion UI (`finished_view`) on `CommandSystemExit`; an in-iframe "Thank you" page duplicates it
Upstream eyra/feldspar never renders an end page — the script returns and StopIteration fires directly — so this diverges from upstream
### Pros and Cons

**Auto-resolve the render promise inside EndPage via useEffect**
* Good, because the EndPage stays visible while the exit signal propagates
* Good, because it is a single useEffect addition — minimal code change
* Bad, because it is a subtle discipline: any future display-only page must remember to auto-resolve or the protocol silently hangs again
* Bad, because it keeps a Thank You page that duplicates mono's finished_view
* Bad, because it perpetuates the divergence from upstream eyra/feldspar

**Remove EndPage entirely and rely on the host's completion UI**
* Good, because the completion chain has no silent-hang failure mode — the last `yield` is a log, the generator returns, ScriptWrapper emits CommandSystemExit
* Good, because it removes an entire page type, factory, and 7 translations that duplicate host-side UX
* Good, because it realigns with upstream eyra/feldspar (which has no end page)
* Good, because future display-only pages can't silently hang the protocol if the pattern doesn't exist
* Neutral, because mono's finished_view becomes the only "you're done" signal — acceptable because that is already the authoritative completion UI

**Yield CommandSystemExit explicitly before rendering EndPage**
* Good, because the completion signal is sent immediately
* Bad, because the UI stays on the last platform's consent form (the original spinner problem from commit 142f46ad)
* Bad, because it contradicts AD0004 which chose generator exhaustion over explicit exit


## <a name="outcome"></a> Decision Outcome
We decided for [Option 2](#option-2) because: the in-iframe Thank You page duplicates mono's `finished_view` (the checkmark UI that appears when the host receives `CommandSystemExit`), and keeping the page required a subtle auto-resolve pattern that any future display-only page would have to replicate or silently reintroduce the hang. Removing EndPage leaves one authoritative completion signal — generator exhaustion → `CommandSystemExit` → `finished_view` — and realigns with upstream eyra/feldspar, which never shipped an end page.

Concretely: `PropsUIPageEnd`, `render_end_page()`, the `EndPage` component, `EndPageFactory`, and the final `yield ph.render_end_page()` in `script.py` are all removed. `script.py`'s last yield is `emit_log("Study complete")`; the generator then returns and ScriptWrapper converts StopIteration to `CommandSystemExit`, which the bridge forwards to mono's `waitForDonationsAndExit`, triggering `:tool_completed` and the `finished_view` checkmark.

Consequence: there is no longer any display-only page in the workflow. If one is ever added, it must not rely on an unresolved render promise for "don't advance yet" semantics.

## <a name="comments"></a> Comments
<a name="comment-1"></a>1. (2026-04-14 09:00:00) Danielle McCool: rewrote AD0005 — the original decision (auto-resolve EndPage) was superseded before merge in favor of removing EndPage entirely.
