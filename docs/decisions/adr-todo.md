# ADR Todo

Decision points identified from eyra/feldspar feature analysis. To be written up as
formal ADRs (using `write-adr` skill) as each feature is integrated.

## From eyra/feldspar changes

### Sync file reader / PayloadFile (eyra #482)
- **Decision**: Replace WORKERFS file copy with on-demand FileReaderSync slicing
- **Why it matters**: Previous approach copied entire DDP zip to Pyodide FS, causing
  out-of-memory crashes on large files. New approach reads slices on demand — no copy,
  lower memory, faster.
- **Architectural scope**: Changes the contract between py_worker.js and Python scripts
  (PayloadString → PayloadFile, AsyncFileAdapter wraps JS file reader as Python file-like object)
- **Model**: `feldspar` (bridge/worker protocol change)

### Dataframe size limits — two-tier truncation (eyra milestone 6)
- **Decision**: Truncate consent table data at two levels: 10,000 rows in Python
  (PropsUIPromptConsentFormTable), 50,000 rows in UI (consent_table.tsx)
- **Why it matters**: Large DataFrames cause browser tab crashes. Two tiers give Python
  scripts control over the default while the UI enforces a hard ceiling.
- **Architectural scope**: Python props API gains `data_frame_max_size` field;
  UI gains `MAX_ROWS` constant and truncation utilities
- **Model**: `feldspar` or `extraction` (touches both framework and data presentation)

### Structured logging via bridge layer (eyra #663)
- **Decision**: Replace ad-hoc console.log and meta_data frame donations with a structured
  logging protocol through the bridge layer
- **Why it matters**: Previous approach (donating a "meta_data" frame) mixed debug info with
  participant data. New approach: Python `logging.Handler` → command queue → bridge →
  host `postMessage`. Log entries have level, timestamp, structured data.
- **Components**: LogForwarder (buffered, auto-flush on error), WindowLogSource (captures
  unhandled errors with memory context), LogForwardingHandler (Python), CommandSystemLog
  (backwards-compatible with mono's feldspar_app.js via `json_string` field)
- **Model**: `feldspar` (bridge protocol) — possibly also `fork-governance` (backwards compat
  with mono via json_string)

### Font change: Finador → Nunito (eyra)
- **Decision**: Switch from proprietary Finador font family (32 files) to open-source
  Nunito / Nunito Sans (3 variable font files)
- **Why it matters**: Reduces bundle size, removes proprietary dependency, uses Google Fonts
  with OFL license
- **Model**: `feldspar` (UI framework)

### Tailwind CSS v4 migration (eyra develop)
- **Decision**: Upgrade from Tailwind CSS v3 to v4 using official migration tool
- **Changes**: `@tailwind` directives → `@import 'tailwindcss'`; PostCSS plugin →
  `@tailwindcss/postcss`; deprecated utility renames (flex-shrink-0 → shrink-0, etc.);
  `@config` directive for config discovery
- **Why it matters**: Tailwind v4 is a major version with breaking changes to config and
  PostCSS integration. Affects all downstream forks.
- **Model**: `feldspar` (framework infrastructure)

## From integration process (d3i-specific)

### Mono compatibility layer
- **Decision**: TBD — how to maintain backwards compatibility with d3i-infra's mono
  (self-hosted, SURF Research Cloud) while tracking eyra/feldspar upstream
- **Context**: dd-vu-2026 targeted Eyra Next, not d3i mono. Some bridge/postMessage
  differences may exist (e.g. `json_string` field in CommandSystemLog for backwards compat)
- **Model**: `fork-governance`

### Release workflow: eyra vs d3i
- **Decision**: TBD — whether to adopt eyra's GitHub Actions release workflow, keep d3i's
  per-platform release.sh, or combine both
- **Current state**: d3i uses local `release.sh` (per-platform VITE_PLATFORM loop) +
  `gh-pages.yml` CI deploy. Eyra's 9-commit release workflow (858cda49 + follow-ups)
  was reviewed during integration but not ported — it targets their single-build
  milestone/develop/main model. Dependency verification (check-deps.sh) was ported
  independently.
- **Context**: eyra has CI-driven releases (milestone/* branches → artifacts); d3i/dd-vu-2026
  has local `release.sh` with VITE_PLATFORM loop
- **Model**: `fork-governance`
