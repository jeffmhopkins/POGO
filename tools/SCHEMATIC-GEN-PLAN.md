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
| 1 | **A** Input buffers | audio | OPA1612, BAT54S | — (✅ all added) | ✅ DONE |
| 2 | **B** Output buffers | audio | 2× TL072 | — (jack/opamp exist) | ✅ DONE. MAIN (U61) + BP3 tap (U62); BP3/LFO jacks live in other blocks (boundary nets). |
| 3 | **1** Pre-gain | audio | 2× OPA1612, 2× DW3 | DW3 toggle sym + pins (✅ added; DW5 too) | ✅ DONE. DPDT path-select 1×/5×; ALT path protected (R38/R39+D8/D9). |
| 4 | **2** Dual LFO | utility | 2× TL072 | diode/led syms + trimpot (✅ added) | ✅ DONE. Rate network FINALIZED (drive-attenuator); SOD-123 footprint vendored; LFO LEDs added to BOM. |
| 5 | **4** VCA | audio | 2× THAT2180, 2× TL072, BAT54S | that2180_pins (✅) | ✅ DONE. THAT2180 pinout/topology CORRECTED from datasheet (current-in/I-V-out); 3224W SMD footprint vendored. |
| 6 | **5** LP1 | audio | LM13700, OPA1612, TL072, 2× THAT340 | lm13700/that340 (✅) | ✅ DONE (dual-derivation). Per-channel expo (true tilt); hosts the shared U9/U10 Q-VCAs (co-owned by block-8); buffer pulldowns added. |
| 8 | **8** LP2 | audio | LM13700, OPA1612, TL072, THAT340 | — (reuse) | ✅ DONE. LP1 minus tilt (single expo); Q via the shared U9/U10 cell B (hosted on block-5); own IRES_AMP added. |
| 9 | **7** HP | audio | 4× LM13700, OPA1612, TL072, THAT340 | — (reuse) | ✅ DONE. Mono SVF; HP inverting output buffer; own Q-VCAs (cell B spare/terminated); IRES_AMP added. |
| 10 | **3** Mod bus | utility | 7× TL074, DW5 | tl074 multi-unit (✅), zener (✅) | ✅ DONE. MB proc + 3 lights + ±10V clamp + 19 destinations (generated); MOD_<DEST> outputs; MOD_SRC deferred. |
| 11 | **6** Triple BP + Dist | audio | 6× LM13700 (int) + 3× LM13700 (Q) + 12× OPA1612/TL072 SVF/aux + 6× THAT340 + 6× CD4053 + 18× TL072 dist/mix | **cd4053 sym pinout FIXED** | ✅ DONE 2026-05-29 (`tools/gen_block6.py`, 418 parts / 239 nets). Option-B DSP-faithful SVF (v1/BP tap); per-channel expo; per-group Q-VCAs (U67-69); SC/HC/WF cells; 2×CD4053/group stereo 1-of-3 mux. 3 Phase-3R flags (below). |

Remaining: **none** — all 10 blocks transcribed and `--check` clean (10/10). The shared U9/U10 Q-VCAs are hosted on block-5 (dual-owned, `shared: true`).

### block-6 transcription notes (2026-05-29)
- **CD4053 symbol bug fixed:** the registered `sym_cd4053`/`cd4053_pins` had scrambled
  channel pin numbers (e.g. pin 15 is the Y-channel common, not X1_A; pins 1/2/3 and
  4/5 were swapped) **and** overlapped VEE(7) with X1_C(12) at one coordinate. Both
  corrected against the TI CD4053B datasheet (selects A/B/C = 11/10/9; X com/0/1 =
  14/12/13; Y = 15/2/1; Z = 4/5/3). No other block uses CD4053, so no drift.
- **Built by script** `tools/gen_block6.py` (3-group repetition, like block-3). Only
  audio-board parts are placed; control-board pots (RV29-39) and DW5 mode switches
  (SW4-6) arrive as boundary CV, exactly like block-5/7/8 scope their panel controls.
