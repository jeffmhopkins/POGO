# 0026 — SPICE circuit-math validation: block-3 (Mod Bus)

- **Slug:** spice-math-block3  **Branch:** `change/0026-spice-math-block3`
- **Lane:** B (tooling + test fixtures) — and possibly **a real netlist/spec fix** if the gate
  surfaces one (as 0024/0025 did). Touches `specs/block-3/sim/**` (+ nets/components values only if a
  bug is found). No plugin/panel/connectivity change.
- **Status:** OPEN
- **Opened:** 2026-05-31
- **Blocks:** block-3   **Boards:** utility

## Intent

Third run of the multi-agent SPICE-math pipeline (`tools/SPICE-DECK-GUIDE.md` Part 2), on **block-3
(Mod Bus)** — chosen for **distinct linear-summing/distribution physics** (after block-7 filter,
block-4 VCA) and because it is the **most checkable** remaining analog block: the processor gain
range, the OFFSET ±5 V law, the polarity inverter, the per-destination −V_src inverter + bipolar
attenuverter law, and the ±10 V clamp are all NV-safe absolutes derivable straight from the netlist
resistor values. Goal: prove every circuit-math reference in block-3's schematic is netlist-bound.

Already covered (0022/0023, BASELINE — no binds): `modbus_depth.cir` (the §H low-Z-normal depth fix).

## Pipeline (per the guide)
1. **Derive** [1 agent] — structured manifest of block-3 math claims → check candidates.
2. **Write** [parallel] — author the shortlist decks + `.expect.yaml` (with `netlist_bind`).
3. **Verify** [parallel adversarial] — three killer questions; Q3 (would it fail if the netlist were
   wrong?) load-bearing. Also retrofit/audit the BASELINE `modbus_depth` deck.
4. **Integrate** — fix findings, close seams, correct any spec/netlist bug surfaced, full gate stack.

## Manifest (Stage 1) ✅ — arithmetic verified independently against the netlist + plugin

| id | claim (computed) | netlist refs (bind) | nv | shortlist |
|---|---|---|---|---|
| **mb-offset-level** | OFFSET = ±12V·(R13/R15) = 12·100/240 = **±5.0V** at summer (the §M2 fix) | R13=100k, R15=240k | NO | **#1 (top)** |
| **mb-gain-max** | SCALE full-CW: R13/R14 = 100/22 = **4.545×** (analog approx of plugin 5×) | R13=100k, R14=22k | NO | #2 |
| **mb-bipolar-attenuverter** | pot across V_src↔−V_src: noon=0, CW=+V_src, CCW=−V_src (vs unipolar bug) | none (ratio/topology) | NO | #3 |
| **mb-gain-min** | SCALE full-CCW: R13/(R14+RV3) = 100/492 = **0.203×** (plugin 0.2×) | R13, R14 (RV3 470k = spec literal) | NO | #4 (partial bind) |
| **mb-dest-inv-unity** | per-dest −V_src inverter R_INV_FB/R_INV_IN = 47/47 = **−1** (§H 10k→47k) | R_INV_IN_1=47k, R_INV_FB_1=47k | NO | #5 |
| **mb-polarity-unity** | processor polarity inverter R16_2/R16_1 = 100/100 = **−1** | R16_1=100k, R16_2=100k | NO | #5 |
| mb-depth (retrofit) | §H low-Z normal ~99% vs ~3% bug; add bind to the existing deck | R37_1=100R (16.3k/3.3k derived) | NO | #6 |
| ~~mb-clamp-10v~~ | ±10V zener clamp | — (BZX84C10 part#, unbindable) | YES | **dropped (vacuous)** |

**Escalations from the deriver (recorded):**
1. **RV3/RV4 carry symbolic values** (`MOD_SCALE`/`MOD_OFFSET`) in nets.yaml, not numeric — the 470k log
   pot lives only in spec prose. `mb-gain-min` can bind R13/R14 only; 470k stays a spec literal (same
   precedent as block-4's symbolic-pot RVs, left unbound). Tracked gap, not fixed here.
2. **4.545× vs plugin 5.0×** is a spec-acknowledged analog deviation (spec.md:88) — `expect` is derived
   from the netlist (4.545), NOT the plugin (5.0); decks must label it a documented deviation.
3. **Zener/Schottky clamps** (D5/D6, BAT54S) are unbindable-numeric (Vz in the part#, not a netlist R) —
   acknowledged [NV]; no falsifiable gate authored (would be ideal-on-both-sides).

**NOT spice-able (out of scope):** MOD_SRC switch contact sequence, bridged-COM steering, pinouts,
BAT54S/zener clamp absolutes, RV3 log taper midpoint, distribution-buffer fan-out/current budget, IC
count/power/sourcing, normalling mechanics (its *effect* = depth is covered).

**Writer slices:** Group P (processor): mb-offset-level, mb-gain-max, mb-gain-min, mb-polarity-unity.
Group A (attenuverter + depth): mb-dest-inv-unity, mb-bipolar-attenuverter, mb-depth retrofit.

## Decisions log
- 2026-05-31: picked block-3 over block-6-dist — block-3 is distinct linear-summing physics, the most
  checkable remaining block (NV-safe absolutes everywhere), and self-contained; block-6-dist is sprawling
  with the most [NV] debt (clip/fold laws are Phase-3R). Done so far: block-7 (filter), block-4 (VCA).

## Gate checklist
- [ ] Stage 1 derive → manifest
- [ ] Stage 2 write decks (parallel)
- [ ] Stage 3 verify-intent (parallel adversarial)
- [ ] Stage 4 integrate (fix findings; all 7 gates green)
- [ ] Update `specs/SPICE-COVERAGE.md` (block-3 BASELINE → FULL)
- [ ] PR `change/0026-spice-math-block3` → `dev`

## Outstanding (tracked in `specs/SPICE-COVERAGE.md`)
- Remaining BASELINE blocks (5/8/1/A + block-6 svf1/dist1/mix) still need the binds+verify promotion.
- block-2 LFO has no deck. [NV] items await bench measurement.
