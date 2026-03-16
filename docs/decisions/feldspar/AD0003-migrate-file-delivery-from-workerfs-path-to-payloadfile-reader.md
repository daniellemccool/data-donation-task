---
adr_id: "0003"
comments:
    - author: Danielle McCool
      comment: "1"
      date: "2026-03-16 14:57:59"
    - author: Danielle McCool
      comment: "2"
      date: "2026-03-16 15:14:32"
links:
    precedes: []
    succeeds: []
status: open
tags:
    - worker-protocol
    - file-delivery
    - backwards-compatibility
title: Migrate file delivery from WORKERFS path to PayloadFile reader
---

## <a name="question"></a> Context and Problem Statement

The py_worker delivers files from the browser to Python scripts running in Pyodide. The old approach (WORKERFS via d3i_py_worker.js) copies the entire file into Pyodide's virtual filesystem and passes a path string (PayloadString). The new approach (py_worker.js, from eyra/feldspar) passes an on-demand file reader (PayloadFile) that avoids the full copy, preventing OOM crashes on large DDPs. During the eyra/feldspar integration, App.tsx was switched from d3i_py_worker.js to py_worker.js (Task 8), but the Python scripts were not updated to handle PayloadFile. The result: script.py checks file_result.__type__ == 'PayloadString', gets 'PayloadFile' instead, falls to the else branch, and the entire extraction is skipped. Multiple researcher forks have scripts in production that expect PayloadString paths. How should the worker transition from WORKERFS/PayloadString to PayloadFile while maintaining backwards compatibility?

## <a name="options"></a> Considered Options
1. <a name="option-1"></a> Revert to WORKERFS only
2. <a name="option-2"></a> Switch to PayloadFile only, update all scripts immediately
3. <a name="option-3"></a> Support both: WORKERFS copy with PayloadString plus PayloadFile reader, deprecation path
4. <a name="option-4"></a> Support both: let scripts opt in to PayloadFile via a capability flag

## <a name="criteria"></a> Decision Drivers
Memory safety: Large DDPs (100MB+) cause OOM when fully copied into Pyodide WORKERFS. PayloadFile reads slices on demand, avoiding this.
Backwards compatibility: 5+ platform scripts in this repo and scripts in researcher forks use PayloadString paths with zipfile.ZipFile(path). Breaking these blocks all studies.
Upstream alignment: eyra/feldspar uses PayloadFile. Staying aligned reduces future merge friction.
Transition time: Researcher forks cannot be updated on our schedule. Need a deprecation path, not a flag day.
Complexity budget: The worker is a ~150-line JS file. Adding too much abstraction creates maintenance burden.
### Pros and Cons

**Revert to WORKERFS only**
* Good, because all existing scripts work without modification
* Good, because minimal code change (revert unwrap())
* Bad, because loses the OOM fix — large DDPs will still crash
* Bad, because diverges from eyra upstream direction

**Switch to PayloadFile only, update all scripts immediately**
* Good, because clean break — one protocol, no legacy
* Good, because fully aligned with eyra upstream
* Bad, because requires updating every platform script in this repo (5 platforms)
* Bad, because breaks all researcher forks that haven't updated their scripts

**Support both: WORKERFS copy with PayloadString plus PayloadFile reader, deprecation path**
* Good, because existing scripts work immediately
* Good, because PayloadFile is available for new/updated scripts
* Neutral, because file is still copied (memory cost exists for legacy scripts)
* Bad, because dual-protocol complexity in the worker
* Bad, because no incentive to migrate (WORKERFS just works)

**Support both: let scripts opt in to PayloadFile via a capability flag**
* Good, because existing scripts work without modification (WORKERFS default)
* Good, because new scripts get the memory benefit of PayloadFile
* Good, because migration happens per-script, at each script author's pace
* Good, because clear deprecation path: eventually flip the default, then remove WORKERFS
* Neutral, because adds a capability negotiation mechanism to the worker


## <a name="comments"></a> Comments
<a name="comment-2"></a>2. (2026-03-16 15:14:32) Danielle McCool: Current state (2026-03-16): Implementation follows Option 4 (capability flag via VITE_PAYLOAD_FILE env var). Default is WORKERFS/PayloadString for backwards compatibility. VITE_PAYLOAD_FILE=true enables PayloadFile. This repo's standard script.py has been updated to handle PayloadFile. Decision remains open — should be re-evaluated once researcher forks have had time to migrate and the deprecation path is further along.
