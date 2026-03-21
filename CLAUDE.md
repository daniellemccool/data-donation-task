# CLAUDE.md — daniellemccool/data-donation-task

This repo is a personal fork of `d3i-infra/data-donation-task` used to systematically
integrate changes from `eyra/feldspar` (and `eyra/feldspar` develop), test them, and
port them upstream via PR once proven working.

- **Never commit to `master`** — use `feat/*` / `fix/*` / `chore/*` + PR
- Use `superpowers:using-git-worktrees` before executing any plan
- Never push directly to `d3i-infra` repos — changes flow upstream via PR only

## Remotes

| Remote     | Repo                                            | Role                        |
|------------|-------------------------------------------------|-----------------------------|
| `origin`   | `git@github.com:daniellemccool/data-donation-task.git` | This fork (push here) |
| `d3i-infra`| `https://github.com/d3i-infra/data-donation-task.git` | Upstream target (PR only) |
| `eyra`     | `https://github.com/eyra/feldspar.git`          | Upstream source             |

## Tests, Type Checking & Build

**Use these canonical commands — never call pytest or pyright directly:**

```bash
pnpm test               # run Python tests (alias for test:py)
pnpm test:py            # run Python tests (works from any cwd/worktree)
pnpm test:py -- tests/test_specific.py -q  # run specific tests
pnpm typecheck:py       # run Pyright type checker
pnpm verify:py          # run both tests + type checks
pnpm doctor             # check environment setup
pnpm run build          # full build (Python wheel + feldspar + data-collector)
pnpm run start          # dev server at localhost:3000
```

**If verification fails because the environment is broken, do not skip silently — report the blocker explicitly.** Run `pnpm doctor` to diagnose.

## Forbidden

- **Never commit** `.zip`, DDP files, or anything in `tests/data/`, `tests/fixtures/`
- Real DDPs: `~/data/d3i/test_packages/` — outside repo, never in version control

## Architecture

See `docs/decisions/` for ADRs. Key architectural decisions:
- `feldspar/` is upstream infrastructure — almost never modify it
- Custom UI components go in `data-collector/`, not `feldspar/`
- Python dependency direction: `script.py → helpers/ → api/` (never reverse)

## Packages

- `packages/python` — Python extraction scripts (per-platform, script.py)
- `packages/feldspar` — workflow UI framework (React/TypeScript, upstream)
- `packages/data-collector` — host app / dev server
