# Change 0012: data-driven symbols — load pinouts/symbols from components/symbols.yaml

- **Slug:** data-driven-symbols   **Branch:** `change/data-driven-symbols`
- **Lane:** B (build-system refactor: schematic generator symbol layer; no plugin DSP / panel geometry / nets connectivity content — regenerated .kicad_sch are connectivity-identical)
- **Status:** IMPLEMENTED (awaiting CI green + merge)   **Blocks:** all schematic (structural)   **Boards:** n/a
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

## Implementation (what landed)
- `components/symbols.yaml` (authored): 16 archetypes mechanically extracted from the old
  `kicad_common.sym_*()` bodies — lib_id, pin_names, ref/value property geometry, per-unit body
  graphics + pins (`{num,name,at,angle,len,type,font}`), `placement` (was `MULTI_UNIT`), and a
  `pinout_datasheet` citation per non-primitive.
- `tools/symbols.py` (new): tokenizer + `parse_symbol`/`emit_symbol`, a single `connection_point()`
  feeding BOTH the emitted pin `(at)` and `pin_points()`, plus `placement`/`pin_number`/`all_pin_numbers`
  and `selfcheck()`. `python3 tools/symbols.py --check` → 16 archetypes OK.
- `tools/kicad_common.py`: slimmed from 1030 → ~90 lines. Now ONLY the generic, symbol-agnostic
  emitters (`reset/uid/emit/begin_schematic/end_schematic/place_symbol/global_label/connect_pin`).
  Every `sym_*()` / `*_pins()` / `_opamp_triangle` / `_sym_dpdt` / `power_sym` / `import math` deleted.
- `tools/generate_schematic.py`: `_SYMS = symbols.load()`; emits via `S.emit_symbol`, places via
  `S.placement` / `S.pin_points`. `--check` now also runs the archetype self-test (fails on
  malformed/uncited symbol) and a warn-first symbol-pin ⊆ footprint-pad advisory.
- `tools/gen_block6.py`: `supply()` resolves rail pins by NAME from data (`_SYM`/`_RAIL`), board rail
  POLICY unchanged → `specs/block-6/block-6.nets.yaml` regenerates byte-identical.

## Verification (actual)
- `tools/symbols.py --check` → OK (16 archetypes); self-test covers structure, pin-number uniqueness,
  emit→parse→emit byte-stability, multi-unit placement coverage, and datasheet-citation non-placeholder.
- All 5 CI gates green: `components.py`, `fetch_datasheets.py`, `build_components.py`,
  `generate_schematic.py` (10/10 blocks OK), `build_panel.py` (DRC PASS).
- All 10 regenerated `.kicad_sch` differ from HEAD by **whitespace only** (new emitter writes each pin
  on one line vs the old wrapped form) — verified via whitespace-collapsed compare; zero connectivity /
  pin-coordinate / lib_id change. KiCad-equivalent.
- `gen_block6` re-run → `block-6.nets.yaml` byte-identical (free regression check).
- pin⊆pad advisory surfaced one **pre-existing** divergence: `jack` numbers pins `1/2/3` vs footprint
  pads `S/T/TN` → emitted as `WARN` (non-failing), logged for a follow-up Lane-B reconciliation.

## Decisions log
- 2026-05-30: FULL scope (incl. body graphics), one change — maintainer chose over the agents' lean rec.
- 2026-05-30: hardened via adversarial + review agents (schema field inventory, connection_point unity,
  multi-unit offsets→data, supply policy stays, pin⊆pad subset+nc_pads, doc#+page citations, atomic
  re-baseline + connectivity parity).
- 2026-05-30: symbol self-test + datasheet-citation gate fold into `generate_schematic.py --check`
  (no new CI step → "five gates" invariant preserved). pin⊆pad kept **warn-first** so the known jack
  pad-name mismatch surfaces without failing CI on pre-existing state.
- 2026-05-30: `.kicad_sch` re-baseline accepted as whitespace-only (lib_symbols pin formatting); the
  earlier "byte-identical" target applied to the authored `block-6.nets.yaml`, not the generated sheets.
