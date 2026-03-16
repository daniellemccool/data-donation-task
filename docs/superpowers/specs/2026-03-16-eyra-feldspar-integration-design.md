# Design: Eyra/Feldspar Integration into data-donation-task

**Date**: 2026-03-16
**Status**: Approved
**Goal**: Bring eyra/feldspar changes into daniellemccool/data-donation-task in a way that
produces a clean, auditable commit history suitable for PRing into d3i-infra/data-donation-task.

## Context

Three repos are involved:

| Repo | Role |
|------|------|
| `eyra/feldspar` (develop is production) | Upstream source of framework changes |
| `d3i-infra/data-donation-task` (master) | Target for eventual PRs; base for this fork |
| `daniellemccool/dd-vu-2026` (master) | Study fork that has already integrated most eyra changes |

The merge-base between this fork's master and eyra is `a4240aff` (very old, pre-monorepo
restructure). dd-vu-2026 synced to eyra/develop at `ed629b54` and additionally cherry-picked
eyra PR #663 (logging). dd-vu-2026 is essentially current with eyra/develop at that point.

**Note**: eyra/master is unused; eyra/develop is the production branch.

Since `ed629b54`, eyra/develop has gained these non-chore commits:

- `1dd29685` — logging PR #663 (already in dd-vu-2026 via cherry-pick) → Phase 2 #11
- `37c2c892` — remove unused _build_release.yml → Phase 4 #12
- `189879f8` — status text during submission (#672) → Phase 1 #7
- `d3c715d2` + `10cbf186` — dependency verification → Phase 4 #13
- `01e1387b` — Milestone 7 (merge commit on eyra/master bundling the above; not
  cherry-picked directly since its constituents are tracked individually)

## Approach: Hybrid cherry-pick (Approach C)

**Base**: Reset this fork's master to `d3i-infra/master`.

**Categorization of eyra features**:
- **Pure feldspar** (only touches `packages/feldspar/` or root docs): cherry-pick from eyra
  directly, since d3i doesn't modify feldspar.
- **Cross-package** (touches `py_worker.js`, `script.py`, `main.py`, `props.py`, etc.):
  extract from dd-vu-2026's proven integration, since d3i's Python layer differs from
  eyra's example scripts.

**Each feature** gets its own branch and merge commit. Commit messages reference the eyra
source commit hash for traceability.

**Ordering**: Broadly chronological by eyra commit date. Within a single feature group
(e.g. Tailwind v4's 3 commits), branch topology takes precedence over author timestamps
— some commits were reordered via rebase upstream.

**Phases are ordered by type** (pure feldspar before cross-package), not strict chronology.
PayloadFile (`0b2a8c9f`, Nov 2025) predates the font change (Dec 2025) but appears in
Phase 2 because it requires d3i adaptation.

**Verification**: After all features are integrated, diff `packages/feldspar/` between this
fork and dd-vu-2026 to catch anything missed.

**ADR capture**: Decision points identified during integration are noted in
`docs/decisions/adr-todo.md` and written as formal ADRs afterwards.

**Failure strategy**: Each feature gets its own branch. If a cherry-pick causes significant
conflicts or test failures, the branch can be abandoned and revisited later. The
verification gate (Phase 3) catches anything skipped. Features within a phase are
independent unless noted.

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
| 6 | Tailwind CSS v4 migration | `eb621b17` + `f30774c0` + `6cc392c4` + `26c6030c` | Feb 2026 | PostCSS config, styles.css, 12 component files. Apply in branch order (topology), not author-date order. Includes postcss v8.5.8 update (`26c6030c`) as prerequisite. |
| 7 | Status text during submission | `189879f8` (#672) | Mar 2026 | donate_buttons.tsx — "Transferring data..." text while spinning |

### Phase 2: Cross-package features (from dd-vu-2026)

These require d3i adaptation. Source from dd-vu-2026's proven integration.

| # | Feature | Eyra source | dd-vu-2026 source | Key files |
|---|---------|-------------|-------------------|-----------|
| 8 | PayloadFile / sync file reader | `0b2a8c9f` (#482) | `525b70c` + `075c934` | py_worker.js, file_utils.py, main.py, script.py |
| 9 | Dataframe size limits | `bd7bf248` | `525b70c` | consent_table.tsx, props.py, script.py |
| 10 | Truncation tests + utility | `fd16e34e` | `525b70c` | truncation.ts, truncation.test.ts, jest.config.js, test_dataframe_truncation.py |
| 11 | Log forwarder + monitor protocol | `1dd29685` (#663) | `a48be83` (11 commits) | logging.ts, commands.ts/py, assembly.ts, worker_engine.ts, live_bridge.ts, main.py, script.py, App.tsx |

**Note on donate helper** (`df3a8999`): This eyra commit adds a `donate()` helper and debug
tracking event to `script.py`. Since d3i has its own `script.py` with different donation
logic, this is deferred to Phase 6 (platform script modernization) where d3i's scripts
are updated holistically.

### Phase 3: Feldspar verification gate

Diff `packages/feldspar/` between this fork and dd-vu-2026. Identify and bring in
anything missed by the per-feature integration.

### Phase 4: Remaining eyra/develop changes

| # | Feature | Eyra commit(s) | Notes |
|---|---------|----------------|-------|
| 12 | Remove unused _build_release.yml | `37c2c892` | Trivial file deletion |
| 13 | Dependency verification | `d3c715d2` + `10cbf186` | check-deps.sh, release.sh updates. May need adaptation for d3i's release process. |
| 14 | CI: release workflow | `858cda49` + `fc30ef44` + `504fbe25` + `3f672ead` + `1124e4d7` + `048346bc` + `239c5876` + `84e32328` + `a6e1ad34` | Base workflow + 8 follow-up fixes (branch triggers, tag format, artifact naming, pre-commit hooks, GitHub Release creation). |
| 15 | CI: dependency-updates workflow | `76ed7890` + `328777be` + `9eaf9473` | CI for Renovate/Dependabot PRs |
| 16 | CI: permissions + cleanup | `447016d7` + `943393fc` + `1790c52e` + `40ffd24c` | Workflow permissions, remove redundant playwright.yml, E2E LFS checkout, test zip LFS files |

### Phase 5: Mono compatibility audit

Review d3i-infra/master for mono-specific changes (bridge, postMessage, env vars).
Verify they are preserved after the eyra integration. This is investigation, not a
predefined set of commits.

### Phase 6: Platform script modernization (future)

Separate planning cycle. Bring d3i-infra/master's standard platform scripts forward
using dd-vu-2026's VU 2026 migration as reference. Requires both versions visible.
Includes the donate helper (`df3a8999`) disposition.

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

1. All features (phases 1-4) integrated via individual branches/PRs onto d3i-infra/master base
2. Feldspar verification gate passes (diff against dd-vu-2026 shows no gaps)
3. Mono compatibility audit complete
4. `adr-todo.md` entries enriched with integration context
5. Platform script modernization scoped as separate follow-up
