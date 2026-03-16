# Design: Eyra/Feldspar Integration into data-donation-task

**Date**: 2026-03-16
**Status**: Approved
**Goal**: Bring eyra/feldspar changes into daniellemccool/data-donation-task in a way that
produces a clean, auditable commit history suitable for PRing into d3i-infra/data-donation-task.

## Context

Three repos are involved:

| Repo | Role |
|------|------|
| `eyra/feldspar` (develop @ `ed629b54`) | Upstream source of framework changes |
| `d3i-infra/data-donation-task` (master) | Target for eventual PRs; base for this fork |
| `daniellemccool/dd-vu-2026` (master) | Study fork that has already integrated most eyra changes |

The merge-base between this fork's master and eyra is `a4240aff` (very old, pre-monorepo
restructure). dd-vu-2026 synced to eyra/develop at `ed629b54` and additionally cherry-picked
eyra PR #663 (logging). dd-vu-2026 is essentially current with eyra/develop.

## Approach: Hybrid cherry-pick (Approach C)

**Base**: Reset this fork's master to `d3i-infra/master`.

**Categorization of eyra features**:
- **Pure feldspar** (only touches `packages/feldspar/` or root docs): cherry-pick from eyra
  directly, since d3i doesn't modify feldspar.
- **Cross-package** (touches `py_worker.js`, `script.py`, `main.py`, `props.py`, etc.):
  extract from dd-vu-2026's proven integration, since d3i's Python layer differs from
  eyra's example scripts.

**Each feature** gets its own branch and merge commit. Commit messages reference the eyra
source commit hash for traceability. Ordering is chronological by eyra commit date.

**Verification**: After all features are integrated, diff `packages/feldspar/` between this
fork and dd-vu-2026 to catch anything missed.

**ADR capture**: Decision points identified during integration are noted in
`docs/decisions/adr-todo.md` and written as formal ADRs afterwards.

## Feature Sequence

### Phase 1: Pure feldspar cherry-picks

These touch only `packages/feldspar/` (or root docs) and should apply cleanly.

| # | Feature | Eyra commit(s) | Date | Scope |
|---|---------|----------------|------|-------|
| 1 | Font: Finador → Nunito | `5eccca12` + `68b488b3` + `fd2c8e41` | Dec 2025 | 32 font files removed, 3 added; tailwind.config.js + fonts.css |
| 2 | Search case-insensitive fix | `ea959135` | Jan 2026 | 2-line change in table.tsx |
| 3 | Button spinner alignment | `e6289437` | Feb 2026 | Layout fix in button.tsx |
| 4 | LT/RO translations | `096dcae4` + `8cd1cd87` | Feb 2026 | New translation files |
| 5 | DISCLAIMER.md | `bb456ec3` | Feb 2026 | New root file |
| 6 | Tailwind CSS v4 migration | `eb621b17` + `f30774c0` + `6cc392c4` | Feb 2026 | PostCSS config, styles.css, 12 component files |

### Phase 2: Cross-package features (from dd-vu-2026)

These require d3i adaptation. Source from dd-vu-2026's proven integration.

| # | Feature | Eyra source | dd-vu-2026 source | Key files |
|---|---------|-------------|-------------------|-----------|
| 7 | PayloadFile / sync file reader | `0b2a8c9f` (#482) | `525b70c` + `075c934` | py_worker.js, file_utils.py, main.py, script.py |
| 8 | Dataframe size limits | `bd7bf248` | `525b70c` | consent_table.tsx, props.py, script.py |
| 9 | Truncation tests + utility | `fd16e34e` | `525b70c` | truncation.ts, truncation.test.ts, jest.config.js, test_dataframe_truncation.py |
| 10 | Log forwarder + monitor protocol | `1dd29685` (#663) | `a48be83` (11 commits) | logging.ts, commands.ts/py, assembly.ts, worker_engine.ts, live_bridge.ts, main.py, script.py, App.tsx |

### Phase 3: Feldspar verification gate

Diff `packages/feldspar/` between this fork and dd-vu-2026. Identify and bring in
anything missed by the per-feature integration.

### Phase 4: Remaining eyra/develop changes

| # | Feature | Eyra commit | Notes |
|---|---------|-------------|-------|
| 11 | Remove unused _build_release.yml | `37c2c892` | Trivial file deletion |
| 12 | CI workflow + permissions | `858cda49` + `447016d7` + related | May need d3i adaptation |
| 13 | postcss dep update | `26c6030c` | May be needed for Tailwind v4 |

### Phase 5: Mono compatibility audit

Review d3i-infra/master for mono-specific changes (bridge, postMessage, env vars).
Verify they are preserved after the eyra integration. This is investigation, not a
predefined set of commits.

### Phase 6: Platform script modernization (future)

Separate planning cycle. Bring d3i-infra/master's standard platform scripts forward
using dd-vu-2026's VU 2026 migration as reference. Requires both versions visible.

## ADR Capture

Decision points identified from the eyra features are tracked in
`docs/decisions/adr-todo.md`. Key decisions to document:

- **PayloadFile / sync file reader**: WORKERFS copy → on-demand FileReaderSync slicing
- **Two-tier dataframe truncation**: 10k Python / 50k UI hard cap
- **Structured logging via bridge**: Replaces ad-hoc console.log and meta_data donations
- **Font: Finador → Nunito**: Proprietary → open-source, bundle size reduction
- **Tailwind v4 migration**: Breaking changes to PostCSS integration and config
- **Mono compatibility layer**: TBD — backwards compat with d3i mono
- **Release workflow**: TBD — eyra CI vs d3i per-platform release.sh

## Completion Criteria

1. All features integrated via individual branches/PRs onto d3i-infra/master base
2. Feldspar verification gate passes (diff against dd-vu-2026 shows no gaps)
3. Mono compatibility audit complete
4. `adr-todo.md` entries enriched with integration context
5. Platform script modernization scoped as separate follow-up
