# 48HP Schematic Generator — Rollout Plan

Status as of 2026-05-29. The data-driven schematic generator
(`tools/generate_schematic.py`) is built and proven on **block-A**. This document
is the plan for transcribing the remaining blocks. It is the gate doc for that work.

This file is the *rollout
order, symbol gaps, and per-block transcription checklist*.

---

## How a block gets added (the repeatable unit of work)

1. Write `specs/<block>/<block>.nets.yaml`:
   - `parts:` — each `REF: { sym, part?, value }`. `sym` selects a symbol primitive
     (lib symbol + pin geometry) `components/symbols/<sym>.yaml`; `part` (optional)
     binds to the `components/` registry by a `matches[]` string for footprint/MPN;
     passives use `value` only. A sourced part also declares its `symbol:` in
     `component.yaml`; `generate_schematic.py --check` asserts the two agree.
   - `nets:` — `NET_NAME: [REF.PIN, ...]`. Name-based connectivity.
   - `no_connect:` — every pin not in a net (e.g. LM13700 pin 12, THAT2180 pin 7).
   - `boundary:` — nets that leave the sheet to other blocks (doc + label shape).
2. If the block uses a symbol not yet present, add `components/symbols/<token>.yaml`
   (lib_id, body graphics, per-unit pins with their `at` connection point, and a
   `pinout_datasheet:` citation for non-primitives — `tools/symbols.py --check` enforces it).
3. `python3 tools/generate_schematic.py --block <block>` → emits
   `kicad/pogo-<block>.kicad_sch`.
