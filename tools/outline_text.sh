#!/usr/bin/env bash
# Regenerate all panel outputs (Pogo-source.svg, Pogo.svg, panel-debug.html).
# Prefer using this over calling build_panel.py directly — it ensures Pogo.svg
# (the Inkscape path-converted file VCV Rack loads) is always in sync.
# Requires: inkscape >= 1.0 on PATH, python3, pyyaml
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${REPO_ROOT}"
python3 tools/build_panel.py
