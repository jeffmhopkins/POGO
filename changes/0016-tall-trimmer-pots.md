# Change 0016: small panel pots → Song Huei 9mm tall trimmers (finger-adjustable)

- **Slug:** tall-trimmer-pots   **Branch:** `change/tall-trimmer-pots`
- **Lane:** B+panel (hardware part + panel geometry; plugin LOCKED/unchanged — `trimpot`-type controls
  stay `Trimpot` widget / `type: trimpot`). Gates: **G6b** footprint, **G6a** component, **G2** panel layout.
- **Status:** OPEN — WIP (footprint vendored + bound; **panel re-layout pending — maintainer editor pass**)
- **Opened:** 2026-05-30

## Intent
Every panel `type: trimpot` control (19 attenuverters, LFO Rate ×2, MOD Scale/Offset, VCA Amt/Ofs, the
per-filter RES pots) is currently bound to the **Bourns 3296W** screwdriver board-trimmer footprint —
wrong for a finger-adjustable panel control. Convert them to **Song Huei 9mm tall trimmers** (Thonk
"ttpots"; Taiwan), which are drop-in compatible with the standard Alpha 9mm vertical land pattern and
come in linear / log / **centre-detent** tapers (centre-detent for the bipolar attenuverters).

## Why this needs a panel re-layout (G2)
A 9mm vertical pot's land pattern is ~13.75 × 13.34 mm (round body offset from the side pins) vs the
3296W's 5.33 × 6.77 mm. The mod/filter control bank is on an **11.43 mm column pitch** with the
attenuverter row at cy=100 directly above the CV jack row at cy=112 — laid out for the tiny trimmer.
With the 9mm footprint, DRC now reports overlaps throughout that region (≈2.3 mm horizontally between
adjacent trimpots; ≈2.57 mm vertically between the ATT row and the jack row). The bank must be
re-spaced (≈12.7 mm pitch and/or rotation, more vertical separation) — a maintainer-driven panel-editor
pass (G2): edit in `docs/panel-editor.html` → Export YAML → assistant pastes over `panel-data.yaml` →
re-DRC → loop until clean.

## Done so far
- Vendored `components/footprints/Potentiometer_THT.pretty/Potentiometer_Songhuei_9mm_TallTrimmer_Vertical.kicad_mod`
  (standard 9mm vertical pads from the RD901F land pattern; knob graphic removed; Song Huei/Thonk cited).
- `components/footprints.yaml`: `trimpot` → the new footprint (ox/oy 7.5/2.5, shaft-centred like the knob).
- Regenerated `docs/panel-editor.html` + `docs/panel-debug.html` (now show the real 9mm keepouts/overlaps).
- **Fixed a pre-existing bug** in `tools/build_panel.py`: the `--editor` path referenced an undefined
  `HTML_EDITOR` (CI only runs `--check`/`--resource`, so the editor-write path was never exercised) →
  now writes `docs/panel-editor.html` only. This unblocks editor regeneration.

## DRC refined to real footprint collisions (maintainer-requested)
The PCB-overlap DRC previously compared each component's **conservative courtyard bounding
box** — which for a 9mm pot wraps the offset side-pins + mounting legs, ~13.75×13.34mm — so
densely interleaved pots were false-flagged even when the round bodies clear. Changed
`_check_pcb_overlaps` (and the editor's live JS DRC) to test the **actual pads + body**:
- `panel_kicad.footprint_shapes(ctype)` — per-feature keepout rects from the `.kicad_mod`
  (each pad as its rect; body = the F.Fab circle for round pots, else the F.Fab bbox).
- `panel_rules._check_pcb_overlaps` now overlaps every pad/body rect of A against B (real
  keepout ⊆ courtyard, so it never regresses an already-passing layout). Message: "footprint
  overlap" instead of "courtyard overlap".
- `panel_editor.py` exports the shapes; `tools/editor/editor.js` `runDRC` mirrors it exactly,
  so the editor's live overlaps match the gate. Use the editor's **kicad** layer to see the
  real pads/body. (Body circle in the Songhuei footprint re-centred on the shaft.)

Effect: courtyard's phantom 2.3×13.34mm overlaps → genuine ones (e.g. a neighbour's signal
pin under a body = 1.8×1.8mm). 9mm pots still need ~12mm pitch (the pin/leg pads collide at
11.43mm in some orientation), but the editor and DRC now agree on the *real* constraint.

## DRC verification suite (reviewed plan WS3 / #3 / WS3.5 — done)
After an adversarial review of the test plan, implemented:
- **WS1 (footprint/body):** `footprint_shapes` body = bbox of the full F.Fab outline (was
  grabbing the tiny indicator circle → jack/knob/pot under-claimed); restored the pot's
  squarish base. Bodies now correct (pot/knob 11.35×9.5, jack 9×12.5, LED its circle).
- **#3 (metric):** `_check_pcb_overlaps` reports boolean + true penetration depth (max over
  colliding feature-pairs of min(dx,dy)), not the lossy max-area pair.
- **WS3 (unit tests):** `tools/test_drc.py` updated to the real pads+body model — proximity
  thresholds derived from `footprint_shapes` via `_touch_sep` (no courtyard magic numbers);
  new `TestRealCollisionModel` locks body=squarish base, trimpot==knob land pattern,
  pin-of-neighbour-under-body collides, clear @14mm, rotation matches the SVG draw,
  full colliding-pair set, penetration message. **41 pass / 1 xfail.**
- **#2 / WS3.5 (parity):** extracted the editor's pure DRC into `tools/editor/drc.js`
  (`PogoDRC`, UMD — browser + Node); `editor.js` now delegates to it (single source);
  `panel_editor.py` embeds it. `tools/test_parity.py` runs Python `_check_pcb_overlaps`
  and the JS twin (via `tools/editor/drc_cli.js` under Node) over 437 scenarios (every
  type × rotation × separation, a cluster, AND the real panel) and asserts identical
  collisions + penetrations. **The gate immediately caught a real drift** — JS read
  `c.rot` while Python/panel-data use `rotate` (JS silently ignored rotation); fixed.
- **CI:** `test_drc` (pytest) + `test_parity` (Node) wired into the Linux gate block,
  before the panel-layout DRC.

## Pending (after the grid is settled)
- **G2:** re-spaced `panel-data.yaml` (maintainer editor pass) → DRC clean → re-sync `--cpp` if positions move.
- **G6a:** source the Song Huei tall trimmer in `specs/components.yaml` + `components/parts/` (+ datasheet).
- Repoint the ~25 `trimpot`-type BOM refs to the Song Huei part (centre-detent linear / log per control).
- Regenerate BOM + schematics; all five `--check` gates green.

## Decisions log
- 2026-05-30: maintainer chose Alpha/Song Huei 9mm tall trimmers for all small panel pots, and to drive
  the grid re-layout themselves in the panel editor (grid-first; BOM repoint after).
