# Change 0011: move scripts/outline_text.sh into tools/

- **Slug:** scripts-into-tools   **Branch:** `change/scripts-into-tools`
- **Lane:** C (move one convenience script; no DSP / panel-geometry / components / nets)
- **Status:** CLOSED   **Blocks:** none   **Boards:** n/a
- **Opened:** 2026-05-30

Intent: the last stray script (`scripts/outline_text.sh`, a wrapper for
`tools/build_panel.py`) lived in its own `scripts/` dir. Moved to `tools/` so all
scripts live there; `scripts/` removed. The script's `REPO_ROOT` is computed from its
own path, so it works unchanged. No references to update. `--check` gates unaffected.
