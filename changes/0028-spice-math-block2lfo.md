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

## Manifest (Stage 1) ✅ — arithmetic verified independently; frequency formula derived

Oscillator: **f = (R5+R7)/(4·R7·R_INT·C_INT)** (integrator + non-inverting Schmitt; V_sat CANCELS).

| id | claim (computed) | netlist refs (bind) | nv | shortlist |
|---|---|---|---|---|
| **lfo-fmax** | full drive: f = (R5+R7)/(4·R7·R1·C1) = 182k/(4·82k·590k·47nF) = **20.0 Hz** (`.tran`) | R1=590k, R5=100k, R7=82k, C1=47nF | NO (V_sat cancels) | **#1 (headline)** |
| **lfo-fmin** | floor: k_min = R3/(RV1+R3) = 2k4/(1M+2k4) = 0.00239 → f_min ≈ **0.0479 Hz** (`op` ratio, not a 21s tran) | R3=2k4 (RV1=1M spec literal) | NO | #2 |
| **lfo-vsat-independence** | f is V_sat-INDEPENDENT (threshold scales with V_sat → cancels); ratio f(V_sat_a)/f(V_sat_b) = **1.0** | (shared topology) | NO (proves the [NV] drops out) | #3 |
| **lfo-vth-ratio** | Schmitt threshold V_H = V_sat·R7/(R5+R7) = **0.4505·V_sat** (sets the ±5V triangle peak) | R5=100k, R7=82k | abs [NV] (V_sat); ratio NO | #4 |
| **led-bias-superposition** | NPN base = (V_tri/R19 + 12/R20)/(ΣG) → **0.584 / 1.314 / 2.044 V** at V_tri=−5/0/+5 | R19=51k, R20=68k, R21=10k | NO | #5 |
| **led-slope-monotone** | I_LED = (V_base−Vbe)/R9 rises 0→~3mA as V_tri −5→+5 (R9=470R) | R9=470R | **YES** (Vbe) | #6 |
| ~~lfo-rout-scaling~~ | R11/R12=1k series into hi-Z jack (unity) | — (value-independent) | NO | **dropped (vacuous)** |

**Key derivations confirmed:** f_max=20.0 Hz ✓ (plugin 20 Hz), f_min=0.0479 Hz ✓ (plugin 0.05 Hz), LED
bias 0.584/1.314/2.044V ✓ (spec). **V_sat cancels in f** — so the headline rate law is NOT [NV] despite
the op-amp saturation being unmeasured; `lfo-vsat-independence` proves it cheaply.

**First `.tran` deck — new ngspice mechanics for writers (deriver-supplied):**
1. `.tran <step> <stop>` bounded < ~1–2s sim time → run at 20 Hz (~0.6s), NEVER the real 0.05 Hz (21s) —
   use the `op` divider-ratio for f_min.
2. The oscillator needs a KICK (`.ic v(vtri)=0` + offset, or a t=0 PULSE on V_sq) — ideal sim sits at the
   metastable point otherwise.
3. Skip startup: measure the period on the 2nd–3rd zero-crossings (`meas tran ... RISE=2`/`RISE=3`).
4. The Schmitt comparator must HOLD state between thresholds (hysteresis) — a memoryless B-source won't
   oscillate; use the R5/R7 divider on a real (+) node feeding a high-gain comparator.

**Escalations:** RV1/RV2 are symbolic log-pot values (`LFO1_RATE`) → unbindable (like block-3 RV3);
1M stays a spec literal in lfo-fmin. V_sat / Vbe are [NV] — checked via ratios / base-voltage, not absolutes.

**NOT spice-able:** the exponential taper mid-curve (log pot, symbolic), the one-pole rounding LP (DSP
artifact), LED Vf/brightness/beta, MOD_SRC tap, pinouts, output normalling, sourcing/power/decoupling.

**Writer slices:** Group OSC (lfo-fmax, -fmin, -vsat-independence, -vth-ratio — owns the first `.tran`
+ period-meas + `.ic` pattern); Group LED (led-bias-superposition, led-slope-monotone — pure `op`).

