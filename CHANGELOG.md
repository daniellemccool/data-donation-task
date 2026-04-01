# Changelog

This project follows [semantic versioning](https://semver.org/) starting from v2.0.0.
Earlier releases used sequential numbering (#1-#5) matching the upstream
[eyra/feldspar](https://github.com/eyra/feldspar) convention.

## v2.0.0 — 2026-03-23

Incorporates upstream eyra/feldspar #6 (2026-02-25) and #7 (2026-03-05), plus
d3i extraction consolidation, platform updates, and bridge alignment.

### Breaking

* File delivery uses PayloadFile (FileReaderSync) instead of WORKERFS/PayloadString
* CommandSystemLog forwarding from Python and JS to host platform
* Donation keys changed from `{session_id}` to `{session_id}-{platform_name}`
* script.py rewritten as FlowBuilder orchestrator — forks using the old script.py pattern must migrate
* ScriptWrapper catches all Python exceptions as PII safety boundary (AD0009)

### Added

* FlowBuilder: standard template for per-platform extraction flows (extraction/AD0001)
* ZipArchiveReader: deterministic archive member resolution with cached inventory (extraction/AD0006)
* ExtractionResult dataclass with Counter[str] error counting
* Chrome platform extraction
* Upload validation — file type and size checks before extraction (extraction/AD0003)
* PII-safe logging boundaries — explicit CommandSystemLog yields for host-visible milestones, local loggers for diagnostics (AD0011)
* Per-platform release builds via VITE_PLATFORM env var (fork-governance/AD0005)
* Verification commands: `pnpm test`, `pnpm typecheck:py`, `pnpm verify:py`, `pnpm doctor`
* 74 Python unit tests
* Dependency update CI workflow
* DISCLAIMER.md (EUPL)
* 20+ architectural decision records in `docs/decisions/`

### Changed

* All 9 existing platforms migrated to FlowBuilder + ZipArchiveReader + bilingual headers
* Font: Finador replaced with Nunito (open-source)
* Tailwind CSS v3 → v4
* Dataframe truncation limits (Python + TypeScript) to prevent UI overload
* Status text shown during data submission
* Error page shows user-friendly message instead of stacktrace
* Async donation responses via PayloadResponse (backward-compatible with PayloadVoid)
* Case-insensitive search in consent table (from eyra #6)
* Lithuanian and Romanian translations (from eyra #6)

### Removed

* `d3i_example_script.py` — superseded by FlowBuilder pattern
* `donation_flows/` extraction system — consolidated into FlowBuilder (AD0006)
* `script_custom_ui.py` — eyra demo script, not used by d3i platforms
* `d3i_py_worker.js` — dead code, all worker traffic through `py_worker.js`
* Dead CI workflows: `_build_release.yml` (Earthly), `playwright.yml`, `release.yml`

### Migration

See [MIGRATION.md](MIGRATION.md) for a guide to updating downstream forks.

## \#5 2025-09-10

* Switched to pnpm for package management
* Switched to Vite for the frontend build system
* Added Spanish language
* Changed: split script.py into a default basic version in script.py and an advanced version script_custom_ui.py
* Added renovate

## \#4 2025-05-02

* Fixed - Explicit loaded event is sent to ensure proper initialization (channel setup)
* Changed: Feldspar is now split into React component and app
* Changed: Allow multiple block-types to interleave on a submission page
* Added: end to end tests using Playwright

## \#3 2025-04-08

* Changed: layout to support mobile screens (enables mobile friendly data donation)
* Added: support for mobile variant of a table using cards (used for data donation consent screen)

## \#2 2024-06-13

* Added: Support for progress prompt
* Added: German translations
* Added: Support for assets available in Python

## \#1 2024-03-15

Initial version
