# Change 0009: consolidate repo — nets→specs, footprints→components, scrub stale

- **Slug:** repo-consolidation   **Branch:** `change/repo-consolidation`
- **Lane:** B (structural/build refactor — edits the schematic generator + `build_components`/`components`/`panel_kicad` path code; no plugin DSP / panel-geometry / nets-connectivity / components.yaml-data change). Not Lane C (it changes a stated invariant and build-system code).
- **Status:** OPEN   **Blocks:** all (structural)   **Boards:** n/a
- **Opened:** 2026-05-29   **Closed:** —   **PR:** —

## Intent

Consolidate so design lives in `specs/`, component sourcing in `components/`, generated/KiCad
artifacts in `kicad/`; remove stale duplication; and clearly mark generated vs authored files.

## Moves & edits (each move + its code edits + regen is atomic)

1. **Netlists → specs.** `kicad/nets/block-N.nets.yaml` → `specs/block-N/block-N.nets.yaml`.
   The former shared-q sheet is **folded into block-5** (its host) under the new shared-resource
   model — no `block-Q` pseudo-block/sheet (see the shared-resource decision below). Edit
   `generate_schematic.py` (`_NETS_DIR` + `_block_files()` to scan `specs/block-*/*.nets.yaml`;
   keep `out_path_for`/`_HERE` so generated `.kicad_sch` stay in `kicad/`) and `gen_block6.py`
   `OUT`. Generated `.kicad_sch` for the unchanged blocks are byte-stable (nicknames, not paths);
   block-5 regenerates to include U9/U10.
2. **Footprints → components.** `kicad/footprints/*.pretty` → `components/footprints/`. Edit
   `_FP_ROOT` in `build_components.py`, `components.py`, `footprint_svg.py`, `panel_kicad.py`,
   **and** the URI literal in `build_components.gen_fplib` →
   `${KIPRJMOD}/../components/footprints/<lib>.pretty`. Only `kicad/fp-lib-table` byte-drifts
   (.kicad_sch/BOM/footprint-SVGs embed `POGO_lib:name` nicknames, not paths).
3. **Delete stale 40HP KiCad**: `generate_control_board.py`, `generate_utility_board.py`,
   `validate_schematic.py`, `validate_utility_board.py`, `pogo-control-board.kicad_sch`,
   `pogo-utility-board.kicad_sch`, `kicad/README-STALE.md`; remove the **dead commented-out
   `kicad-build` CI job** + stale comments in `build.yml`. **Repoint** `pogo.kicad_pro` root
   sheet to a real per-block `.kicad_sch` (placeholder project root until Phase-5R board assembly).
4. **Remove §4 tables** (table only) from all 10 block specs → pointer to the BOM + keep the
   STALE caveat; **preserve** derivations / trim-pot procedures / board-assignment prose; update
   the CLAUDE.md spec template (which mandates §4).
5. **Mark generated files**: `.gitattributes` `linguist-generated` (explicit paths only — never
   `*.svg`, which would catch the plugin input `plugin/res/Pogo.svg`); standardized
   `GENERATED — DO NOT EDIT` banners where safe (SVG/HTML/fp-lib-table; **not** CSV — breaks the
   BOM viewer parser — and **not** `.kicad_sch`); a `GENERATED.md` build-graph manifest with a
   `--check` so it can't rot.

## Sources of truth (target)

- **specs/** = design: intent + topology + netlists + the ref/block/qty/function manifest
  (`specs/components.yaml`, the *design manifest* — distinct from `components/`).
- **components/** = sourcing: parts catalog (`parts/<slug>/`) + footprints + datasheets.
- **kicad/** = generator + generated artifacts (`.kicad_sch`, `fp-lib-table`, `.kicad_pro`).
- panel → `tools/panel-data.yaml`; plugin → `plugin/`; docs site → `docs/`.
- *The `.nets.yaml` is authored design (lives with the block spec); the `.kicad_sch` is a
  generated artifact (lives in `kicad/`). They are linked by `generate_schematic.py --check`,
  not by directory adjacency.*

## Decisions log

- 2026-05-29: nets→specs/block-N; footprints→components/footprints; .kicad_sch + components.yaml stay.
- 2026-05-29: §4 table removed, prose preserved; CLAUDE.md template updated.
- 2026-05-29: delete 40HP cruft incl. dead CI job; **keep + repoint** pogo.kicad_pro.
- 2026-05-29: shared-q → specs/block-Q/ + stub spec.
- 2026-05-29: built-file marking = .gitattributes (explicit paths) + safe banners + gated GENERATED.md.
- 2026-05-29: Shared-resource MODEL change (replaces the block-Q approach): shared parts now carry
  `block: [block-5, block-8]` + `shared: true` in components.yaml (dual ownership, one refdes), and
  the U9/U10 Q-VCAs are folded onto block-5's sheet (host) — `specs/block-Q/` + the shared-q sheet
  removed. BOM renders dual blocks; the docs viewer groups a shared part under each block.
- 2026-05-29: Shared-component clarity (follow-on to §4 removal): block-5/8 §4 pointers now flag
  the shared block-Q Q-VCAs (`U9`/`U10`, owned by `specs/block-Q/`); fixed the stale `IC_Q_AB`
  generic name → `U9/U10` in block-5/8 §3 prose, and corrected the block-5 power line (the shared
  Q-VCAs are 2 ICs: ~4 mA × 2 = 8 mA, block-5 total ~31 mA). `aux/aux-q-control.md` keeps `IC_Q_AB`
  as a generic building-block label (aux convention).
- 2026-05-29: Lane B (build-system surgery), not Lane C. Hardened via adversarial + review agents:
  KiCad ${KIPRJMOD}/../ resolution + the broken .kicad_pro root sheet, atomic-commit ordering,
  CSV-banner hazard, .gitattributes over-glob, §4 prose preservation, full scrub list.

## Phase-5R note

KiCad footprint *nickname* resolution (`POGO_lib:name` → `${KIPRJMOD}/../components/footprints/`)
is not exercised until a board project is assembled (Phase 5R). At that point, verify footprints
resolve when opening the project (no `--check` gate covers KiCad itself).

## Verification

All five CI `--check` gates green in CI order (components → build_components → generate_schematic
→ build_panel); fp-lib-table diff = URI lines only; full-repo grep shows zero live refs to old paths.
