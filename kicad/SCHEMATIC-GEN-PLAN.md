# 48HP Schematic Generator — Rollout Plan

Status as of 2026-05-29. The data-driven schematic generator
(`kicad/generate_schematic.py`) is built and proven on **block-A**. This document
is the plan for transcribing the remaining blocks. It is the gate doc for that work.

See `kicad/README-STALE.md` for the generator's design; this file is the *rollout
order, symbol gaps, and per-block transcription checklist*.

---

## How a block gets added (the repeatable unit of work)

1. Write `kicad/nets/<block>.nets.yaml`:
   - `parts:` — each `REF: { sym, part?, value }`. `sym` selects the lib symbol +
     pin map from `SYM_TABLE`; `part` (optional) binds to the `components/`
     registry by a `matches[]` string for footprint/MPN; passives use `value` only.
   - `nets:` — `NET_NAME: [REF.PIN, ...]`. Name-based connectivity.
   - `no_connect:` — every pin not in a net (e.g. LM13700 pin 12, THAT2180 pin 7).
   - `boundary:` — nets that leave the sheet to other blocks (doc + label shape).
2. If the block uses a symbol/pin-map not yet in `SYM_TABLE`, add it (see gaps below).
3. `python3 kicad/generate_schematic.py --block <block>` → emits
   `kicad/pogo-<block>.kicad_sch`.
4. `python3 kicad/generate_schematic.py --check` must pass (pin coverage +
   structural verify + byte drift). Commit the `.nets.yaml` **and** the `.kicad_sch`.

**Transcription source of truth:** `specs/block-N/spec.md` §1 (panel-verified) +
the relevant `specs/aux/aux-*.md`. ⚠️ All `aux/*` and block §2/§3/§4 are marked
**STALE** (see `specs/STATUS.md`) — transcribing a netlist is the first real
re-verification of those sections. Reconcile any drift against the panel/plugin
(the ground truth) before trusting a STALE schematic detail; note corrections in
the block spec as you go.

---

## Reference scoping (important)

Schematics are generated **per block**, but reference designators are unique
**per board**, not per block. Audio-board blocks (A, 1, 4, 5, 6, 7, 8, B) share one
`U#`/`RV#`/`J#`/`D#` sequence; utility-board blocks (2, 3) share a separate one.
The per-block `.kicad_sch` files are therefore directly mergeable into a board-level
sheet later without renumbering. Keep refs matching `specs/components.yaml`.

---

## Rollout order

Ordered by rising symbol/wiring risk so each step de-risks the next. ✅ = done.

