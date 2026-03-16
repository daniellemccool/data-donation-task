# Eyra/Feldspar Integration — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring eyra/feldspar framework changes into daniellemccool/data-donation-task as individually-branched, merge-committed features suitable for PR to d3i-infra/data-donation-task.

**Architecture:** Cherry-pick pure feldspar changes from eyra/develop directly; extract cross-package changes from dd-vu-2026's proven integration. Each feature gets its own branch off master and a `--no-ff` merge commit referencing the eyra source hash. The result is a linear series of merge commits on master, each self-contained.

**Tech Stack:** pnpm monorepo (feldspar: Rollup+PostCSS+Tailwind, data-collector: Vite+React, python: Poetry+pytest). Node 22, Python 3.13.

**Spec:** `docs/superpowers/specs/2026-03-16-eyra-feldspar-integration-design.md`

---

## Prerequisites

Before starting any task, ensure these remotes are configured:

```bash
cd /home/dmm/src/d3i/forks/daniellemccool/data-donation-task

# Verify existing remotes
git remote -v
# Expected: origin (daniellemccool/data-donation-task), d3i-infra, eyra

# Add dd-vu-2026 as remote (needed for Phase 2 cross-package features)
git remote add dd-vu-2026 https://github.com/daniellemccool/dd-vu-2026.git
git fetch dd-vu-2026

# Fetch all remotes
git fetch --all
```

### Verification commands used throughout

```bash
# Build check (runs Python wheel + feldspar + data-collector)
pnpm run build

# Feldspar tests (Jest)
cd packages/feldspar && pnpm test && cd ../..

# Python tests
cd packages/python && poetry run pytest -v && cd ../..

# E2E tests (requires dev server running)
pnpm run test:e2e

# Dev server (for manual verification)
pnpm run start   # → localhost:3000
```

### Branch naming convention

Each feature branch follows: `feat/eyra-<short-name>`
Example: `feat/eyra-font-nunito`, `feat/eyra-tailwind-v4`

### Merge commit convention

```bash
git checkout master
git merge --no-ff feat/eyra-<name> -m "$(cat <<'EOF'
feat: <description>

Cherry-picked from eyra/feldspar <commit-hash>.
Ref: eyra PR #<number> (if applicable)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Chunk 1: Phase 1 — Pure Feldspar Cherry-Picks (Features 1–3)

These features touch only `packages/feldspar/` and should apply cleanly from eyra/develop.

---

### Task 1: Font — Finador → Nunito (eyra `fd2c8e41` + `5eccca12` + `68b488b3`)

Three commits in branch-topology order:
1. `fd2c8e41` — Move fonts from `src/fonts/` to `src/framework/fonts/`, update rollup config
2. `5eccca12` — Replace Finador with Nunito/NunitoSans in the new location
3. `68b488b3` — Fine-tune font weights

**Files (feldspar only):**
- Remove: `packages/feldspar/src/fonts/Finador-*.woff` and `.woff2` (32 files)
- Create: `packages/feldspar/src/framework/fonts/Nunito.woff2`
- Create: `packages/feldspar/src/framework/fonts/NunitoSans-Italic-VariableFont_wght.woff2`
- Create: `packages/feldspar/src/framework/fonts/NunitoSans-VariableFont_wght.woff2`
- Create: `packages/feldspar/src/framework/fonts/OFL.txt`
- Modify: `packages/feldspar/src/framework/fonts.css`
- Modify: `packages/feldspar/tailwind.config.js`
- Modify: `packages/feldspar/rollup.config.js` (font copy path update)

**Secondary (data-collector — manual update needed):**
- Modify: `packages/data-collector/tailwind.config.js` — update Finador → Nunito font references
  (spec says "pure feldspar" but data-collector has 18 Finador refs that would break; this
  deviation is justified to keep the build working)

- [ ] **Step 1: Create feature branch**

```bash
git checkout master
git checkout -b feat/eyra-font-nunito
```

- [ ] **Step 2: Cherry-pick the 3 font commits from eyra (in branch-topology order)**

```bash
git cherry-pick fd2c8e41 5eccca12 68b488b3
```

**Order matters:** `fd2c8e41` relocates fonts to `src/framework/fonts/` first;
`5eccca12` then replaces Finador with Nunito in that location.

If conflicts occur in `tailwind.config.js` (likely due to d3i customizations), resolve by:
- Accepting eyra's font family changes (Finador → Nunito)
- Preserving any d3i-specific theme extensions (colors, spacing) that don't exist in eyra

- [ ] **Step 3: Update data-collector tailwind config**

The feldspar `tailwind.config.js` will have Nunito after the cherry-pick, but `packages/data-collector/tailwind.config.js` has its own copy of the Finador font references. Update it to match.

Open `packages/data-collector/tailwind.config.js` and replace all `Finador` font family references with `Nunito Sans` (body text) and `Nunito` (headings), matching the pattern in `packages/feldspar/tailwind.config.js`.

```bash
git add packages/data-collector/tailwind.config.js
git commit -m "chore: sync data-collector tailwind font config to Nunito"
```

- [ ] **Step 4: Verify build passes**

```bash
pnpm run build
```

Expected: Clean build. Font files are copied by rollup-plugin-copy during feldspar build.

- [ ] **Step 5: Verify dev server renders correctly**

```bash
pnpm run start
# Open localhost:3000, confirm text renders in Nunito (not fallback sans-serif)
# Check browser DevTools → Network tab → confirm .woff2 files load
```

- [ ] **Step 6: Merge to master**

```bash
git checkout master
git merge --no-ff feat/eyra-font-nunito -m "$(cat <<'EOF'
feat: replace Finador font with Nunito (open-source)

Cherry-picked from eyra/feldspar 5eccca12 + 68b488b3 + fd2c8e41.
Removes 32 proprietary Finador font files, adds 3 Nunito/NunitoSans
variable font files under OFL license. Bundle size reduction.
Also syncs data-collector tailwind config to use Nunito.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 7: Delete feature branch**

```bash
git branch -d feat/eyra-font-nunito
```

---

### Task 2: Search case-insensitive fix (eyra `ea959135`)

Tiny 2-line change in table search.

**Files:**
- Modify: `packages/feldspar/src/framework/visualization/react/ui/elements/table.tsx`

- [ ] **Step 1: Create feature branch and cherry-pick**

```bash
git checkout master
git checkout -b feat/eyra-search-case-fix
git cherry-pick ea959135
```

This should apply cleanly — it's a 2-line change adding `.toLowerCase()` to search matching.

- [ ] **Step 2: Verify build**

```bash
pnpm run build
```

- [ ] **Step 3: Run feldspar tests**

```bash
cd packages/feldspar && pnpm test && cd ../..
```

- [ ] **Step 4: Merge to master**

```bash
git checkout master
git merge --no-ff feat/eyra-search-case-fix -m "$(cat <<'EOF'
fix: make table search case-insensitive

Cherry-picked from eyra/feldspar ea959135.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
git branch -d feat/eyra-search-case-fix
```

---

### Task 3: Button spinner alignment (eyra `e6289437`)

Layout fix centering the spinner in buttons.

**Files:**
- Modify: `packages/feldspar/src/framework/visualization/react/ui/elements/button.tsx`

