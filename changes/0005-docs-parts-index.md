# Change 0005: docs landing page — parts/code/BOM/schematic links + BOM viewer

- **Slug:** docs-parts-index   **Branch:** `change/docs-parts-index`
- **Lane:** C (docs + build-tooling — touches no DSP math / panel geometry / `components.yaml` data / nets connectivity)
- **Status:** OPEN   **Blocks:** none   **Boards:** n/a
- **Opened:** 2026-05-29   **Closed:** —   **PR:** —

## Intent

Make the GitHub-Pages docs landing page (`docs/index.html`) a real entry point: link the
plugin codebase, the BOM (by project **and** by block), the per-block schematics, the front
panel, and a placeholder for the (pending) PCB layout.

## Plan

- `docs/index.html`: add cards (absolute GitHub URLs, robust to how Pages is served):
  Plugin Source (`plugin/src`), Bill of Materials (→ `bom.html`), Schematics (`kicad/`),
  Front Panel SVG (`plugin/res/Pogo.svg`), and PCB Layout (Phase 5R — pending → board-layout notes).
- `docs/bom.html`: new self-contained interactive BOM viewer — search/sort, toggle
  whole-project vs group-by-block. Fetches `./pogo-bom.csv` relatively.
- `tools/build_components.py`: `--gen-bom` also writes `docs/pogo-bom.csv` (copy of
  `kicad/pogo-bom.csv`); `--check` drift-gates both. Keeps the viewer's data in sync.

## Decisions log

- 2026-05-29: BOM "by block" = interactive `docs/bom.html` viewer (group/filter), not per-block CSV files.
- 2026-05-29: Viewer data via a committed `docs/pogo-bom.csv` copy (build-emitted, `--check`-gated),
  so it works regardless of how `docs/` is published.
- 2026-05-29: Show all five hardware/fab cards incl. a "PCB Layout — Phase 5R (pending)" placeholder
  (no `.kicad_pcb` exists yet; schematics + front-panel SVG do).
- 2026-05-29: Classified Lane C (docs+tooling) per the written lane test, though it edits a build tool.

## Verification

`build_components.py --check` (BOM + docs copy in sync), `generate_schematic.py --check`,
`build_panel.py --check` all green.