| # | Block | Board | Key actives | New symbols/helpers needed | Notes |
|---|---|---|---|---|---|
| 1 | **A** Input buffers | audio | OPA1612, BAT54S | — (✅ all added) | ✅ DONE |
| 2 | **B** Output buffers | audio | 2× TL072 | — (jack/opamp exist) | ✅ DONE. MAIN (U61) + BP3 tap (U62); BP3/LFO jacks live in other blocks (boundary nets). |
| 3 | **1** Pre-gain | audio | 2× OPA1612, 2× DW3 | DW3 toggle sym + pins (✅ added; DW5 too) | ✅ DONE. DPDT path-select 1×/5×; ALT path protected (R38/R39+D8/D9). |
| 4 | **2** Dual LFO | utility | 2× TL072 | — (trimpots = rpot) | Re-verify `aux-lfo-core` (STALE). |
| 5 | **4** VCA | audio | 2× THAT2180, TL072, BAT54S | **that2180_pins** all-pins | First THAT2180; AMT/OFS trims. |
| 6 | **5** LP1 | audio | 4× LM13700, 2× OPA1612, TL072, THAT340 | **lm13700_pins**, **that340 all-pins use** | First OTA-C SVF; re-verify `aux-ota-c-svf`, `aux-expo-converter`, `aux-q-control` (all STALE). |
| 7 | **8** LP2 | audio | 2× LM13700, 2× OPA1612, THAT340 | — (reuse #6) | Same SVF core as LP1, independent. |
| 8 | **7** HP | audio | 4× LM13700, 2× OPA1612, THAT340 | — (reuse #6) | G=−1 buffer corrects SUM_AMP inversion. |
| 9 | **3** Mod bus | utility | 7× TL074, DW5 | **tl074 all-pins (+power 4/11)**, **DW5 toggle** | 19 attenuverters (repetitive), 19 override jacks. |
| 10 | **6** Triple BP + Dist | audio | 6× LM13700, 6× OPA1612, 3× THAT340, 3× CD4053, 15× TL072, 3× DW5 | — (reuse #5/#9; **cd4053 all-pins use**) | Largest/last; per-band DIST mux + FOCUS + TILT; verify `aux-distortion` (STALE). |

Doing 6→7→8 consecutively reuses the SVF transcription; 9 before 6 introduces the
DW5 toggle and TL074 power helper that 6 also needs.

---

## Symbol / pin-helper gaps to close (in `kicad/kicad_common.py`)

`SYM_TABLE` (in `generate_schematic.py`) maps `sym` → (lib_id, `sym_*()`,
**all-pins fn**). The all-pins fn must return *every electrical pin* so the coverage
validator works. Current state:

| Device | lib symbol | all-pins helper | Gap |
|---|---|---|---|
| OPA1612 / TL072 / LM4562 / NE5532 | ✅ | `opamp_dual_all_pins` ✅ | none |
| BAT54S | ✅ | `bat54s_pins` ✅ | none |
| Jack (PJ398SM) | ✅ | `jack_pins` ✅ | none |
| R / C / pot+trimpot+slider | ✅ | `r_pins`/`c_pins`/`rpot_pins` ✅ | none |
| THAT340 | ✅ | `that340_pins` ✅ (all 16) | wire into SYM_TABLE |
| CD4053 | ✅ | `cd4053_pins` ✅ (all 16) | wire into SYM_TABLE |
| **THAT2180** | ✅ sym | ❌ | add `that2180_pins` (8 pins; pin 7 NC) |
| **LM13700** | ✅ sym | ❌ | add `lm13700_pins` (16 pins; pin 12 NC) |
| **TL074** | ✅ sym | partial (`opamp_quad_pins`, no power) | add `opamp_quad_all_pins` (units 1–4 + V+ 4, V− 11) |
| DW3 toggle (DPDT ON-ON) | ✅ `sym_dw3` | ✅ `dpdt6_pins` | done (sym `dw3` in SYM_TABLE) |
| DW5 toggle (DPDT ON-ON-ON) | ✅ `sym_dw5` | ✅ `dpdt6_pins` (shared) | done (sym `dw5`); same 6-pin body as DW3 |

The stale `sym_spdt`/`sym_sp3t` + `spdt_pins`/`sp3t_pins` are 40HP single-pole
parts and must **not** be reused — the 48HP toggles are the Dailywell DPDT DW3/DW5
(see the switch-standardization work). Footprints already exist in
`kicad/footprints/Button_Switch_THT.pretty/` and resolve via the registry.

---

## Boundary-net registry (cross-block net names)

Per-block sheets join at board level by **matching net name**, so boundary nets
must use one canonical name on both sides. Registry (extend as blocks are added):

| Net | Producer → Consumer | Meaning |
|---|---|---|
| `L_OUT`, `R_OUT` | block-A → block-1 | buffered stereo input |
| `PG_OUT_L`, `PG_OUT_R` | block-1 → block-VCA | main pre-gain out (post 1×/5× toggle) |
| `ALT_OUT_L`, `ALT_OUT_R` | block-1 → block-6 | ALT path direct into BP (post toggle) |
| `LP2_OUT_L`, `LP2_OUT_R` | block-8 → block-B | final LP2 stereo to MAIN buffers |
| `BP3_TAP_L`, `BP3_TAP_R` | block-6 → block-B | BP3 group tap to BP3 buffers |
| `BP3_L_OUT`, `BP3_R_OUT` | block-B → block-6 | buffered BP3 to panel jacks J27/J28 |

When transcribing the consuming block, use these exact names on the matching pins.

## Refdes convention for multi-instance parts (decision 2026-05-29)

`specs/components.yaml` keeps grouped refs with `qty>1` for stereo pairs / repeated
parts (e.g. `R3` qty 2 = R_g for L and R). Per-instance **schematic** refdes are
derived by suffix — **L/R** for stereo pairs (`R3`→`R3L`/`R3R`), and letters
`A,B,C…` for non-channel repeats (e.g. block-6 `C15` qty 4 → `C15A…C15D`). This is
non-destructive (no whole-board renumber) and keeps the grouped BOM traceable.
Fix any missing `qty` on grouped rows as you go (block-1 fixed R3–R6).

## Conventions / open decisions

- **Power rails:** currently global labels (`+12V`/`-12V`/`GND`) — uniform with
  signal nets, so the coverage validator treats them identically. Alternative:
  `power_sym()` symbols. Keep global labels unless a board-level sheet needs the
  power-symbol convention; revisit at board assembly.
- **No-connect policy:** prefer listing real NC pins (datasheet NC, spare half of a
  dual, unused switch lug) in `no_connect` over inventing tie nets. The validator
  requires every pin be wired or NC, so this is enforced.
- **Footprints:** all block-A parts resolve. Pots/trimpots/sliders/toggles resolve
  via panel-type footprints; verify each `part:` string has a registry `matches[]`
  entry as blocks are added (missing → blank Footprint, not an error — grep for
  empty `(property "Footprint" ""` after generating).
- **Layout:** auto-grid (non-overlap only); connectivity is by name, so placement
  aesthetics don't affect correctness. A nicer per-block layout can come later.

---

## Done / definition of complete for the generator

- [x] block-A vertical slice + framework + CI gate
- [x] BAT54S SOT-23 footprint vendored; structural verifier
- [x] block-B transcribed + verified
- [x] block-1 transcribed + verified (DW3/DW5 symbols; refdes-suffix convention)
- [ ] blocks 2, 4, 5, 6, 7, 8, 3 transcribed + verified
- [ ] (optional) board-level sheets combining per-block schematics by board
- [ ] (gated separately) enable a KiCad CI job (kiutils) — currently disabled
