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

## Candidate math claims (pre-derive sketch — the deriver produces the authoritative manifest)
- **mb-gain-range** — processor gain G = R13/(R14+RV3): G_max=100k/22k=4.55× (pot=0), G_min=100k/492k=0.20×
  (pot=470k). Plugin law 0.2×–5× (`ModBus.hpp:17–20`). The 4.55×≈5× endpoint is a documented analog
  deviation; midpoint depends on log-pot taper ([NV]). Bind R13, R14.
- **mb-offset-level** — OFFSET contributes −V_wiper·(R13/R15)=−V_wiper·(100/240); ±12 V wiper → ±5.0 V at
  the summer (the §M2 fix). Plugin `offsetParam·5` (`ModBus.hpp:24`). Bind R13, R15.
- **mb-inv-unity** — polarity inverter R16_2/R16_1 = 100k/100k = 1 (restores summer sign). Bind R16_1/2.
- **att-inverter-unity** — per-destination −V_src inverter R_INV_FB/R_INV_IN = 47k/47k = −1. Bind the pair.
- **att-bipolar-law** — attenuverter pot across V_src↔−V_src: wiper = 0 at noon, +V_src CW, −V_src CCW
  (the `applyDestination` source·att law, att∈[−1,+1]). Bind the inverter pair feeding −V_src.
- **mb-clamp-10v** — back-to-back BZX84C10 zeners → ±10 V clamp (plugin hard clamp ±10 V). [NV] on zener
  tolerance (9.5–10.5 V); the 10 V nominal lives in the part number, not a bindable numeric.
- **modbus-depth retrofit** — add `netlist_bind` to the existing deck (Rprot→R37/R99=100R) and audit it.

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
