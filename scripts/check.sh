#!/usr/bin/env bash
# Every check LETS's own code must pass before a release: lint, format, types, unit tests, the plugin build, and the
# end-to-end tests. Usage: scripts/check.sh   (needs uv; `npm install` once for OpenSpec)
set -euo pipefail
cd "$(dirname "$0")/.."
uv run --group dev ruff check lib scripts tests/unit
uv run --group dev ruff format --check lib/lets scripts tests/unit
uv run --group dev pyright
uv run --group dev pytest -q
python3 scripts/maint.py build >/dev/null && git diff --exit-code -- plugin >/dev/null || { echo "plugin/ was out of date: rebuilt; commit it"; exit 1; }
python3 scripts/maint.py check
bash tests/run.sh
