# Change 0016: small panel pots → Song Huei 9mm tall trimmers (finger-adjustable)

- **Slug:** tall-trimmer-pots   **Branch:** `change/tall-trimmer-pots`
- **Lane:** B+panel (hardware part + panel geometry; plugin LOCKED/unchanged — `trimpot`-type controls
  stay `Trimpot` widget / `type: trimpot`). Gates: **G6b** footprint, **G6a** component, **G2** panel layout.
- **Status:** OPEN — ready for close (footprint vendored+bound, **G2 applied & DRC-clean**, **G6a sourced**, **BOM repointed**, `--cpp` bug fixed, GUI synced; all gates green)
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


## Collision model reworked to real fab rules (maintainer-directed)
The DRC overlap check now mirrors real PCB DRC instead of a bounding keepout:
- **Body = the centred ~9.7mm can** (F.Fab circle on the shaft), not the offset KiCad
  outline — matches the round cap you see. Bodies must not OVERLAP (placement).
- **Electrical (named) pads** drawn at REAL copper size; they keep **0.2mm clearance**
  (industry pad-to-pad min — JLCPCB/PCBWay; OSH Park 6mil traces).
- **Mounting legs (unnamed pads)** are structural (case/ground): leg-vs-leg is exempt,
  but a leg intersecting a neighbour's SIGNAL pad still flags.
- **No pad-vs-body cross** — a pad under a raised tall-trimmer body is fine.
Effect: side-by-side and stacked pots clear at ~the body width (≈9.7mm) instead of being
false-flagged by offset pins/legs; live panel 45→23 overlaps (the 23 are real leg↔signal).
Mirrored in tools/editor/drc.js + parity (437 scenarios incl. the real panel); pads now
drawn full-size in the editor (legs fainter). 45 unit tests / parity green.

## G2 applied (2026-05-30)
Maintainer editor pass exported; pasted over `panel-data.yaml`. Attenuverter bank re-spaced
(explicit `cx` per pot; ATT row cy 100→98.996/99.5 to clear the CV-jack row at cy 112 with the
centred R0904N can). `build_panel.py --check` → **DRC PASS — no violations**; full gate stack +
45 unit tests + 437-scenario parity green. Committed with regenerated `Pogo-source.svg` +
`panel-editor.html` (`Pogo.svg` regenerates in CI — inkscape is CI-only).

> **Pogo.cpp widget positions NOT synced** (plugin LOCKED, Lane B; the ATT move is ~1mm cosmetic
> in the module GUI). Also surfaced a tooling bug: `build_panel.py --cpp` emits `cx=0.00` for any
> **column-grid–positioned** component (the LFO/MOD/VCA trimpots + the CV jacks resolve their cx
> from a zone column grid, which `panel_cpp._cx` does not apply — it only reads an explicit `cx`).
> So `--cpp` output cannot be pasted wholesale without zeroing those x positions. Tracked as a
> separate follow-up (teach `panel_cpp` the column-grid resolver, or have it consume resolved
> positions from `panel_svg`).

## G6a + BOM repoint + tool fix (2026-05-30) — DONE
- **`--cpp` generator bug fixed** (`tools/panel_cpp.py`): `_cx` now mirrors
  `build_panel._resolve_comp` — resolves column-grid (`col`+zone `x_start`/`col_pitch`)
  and adds `rules.x_offset`. Was emitting `cx=0.00` for all column-grid components
  (LFO/MOD/VCA trimpots + CV jacks). Verified `--cpp` == authoritative `resolve_components`
  for all 80 widgets.
- **Pogo.cpp widget sync (GUI only):** synced the 18 in-scope attenuverter Y positions to
  the re-spaced panel (cy 100→99.5; LP1_FREQ_ATT 41.91/100→41.79/99.0). DSP `process()`
  untouched → behavior identical (G3 holds). **Pre-existing, out-of-scope drift left as-is
  and documented:** the MOD/VCA cluster (MOD_INPUT/SCALE/OFFSET, VCA_AMT/OFS) sits a full
  column off in the committed Pogo.cpp (predates this branch — panel-data base→current did
  not move it). A follow-up Lane-A "resync plugin GUI to panel" change should fix it now that
  `--cpp` is reliable.
- **G6a part sourced:** `components/parts/songhuei_r0904n/component.yaml` (mpn R0904N, Song
  Huei, Thonk; symbol `trimpot`; footprint `Potentiometer_Songhuei_9mm_TallTrimmer_Vertical`;
  url-only supplier datasheet like alpha; `matches: lin pot / log pot / bipolar pot`).
- **Registry repoint (unique resolution):** moved the three taper tags **off** `alpha_rd901f`
  (it keeps `knob / large knob / xl knob` → still the panel knobs) onto `songhuei_r0904n`.
  Now `lin/log/bipolar pot → R0904N`, `knob/large/xl knob → alpha`. The big freq/focus/dist
  finger-**knobs** stay Alpha; only the small finger-**pots** move to R0904N.
- **RV41/RV43** (HP_RES, LP2_RES) repointed `Bourns 3296W → "lin pot"` (R0904N) — they are
  panel `type: trimpot` RES controls. `bourns_3296w` part is now unreferenced (kept in the
  catalog; no BOM rows).
- **Regenerated:** block-2/3/4 schematics (att/LFO/VCA pot Footprint alpha→R0904N), BOM
  (`kicad/pogo-bom.csv` + `docs/pogo-bom.csv` — 27 control pots now Song Huei R0904N).
  RV41/RV43 are BOM-only (not drawn as block-7/8 symbols), so only their BOM rows changed.
- **All gates green:** components / fetch_datasheets / build_components / generate_schematic /
  build_panel `--check`, plus `test_drc` (45 pass/1 xfail) + 437-scenario parity.

## Pending
- Maintainer load the CI `.vcvplugin` to eyeball the synced attenuverter GUI (behavior unchanged).
- Eventually rename the footprint file to `…_Songhuei_R0904N_…` (filename still says `TallTrimmer`).
- Follow-up (separate change): resync the pre-existing MOD/VCA plugin-GUI column drift; consider
  retiring the now-unreferenced `bourns_3296w` catalog part.
- Close out #0016 (PR `change/tall-trimmer-pots` → dev; squash on green CI).

## Decisions log
- 2026-05-30: maintainer chose Alpha/Song Huei 9mm tall trimmers for all small panel pots, and to drive
  the grid re-layout themselves in the panel editor (grid-first; BOM repoint after).
- 2026-05-30: settled the collision model on the real **Song Huei R0904N** geometry — 9.7mm square
  body, shaft centred, 3 signal pins one edge / 2 snap-in legs the opposite edge. DRC: bodies must
  not overlap + a signal pin in a body fails; electrical copper keeps 0.2mm; leg-vs-leg and
  leg-vs-body exempt, leg-vs-signal-pad flags. Python↔JS parity over 437 scenarios.
- 2026-05-30: G2 layout applied & DRC-clean. Decided NOT to sync Pogo.cpp widget positions in this
  Lane-B change (plugin locked; ~1mm cosmetic move) and to fix the `--cpp` column-grid `cx=0` bug
  as a separate follow-up rather than hand-edit the locked plugin from unreliable generator output.
