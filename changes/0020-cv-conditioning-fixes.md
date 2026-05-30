# 0020 — CV-conditioning & behavioral netlist fixes (adversarial-review findings)

- **Lane:** B (hardware-only). The plugin is ground truth and already LOCKED for these blocks;
  only spec §2–4 / nets / components change. Enter at Step 5, gates G4–G6 + `--check`.
- **Status:** OPEN — G1 confirmed (fix all CRIT+HIGH; full H5/H6/M5 fixes). Working per cluster.
- **Opened:** 2026-05-30
- **Branch:** `change/0020-cv-conditioning-fixes` (stacked on `change/0019-doc-staleness-refresh`;
  rebase onto `dev` once 0019 merges).
- **Stacked-on:** 0019 (inherits the corrected aux-expo / aux-distortion / block-6 docs).

## Intent

A 6-agent adversarial review (plugin→spec→nets→schematic, primary sources) found the **signal
paths sound** but the **CV-conditioning sub-circuits and a few change-0018 behavioral wirings
wrong** vs the locked plugin. Fix the confirmed netlist/topology defects so the hardware spec
faithfully reproduces the plugin. No plugin/panel change (Lane B).

## Findings to address (prioritized; severity from review, ✓ = I independently verified)

### CRITICAL
- **C1 — Expo V/oct has no attenuation divider (blocks 5,7,8 + 6 by inheritance). ✓**
  CV reaches the THAT340 base through series R only (`R_VOCT`+`RV_1VOCT`), no shunt → no ~18 mV/oct
  scaling; converter rails. Needs a base divider (≈1:55) / proper summing node + the 1V/oct trim
  acting within it. (block-5/7/8 nets + aux-expo-converter §Schematic/Transfer.)
- **C2 — Mod-bus delivers ~3% depth at unpatched destinations (block 3). ✓**
  100 kΩ `R_SRC_NORM` into a ~3.3 kΩ destination node (10 kΩ inverter-in ∥ 10 kΩ pot) → ÷31.
  Fix: low-Z/direct normal (tip-switch breaks it) or buffer per destination. Pairs with H-mod below.
- **C3 — LP1 stereo-tilt "summer" injects into the raw expo base, not a summing node (block 5). ✓**
  Same root as C1; tilt scaling unrealizable. Fix together with C1.