4. `python3 tools/generate_schematic.py --check` must pass (pin coverage +
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
| 1 | **A** Input buffers | audio | OPA1612, BAT54S | — | ✅ DONE + ✅ re-verified 0018 (no behavioral divergence vs plugin). |
| 2 | **B** Output buffers | audio | 2× TL072 | — | ✅ DONE + **aligned 0018**: MAIN (U61) + BP3 tap (U62), non-inverting; **BP3_R→BP3_L output normal added** (J28.3 in block-6-mix); R37→R224. |
| 3 | **1** Pre-gain | audio | 2× OPA1612, 2× DW3 | — | ✅ DONE + **aligned 0018**: ALT path corrected (→ VCA → BP3-only); ALT_L_DET added for the BP3 selector. |
| 4 | **2** Dual LFO | utility | 2× TL072 + 2× MMBT3904 | npn sym (✅), MMBT3904 (✅) | ✅ DONE + **aligned 0018**: both LFOs → MOD_SRC switch; **breathing LED driver** (MMBT3904 current source) replaces half-wave. |
| 5 | **4** VCA | audio | 4× THAT2180, 3× TL072, BAT54S | — | ✅ DONE + **aligned 0018**: +ALT-BP VCA cell (THAT2180 2→4, shared V_ctrl → BP3); VCA_OFS placement fixed; RV24/25→RV44/45. |
| 6 | **5** LP1 | audio | LM13700, OPA1612, TL072, 2× THAT340 | — | ✅ DONE + ✅ re-verified 0018: per-channel expo (true tilt); reaches self-oscillation (matches plugin); hosts shared U9/U10 Q-VCAs (co-owned block-8). |
| 8 | **8** LP2 | audio | LM13700, OPA1612, TL072, THAT340 | — | ✅ DONE + ✅ re-verified 0018: LP1 minus tilt; non-inverting LP output (matches plugin); Q via shared U9/U10 cell B (block-5). |
| 9 | **7** HP | audio | 3× LM13700, OPA1612, TL072, THAT340 | — (reuse) | ✅ DONE + **aligned 0018**: HP output is a unity NON-inverting follower (was a double-inversion bug); Q collapsed to one LM13700 (cell A=L/B=R; U52 removed). |
| 10 | **3** Mod bus | utility | 6× TL074, DW5 | tl074 multi-unit (✅), zener (✅) | ✅ DONE + **aligned 0018**: MOD_SRC switch (SW7/DW5) wired (LFO1/LFO2/EXT); MOD-bus LEDs removed; VCA→raw normal; FOCUS→TILT; 6× TL074 (was 7). |
| 11 | **6** Triple BP + Dist | audio | **split into 7 sections** (svf1-3 / dist1-3 / mix) | cd4053 sym (✅); npn sym (✅) | ✅ DONE + **aligned 0018**: monolith split into `block-6-{svf1,svf2,svf3,dist1,dist2,dist3,mix}` (7 schematics). DIST→SVF reorder; F_REF 400Hz all bands; BP3 ALT-VCA selector (CD4053 U81); per-band TILT ×0.22; variable DRIVE (THAT2180 VCA/band, U85-90); CLIP drivers (U94-96); two-scaler dry/wet mix. Exact drive/clip/mix scaling = Phase-3R. |

Remaining: **none** — all 10 blocks transcribed, `--check` clean, and **aligned to the locked plugin (change 0018)**. Block 6 is now 7 schematics (svf1-3/dist1-3/mix). The shared U9/U10 Q-VCAs are hosted on block-5 (dual-owned, `shared: true`).

### block-6 transcription notes (2026-05-29)
- **CD4053 symbol bug fixed:** the CD4053 symbol (now `components/symbols/cd4053.yaml`) had
  scrambled channel pin numbers (e.g. pin 15 is the Y-channel common, not X1_A; pins 1/2/3 and
  4/5 were swapped) **and** overlapped VEE(7) with X1_C(12) at one coordinate. Both
  corrected against the TI CD4053B datasheet (selects A/B/C = 11/10/9; X com/0/1 =
  14/12/13; Y = 15/2/1; Z = 4/5/3). No other block uses CD4053, so no drift.
- **NOTE (change 0018):** the original monolith was generated by `tools/gen_block6.py`
  (3-group repetition). That monolith (`block-6.nets.yaml`) was **split into 7 hand-authored
  section nets files** (`block-6-{svf1,svf2,svf3,dist1,dist2,dist3,mix}`), which are now the
  source of truth — `gen_block6.py` is **superseded/orphaned** (its single-file output is no
  longer used). Control-board pots and DW5 mode switches still arrive as boundary CV.
- **The 3 original Phase-3R flags — status after change 0018:**
  1. **DRIVE→variable gain — BUILT (0018, Stage 5).** A stereo THAT2180 VCA per band
     (U85-90 + I/V U91-93) now sits at each distortion input, gain set by the DRIVE knob
     (RV33/36/39) + DRIVE CV (MOD_BPn_DIST) into Ec+. A single dB-law VGA per band
     approximates the plugin's per-mode gain — accepted deviation; the **exact knob→Ec+ dB
     law and the knob=0.20⇒unity bias remain Phase-3R bring-up** (like block-4's Ec+).
  2. **DW5 ON-ON-ON → 2-bit encoding — still Phase-3R.** BP{g}_SEL_SC/SEL_WF leave as
     boundary nets to SW4-6; pull-ups (R128) to a 5V logic rail (D7/R29/C27/C28). 5V-high vs
     VDD=+12V is marginal per the CD4053B datasheet → prototype-verify (level shift or
     VDD=+5V). (Same logic-level caveat now also applies to the new BP3 selector ALT_L_DET
     and the CLIP comparator refs.)
  3. **BP_MIX blend — BUILT (0018, Stage 7).** Reworked to the plugin's two independent
     scalers: wet sum (U46/47-A) re-inverted by U48 (G=−1) → BP_WETPOS; a BYPASS dual-gang
     pot (RV30/58) scales dry LP1, a new WET dual-gang pot (RV57/59) scales wet; both sum in
     the final summer (U46/47-B) → per-channel output polarity restore (U27-B=L, U27-A=R) →
     BP_OUT. Wet arranged to **add** with dry; the **exact wet-vs-dry phase across freq/mode
     and the pot tapers remain Phase-3R**.

---

## Symbol primitives (`components/symbols/<token>.yaml`)

Symbols are **authored data**, not code — one self-contained file per primitive, the
filename being the nets `sym:` token. `tools/symbols.py` globs the dir and provides the
emitter (`emit_symbol`), the pin connection-points (`pin_points`, the single source
shared by emit + coverage), multi-unit `placement`, and the `selfcheck()` gate. A
pin's `at` coordinate IS its connection point, so the lib-symbol geometry and the
coverage pin-map cannot drift — the bug class behind the LM13700 / THAT340 / CD4053
fixes (a hand-written `sym_*()` body disagreeing with its `*_pins()` helper). The old
per-symbol `sym_*()` / `*_pins()` functions in `kicad_common.py` are gone; that file
is now only the generic, symbol-agnostic s-expr emitters.

All 16 archetypes are present and self-test clean (`tools/symbols.py --check`, also run
inside `generate_schematic.py --check`):

| `sym` | lib_id | units | datasheet citation |
|---|---|---|---|
| `opamp2` (OPA1612 / TL072 / LM4562 / NE5532) | `Amplifier_Operational:OPA1612` | A,B,pwr | ✅ |
| `opamp4` (TL074) | `Amplifier_Operational:TL074` | A–D,pwr | ✅ |
| `ota` (LM13700) | `Amplifier_Operational:LM13700` | 1 | ✅ datasheet-verified 16-pin |
| `vca` (THAT2180) | `POGO:THAT2180` | 1 | ✅ Input=1…Output=8 |
| `expo` (THAT340) | `POGO:THAT340` | 1 | ✅ SO14 (NPN Q1/Q2 + PNP Q3/Q4) |
| `cd4053` | `Analog_Switch:CD4053` | 1 | ✅ TI CD4053B (no coincident pins) |
| `bat54s` | `Diode:BAT54S` | 1 | ✅ |
| `dw3` / `dw5` (Dailywell DPDT) | `Switch:SW_Dailywell_DW3/5` | 1 | ✅ |
| `zener` (BZX84) | `Diode:D_Zener` | 1 | ✅ (pad 2 = N/C) |
| `diode` / `led` / `r` / `c` / `trimpot` / `jack` | Device:* | 1 | primitive (self-evident) |

The stale 40HP single-pole `sym_spdt`/`sym_sp3t` are **deleted** (the 48HP toggles are
the Dailywell DPDT DW3/DW5). DPDT footprints live in
`components/footprints/Button_Switch_THT.pretty/` and resolve via the registry.

> **Known divergence (warn-first):** the `jack` archetype numbers its pins `1/2/3`
> (T/S/SW) while the QingPu PJ398SM footprint pads are `S/T/TN`. `generate_schematic.py
> --check` prints this as a `WARN` (symbol-pin ⊆ footprint-pad guard) without failing.
> Reconcile the pin-number ↔ pad-name scheme in its own Lane-B change before PCB netlist.

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
| `LFO1_OUT` | block-2 → block-3 | LFO1 normals into MOD_IN tip-switch ring |
| `VCA_OUT_L`, `VCA_OUT_R` | block-4 → block-5 | VCA out to LP1 (inverted; LP1 SUM_AMP restores) |
| `MOD_BUS` | block-3 → block-4 | mod bus → VCA_IN tip-switch normalling |

When transcribing the consuming block, use these exact names on the matching pins.

## block-6 — DONE (split into 7 sections + aligned to plugin, change 0018)

block-6 is complete. The original single-sheet plan in this section (Option-B SVF, distortion
**after** the SVF, single BP_MIX crossfade, a `gen_block6.py` 3-group generation script) was
**superseded by change 0018**: block-6 was split into 7 hand-authored section sheets
(`block-6-{svf1,svf2,svf3,dist1,dist2,dist3,mix}`) and aligned to the locked plugin —

- distortion now runs **before** the SVF (per band), with a per-band **DRIVE VCA** (THAT2180);
- mode is **per-band** `BP{n}_DIST_MODE` (not a global switch);
- the output uses **two independent scalers** `BP_BYPASS` + `BP_WET` (not a single MIX crossfade);
- F_REF = 400 Hz on all three bands; per-band TILT (×0.22 CV); CLIP LED comparators added.

`gen_block6.py` is **superseded/orphaned** (the 7 `specs/block-6-*/*.nets.yaml` files are now the
source of truth). See the rollout table above (row 11), the block-6 §1 + Stage notes, and the
section nets for the current design.

## Shared / cross-block parts → dual ownership + a `shared` flag (decision 2026-05-29, revised again)

Parts that span two blocks are **dual-owned and hosted on the primary block**, not parked in a
synthetic "shared" block. In `components.yaml` the part carries `block: [block-A, block-B]` +
`shared: true` (one refdes, listed once); in the schematic it is **placed on the first-listed
(host) block's sheet**, and the co-owning block reaches it by boundary nets. The earlier
"dedicated shared-q sheet under `block-Q`" approach was removed (no synthetic block / pseudo-spec).

First instance: the LP1/LP2 Q-VCAs **U9** (L) / **U10** (R) (each LM13700: cell A = LP1 Q,
cell B = LP2 Q) + their decoupling/Iabc caps. `components.yaml`: `block: [block-5, block-8]`,
`shared: true`. They live on **block-5's** sheet (`specs/block-5/block-5.nets.yaml`):

- block-5 (LP1, host) wires cell A internally: `LP1_V1_{L,R}` (BP node → OTA In+),
  `LP1_SUMINV_{L,R}` (SUM_AMP virtual ground → OTA In−/Out), `LP1_QIABC_{L,R}` (V_ires→Iabc).
- block-8 (LP2) reaches cell B via boundary nets `LP2_V1_*`, `LP2_SUMINV_*`, `LP2_QIABC_*`
  (produced on block-5's sheet, consumed on block-8's).

The BOM renders such a part under all its blocks (`Block = "block-5, block-8"`); the docs BOM
viewer's group-by-block shows it under each. (The expo converter THAT340 is per-block, not
shared — LP1 has its own U14.)

## Refdes convention for multi-instance parts (decision 2026-05-29)

`specs/components.yaml` keeps grouped refs with `qty>1` for stereo pairs / repeated
parts (e.g. `R3` qty 2 = R_g for L and R). Per-instance **schematic** refdes are
derived by suffix — **L/R** for stereo pairs (`R3`→`R3L`/`R3R`), and letters
`A,B,C…` for non-channel repeats (e.g. block-6 `C15` qty 4 → `C15A…C15D`). This is
non-destructive (no whole-board renumber) and keeps the grouped BOM traceable.
Fix any missing `qty` on grouped rows as you go (block-1 fixed R3–R6).

## Conventions / open decisions

- **Power rails:** currently global labels (`+12V`/`-12V`/`GND`) — uniform with
  signal nets, so the coverage validator treats them identically. Alternative: dedicated
  power-port symbols (a `power:` archetype + emitter would need to be (re)added — the old
  `power_sym()` helper was removed with the rest of the hand-coded symbols). Keep global
  labels unless a board-level sheet needs the power-symbol convention; revisit at board assembly.
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
- [x] block-2 transcribed + verified (LFO rate net FINALIZED; diode/led/trimpot syms; SOD-123 fp)
- [x] block-4 transcribed + verified (THAT2180 pinout/topology CORRECTED; vca sym; 3224W SMD fp)
- [x] block-5 transcribed + verified — hosts the shared U9/U10 Q-VCAs (dual-derivation; LM13700/THAT340 datasheet-corrected;
      per-channel expo; OTA buffer pulldowns added; SOD-123 already present)
- [x] block-8 (LP2) transcribed + verified (mirrors LP1 minus tilt; Q via shared U9/U10 cell B on block-5; IRES_AMP added)
- [x] block-7 (HP) transcribed + verified, then aligned (0018): mono SVF; HP **unity** output follower (polarity fix); Q collapsed to 1 LM13700; IRES_AMP
- [x] block-3 (mod bus) transcribed + verified, then aligned (0018): TL074 quad multi-unit; BZX84C10 ±10V clamp; 18 attenuverter destinations + VCA normal; MOD-bus LEDs removed; MOD_SRC switch wired
- [x] GENERATOR FIX: multi-unit op-amps now placed as separate gate instances (units A/B/power at
      distinct offsets) — previously overlapped → shorted halves; structural_check now unit-aware
      and detects coincident-distinct-net shorts. All blocks regenerated.
- [x] block 6 transcribed + verified, then **split into 7 sections + aligned to plugin (0018)**:
      CD4053 symbol datasheet-corrected; per-channel expo; per-group Q-VCAs; SC/HC/WF stereo mux;
      distortion-before-SVF; per-band DIST_MODE + DRIVE VCA; two-scaler mix. (`gen_block6.py`
      superseded.) — **10/10 blocks aligned**
- [ ] (optional) board-level sheets combining per-block schematics by board
- [ ] (gated separately) enable a KiCad CI job (kiutils) — currently disabled
