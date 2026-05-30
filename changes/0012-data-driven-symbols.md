# Change 0012: data-driven symbols — load pinouts/symbols from components/symbols.yaml

- **Slug:** data-driven-symbols   **Branch:** `change/data-driven-symbols`
- **Lane:** B (build-system refactor: schematic generator symbol layer; no plugin DSP / panel geometry / nets connectivity content — regenerated .kicad_sch are connectivity-identical)
- **Status:** OPEN   **Blocks:** all schematic (structural)   **Boards:** n/a
- **Opened:** 2026-05-30

## Intent
Per-device symbol + pinout knowledge is hand-coded in tools/kicad_common.py (sym_*() + *_pins(),
two hand-synced copies) and re-encoded a 3rd time in gen_block6.supply(). That duplication caused
3 shipped pin bugs (LM13700, THAT340, CD4053). Move it to authored data so one pin source drives
both the symbol and the pin-map (kills the drift class), datasheet-cited and machine-checked.

## Scope (maintainer: FULL — all archetypes incl. body graphics, one change)
- New `components/symbols.yaml` (archetype-keyed = the nets `sym:` token): lib_id, ref_prefix,
  pin_names offset/hide, property (ref/value) geometry, per-unit body graphics (rect/polyline/circle
  w/ stroke+fill) + pins ({num,name,at,angle,len,type,font}), placement offsets (was MULTI_UNIT),
  and a pinout_datasheet citation (doc#+page).
- `tools/symbols.py` (new): parse/emit/load + a single `connection_point()` feeding BOTH the emitter
  `(at)` and `pins()` (eliminates the sym↔pins split). kicad_common's sym_*()/*_pins() deleted.
- `generate_schematic.SYM_TABLE` + `MULTI_UNIT` loaded from data; `gen_block6.supply()` looks pin
  numbers up by name from data but keeps the board RAIL POLICY (V+→+12, SUB→−12, INH/VSS→GND).

## Verification plan (per adversarial review)
- symbols.yaml mechanically EXTRACTED from the current functions (not hand-typed); round-trip checked.
- Per-archetype self-test: emitted `(at)` == `pins()` for every pin/unit; new pins() == old *_pins().
- Regenerate all 10 .kicad_sch atomically; verify CONNECTIVITY PARITY (ref.pin→net + pin coords) old
  vs new, not raw bytes. gen_block6 re-run → block-6.nets.yaml byte-identical (free regression check).
- New gates: archetype coverage; datasheet citation (doc#+page); symbol-pin ⊆ footprint-pad (with
  authored nc_pads; skip when no footprint; warn-first).
- Docs: SCHEMATIC-GEN-PLAN "Symbol gaps" → archetype registry; CLAUDE invariants + reword
  "fetch_datasheets enforces symbols datasheet-verified". symbols.yaml is AUTHORED (not in GENERATED.md).

## Decisions log
- 2026-05-30: FULL scope (incl. body graphics), one change — maintainer chose over the agents' lean rec.
- 2026-05-30: hardened via adversarial + review agents (schema field inventory, connection_point unity,
  multi-unit offsets→data, supply policy stays, pin⊆pad subset+nc_pads, doc#+page citations, atomic
  re-baseline + connectivity parity).
