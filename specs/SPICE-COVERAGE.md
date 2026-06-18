# SPICE behavioral-check coverage tracker

Living status of the per-block SPICE math-validation effort. The gate
(`tools/build_spice.py --check`, blocking since 0023) runs every deck listed here.
Methodology + how to extend: `tools/SPICE-DECK-GUIDE.md`.

**Last updated:** 2026-05-31 (change 0029) · **47 decks across 13 block dirs, all passing.**
**🎉 ALL blocks are 🟢 FULL** — every block with a netlist now has netlist-bound, adversarially-verified
SPICE coverage (svf2/svf3 + dist2/dist3 are identical copies of svf1/dist1, covered by representative).

## Coverage levels
- **🟢 FULL** — the multi-agent pipeline (derive → write → adversarial-verify → integrate) has been run;
  decks `netlist_bind` their load-bearing values; verify stage probed Q3 (would-fail-if-netlist-wrong).
- **🟡 BASELINE** — has decks (from the 0022/0023 broad-coverage pass) but NOT the full pipeline; decks
  may lack `netlist_bind` and have not been adversarially verified.
- **⚪ NONE** — no decks yet.

| Block | Decks | Level | Notes / what's checked |
|---|---|---|---|
| **block-7** HP | 9 | 🟢 FULL (0024 pilot) | expo divider, OTA tap+f_ref, Q-cell, V/oct octave, HP transfer (2-pole proof), polarity (0018 guard), SUM_AMP vground, IRES summer, I_ref trim. All binds. |
| **block-4** VCA | 7 | 🟢 FULL (0025) | AMT-symmetric (0018 OFS fix), CV summer, I/V unity, gain-law shape, V_CTRL buffer, ref divider, Ec+ injection. **Found+fixed the ref-divider bug.** |
| **block-5** LP1 | 4 | 🟢 FULL (0029) | expo (R63/R231), OTA loop (C11→632Hz), q_cell (R57/R58=100k), tilt-passive (R63/R55/R231; freq==tilt). All binds; tilt deck is bind+topology. |
| **block-8** LP2 | 2 | 🟢 FULL (0029) | expo (R86=49k9/R230=1k), OTA loop (C33A=47nF→632Hz). All binds load-bearing. |
| **block-3** Mod Bus | 7 | 🟢 FULL (0026) | offset ±5V (§M2 guard), gain max/min (4.55×/0.20×), polarity inverter, attenuverter −V_src unity, bipolar-pot topology, depth (§H, now bound). All binds (RV3 470k unbindable — symbolic pot value). **Surfaced+fixed the `100R` parser gap.** |
| **block-A** Input | 1 | 🟢 FULL (0029) | input_clamp: unity follower (topology), BAT54S clamp level [NV], **clamp current bound to R1=100R** (reworked in 0029 so R1 is load-bearing). |
| **block-1** Pre-Gain | 1 | 🟢 FULL (0029) | pregain (R3L=4k7/R4L=18k → 4.83× gain, both bound); clip ±10.5V [NV] (OPA1612 rail). |
| **block-6-svf1** | 1 | 🟢 FULL (0029) | bp_fref (C15=68nF→400Hz bound; 47nF "copied-LP-cap" trap correctly unbound). Representative for svf2/svf3. |
| **block-6-dist1** | 7 | 🟢 FULL (0027) | DRIVE ref-divider (±1.2V, **closed the block-6 0025-fix gap**), DRIVE I/V + summer, wavefold G=+2 reflection (signature), HC/SC unity cells, ±4V CLIP threshold, dist_clip ([NV] clamp levels — zener/diode part#, documentary). Fixed a stale hysteresis comment. Representative for dist2/dist3. |
| **block-6-mix** | 1 | 🟢 FULL (0029) | bp3_normal (§G R→L normal): topology + R36==R224 match, both value-independent of block-6-mix parts → honest no-bind (the load-bearing Rs live in block-B; cross-block bind unsupported). Falsifiable on the wiring + match. |
| **block-2** LFO | 6 | 🟢 FULL (0028) | **first `.tran` decks**: f_max=20Hz oscillator (real integrator+Schmitt loop), f_min divider, V_sat-independence, Schmitt threshold ratio, LED breathing bias + slope. All binds (RV1 1M unbindable — symbolic log-pot). Established the `.tran`/`.ic`/`meas`-period pattern. |
| **block-B** Output | 1 | 🟢 FULL (0029) | out_buffer: unity follower (topology), **div_ratio 0.990× bound to R34=1k** (1k series into 100k load), clamp ±11V [NV] (TL072 rail). New deck. |
| block-6-svf2/svf3 | 0 | ⚪ (covered by svf1) | identical to svf1 — one representative deck stands for the repeat. |
| block-6-dist2/dist3 | 0 | ⚪ (covered by dist1) | identical to dist1. |

## Outstanding work (prioritized)

### A. Promote BASELINE → FULL — ✅ COMPLETE (change 0029)
All baselines promoted: block-5, block-8, block-1, block-A, block-6-svf1, block-6-mix (+ block-3/0026,
block-6-dist1/0027 earlier). Every deck is now netlist-bound (or documented honest no-bind) and adversarially
verified. **No BASELINE blocks remain.**

### B. New blocks (⚪ → coverage) — ✅ COMPLETE
- [x] ~~**block-2 LFO**~~ — ✅ FULL in 0028 (first `.tran` decks).
- [x] ~~**block-B**~~ — ✅ FULL in 0029 (out_buffer: div_ratio bound to R34; clamp [NV]).

(svf2/svf3 + dist2/dist3 remain ⚪ by design — identical copies of svf1/dist1; one representative deck
stands for the repeat. No further block-level coverage is outstanding.)

### C. Deferred / [NV] items awaiting bench measurement (cannot close in-env)
These need real hardware/datasheet numbers before a deck can assert an absolute. **Change 0036 converted
three of them from "deferred" to "trim-authority / temperature verified"** — the absolute stays [NV], but
the design is now proven *calibratable + temperature-stable* across the device-constant datasheet band:
- [x] ✅ **block-4/6 VCA Ec+** — **0036** `vca_unity_band`: the Ec+ injection keeps ≥±0.5 dB unity-null
      authority across the THAT2180 **6.0–6.2 mV/dB** datasheet band (worst case 6.2). Absolute mV/dB still [NV].
- [x] ✅ **block-6 DRIVE** — **0036** `drive_db_band`: the summer+injection has ≫10× headroom for the SOFT
      +34.75 dB target across the band (scope: knob→Ec+ full-scale is Phase-3R; reachability proven, not scaling).
- [x] ✅ **THAT340 tempco / V/oct** — **0036** `voct_slope_band` (room-temp trim authority, 20k pot brackets
      ±5%) + `voct_tempco_tracking` (full 0–50 °C: the +4110 ppm/K tempco holds cutoff to **≈ −2.1%/+1.5%**,
      within a ±3% filter spec; PROVEN the tempco earns its place — remove it → ±8–10% fails). **Finding:**
      +4110 ppm/K over-compensates V_T (ideal ≈ +3394 ppm/K); a ~+3300–3400 ppm/K part would track ≈8× tighter
      (≈±0.25%). Acceptable for a filter cutoff; logged in aux/filter/voct-expo-divider/spec.md §Temp comp.
- [ ] **block-7/5/8 Q-cell** — the IRES_AMP **negative-V_ires drive + clamp polarity** (R_Iabc=100k done;
      the bias-network drive into the −10.8V window is Phase-3R). **Still blocked: no trim circuit exists to
      authority-check until the negative-drive bias network is designed.** See 0020 §D, 0024.
- [ ] **block-7 D12 clamp** — V_ires clamp polarity; deck deferred until the Q-cell bias redesign closes.
- [ ] **block-2 LFO rate** — absolute 0.05–20 Hz (the log-pot taper) is [NV]; endpoints/shape checked (0028).

#### Outstanding follow-ups surfaced by 0036
- [ ] **expo_voct / voct_octave decks (block-7/5/8 + aux) model the 1V/oct pot as 10k** — the sourced part
      is **20 kΩ** (Bourns 3224W; components.yaml; block-7 spec.md:185). Those decks PASS but are *conservative*
      (understate the trim range); 0036 corrected `voct_slope_band` to 20k. A focused cleanup should reconcile
      the pre-existing `expo_voct`/`voct_octave` pot model to 20k (recomputes their assertion values).

### D. Known real fixes already applied (for the record)
- ✅ **0024:** built `netlist_bind` (the gate wasn't netlist-bound); fixed stale spec.md:152 (R_Iabc 1M→100k).
- ✅ **0025:** fixed the HIGH-3 ±ref divider — R233/R234 45k3→11k3 (block-4) + R243…R256 45k3→22k6
      (block-6 DRIVE); the 45k3 gave ±0.32V (~±0.5dB authority) not the intended ±1.2V/±2dB.
- ✅ **0026:** fixed `parse_value()` in `build_spice.py` — it couldn't read bare-`R` ohms notation
      (`100R`/`47R`, only `1R0`/`4k7`); block-3's protection resistors use it and this was the first bind
      to exercise it. No netlist bug found in block-3 (the §M2 offset + §H depth fixes verified correct).
- ✅ **0027:** closed the **block-6 DRIVE ref-divider coverage gap** — 0025 fixed R243/R244 45k3→22k6 but
      only block-4 got a `ref_divider` deck; block-6's copy was unchecked. Now bound (±1.195V; reverting to
      45k3 fails). Also fixed a stale netlist comment (R181 hysteresis "~50mV"→"~0.95V input-referred").
      No netlist bug found in block-6-dist (the 22k6 ref + ±4V CLIP + wavefold all verified correct).
- ✅ **0028:** block-2 LFO → FULL (first `.tran` decks). No netlist bug found (f_max=20Hz, Schmitt ratio,
      LED bias all verified correct). Extended `SPICE-DECK-GUIDE.md` with the `.tran`/`.ic`/`meas`-period
      oscillator pattern + 3 new ngspice gotchas (`gt`/`and` not `>` in `let`; `2k4` misparse in `.cir`;
      `.param` not in `.control` scope).
- ✅ **0029:** promoted the last 6 baselines + authored block-B → **all blocks FULL**. Reworked the block-A
      `input_clamp` deck so R1 is load-bearing (clamp current, was a dangling bind); fixed a stale block-5
      spec.md §3 line (R_Iabc 1M→100k). No netlist bugs found in any baseline (all values verified correct).

## Status: COMPLETE
Every block with a netlist has netlist-bound, adversarially-verified SPICE coverage. The only remaining
work is the **[NV] items in section C** — they need bench/datasheet numbers (device constants the gate
can't assert in-env) — and would graduate from trim-authority/ratio checks to absolute assertions once
hardware exists. The `tools/SPICE-DECK-GUIDE.md` methodology (derive → write → adversarial-verify →
integrate) + the per-block `sim/` layout are the template for any future block or re-validation.
