# Change 0013: per-file symbol primitives + component-selected symbol

- **Slug:** per-file-symbols   **Branch:** `change/per-file-symbols`
- **Lane:** B (build-system: symbol registry layout + component schema; no plugin DSP / panel geometry / nets connectivity content — schematics + BOM regenerate byte-identical)
- **Status:** OPEN   **Blocks:** all schematic (structural)   **Boards:** n/a
- **Opened:** 2026-05-30

## Intent
`components/symbols.yaml` is a 1659-line monolith holding all 16 symbol archetypes. Make each
symbol a **self-contained primitive file** that's discovered dynamically, and make each sourced
**component select its primitives itself** — so a `components/parts/<slug>/` dir declares its
footprint primitive (already) AND its symbol primitive (new), and adding a symbol = dropping a file.

Maintainer decision: symbols stay SHARED archetypes (opamp2 ← OPA1612/TL072/LM4562/NE5532; r/c/diode
used value-only) — split per-archetype, NOT folded per-MPN (folding would re-duplicate the shared
shape, undoing 0012). Footprints follow the "same idea": the land patterns are already individual
`.kicad_mod` primitives; the component selects the primitive.

## Scope
- Split `components/symbols.yaml` → `components/symbols/<token>.yaml` (16 authored files; filename =
  the nets `sym:` token). `symbols.load()` globs the dir and merges. Delete the monolith.
- Add `symbol: <token>` to each `components/parts/<slug>/component.yaml` (the part selects its symbol
  primitive, mirroring the existing `footprint:` selection).
- `components.py --check`: a declared `symbol:` must resolve to a real symbol primitive.
- `generate_schematic.py --check`: NEW consistency gate — when a nets part has both `part:` and `sym:`,
  the resolved part's declared `symbol:` must equal the nets `sym:` (catches wiring a part with the
  wrong symbol). Nets `sym:` stays the connectivity source (value-only parts keep it standalone).

## Verification plan
- All 10 `.kicad_sch` + `pogo-bom.csv` regenerate BYTE-IDENTICAL (load() returns the same specs, just
  from many files; component.yaml gains a field the BOM doesn't render).
- `tools/symbols.py --check` → 16 archetypes OK after the split.
- All 5 CI gates green.
- Docs: CLAUDE.md tree (symbols.yaml → symbols/), SCHEMATIC-GEN-PLAN archetype section.

## Decisions log
- 2026-05-30: per-archetype files (not per-MPN fold) + component-selected symbol primitive
  (maintainer: "individual files for each component… have the component itself select the primitive…
  each component fully self-contained").