## Pipeline (per the guide)
1. **Derive** [1 agent] — structured manifest; ESPECIALLY work out the exact analog oscillation-frequency
   formula + how a `.tran` deck measures it (first transient deck — may extend the guide's ngspice notes).
2. **Write** [parallel] — author the shortlist decks + `.expect.yaml` (with `netlist_bind`).
3. **Verify** [parallel adversarial] — three killer questions; Q3 load-bearing.
4. **Integrate** — fix findings, full gate stack; if the `.tran` pattern is novel, add a note to the guide.

## Decisions log
- 2026-05-31: picked block-2 LFO (distinct time-domain oscillator physics, ⚪→FULL, first transient deck)
  over the quick filter-sibling baseline promotions (block-5/8). Done: block-7, block-4, block-3, block-6-dist1.

## Stage 2 — writers (2 parallel) ✅ — 6 decks, all PASS
- **Group OSC (first `.tran` decks):** lfo_fmax (real integrator+Schmitt loop oscillates → fhz=20.000 Hz;
  binds R1/R5/R7/C1), lfo_fmin (`op` divider k_min=0.002394 → 0.0479 Hz; binds R3, RV1=1M unbindable),
  lfo_vsat_indep (two-V_sat ratio=1.0 proves V_sat cancels), lfo_vth_ratio (Schmitt 0.4505=R7/(R5+R7)).
- **Group LED:** led_bias (NPN base superposition 0.584/1.314/2.044V; binds R19/R20/R21), led_slope
  (I_LED 0→3.07mA range; binds R9 + bias Rs; Vbe [NV] → loose tol/shape).
- Found **3 new ngspice gotchas** (now in the guide): `gt`/`and` not `>` in `let` (a bare `>` is a shell
  redirect — created stray `iled_0)` files); `2k4` misparsed inside a `.cir` (write `2.4k`, bind `2k4`);
  `.param` not in `.control` vector scope. Cleaned the stray redirect artifacts.

## Stage 3 — verifiers (2 parallel adversarial) ✅ — live ngspice perturbation; ALL SOUND
- **OSC: all 4 SOUND, no defects.** lfo_fmax's frequency is GENUINELY set by the bound R1/C1/R5/R7 —
  every perturbation moves fhz to the formula value (R1→1M→11.79Hz, C1→100nF→9.40Hz), and it's invariant
  to the `.ic` kick / step / stop time (so NOT pinned by the sim setup — the deepest `.tran` risk, ruled
  out). lfo_vsat_indep ratio=1.0 is a real guard (the bind catches drift), honestly scoped.
- **LED: both SOUND, no defects.** All 4 bias/slope binds load-bearing; the [NV] tol is honest (Vbe band
  physically bounded; a bias-resistor error is caught by the bind, NOT swallowed by the loose tolerance).
  Verifier used an isolated `git worktree` (no concurrent-perturbation race).

## Stage 4 — integrate ✅ (no deck fixes needed; guide extended; gates green)
- **No netlist bug found** (f_max=20Hz, Schmitt ratio, LED bias all verified correct — like block-3/6, the
  values were already right). The run's products: the first transient-deck coverage + the reusable pattern.
- **Extended `tools/SPICE-DECK-GUIDE.md`** with the `.tran`/`.ic`/`meas`-period oscillator pattern (items
  10–12 + a transient subsection) so the next time-domain block reuses it.
- All 7 `--check` gates green; 6 block-2 decks pass (46 decks total).

## Gate checklist
- [x] Stage 1 derive → manifest (6 checks; f=20Hz headline, V_sat cancels, first `.tran`)
- [x] Stage 2 write decks (2 parallel → 6 decks; found 3 new ngspice gotchas)
- [x] Stage 3 verify-intent (2 adversarial → ALL SOUND; oscillator proven value-bound, not vacuous)
- [x] Stage 4 integrate (no deck fixes; extended the guide; all 7 gates green)
- [x] Update `specs/SPICE-COVERAGE.md` (block-2 NONE → FULL)
- [ ] PR `change/0028-spice-math-block2lfo` → `dev` (after 0027 merges; rebase first)

## Outstanding (tracked in `specs/SPICE-COVERAGE.md`)
- Remaining BASELINE blocks (5/8/1/A + block-6 svf1/mix) still need the binds+verify promotion.
- [NV] items: log-pot taper (exponential rate curve), op-amp V_sat absolute, NPN Vbe — bench/trim items.
