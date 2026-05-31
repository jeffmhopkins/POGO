# 0028 — SPICE circuit-math validation: block-2 (Dual LFO)

- **Slug:** spice-math-block2lfo  **Branch:** `change/0028-spice-math-block2lfo`
  (stacked on `change/0027-spice-math-block6dist` — shares the SPICE-COVERAGE.md tracker; rebase onto
  `dev` after 0027 merges).
- **Lane:** B (tooling + test fixtures) — possibly a real netlist/spec fix if the gate surfaces one.
  Touches `specs/block-2/sim/**` (NEW dir) (+ nets/components values only if a bug is found). No
  plugin/panel/connectivity change.
- **Status:** OPEN
- **Opened:** 2026-05-31
- **Blocks:** block-2   **Boards:** utility

## Intent

Fifth run of the multi-agent SPICE-math pipeline (`tools/SPICE-DECK-GUIDE.md` Part 2), on **block-2
(Dual LFO)** — chosen for **distinct time-domain physics**: it's the only oscillator (triangle, 0.05–20
Hz) and currently ⚪ NONE (zero decks). This is the harness's **first transient (`.tran`) deck** — new
territory after the op/ac decks of block-7/4/3/6. Brings block-2 ⚪ → 🟢 FULL.

The analog core (aux-lfo-core): one TL072 per LFO — half A = integrator (triangle), half B = Schmitt
comparator (square). Rate = attenuate V_sq into the integrator via a log-pot divider → fixed R_INT →
integrator; f ∝ wiper fraction; R_FLOOR bounds the slow end. A change-0018 NPN "breathing" LED current
source maps V_tri∈[−5,+5] → I_LED ∝ (V_tri+5)/10.

Plugin ground truth (`LFO.hpp`): `f = 0.05·400^param` (0.05 Hz @ 0, ~20 Hz @ 1, exponential); triangle
±1 → ±5V; one-pole LP at 10× rate models Schmitt/integrator rounding.

## Candidate claims (pre-derive sketch — the deriver produces the authoritative manifest)
- **lfo-freq-max / -min** — oscillation frequency f = 1/(4·R_INT·C·β), β=R7/R5 (Schmitt trip ratio),
  measured by a TRANSIENT sim (count the period). f_max at full wiper (R1=590k, C1=47nF), f_min bounded
  by R_FLOOR (R3=2k4). Endpoints bindable (R1/R3/R5/R7/C1); the log-pot taper midpoint is [NV] (symbolic
  RV1 value). The exponential 0.05·400^param law itself is set by the log pot → only endpoints checkable.
- **lfo-triangle-amplitude** — triangle peak = β·V_sat = (R7/R5)·V_sat sets the ±5V swing (vs the rails).
  Bind R5, R7. [NV] on V_sat (op-amp output saturation ≈ ±10.5V) — check the RATIO/shape.
- **schmitt-thresholds** — comparator trip points ±V_sat·R7/(R5+R7) (or the relevant divider). Bind R5, R7.
- **led-breathing-bias** — NPN level-shift: V_tri (R19=51k) + 12V bias (R20=68k) + GND (R21=10k) → base;
  emitter R_E (R9=470R) → I_LED ∝ (V_tri+5). Check the bias maps V_tri=−5→I≈0 and V_tri=+5→I_max
  (matches plugin (V_tri+5)/10). Bind R19/R20/R21/R9.

## Pipeline (per the guide)
1. **Derive** [1 agent] — structured manifest; ESPECIALLY work out the exact analog oscillation-frequency
   formula + how a `.tran` deck measures it (first transient deck — may extend the guide's ngspice notes).
2. **Write** [parallel] — author the shortlist decks + `.expect.yaml` (with `netlist_bind`).
3. **Verify** [parallel adversarial] — three killer questions; Q3 load-bearing.
4. **Integrate** — fix findings, full gate stack; if the `.tran` pattern is novel, add a note to the guide.

## Decisions log
- 2026-05-31: picked block-2 LFO (distinct time-domain oscillator physics, ⚪→FULL, first transient deck)
  over the quick filter-sibling baseline promotions (block-5/8). Done: block-7, block-4, block-3, block-6-dist1.

## Gate checklist
- [ ] Stage 1 derive → manifest
- [ ] Stage 2 write decks (parallel)
- [ ] Stage 3 verify-intent (parallel adversarial)
- [ ] Stage 4 integrate (fix findings; all 7 gates green)
- [ ] Update `specs/SPICE-COVERAGE.md` (block-2 NONE → FULL)
- [ ] PR `change/0028-spice-math-block2lfo` → `dev` (after 0027 merges; rebase first)

## Outstanding (tracked in `specs/SPICE-COVERAGE.md`)
- Remaining BASELINE blocks (5/8/1/A + block-6 svf1/mix) still need the binds+verify promotion.
- [NV] items: log-pot taper (exponential rate curve), op-amp V_sat absolute, NPN Vbe — bench/trim items.
