#!/bin/bash
# Location-independent wrapper for Python tooling.
# Works from any cwd and any worktree.
#
# Usage:
#   scripts/py-run.sh test [pytest args...]
#   scripts/py-run.sh typecheck [pyright args...]
#   scripts/py-run.sh verify              # runs both test + typecheck

set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
PY_DIR="$REPO_ROOT/packages/python"

if [ ! -d "$PY_DIR" ]; then
    echo "ERROR: packages/python not found at $PY_DIR"
    exit 1
fi

cd "$PY_DIR"

case "${1:-}" in
    test)
        shift
        poetry run pytest -v "$@"
        ;;
    typecheck)
        shift
        npx pyright "${@:-port/platforms/*.py port/helpers/*.py port/api/*.py port/main.py port/script.py}"
        ;;
    verify)
        echo "=== Running tests ==="
        poetry run pytest -v
        echo ""
        echo "=== Running type checks ==="
        npx pyright port/platforms/*.py port/helpers/*.py port/api/*.py port/main.py port/script.py
        echo ""
        echo "=== All checks passed ==="
        ;;
    *)
        echo "Usage: scripts/py-run.sh {test|typecheck|verify} [args...]"
        echo ""
        echo "  test [args]     Run pytest with optional arguments"
        echo "  typecheck       Run Pyright type checker"
        echo "  verify          Run both tests and type checks"
        exit 1
        ;;
esac