### HIGH
- **H1 — BP3 input selector ignores ALT_BP_R (block-6-dist3). ✓** `ALT_L_DET` drives both U81
  selects; no `ALT_R_DET`. Plugin gates BP3_R on `altLConn||altRConn` (`Pogo.cpp:441`). Need an
  ALT_R detect + an OR into the Y(R) select; X(L) select stays on ALT_L_DET.
  **CONSTRAINT (found 2026-05-30):** `J4.3` (ALT_R jack's only switch lug) is already the
  normalling contact (`block-1.nets.yaml:76` `ALT_L_IN:[...,J4.3]` realizes the plugin's
  "normalise R to L if only L patched"). PJ301M-12 has one switch contact, so J4 can't both
  normal and cleanly detect — the ALT_R_DET derivation is a **G5 topology decision** (options:
  comparator off the normalling node / a second detect scheme / document as a minor limitation).
- **H2 — Mod-bus distribution buffer specified but absent (block 3).** Spec says U3 C/D parallel
  buffer; nets ground them as spares. Bare `MB_INV` (one TL074 section) drives 18 loads. Fix with C2.
- **H3 — VCA "unity trims" are series rheostats into the high-Z Ec+ port (block-4; copied to
  block-6 DRIVE trims). ✓** Series R can't set a DC offset on a µA control input. And the shared
  unbuffered V_CTRL wiper couples all 4 cells. Needs a real offset-injection (divider→Ec+) + a
  wiper buffer.
- **H4 — Wavefold mode phase-inverted vs Soft/Hard (block-6-dist, all 3 bands).** Net-by-net
  polarity makes WF net-inverting; flips wet contribution at mix + BP3 tap. Add one inversion in WF.
- **H5 — State variable tapped from LM13700 Darlington buffer → ~1.2 V DC into next OTA input
  (blocks 5,7,8).** Saturates the µV-class OTA input. Tap the unbuffered integrator node, or
  offset-correct. (Needs bias analysis to confirm severity/fix.)
- **H6 — Q=2000 self-osc needs ~260 pA Iabc, below LM13700 floor (5,7,8).** Top decade of Q
  uncontrollable. Likely a documented-limit + soft-limit addition rather than a full fix.

### MED (fold in where cheap)
- **M1 — BP3 R→L output normal averages (L+R)/2 through 2×1 kΩ instead of delivering L (block-6-mix). ✓**
- **M2 — Mod OFFSET range ±12 V vs plugin ±5 V (block 3).** Scale R15 or use ±5 V references.
- ~~M3 — BP per-band TILT CV missing the plugin ×0.22.~~ **RESOLVED / NON-ISSUE (verified
  2026-05-30).** block-6-svf1/2/3 already apply it: `R137/R143/R149 = 470k` into the 100k tilt
  summer = ×0.213 ≈ plugin ×0.22 (the net comment even says so). block-3's BP-tilt destinations are
  plain attenuverters feeding `MOD_BP{n}_TILT` into that summer; the scaling is applied once, in
  block-6, matching the plugin's single `×0.22f`. No change needed — dropped from scope.
- **M4 — I/V transimpedance has no feedback comp cap (block-4, 4 channels).** Add small C_f.
- **M5 — Q-cell Iabc bias math ignores the Iabc-pin rail potential (5,7,8).** Recheck arithmetic.

### Decisions made (G1, 2026-05-30)
- **Scope: fix all confirmed CRITICAL + HIGH defects in this one change (0020)**, plus the cheap
  MEDs (M1, M2, M4, M5). M3 dropped (non-issue, verified).
- **H5/H6/M5: full netlist fixes now** (not deferred to Phase-3R), backed by deeper LM13700
  datasheet analysis.
- Mod-bus strategy + expo divider topology will still be presented at **G5** for approval before
  the nets are rewired (the *decision to fix* is made; the *exact topology* is the G5 gate).

## Status
- **Status:** OPEN — G1 confirmed. Working cluster-by-cluster, committing per cluster.

## Scope / blocks
block-3, block-4, block-5, block-7, block-8, block-6-svf{1,2,3}, block-6-dist{1,2,3}, block-6-mix;
aux-expo-converter, aux-q-control, aux-ota-c-svf, aux-vca-cell, aux-mod-bus-core, aux-distortion;
components.yaml (new parts: shunt resistors, comp caps, possible buffer op-amps, ALT_R detect).

## Reconnaissance notes (wiring facts gathered before G5)
- **M1 mechanism (block-6-mix:88-89):** `BP3_L_OUT:[J27.1, J28.3]` + `BP3_R_OUT:[J28.1]`. BP3_L/R_OUT
  are block-B-buffered (U62, 1k series each). J28 unpatched shorts tip↔switch → ties both buffer
  outputs through 2k → tip = (L+R)/2, and back-feeds R into the J27(L) node. Fix: normal the L
  *source* into J28's switch ahead of R's buffer/series-R, not tie two driven outputs. (Wiring-only.)
- **H4 (WF phase, dist3 + dist1/2):** WF folder `BP3_WFOUT = 2·Vclamp − Vfoldin` with the leading
  DRIVE-VCA I/V inversion makes WF net-inverting while SC/HC are net non-inverting. Fix: add one
  unity inversion in the WF path (or swap a summing polarity) so all 3 modes share sign. Need to
  confirm a free op-amp half exists per dist section (U38/39/44/45 usage) — else +1 component.
- **H1 (BP3 selector):** see CONSTRAINT above — J4.3 already normalling; ALT_R_DET source is a G5 call.

## Gate checklist
- [x] **G1 — intent** confirmed (fix all CRIT+HIGH; full H5/H6/M5). 
- [ ] **G5 — topology proposal** (assemble after analog-values agent returns) ← CURRENT STOP
- [ ] G4 — spec parity vs locked plugin (per block) [folded with G5 per-block]
- [ ] G4 — spec parity vs locked plugin (per block)
- [ ] G5 — topology approval (per block; mod-bus + expo strategy decisions)
- [ ] G6a/b — new components + footprints
- [ ] `--check` gates + parity green
- [ ] PR `change/0020-cv-conditioning-fixes` → `dev`

## Decisions log
- 2026-05-30: opened off the 0019 tip (stacked) to inherit corrected docs and avoid re-touching
  the same stale text; will rebase onto dev after 0019 merges.
