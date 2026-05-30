# Change 0010: repo structure — design/→docs, generators→tools, drop dup + 40HP HTML

- **Slug:** repo-structure-v2   **Branch:** `change/repo-structure-v2`
- **Lane:** B (structural/build refactor — moves build scripts + their CI calls + output paths; no plugin DSP / panel-geometry / nets-connectivity / components.yaml-data change)
- **Status:** OPEN   **Blocks:** all (structural)   **Boards:** n/a
- **Opened:** 2026-05-30   **Closed:** —   **PR:** —

## Intent

Tighten the layout: generated HTML under `docs/`, all build scripts under `tools/`,
`kicad/` = generated KiCad artifacts only.

## Moves

1. **`design/` → `docs/`.** `design/panel-debug.html` → `docs/panel-debug.html`
   (`build_panel.py --design` output repointed). `design/panel-editor.html` was a
   byte-identical **duplicate** of `docs/panel-editor.html` → dropped (build now writes
   only the `docs/` copy). `design/archive/` (15 stale 40HP HTML previews) **deleted**.
   `design/` removed.
2. **`kicad/*.py` → `tools/`.** `generate_schematic.py`, `gen_block6.py`, `kicad_common.py`,
   and `SCHEMATIC-GEN-PLAN.md` → `tools/`. `generate_schematic.py` output path fixed to
   write into `kicad/` explicitly (`_KICAD`). CI calls + all doc refs updated. `kicad/` now
   holds only generated artifacts (`pogo-*.kicad_sch`, `fp-lib-table`, `pogo.kicad_pro`).

## Decisions log

- 2026-05-30: design/→docs; generators→tools (kicad/ = artifacts only); SCHEMATIC-GEN-PLAN→tools.
- 2026-05-30: delete design/archive 40HP HTML; drop the design/ panel-editor duplicate.
- 2026-05-30: deferred (no preference): test_drc.py→tests/, panel-doc consolidation.

## Verification

All five `--check` gates green in CI order; grep shows zero live refs to `design/` or `kicad/*.py`.