- [ ] **Step 1: Create feature branch and cherry-pick**

```bash
git checkout master
git checkout -b feat/eyra-button-spinner
git cherry-pick e6289437
```

- [ ] **Step 2: Verify build**

```bash
pnpm run build
```

- [ ] **Step 3: Manual verification**

```bash
pnpm run start
# Navigate to a page with a submit/donate button
# Trigger the spinner state and confirm it's centered
```

- [ ] **Step 4: Merge to master**

```bash
git checkout master
git merge --no-ff feat/eyra-button-spinner -m "$(cat <<'EOF'
fix: center spinner alignment in buttons

Cherry-picked from eyra/feldspar e6289437.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
git branch -d feat/eyra-button-spinner
```

---

## Chunk 2: Phase 1 — Pure Feldspar Cherry-Picks (Features 4–7)

---

### Task 4: LT/RO translations (eyra `096dcae4` + `8cd1cd87`)

**Scope note:** The spec categorizes this as "pure feldspar," but `096dcae4` modifies
`packages/python/port/script.py` and `script_custom_ui.py` (eyra's example scripts). Since
d3i has its own versions of these files, only the feldspar UI commit (`8cd1cd87`) can be
cleanly cherry-picked. The Python translation strings from `096dcae4` should be manually
ported into d3i's scripts during Phase 6 (platform script modernization), not cherry-picked.

**Files:**
- Modify (via cherry-pick of `8cd1cd87`):
  - `packages/feldspar/src/framework/visualization/react/ui/elements/table.tsx`
  - `packages/feldspar/src/framework/visualization/react/ui/elements/table_card_item.tsx`
  - `packages/feldspar/src/framework/visualization/react/ui/elements/table_page.tsx`
  - `packages/feldspar/src/framework/visualization/react/ui/pages/end_page.tsx`
  - `packages/feldspar/src/framework/visualization/react/ui/prompts/donate_buttons.tsx`
  - `packages/feldspar/src/framework/visualization/react/ui/prompts/file_input.tsx`
- Skip (deferred to Phase 6):
  - `packages/python/port/script.py`
  - `packages/python/port/script_custom_ui.py`

- [ ] **Step 1: Create feature branch**

```bash
git checkout master
git checkout -b feat/eyra-lt-ro-translations
```

- [ ] **Step 2: Cherry-pick only the feldspar UI commit**

```bash
# Skip 096dcae4 (modifies d3i's Python scripts — deferred to Phase 6)
git cherry-pick 8cd1cd87
```

This should apply cleanly since it only touches feldspar UI component files.

- [ ] **Step 3: Verify build**

```bash
pnpm run build
```

- [ ] **Step 4: Run feldspar tests**

```bash
cd packages/feldspar && pnpm test && cd ../..
```

- [ ] **Step 5: Merge to master**

```bash
git checkout master
git merge --no-ff feat/eyra-lt-ro-translations -m "$(cat <<'EOF'
feat: add Lithuanian (LT) and Romanian (RO) UI translations

Cherry-picked from eyra/feldspar 8cd1cd87.
Note: 096dcae4 (Python script translations) deferred to Phase 6
(platform script modernization) since d3i has its own script.py.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
git branch -d feat/eyra-lt-ro-translations
```

---

### Task 5: DISCLAIMER.md (eyra `bb456ec3`)

New root-level file documenting technical limitations of the framework.

**Files:**
- Create: `DISCLAIMER.md` (71 lines, documents payload limits, truncation, client constraints)

- [ ] **Step 1: Create feature branch and cherry-pick**

```bash
git checkout master
git checkout -b feat/eyra-disclaimer
git cherry-pick bb456ec3
```

This creates a new file — no conflicts expected.

- [ ] **Step 2: Review content for d3i applicability**

Read `DISCLAIMER.md` and verify the documented limits match d3i's deployment
(SURF Research Cloud, not Eyra Next). If any limits differ (e.g., server payload
limit), add a note to `docs/decisions/adr-todo.md` for follow-up.

- [ ] **Step 3: Merge to master**

```bash
git checkout master
git merge --no-ff feat/eyra-disclaimer -m "$(cat <<'EOF'
docs: add technical limitations disclaimer

Cherry-picked from eyra/feldspar bb456ec3.
Documents payload limits, dataframe truncation, and client-side constraints.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
git branch -d feat/eyra-disclaimer
```

---

### Task 6: Tailwind CSS v4 migration (eyra `eb621b17` + `f30774c0` + `6cc392c4`)

**This is the most complex Phase 1 feature.** Three sequential commits migrating from
Tailwind CSS v3 to v4. The spec also lists `26c6030c` (postcss v8.5.8 update), but that
commit only changes `pnpm-lock.yaml` — we handle the dependency update via `pnpm install`
after the migration instead of cherry-picking a lockfile.

**Commit sequence (apply in this order):**
1. `eb621b17` — Update PostCSS config to use `@tailwindcss/postcss` plugin
2. `f30774c0` — Add `@config` directive in `styles.css` for v4 config discovery
3. `6cc392c4` — Full migration: `@import 'tailwindcss'` syntax, rename deprecated
   utilities (`flex-shrink-0` → `shrink-0`, `flex-grow` → `grow`), bump tailwindcss
   to ^4.2.1, remove postcss-import and autoprefixer

**Files modified by the 3 commits combined:**
- Modify: `postcss.config.js` (root)
- Modify: `packages/data-collector/postcss.config.js`
- Modify: `packages/feldspar/package.json`
- Modify: `packages/feldspar/src/framework/styles.css`
- Modify: `packages/feldspar/src/framework/visualization/react/ui/elements/bullet.tsx`
- Modify: `packages/feldspar/src/framework/visualization/react/ui/elements/button.tsx`
- Modify: `packages/feldspar/src/framework/visualization/react/ui/elements/check_box.tsx`
- Modify: `packages/feldspar/src/framework/visualization/react/ui/elements/instructions.tsx`
- Modify: `packages/feldspar/src/framework/visualization/react/ui/elements/number_icon.tsx`
- Modify: `packages/feldspar/src/framework/visualization/react/ui/elements/page_icon.tsx`
- Modify: `packages/feldspar/src/framework/visualization/react/ui/elements/pagination.tsx`
- Modify: `packages/feldspar/src/framework/visualization/react/ui/elements/progress_bar.tsx`
- Modify: `packages/feldspar/src/framework/visualization/react/ui/elements/table.tsx`
- Modify: `packages/feldspar/src/framework/visualization/react/ui/elements/table_card.tsx`
- Modify: `packages/feldspar/src/framework/visualization/react/ui/prompts/file_input.tsx`
- Modify: `package.json` (root — adds `@tailwindcss/postcss` dep)
- Modify: `pnpm-lock.yaml` (regenerated, not cherry-picked)

**Conflict risk:** `postcss.config.js` may conflict if d3i has diverged. The root
`postcss.config.js` currently uses `tailwindcss` plugin directly — eyra changes it to
`@tailwindcss/postcss`. `button.tsx` may conflict if the spinner fix (Task 3) already
changed the same lines.

- [ ] **Step 1: Create feature branch**

```bash
git checkout master
git checkout -b feat/eyra-tailwind-v4
```

- [ ] **Step 2: Cherry-pick the 3 Tailwind migration commits**

```bash
git cherry-pick eb621b17
```

**Likely conflict:** `pnpm-lock.yaml` will conflict (different lockfile state). Resolve by:
```bash
git checkout --theirs pnpm-lock.yaml   # accept eyra's version temporarily
git add pnpm-lock.yaml
git cherry-pick --continue
```

We'll regenerate the lockfile properly in Step 4.

If `postcss.config.js` or `package.json` conflict, accept eyra's changes — they're adding
the `@tailwindcss/postcss` package. The current root `postcss.config.js` has 3 plugins
(`postcss-import`, `tailwindcss`, `autoprefixer`); eyra replaces all three with just
`@tailwindcss/postcss`.

```bash
git cherry-pick f30774c0
```

This adds 1 line (`@config`) to `styles.css` — should apply cleanly.

```bash
git cherry-pick 6cc392c4
```

**Likely conflicts:**
- `pnpm-lock.yaml`: Same strategy — accept theirs, regenerate later
- `postcss.config.js`: This commit removes `postcss-import` and `autoprefixer` entries.
  Accept eyra's version (only `@tailwindcss/postcss` remains)
- `button.tsx`: If Task 3's spinner fix touched the same lines, resolve by keeping both
  changes (spinner centering + utility rename `flex-shrink-0` → `shrink-0`)

- [ ] **Step 3: Update data-collector PostCSS config**

After the cherry-picks, check if `packages/data-collector/postcss.config.js` was already
updated by `eb621b17`. If not, update it to match the new pattern:

```javascript
// packages/data-collector/postcss.config.js
export default {
  plugins: {
    '@tailwindcss/postcss': {}
  }
}
```

```bash
git add packages/data-collector/postcss.config.js
git commit -m "chore: sync data-collector postcss config for tailwind v4"
```

- [ ] **Step 4: Regenerate lockfile**

```bash
pnpm install
```

This will resolve any lockfile inconsistencies from the cherry-picks and install the new
`@tailwindcss/postcss` and `tailwindcss@^4.2.1` packages.

Verify postcss version matches eyra's `26c6030c` intent:
```bash
pnpm ls postcss
# Expected: postcss >= 8.5.8
```

```bash
git add pnpm-lock.yaml
git commit -m "chore: regenerate pnpm-lock.yaml for tailwind v4 deps"
```

- [ ] **Step 5: Verify build**

```bash
pnpm run build
```

Expected: Clean build. If CSS compilation errors occur, check:
- `styles.css` has `@import 'tailwindcss'` (not the old `@tailwind base/components/utilities`)
- `@config '../../../tailwind.config.js'` directive points to the correct relative path
- No remaining `flex-shrink-0` or `flex-grow` classes (renamed to `shrink-0` / `grow`)

- [ ] **Step 6: Run feldspar tests**

```bash
cd packages/feldspar && pnpm test && cd ../..
```

- [ ] **Step 7: Visual verification**

```bash
pnpm run start
# Open localhost:3000
# Verify all styles render correctly — check:
#   - Buttons have correct padding/colors
#   - Tables render with proper borders and spacing
#   - Spinner animation works
#   - File input area styled correctly
```

- [ ] **Step 8: Merge to master**

```bash
git checkout master
git merge --no-ff feat/eyra-tailwind-v4 -m "$(cat <<'EOF'
feat: migrate to Tailwind CSS v4

Cherry-picked from eyra/feldspar eb621b17 + f30774c0 + 6cc392c4.
- PostCSS plugin changed to @tailwindcss/postcss
- Added @config directive for v4 config discovery
- Migrated deprecated utilities (flex-shrink-0 → shrink-0, etc.)
- Updated tailwindcss to ^4.2.1
- Removed postcss-import and autoprefixer (handled by @tailwindcss/postcss)
Postcss v8.5.8 update (eyra 26c6030c) included via pnpm install.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
git branch -d feat/eyra-tailwind-v4
```

---

### Task 7: Status text during submission (eyra `189879f8`, PR #672)

Adds "Transferring data..." text above the donate button while submission is in progress.
Includes translations for en, de, it, es, nl, ro, lt.

**Files:**
- Modify: `packages/feldspar/src/framework/visualization/react/ui/prompts/donate_buttons.tsx`

**Dependency:** Should be applied AFTER Task 4 (LT/RO translations) since both modify
`donate_buttons.tsx` and `189879f8` includes ro/lt translations for the status text.

- [ ] **Step 1: Create feature branch and cherry-pick**

```bash
git checkout master
git checkout -b feat/eyra-submission-status
git cherry-pick 189879f8
```

If conflict in `donate_buttons.tsx` (likely, since Task 4 added ro/lt translation blocks
to the same file), resolve by keeping both: Task 4's translation additions AND the new
status text with its translations. The file uses language-keyed translation objects
(e.g., `{en: "...", nl: "...", ro: "...", lt: "..."}`). Ensure all language keys from
both commits are present in each translation object, and the new `statusText` property
is added alongside existing translation properties.

- [ ] **Step 2: Verify build**

```bash
pnpm run build
```

- [ ] **Step 3: Manual verification**

```bash
pnpm run start
# Open localhost:3000
# Upload a test file → proceed to donation step
# Click "Yes, donate" → verify:
#   1. Button shows spinner
#   2. Text above button changes to "Transferring data... Please keep this window open."
#   3. (If testing with locale) translations appear correctly
```

- [ ] **Step 4: Merge to master**

```bash
git checkout master
git merge --no-ff feat/eyra-submission-status -m "$(cat <<'EOF'
feat: show status text during data submission

Cherry-picked from eyra/feldspar 189879f8 (PR #672).
Displays "Transferring data... Please keep this window open." while
the donate button is spinning. Includes translations for all
supported languages (en, de, it, es, nl, ro, lt).

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
git branch -d feat/eyra-submission-status
```

---

## Chunk 3: Phase 2 — Cross-Package Features (Features 8–11)

These features touch multiple packages (feldspar + python + data-collector). Source from
dd-vu-2026's proven integration rather than eyra directly, since d3i's Python layer and
worker setup differ from eyra's examples.

**Important:** dd-vu-2026 commit `525b70c` is a large monolithic commit bundling many
features together (font, truncation, PayloadFile, dataframe limits, UI changes). We
cannot cherry-pick it wholesale. Instead, extract specific file changes for each feature
using `git show` or `git diff` targeted at individual files.

**Prerequisite:** Ensure the `dd-vu-2026` remote is added and fetched (see Prerequisites).

---

### Task 8: PayloadFile / sync file reader (eyra `0b2a8c9f`, dd-vu-2026 `525b70c` + `075c934`)

Replaces the current approach of copying files into Pyodide's virtual filesystem (WORKERFS)
with direct streaming via FileReaderSync. This reduces memory usage — files are read
on-demand via slicing instead of fully copied.

**Current state:**
- `packages/data-collector/src/App.tsx` uses `d3i_py_worker.js` (copies files to FS)
- `packages/data-collector/public/d3i_py_worker.js` (154 lines, WORKERFS approach)
- `packages/data-collector/public/py_worker.js` exists but is basic, not the PayloadFile version
- `packages/python/port/api/file_utils.py` does NOT exist
- `packages/python/port/main.py` has no PayloadFile handling

**Target state (from dd-vu-2026):**
- `App.tsx` references `py_worker.js` (FileReaderSync approach)
- `py_worker.js` passes a FileReaderSync-backed reader as PayloadFile
- New `file_utils.py` provides `AsyncFileAdapter` wrapping the JS reader
- `main.py` auto-wraps PayloadFile instances with AsyncFileAdapter

**Files:**
- Create: `packages/python/port/api/file_utils.py` (124 lines)
- Modify: `packages/python/port/main.py` (add PayloadFile wrapping + file_utils import)
- Modify: `packages/data-collector/public/py_worker.js` (replace with PayloadFile version)
- Modify: `packages/data-collector/src/App.tsx` (switch workerUrl)

- [ ] **Step 1: Create feature branch**

```bash
git checkout master
git checkout -b feat/eyra-payload-file
```

- [ ] **Step 2: Extract file_utils.py from dd-vu-2026**

```bash
git show dd-vu-2026/master:packages/python/port/api/file_utils.py \
  > packages/python/port/api/file_utils.py
git add packages/python/port/api/file_utils.py
git commit -m "feat: add AsyncFileAdapter for PayloadFile support

Provides a Python file-like wrapper around the JS FileReaderSync reader
object. Supports read(), seek(), tell(), close(), and context manager protocol.
Sourced from dd-vu-2026 (commit 525b70c, originally eyra PR #482).

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

- [ ] **Step 3: Update main.py for PayloadFile wrapping**

Open `packages/python/port/main.py` and add:
1. Import `AsyncFileAdapter` from `port.api.file_utils`
2. In the `ScriptWrapper.send()` method (or equivalent command dispatch), add logic to
   detect `PayloadFile` type and wrap with `AsyncFileAdapter`:

```python
if data and getattr(data, '__type__', None) == "PayloadFile":
    data.value = AsyncFileAdapter(data.value)
```

Reference dd-vu-2026's `main.py` for exact placement:
```bash
git show dd-vu-2026/master:packages/python/port/main.py
```

Compare with current `main.py` and apply only the PayloadFile-related changes.

```bash
git add packages/python/port/main.py
git commit -m "feat: wrap PayloadFile with AsyncFileAdapter in main.py

Sourced from dd-vu-2026 (commit 525b70c).

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

- [ ] **Step 4: Update py_worker.js**

Extract the PayloadFile-aware worker from dd-vu-2026. **This intentionally overwrites**
the existing `py_worker.js` entirely (the current version is a basic worker that still
copies files to FS; dd-vu-2026's version passes a FileReaderSync reader directly):
```bash
git show dd-vu-2026/master:packages/data-collector/public/py_worker.js \
  > packages/data-collector/public/py_worker.js
```

Review the diff between the old and new `py_worker.js`. The key change is that instead of
copying file data into Pyodide's virtual FS, it passes a FileReaderSync reader object
directly as a `PayloadFile`.

**Keep `d3i_py_worker.js` as fallback** — do not delete it yet. It serves as rollback.

```bash
git add packages/data-collector/public/py_worker.js
git commit -m "feat: update py_worker.js for PayloadFile (FileReaderSync)

Replaces WORKERFS file copy with direct FileReaderSync-backed reader.
Keeps d3i_py_worker.js as fallback.
Sourced from dd-vu-2026 (commit 075c934).

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

- [ ] **Step 5: Switch App.tsx to use py_worker.js**

In `packages/data-collector/src/App.tsx`, change the workerUrl from
`"./d3i_py_worker.js"` to `"./py_worker.js"`.

```bash
git add packages/data-collector/src/App.tsx
git commit -m "feat: switch data-collector to PayloadFile worker

Sourced from dd-vu-2026 (commit 075c934).

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

- [ ] **Step 6: Verify build**

```bash
pnpm run build
```

- [ ] **Step 7: Run Python tests**

```bash
cd packages/python && poetry run pytest -v && cd ../..
```

- [ ] **Step 8: Manual verification**

```bash
pnpm run start
# Open localhost:3000
# Upload a test file (e.g., a small Instagram/Facebook export zip)
# Verify the file is processed successfully
# Check browser DevTools console for any worker errors
```

- [ ] **Step 9: Merge to master**

```bash
git checkout master
git merge --no-ff feat/eyra-payload-file -m "$(cat <<'EOF'
feat: add PayloadFile / sync file reader

Replaces WORKERFS copy-to-FS approach with FileReaderSync streaming.
Files are read on-demand via slicing, reducing memory usage.
Sourced from dd-vu-2026 (525b70c + 075c934, originally eyra PR #482).

Key changes:
- New file_utils.py with AsyncFileAdapter
- main.py wraps PayloadFile with AsyncFileAdapter
- py_worker.js passes FileReaderSync reader as PayloadFile
- App.tsx switches to py_worker.js

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
git branch -d feat/eyra-payload-file
```

---

### Task 9: Dataframe size limits (eyra `bd7bf248`, dd-vu-2026 `525b70c`)

Adds two-tier dataframe truncation: Python truncates to 10,000 rows before sending to
the UI; the UI hard-caps at 50,000 rows as a safety net.

**Current state:**
- `packages/python/port/api/props.py`: No `data_frame_max_size` field, no `__post_init__`
- `packages/feldspar/src/framework/visualization/react/ui/prompts/consent_table.tsx`: No truncation logic

**Files:**
- Modify: `packages/python/port/api/props.py` (add `data_frame_max_size` field + `__post_init__` truncation)
- Modify: `packages/feldspar/src/framework/visualization/react/ui/prompts/consent_table.tsx` (add UI truncation)
- Dependency: Task 10 (truncation utility) provides `truncateRows` and `MAX_ROWS` used by
  `consent_table.tsx`. **Create Task 10's files first**, or combine Tasks 9+10 into a
  single branch.

**Recommended approach:** Combine Tasks 9 and 10 into a single branch since they're
tightly coupled (consent_table.tsx imports from truncation.ts).

- [ ] **Step 1: Create feature branch**

```bash
git checkout master
git checkout -b feat/eyra-dataframe-limits
```

- [ ] **Step 2: Add truncation utility (Task 10 files)**

Create `packages/feldspar/src/framework/utils/truncation.ts`:

```typescript
import { PropsUITableRow } from '../types/elements'

export const MAX_ROWS = 50000

export function truncateRows(rows: PropsUITableRow[], maxRows: number = MAX_ROWS) {
  const truncatedRowCount = Math.max(0, rows.length - maxRows)
  const truncatedRows = rows.slice(0, maxRows)
  return { truncatedRows, truncatedRowCount }
}
```

Create `packages/feldspar/src/framework/utils/truncation.test.ts`:

```typescript
import { truncateRows, MAX_ROWS } from './truncation'

describe('truncateRows', () => {
  const makeRows = (n: number) =>
    Array.from({ length: n }, (_, i) => ({ id: `${i}`, cells: {} }))

  test('under max limit → no truncation', () => {
    const rows = makeRows(10)
    const { truncatedRows, truncatedRowCount } = truncateRows(rows)
    expect(truncatedRows).toHaveLength(10)
    expect(truncatedRowCount).toBe(0)
  })

  test('at max limit → no truncation', () => {
    const rows = makeRows(MAX_ROWS)
    const { truncatedRows, truncatedRowCount } = truncateRows(rows)
    expect(truncatedRows).toHaveLength(MAX_ROWS)
    expect(truncatedRowCount).toBe(0)
  })

  test('over max limit → truncates to max', () => {
    const rows = makeRows(MAX_ROWS + 100)
    const { truncatedRows, truncatedRowCount } = truncateRows(rows)
    expect(truncatedRows).toHaveLength(MAX_ROWS)
    expect(truncatedRowCount).toBe(100)
  })

  test('preserves first N rows', () => {
    const rows = makeRows(10)
    const { truncatedRows } = truncateRows(rows, 5)
    expect(truncatedRows.map(r => r.id)).toEqual(['0', '1', '2', '3', '4'])
  })

  test('empty array', () => {
    const { truncatedRows, truncatedRowCount } = truncateRows([])
    expect(truncatedRows).toHaveLength(0)
    expect(truncatedRowCount).toBe(0)
  })

  test('uses default MAX_ROWS', () => {
    const rows = makeRows(MAX_ROWS + 1)
    const { truncatedRowCount } = truncateRows(rows)
    expect(truncatedRowCount).toBe(1)
  })
})
```

```bash
mkdir -p packages/feldspar/src/framework/utils
git add packages/feldspar/src/framework/utils/truncation.ts \
        packages/feldspar/src/framework/utils/truncation.test.ts
git commit -m "feat: add UI-level dataframe truncation utility

Caps table display at 50,000 rows as safety net.
Sourced from dd-vu-2026 (commit 525b70c, originally eyra).

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

- [ ] **Step 3: Run truncation tests**

```bash
cd packages/feldspar && pnpm test && cd ../..
```

Expected: All 6 truncation tests pass. If jest isn't configured to find files in
`framework/utils/`, check whether a `jest.config.js` is needed. dd-vu-2026 may have
added one — check with:
```bash
git show dd-vu-2026/master:packages/feldspar/jest.config.js 2>/dev/null
```

- [ ] **Step 4: Add Python-level truncation to props.py**

Open `packages/python/port/api/props.py` and modify `PropsUIPromptConsentFormTable`:
1. Add field: `data_frame_max_size: int = 10000`
2. Add `__post_init__()` method that truncates the dataframe if it exceeds max_size

Reference dd-vu-2026's version for exact implementation:
```bash
git show dd-vu-2026/master:packages/python/port/api/props.py
```

Compare with current `packages/python/port/api/props.py` and apply only the truncation
changes (the `data_frame_max_size` field and `__post_init__` method).

```bash
git add packages/python/port/api/props.py
git commit -m "feat: add Python-level dataframe truncation (10k rows)

Truncates dataframes exceeding data_frame_max_size in PropsUIPromptConsentFormTable.
Sourced from dd-vu-2026 (commit 525b70c, originally eyra bd7bf248).

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

- [ ] **Step 5: Add Python truncation tests**

Create `packages/python/tests/test_dataframe_truncation.py` — extract from dd-vu-2026:
```bash
git show dd-vu-2026/master:packages/python/tests/test_dataframe_truncation.py \
  > packages/python/tests/test_dataframe_truncation.py
```

Review the test file and adjust any imports that reference dd-vu-2026-specific modules.
The tests should import from `port.api.props` and test `PropsUIPromptConsentFormTable`
truncation behavior.

```bash
cd packages/python && poetry run pytest tests/test_dataframe_truncation.py -v && cd ../..
```

Expected: All 11 truncation tests pass.

```bash
git add packages/python/tests/test_dataframe_truncation.py
git commit -m "test: add Python dataframe truncation tests

11 test cases covering under/at/over max_size, custom max_size,
zero/negative defaults, and index reset.
Sourced from dd-vu-2026.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

- [ ] **Step 6: Update consent_table.tsx for UI truncation**

Open `packages/feldspar/src/framework/visualization/react/ui/prompts/consent_table.tsx`
and add:
1. Import `truncateRows, MAX_ROWS` from `../../utils/truncation`
2. In the table rendering logic, apply `truncateRows(rows)` before display
3. If truncation occurred, show a warning (console.warn + optional UI indicator)

Reference dd-vu-2026's version:
```bash
git show dd-vu-2026/master:packages/feldspar/src/framework/visualization/react/ui/prompts/consent_table.tsx
```

Compare with current file and apply only truncation-related changes.

```bash
git add packages/feldspar/src/framework/visualization/react/ui/prompts/consent_table.tsx
git commit -m "feat: wire truncation into consent_table.tsx

Applies 50k UI row cap and logs warning on truncation.
Sourced from dd-vu-2026 (commit 525b70c).

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

- [ ] **Step 7: Verify full build**

```bash
pnpm run build
```

- [ ] **Step 8: Run all tests**

```bash
cd packages/feldspar && pnpm test && cd ../..
cd packages/python && poetry run pytest -v && cd ../..
```

- [ ] **Step 9: Merge to master**

```bash
git checkout master
git merge --no-ff feat/eyra-dataframe-limits -m "$(cat <<'EOF'
feat: add two-tier dataframe size limits

Python truncates to 10,000 rows (configurable via data_frame_max_size).
UI hard-caps at 50,000 rows as safety net.
Sourced from dd-vu-2026 (commit 525b70c, originally eyra bd7bf248 + fd16e34e).

Includes:
- truncation.ts utility + 6 Jest tests (spec feature #10, eyra fd16e34e)
- props.py data_frame_max_size field + __post_init__ truncation
- test_dataframe_truncation.py (11 pytest tests)
- consent_table.tsx wired to truncateRows()

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
git branch -d feat/eyra-dataframe-limits
```

---

### Task 10: (Merged into Task 9)

Truncation tests and utility are combined with Task 9 (dataframe size limits) since
`consent_table.tsx` imports from `truncation.ts`. See Task 9, Steps 2–3.

---

### Task 11: Log forwarder + monitor protocol (eyra PR #663, dd-vu-2026 `a48be83`)

**This is the largest and most complex feature.** Adds structured logging that replaces
ad-hoc console.log and meta_data donations. The dd-vu-2026 implementation has 11 commits
in a well-structured merge branch that can be cherry-picked individually.

**Current state:** Zero logging infrastructure exists in this repo. No `CommandSystemLog`,
no `LogForwarder`, no `WindowLogSource`, no `sendLogs` bridge method, no Python
`LogForwardingHandler`, no queue system in `main.py`.

**Architecture (from dd-vu-2026's integration of eyra PR #663):**
```
Python side:                          TypeScript side:
┌─────────────────────┐               ┌──────────────────────┐
│ logging.getLogger()  │               │ WindowLogSource      │
│ → LogForwardingHandler│              │ (window.onerror etc) │
│ → CommandSystemLog   │               └──────┬───────────────┘
│ → queued in main.py  │                      │
└──────────┬──────────┘               ┌──────┴───────────────┐
           │ (via worker postMessage)  │ LogForwarder         │
           ▼                           │ (buffers, filters)   │
┌──────────────────────┐               └──────┬───────────────┘
│ WorkerProcessingEngine│                      │
│ (forwards to bridge)  │──────────────────────┤
└──────────────────────┘               ┌──────┴───────────────┐
                                       │ Bridge.sendLogs()    │
                                       │ → mono host via      │
                                       │   postMessage        │
                                       └──────────────────────┘
```

**dd-vu-2026 commits (cherry-pick in this order):**

| Order | Commit | Description | Key files |
|-------|--------|-------------|-----------|
| 1 | `0ec849d` | CommandSystemLog Python command | `packages/python/port/api/commands.py` |
| 2 | `b7c1f65` | LogForwardingHandler | `packages/python/port/api/logging.py` |
| 3 | `f5c6945` | Queue system in ScriptWrapper | `packages/python/port/main.py` |
| 4 | `bcb865a` | LogForwarder + WindowLogSource (TS) | `packages/feldspar/src/framework/logging.ts` |
| 5 | `21a68cf` | CommandSystemLog TS type | `packages/feldspar/src/framework/types/commands.ts` |
| 6 | `08e41c3` | sendLogs bridge method | `packages/feldspar/src/live_bridge.ts`, `fake_bridge.ts` |
| 7 | `3d52e37` | Logger in WorkerProcessingEngine | `packages/feldspar/src/framework/processing/worker_engine.ts` |
| 8 | `c0be656` | Wire LogForwarder into Assembly | `packages/feldspar/src/framework/assembly.ts` |
| 9 | `0f29cb9` | logLevel prop in ScriptHostComponent | `packages/feldspar/src/components/script_host_component.tsx`, `packages/data-collector/src/App.tsx` |
| 10 | `f696d8c` | Body padding + playwright timeout | misc |
| 11 | `6d3aa74` | Zod v4 visualization type compat | `packages/feldspar/src/framework/types/` |

**Conflict risk:** Commits 3, 6, 7, 8, 9 modify files that may differ between dd-vu-2026
and this repo (main.py, bridge files, assembly, App.tsx). The bridge files in particular
may have d3i-specific async donation logic.

**Note on `script.py`:** The spec lists `script.py` as a key file for this feature.
dd-vu-2026's logging integration may include log calls in `script.py`. Since d3i has its
own platform-specific scripts, any `script.py` changes are **deferred to Phase 6**
(platform script modernization). If any cherry-pick modifies `script.py`, resolve the
conflict by keeping d3i's current version.

- [ ] **Step 1: Create feature branch**

```bash
git checkout master
git checkout -b feat/eyra-logging
```

- [ ] **Step 2: Cherry-pick Python logging commands (commits 1-2)**

```bash
git cherry-pick 0ec849d
```

This adds `CommandSystemLog` to `packages/python/port/api/commands.py`. Should apply
cleanly since d3i only has 3 command classes (CommandUIRender, CommandSystemDonate,
CommandSystemExit).

```bash
git cherry-pick b7c1f65
```

This creates `packages/python/port/api/logging.py` with `LogForwardingHandler`. New file,
should apply cleanly.

Verify:
```bash
cd packages/python && poetry run pytest -v && cd ../..
```

- [ ] **Step 3: Cherry-pick Python queue system (commit 3)**

```bash
git cherry-pick f5c6945
```

**High conflict risk:** This modifies `packages/python/port/main.py` to add queue-based
command dispatch. d3i's `main.py` may differ from dd-vu-2026's base. If conflicts occur:

1. Reference both versions:
   ```bash
   git show dd-vu-2026/master:packages/python/port/main.py   # target state
   cat packages/python/port/main.py                           # current state
   ```
2. Key changes to preserve from dd-vu-2026:
   - `self.queue: deque = deque()` in ScriptWrapper.__init__
   - `add_log_handler()` method
   - Modified `send()` logic: check queue first, then append new command and return first
   - `start()` calls `wrapper.add_log_handler()`
3. Preserve any d3i-specific logic (platform detection, custom error handling, etc.)

```bash
cd packages/python && poetry run pytest -v && cd ../..
```

- [ ] **Step 4: Cherry-pick TypeScript logging infrastructure (commits 4-5)**

```bash
git cherry-pick bcb865a
```

Creates `packages/feldspar/src/framework/logging.ts` (LogForwarder + WindowLogSource)
and `logging.test.ts`. New files — should apply cleanly.

```bash
git cherry-pick 21a68cf
```

Adds `CommandSystemLog` to `packages/feldspar/src/framework/types/commands.ts`. Should
apply cleanly unless d3i has modified the command types.

```bash
cd packages/feldspar && pnpm test && cd ../..
```

- [ ] **Step 5: Cherry-pick bridge integration (commit 6)**

```bash
git cherry-pick 08e41c3
```

**Moderate conflict risk:** Adds `sendLogs()` to Bridge interface and implements in
`live_bridge.ts` and `fake_bridge.ts`. If d3i has an async donation bridge or modified
bridge interface, conflicts will occur.

If conflicts, add `sendLogs()` method manually to each bridge implementation:
- `live_bridge.ts`: Should forward logs via postMessage to the host
- `fake_bridge.ts`: Should store logs in memory (for testing)

- [ ] **Step 6: Cherry-pick worker + assembly integration (commits 7-8)**

```bash
git cherry-pick 3d52e37
```

Adds logger to `WorkerProcessingEngine`. May conflict if d3i has modified the engine.

```bash
git cherry-pick c0be656
```

Wires `LogForwarder` and `WindowLogSource` into `assembly.ts`. May conflict if d3i
has modified the assembly initialization.

- [ ] **Step 7: Cherry-pick app integration (commits 9-11)**

```bash
git cherry-pick 0f29cb9
```

Adds `logLevel` prop to ScriptHostComponent and wires into data-collector App.tsx.
**Will conflict** with App.tsx if Task 8 already changed the worker URL. Resolve by:
- Keep the `py_worker.js` workerUrl from Task 8 (not `d3i_py_worker.js`)
- Add the `logLevel` prop from this cherry-pick
- Keep any other Task 8 changes to App.tsx intact

```bash
git cherry-pick f696d8c
```

Body padding and playwright timeout — minor, low conflict risk. **Evaluate before applying:**
this may include dd-vu-2026-specific changes (playwright timeouts tuned for VU study).
If the changes are generic framework improvements, apply. If study-specific, skip.

```bash
git cherry-pick 6d3aa74
```

Zod v4 visualization type compatibility. **Evaluate before applying:** check if this repo
uses Zod at all (`grep -r "from 'zod'" packages/`). If no Zod dependency exists, **skip
this commit**. If Zod is present, apply to prevent type errors.

- [ ] **Step 8: Verify full build**

```bash
pnpm run build
```

- [ ] **Step 9: Run all tests**

```bash
cd packages/feldspar && pnpm test && cd ../..
cd packages/python && poetry run pytest -v && cd ../..
```

- [ ] **Step 10: Manual verification**

```bash
pnpm run start
# Open localhost:3000
# Open browser DevTools console
# Upload and process a test file
# Verify:
#   1. No worker errors in console
#   2. Python log messages appear (forwarded via CommandSystemLog)
#   3. Window errors are captured (test by adding a temporary throw)
```

- [ ] **Step 11: Merge to master**

```bash
git checkout master
git merge --no-ff feat/eyra-logging -m "$(cat <<'EOF'
feat: add structured logging via bridge protocol

Replaces ad-hoc console.log with structured log forwarding.
Sourced from dd-vu-2026 (merge a48be83, 11 commits, originally eyra PR #663).

Python side:
- CommandSystemLog command type
- LogForwardingHandler (logging.Handler → CommandSystemLog queue)
- Queue-based command dispatch in ScriptWrapper

TypeScript side:
- LogForwarder (buffers, filters by level, auto-flushes on error)
- WindowLogSource (captures window.onerror, unhandledrejection)
- CommandSystemLog type
- Bridge.sendLogs() method
- WorkerProcessingEngine and Assembly integration
- logLevel prop on ScriptHostComponent

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
git branch -d feat/eyra-logging
```

---

## Chunk 4: Phase 3 (Verification Gate) + Phase 4 (Remaining Changes) + Completion

---

### Task 12: Feldspar verification gate (Phase 3)

After all Phase 1 and Phase 2 features are integrated, diff `packages/feldspar/` between
this fork and dd-vu-2026 to catch anything missed.

**This is an investigation task, not a cherry-pick.** The output is either "all clear"
or a list of gaps to address.

- [ ] **Step 1: Diff feldspar packages**

```bash
git diff HEAD dd-vu-2026/master -- packages/feldspar/
```

Review every difference. Expected categories:

**Acceptable differences (d3i-specific, keep ours):**
- Bridge files (`live_bridge.ts`, `fake_bridge.ts`) if d3i has async donation bridge
- Component files with d3i customizations
- package.json version differences

**Gaps to investigate:**
- Missing utility files
- Missing type definitions
- CSS/style differences not covered by Tasks 1–11
- Translation strings present in dd-vu-2026 but missing here

- [ ] **Step 2: Document findings**

For each gap found, decide:
1. **Include now:** Create a follow-up commit on master
2. **Defer:** Add to `docs/decisions/adr-todo.md` with rationale

```bash
# If any follow-up commits needed:
git checkout master
git checkout -b fix/feldspar-verification-gaps
# ... apply fixes ...
git checkout master
git merge --no-ff fix/feldspar-verification-gaps -m "$(cat <<'EOF'
fix: address feldspar verification gate gaps

<list specific gaps addressed>

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
git branch -d fix/feldspar-verification-gaps
```

- [ ] **Step 3: Diff non-feldspar shared files**

Also check for Python and data-collector gaps:
```bash
git diff HEAD dd-vu-2026/master -- packages/python/port/api/
git diff HEAD dd-vu-2026/master -- packages/data-collector/src/
```

Ignore study-specific differences (dd-vu-2026's `script.py` has VU 2026 platform logic).
Focus on framework-level gaps (missing imports, missing utility functions).

---

### Task 13: Remove unused _build_release.yml (eyra `37c2c892`)

Trivial file deletion — removes a reusable workflow that references Earthly (not used).

**Files:**
- Delete: `.github/workflows/_build_release.yml`

**Note:** This file may not exist in this fork. Check first.

- [ ] **Step 1: Check if file exists and cherry-pick**

```bash
ls .github/workflows/_build_release.yml 2>/dev/null && echo EXISTS || echo "SKIP - file not present"
```

If it exists:
```bash
git checkout master
git checkout -b chore/eyra-remove-build-release
git cherry-pick 37c2c892
git checkout master
git merge --no-ff chore/eyra-remove-build-release -m "$(cat <<'EOF'
chore: remove unused _build_release.yml workflow

Cherry-picked from eyra/feldspar 37c2c892.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
git branch -d chore/eyra-remove-build-release
```

If it doesn't exist, skip this task entirely.

---

### Task 14: Dependency verification (eyra `d3c715d2` + `10cbf186`)

Adds dependency checking to the release process. Two commits: first adds checks to
`release.sh`, second extracts them into a standalone `check-deps.sh`.

**Files:**
- Modify: `release.sh`
- Create: `check-deps.sh`
- Modify: `package.json` (script updates)

**Note:** d3i has its own `release.sh` with a `VITE_PLATFORM` loop for per-platform
builds. Eyra's `release.sh` is simpler. The dependency verification logic should be
extracted and adapted rather than blindly cherry-picked.

- [ ] **Step 1: Create feature branch**

```bash
git checkout master
git checkout -b feat/eyra-dep-verification
```

- [ ] **Step 2: Review eyra's dependency checks**

```bash
git show 10cbf186:check-deps.sh   # the final standalone check script
git show 10cbf186:release.sh      # eyra's release.sh for reference
cat release.sh                    # d3i's current release.sh
```

- [ ] **Step 3: Create check-deps.sh adapted for d3i**

Extract the dependency verification logic from eyra's `check-deps.sh` and adapt it for
d3i's tooling (d3i uses Poetry for Python, pnpm for Node). The script should verify:
- `node` is installed (correct version)
- `pnpm` is installed
- `poetry` is installed
- `python3` is installed
- Any other tools required by d3i's build process

```bash
git add check-deps.sh
chmod +x check-deps.sh
git commit -m "feat: add dependency verification script

Adapted from eyra/feldspar d3c715d2 + 10cbf186.
Verifies node, pnpm, poetry, and python3 are available.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

- [ ] **Step 4: Wire into release.sh**

Add a call to `check-deps.sh` at the top of `release.sh` (before any build steps).
Do NOT replace d3i's release.sh with eyra's — d3i has per-platform build logic.

```bash
git add release.sh
git commit -m "feat: run dependency check at start of release

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

- [ ] **Step 5: Update package.json scripts if needed**

Check eyra's `10cbf186` for package.json script changes and apply any that make sense
for d3i (e.g., a `check-deps` script entry).

- [ ] **Step 6: Merge to master**

```bash
git checkout master
git merge --no-ff feat/eyra-dep-verification -m "$(cat <<'EOF'
feat: add dependency verification for release process

Adapted from eyra/feldspar d3c715d2 + 10cbf186.
Adds check-deps.sh script and wires it into release.sh.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
git branch -d feat/eyra-dep-verification
```

---

### Task 15: CI — Release workflow (eyra 9 commits)

**Evaluate, don't blindly apply.** Eyra's release workflow uses GitHub Actions to build
and publish releases with tagged artifacts. d3i has its own release process (`release.sh`
with per-platform `VITE_PLATFORM` loop + GitHub Pages deployment via `gh-pages.yml`).

**Eyra commits:**
- `858cda49` — Base release workflow
- `fc30ef44` — Fix branch name in artifact
- `504fbe25` — Add GitHub Release creation
- `3f672ead` — Tag format with date
- `1124e4d7` — Reorder tag for chronological sorting
- `048346bc` — Match zip filename with tag
- `239c5876` — Pre-commit hooks in release
- `84e32328` — feature/* branch triggers
- `a6e1ad34` — Fix master branch trigger

**Decision point:** This is flagged in `docs/decisions/adr-todo.md` as "Release workflow:
eyra CI vs d3i per-platform release.sh." The right approach depends on d3i-infra's
release strategy.

- [ ] **Step 1: Review eyra's release workflow**

```bash
git show 858cda49:.github/workflows/release.yml
```

- [ ] **Step 2: Compare with d3i's current CI**

```bash
ls .github/workflows/
cat .github/workflows/gh-pages.yml
cat release.sh
```

- [ ] **Step 3: Decide and document**

Three options:
1. **Adopt eyra's workflow** — cherry-pick all 9 commits, adapt for d3i's per-platform builds
2. **Defer** — d3i's release process works; revisit when d3i-infra aligns on CI strategy
3. **Hybrid** — Take the tagging/artifact naming convention, keep d3i's build logic

Document the decision in `docs/decisions/adr-todo.md` (or create a formal ADR).

- [ ] **Step 4: Implement (if option 1 or 3)**

If adopting:
```bash
git checkout master
git checkout -b feat/eyra-release-workflow
# Cherry-pick and adapt commits...
git checkout master
git merge --no-ff feat/eyra-release-workflow -m "$(cat <<'EOF'
feat: add GitHub Actions release workflow

Adapted from eyra/feldspar (858cda49 + 8 follow-ups).
<describe what was adopted vs adapted>

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
git branch -d feat/eyra-release-workflow
```

---

### Task 16: CI — Dependency-updates workflow (eyra `76ed7890` + `328777be` + `9eaf9473`)

Adds a CI workflow that runs tests on Renovate/Dependabot PRs.

**Files:**
- Create: `.github/workflows/dependency-updates.yml`

**Note:** This repo already has `.github/workflows/dependabot-auto-merge.yml` which
auto-merges Dependabot PRs. The new workflow adds test validation before merge.

- [ ] **Step 1: Create feature branch and cherry-pick**

```bash
git checkout master
git checkout -b feat/eyra-dep-updates-ci
git cherry-pick 76ed7890
```

If conflict (likely in workflow path or trigger config), accept eyra's version and adjust:
- Branch triggers should match this repo's branch naming
- Node/Python versions should match (Node 22, Python 3.13)

```bash
# Skip 328777be if it's a duplicate of 76ed7890 (check with git show --stat)
git cherry-pick 9eaf9473   # renames job to 'test'
```

- [ ] **Step 2: Review and adapt**

```bash
cat .github/workflows/dependency-updates.yml
```

Verify:
- Trigger conditions match this repo's Dependabot/Renovate PR patterns
- Build steps match d3i's build process (`pnpm run build`, `pnpm test`)
- Node/Python version matrix is correct

- [ ] **Step 3: Merge to master**

```bash
git checkout master
git merge --no-ff feat/eyra-dep-updates-ci -m "$(cat <<'EOF'
feat: add CI workflow for dependency update PRs

Cherry-picked from eyra/feldspar 76ed7890 + 9eaf9473.
Runs tests on Renovate/Dependabot PRs before auto-merge.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
git branch -d feat/eyra-dep-updates-ci
```

---

### Task 17: CI — Permissions + cleanup (eyra `447016d7` + `943393fc` + `1790c52e` + `40ffd24c`)

Miscellaneous CI improvements: workflow permissions, redundant workflow removal, LFS
checkout for E2E tests, and test zip LFS files.

- [ ] **Step 1: Review each commit**

```bash
git show --stat 447016d7   # Add permissions to workflows
git show --stat 943393fc   # Remove redundant playwright.yml
git show --stat 1790c52e   # Fix E2E tests: enable Git LFS checkout
git show --stat 40ffd24c   # Add test zip files for truncation (LFS)
```

- [ ] **Step 2: Apply relevant commits**

```bash
git checkout master
git checkout -b chore/eyra-ci-cleanup
```

**`447016d7` (permissions):** Cherry-pick if d3i's workflows lack explicit permissions.
```bash
git cherry-pick 447016d7
```

**`943393fc` (remove playwright.yml):** Only apply if `playwright.yml` exists and is
redundant (E2E tests already run in another workflow).
```bash
ls .github/workflows/playwright.yml 2>/dev/null && git cherry-pick 943393fc || echo "SKIP"
```

**`1790c52e` (LFS checkout):** Apply if d3i uses Git LFS for test fixtures.
```bash
git cherry-pick 1790c52e
```

**`40ffd24c` (test zip LFS):** This adds `.zip` test files tracked by LFS. Apply if
Task 9's truncation tests need these fixtures.

**CAUTION:** CLAUDE.md says never commit `.zip` files. Check if these are test fixtures
needed by the truncation tests. If so, they should be tracked in LFS (not raw git).
If the tests can generate their own fixtures, skip this commit.

- [ ] **Step 3: Merge to master**

```bash
git checkout master
git merge --no-ff chore/eyra-ci-cleanup -m "$(cat <<'EOF'
chore: CI permissions, cleanup, and LFS fixes

Cherry-picked from eyra/feldspar:
- 447016d7: explicit workflow permissions
- 943393fc: remove redundant playwright.yml (if applicable)
- 1790c52e: enable Git LFS checkout for E2E tests
- 40ffd24c: test zip files for truncation testing (LFS)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
git branch -d chore/eyra-ci-cleanup
```

---

## Phase 5: Mono Compatibility Audit (Investigation only)

**This is not an implementation task.** Review d3i-infra/master for mono-specific changes
(bridge, postMessage, env vars) and verify they are preserved after the eyra integration.

- [ ] **Step 1: Identify mono-specific code**

```bash
git diff d3i-infra/master..HEAD -- packages/feldspar/src/live_bridge.ts
git diff d3i-infra/master..HEAD -- packages/feldspar/src/fake_bridge.ts
git diff d3i-infra/master..HEAD -- packages/data-collector/src/
grep -r "postMessage\|VITE_\|NEXT_PUBLIC_" packages/data-collector/src/ packages/feldspar/src/
```

- [ ] **Step 2: Document findings**

Add findings to `docs/decisions/adr-todo.md` under "Mono compatibility layer" entry.
If any mono-specific code was accidentally overwritten during Phases 1–4, create a
fix branch to restore it.

---

## Completion Criteria

All of these must be true before considering this integration complete:

- [ ] All Phase 1 features (Tasks 1–7) merged to master via individual `--no-ff` commits
- [ ] All Phase 2 features (Tasks 8–11) merged to master via individual `--no-ff` commits
- [ ] Feldspar verification gate (Task 12) passed — all gaps addressed or documented
- [ ] Phase 4 features (Tasks 13–17) applied or deferred with documented rationale
- [ ] Phase 5 mono compatibility audit complete
- [ ] `pnpm run build` passes cleanly
- [ ] `cd packages/feldspar && pnpm test` passes
- [ ] `cd packages/python && poetry run pytest -v` passes
- [ ] `pnpm run test:e2e` passes (or known pre-existing failures documented)
- [ ] `docs/decisions/adr-todo.md` updated with integration findings
- [ ] All feature branches deleted (only master remains)
- [ ] Ready to push to origin (daniellemccool/data-donation-task)

### Post-integration

After all features are integrated and verified:

1. **Push to origin:**
   ```bash
   # Remote: git@github.com:daniellemccool/data-donation-task.git
   # Branch: master
   git push origin master
   ```

2. **Future PRs to d3i-infra:** Each feature's merge commit produces a clean diff
   suitable for individual PRs to `d3i-infra/data-donation-task`. PRs can be
   opened per-feature or batched by phase.

3. **Phase 6 (platform script modernization):** Separate planning cycle. Includes:
   - Porting d3i platform scripts to use PayloadFile/AsyncFileAdapter
   - Integrating logging into platform scripts
   - LT/RO Python translations from `096dcae4`
   - Donate helper from `df3a8999`
