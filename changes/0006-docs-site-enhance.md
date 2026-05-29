# Change 0006: docs site — BOM type/footprint, panel viewer, CI + change-process pages

- **Slug:** docs-site-enhance   **Branch:** `change/docs-site-enhance`
- **Lane:** C (docs + build-tooling — no DSP math / panel geometry / `components.yaml` data / nets connectivity)
- **Status:** OPEN   **Blocks:** none   **Boards:** n/a
- **Opened:** 2026-05-29   **Closed:** —   **PR:** —

## Intent

Expand the GitHub-Pages docs into a useful hub: a richer BOM (part type + footprint previews),
an embedded front-panel viewer, a "what happens on commit" explainer, and a change-process page.

## Summary

- **BOM viewer (`docs/bom.html`)**
  - New **Type** column (Resistor / Capacitor / IC / Trimpot-Pot / Jack / Diode / Switch / LED),
    derived from the ref-designator prefix in `build_components.py` and added to the canonical BOM.
  - **Footprint hover popups**: each Package cell pops a rendered land-pattern SVG.
- **Footprint renderer (`tools/footprint_svg.py`, new)**: parses each vendored `.kicad_mod`
  (pads + silk/fab/courtyard; legacy `module` + `footprint` formats) → a small SVG.
- **`build_components.py`**: `--gen-fp` writes `docs/footprints/<slug>.svg` (19); `--gen-panel`
  copies the panel art to `docs/Pogo.svg`; both, plus `docs/pogo-bom.csv`, are `--check` drift-gated.
- **Front panel (`docs/panel.html`, new)**: embeds `docs/Pogo.svg` in an HTML container (the index
  card now opens this instead of the raw GitHub SVG).
- **`docs/index.html`**: Front Panel card → `panel.html`; new **Change Process** card; new
  **"What happens when you commit"** section (CI gates, builds, artifacts).
- **Change process (`docs/change-process.html`, new)**: lanes A/B/C, `change/<slug>` + slug PR
  titles, `changes/NNNN`, Step 0–8 / G1–G6 — summarized, with CLAUDE.md as the cited source of truth.

## Decisions log

- 2026-05-29: Type column lives in the canonical BOM (benefits the manufacturing CSV too), derived from ref prefix.
- 2026-05-29: Footprint preview = build-rendered SVG popup (per user choice); all 13 used footprints are vendored.
- 2026-05-29: Panel SVG embedded via a gated `docs/Pogo.svg` copy (offline-safe on Pages), like the BOM CSV.
- 2026-05-29: Change-process page is a curated summary; CLAUDE.md remains the source of truth (drift note on the page).

## Verification

Five `--check` gates green (BOM + 19 footprint SVGs + panel copy in sync; schematic 11/11; panel DRC PASS).
All four docs pages well-formed; `bom.html` JS passes `node --check`; footprint slugs match the BOM footprint ids.
