#!/usr/bin/env bash
# Convert res/Pogo-source.svg text elements to paths for nanosvg compatibility.
# Run this after editing Pogo-source.svg to regenerate res/Pogo.svg.
# Requires: inkscape >= 1.0 on PATH
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${REPO_ROOT}/res/Pogo-source.svg"
DST="${REPO_ROOT}/res/Pogo.svg"

if ! command -v inkscape &>/dev/null; then
    echo "ERROR: inkscape not found on PATH. Install Inkscape >= 1.0." >&2
    exit 1
fi

inkscape \
    --export-text-to-path \
    --export-plain-svg \
    --export-filename="${DST}" \
    "${SRC}"

echo "Generated ${DST} from ${SRC}"