- **3 Phase-3R / prototype flags** (under-specified in the STALE specs; signal path wired
  faithfully, control treated as boundary CV — see the YAML header for detail):
  1. **DRIVE→variable gain** — no in-block variable-gain element exists; the 6 distortion
     cells run at fixed minimum gain (still clip at their diode/zener thresholds). DRIVE
     depth is a Phase-3R element fed by BP{g}_DIST CV. The C_WF 47pF caps were relocated
     from the (off-board) drive-pot wiper to the distortion-input nodes as anti-RF caps.
  2. **DW5 ON-ON-ON → 2-bit encoding** — BP{g}_SEL_SC/SEL_WF leave as boundary nets to
     SW4-6; pull-ups (R128) to a 5V logic rail (D7/R29/C27/C28). 5V-high vs VDD=+12V is
     marginal per the CD4053B datasheet → prototype-verify (level shift or VDD=+5V).
  3. **BP_MIX blend** — plugin uses two scalers (BYPASS+WET); BOM models one MIX pot.
     Wired: wet summer → U48 buffer → off-board MIX pot (BP_WETPOS) → wiper returns as
     BP_MIX_CV into the MIX-amp virtual ground (pot = R_wet) + dry via R27. BP_OUT taken
     directly from the (inverting) MIX amps, L/R symmetric (HP re-inverts downstream);
     U27-B + R17 (the BOM's lone output-restore inverter) is redundant here and wired as
     a reserved Phase-3R inverter off the L MIX output.

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

## block-6 readiness (next session — netlist only; all decisions locked, BOM complete)

block-6 is the last block. Its **BOM is 100% complete** (119 rows, committed) and every
design decision is resolved — the netlist is now a pure transcription. Brief for the
fresh pass:

**Locked decisions (with rationale in commit history):**
- **BP resonator = Option B (DSP-faithful):** the plugin BP (`BandpassSVF.hpp`) is the
  same 2-integrator Simper SVF as LP1/HP/LP2 (Q = damping term). So mirror block-5/8 but
  tap **v1 (BP)** instead of v2, with **separate Q-VCA OTAs U67–U69** (one per group,
  cell A = L, cell B = R) injecting damping at the SUM_AMP virtual ground (like shared-q).
- **Per-channel expo (true BP_TILT):** U28–U30 = L expo, U70–U72 = R expo; each fed
  `BP{g}_VCTRL ± V_tilt` (U27-A inverter makes −V_tilt; R127 tilt summers). Mirror block-5.
- **Distortion mux = +3 CD4053 (stereo 1-of-3):** per group, 2 CD4053 (U31/U75, U32/U76,
  U33/U77): muxA selects SC-vs-MID for L(X_A)/R(X_B); muxB selects HC-vs-WF. DW5 (SW4-6)
  is the **mode encoder** → 2 control bits via R128 pull-ups to the 5V logic rail
  (D7 zener + R29 + C27/C28). INH→GND, X_C unused.
- **Q control:** per group, IRES_AMP (U73-A=BP1, U73-B=BP2, U74-A=BP3; U74-B spare) with
  R117/R118/R119, RV9/12/15 V_bias, D13 V_ires clamp, R116 → Q-cell Iabc.

**Distortion cells (per aux-distortion + block-6 spec §2; 6 paths):** SC = gain amp
(U34–39 half A) + 1N4148 chain D4 across feedback; HC = gain amp (half B) + BZX84C5V1
back-to-back zeners D5 (±5.8V); WF = pre-gain (U40–45 half A) + passive 1N4148 clamp
(D6/R24) + folder (half B, R25/R_f_wf): `V_out = 2·V_clamp − V_in`.

**Wet/mix:** U46/U47 half A = per-channel wet sum (R26); half B = MIX (R27 dry from
`LP1_OUT`, R28 fb); U48 = polarity restore (A=L, B=R) → `BP_OUT_{L,R}`. BP3 distorted tap
→ `BP3_TAP_{L,R}` (to block-B); J27/J28 ← `BP3_L_OUT`/`BP3_R_OUT` (from block-B).

**Boundary nets:** in `LP1_OUT_{L,R}` (BP1/BP2 input + dry), `BP3IN_{L,R}` (BP3 input;
ALT/LP1), `BP{g}_VCTRL`, `BP_TILT_CV`, `BP{g}_FOCUS_CV`, `BP{g}_DIST_CV`, `BP_MIX_CV`;
out `BP_OUT_{L,R}`, `BP3_TAP_{L,R}`; `BP3_L_OUT`/`BP3_R_OUT` in.

**Flag at prototype (under-specified in the STALE specs — interpret + document):** the
DRIVE→variable-gain mechanism (one knob → stereo gain), the DW5 ON-ON-ON→2-bit make
pattern, and the BP_MIX blend control element. Wire the signal path faithfully; treat
these controls as boundary CV applied via a Phase-3R control element.

Build with a generation script (3-group repetition, like block-3), iterate to `--check`
clean, then commit → **10/10 blocks**.

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
- [x] block-2 transcribed + verified (LFO rate net FINALIZED; diode/led/trimpot syms; SOD-123 fp)
- [x] block-4 transcribed + verified (THAT2180 pinout/topology CORRECTED; vca sym; 3224W SMD fp)
- [x] block-5 transcribed + verified — hosts the shared U9/U10 Q-VCAs (dual-derivation; LM13700/THAT340 datasheet-corrected;
      per-channel expo; OTA buffer pulldowns added; SOD-123 already present)
- [x] block-8 (LP2) transcribed + verified (mirrors LP1 minus tilt; Q via shared U9/U10 cell B on block-5; IRES_AMP added)
- [x] block-7 (HP) transcribed + verified (mono SVF; HP inverting output buffer; local Q-VCAs cell B terminated; IRES_AMP added)
- [x] block-3 (mod bus) transcribed + verified (TL074 quad multi-unit; BZX84C10 ±10V clamp; 19 destinations generated; MOD LEDs added; MOD_SRC deferred)
- [x] GENERATOR FIX: multi-unit op-amps now placed as separate gate instances (units A/B/power at
      distinct offsets) — previously overlapped → shorted halves; structural_check now unit-aware
      and detects coincident-distinct-net shorts. All blocks regenerated.
- [x] block 6 transcribed + verified (gen_block6.py; CD4053 symbol datasheet-corrected;
      Option-B SVF v1/BP tap; per-channel expo; per-group Q-VCAs; SC/HC/WF + 2×CD4053/group
      stereo mux; 3 Phase-3R flags documented) — **10/10 blocks**
- [ ] (optional) board-level sheets combining per-block schematics by board
- [ ] (gated separately) enable a KiCad CI job (kiutils) — currently disabled
