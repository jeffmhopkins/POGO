# 0027 — SPICE circuit-math validation: block-6-dist (BP distortion)

- **Slug:** spice-math-block6dist  **Branch:** `change/0027-spice-math-block6dist`
- **Lane:** B (tooling + test fixtures) — possibly a real netlist/spec fix if the gate surfaces one.
  Touches `specs/block-6-dist1/sim/**` (+ nets/components values only if a bug is found). No
  plugin/panel/connectivity change.
- **Status:** OPEN
- **Opened:** 2026-05-31
- **Blocks:** block-6-dist1 (representative; dist2/dist3 are identical copies)   **Boards:** audio

## Intent

Fourth run of the multi-agent SPICE-math pipeline (`tools/SPICE-DECK-GUIDE.md` Part 2), on
**block-6-dist (BP distortion)** — chosen for **distinct nonlinear physics** (soft-clip tanh diode
chain, hard-clip zener, Buchla wavefold) after block-7 (filter), block-4 (VCA), block-3 (mod-bus).
Promotes block-6-dist1 from 🟡 BASELINE → 🟢 FULL. The dist cell also carries a per-band **DRIVE
THAT2180 VCA** (mirrors block-4) and the change-0018 **±4V CLIP detector**.

Already covered (0023, BASELINE — no binds): `dist_clip.cir` (HC ±5.8V zener / WF-SC ±1.4V diode
clamp thresholds). The clamp absolutes live in part numbers (BZX84C5V1, 1N4148W Vf) → [NV]/unbindable;
the pipeline focuses on the **resistor-derived** laws around them.

## Concrete high-value opportunity (a real gap)
The **HIGH-3 DRIVE Ec+ ±ref divider** (R243/R244 = **22k6**) was the *fix* applied in change 0025
(45k3→22k6, for ±1.2V with the 2-pot/5k bridge) — but only **block-4** got a `ref_divider` SPICE
check; **block-6's copy was never checked**. This run closes that gap: a block-6 ref-divider deck
binding R243=22k6, proving the 0025 fix holds here too (regression-guards the 45k3 mistake).

## Manifest (Stage 1) ✅ — arithmetic verified independently against the netlist + plugin

| id | claim (computed) | netlist refs (bind) | nv | shortlist |
|---|---|---|---|---|
| **D3 drive-ref-divider** | REF_P1 = ±**1.195V** from R243/R244=22k6 + RV51∥RV52 5k bridge (the 0025 fix; block-6 unchecked) | R243=22k6, R244=22k6 | NO | **#1 (top)** |
| **C1 wf-folder-reflection** | Buchla folder V_out = 2·V_clamp − V_in, G=+2 from R25/R_f_wf=10k → slope reversal past ±Vth | R25_1L=10k, R_f_wf_1L=10k | clamp level [NV]; ratio NO | #2 (signature) |
| **L1 clip-threshold-4v** | ±4V CLIP window: R186/R187=20k/10k → +12·10/30 = **+4.0V**; R188/R189 → −4.0V | R186,R187,R188,R189 | NO | #3 |
| **D2 drive-summer-unity** | Ec+ control summer R157/158/159/160=100k → −1 each (knob+CV+bias) | R157–R160=100k | NO | #4 |
| **D1 drive-iv-unity** | DRIVE VCA I/V −R155/R153 = −20k/20k = −1 (mirrors block-4) | R153=20k, R155=20k | NO | #5 |
| **C2 dist-cell-unity** | HC/SC op-amp stages −1 (R20/R21, R18/R19=10k); clip onset set by DRIVE, not cell | R18/R19/R20/R21=10k | NO | #6 |
| C3 dist_clip (existing) | HC ±5.8V / WF-SC ±1.4V clamp levels | — (zener/diode part#, unbindable) | **YES** | keep documentary [NV] |
| ~~L2 clip-hysteresis~~ | comparator hysteresis width | — (model-dependent, no plugin counterpart) | — | **skip (WEAK)** |

**Escalations from the deriver (recorded):**
1. **The block-6 ref-divider gap is real** — 0025 fixed R243/R244 45k3→22k6 but only block-4 got a
   `ref_divider` deck. D3 closes it (binds R243=22k6; reverting to 45k3 → ±0.628V fails). Top priority.
2. **dist_clip is honestly [NV]/unbindable** — the ±5.8V/±1.4V thresholds live in part numbers
   (BZX84C5V1 Vz, 1N4148W Vf); no resistor sets the level. Keep as documentary; add an explicit
   "[NV]: no bindable resistor" note (do NOT fake a bind).
3. **Possible stale netlist comment** — R181 hysteresis is annotated "~50mV @ ±12 swing" but the naive
   100k/2.2M math gives ~545mV. Flag for investigation (the L2 hysteresis check is skipped as WEAK, but
   the comment may need a correction — Stage 4 to confirm/fix if it's genuinely stale).
4. **Symbolic trim values** — RV51/RV52/RV33 carry symbolic value fields (not ohmic) → unbindable, like
   block-4 RVs and block-3 RV3. Only the known 10k-pot bridge topology feeds D3.

**NOT spice-able (out of scope):** CD4053 mux Ron/switching/logic, DIST_MODE switch encoding, pinouts,
THAT2180 absolute dB (6.1mV/dB) + DRIVE knob→Ec+ map (Phase-3R), zener/diode clamp absolutes, diode-OR
+ LED, oversampling (none), sourcing/power/decoupling, SVF-side claims (belong to block-6-svf*).

**Writer slices:** Group A (DRIVE chain): D3, D1, D2. Group B (dist cells): C1, C2, + C3 [NV] note.
Group C (CLIP): L1 (+ investigate the R181 ~50mV comment).

## Pipeline (per the guide)
1. **Derive** [1 agent] — structured manifest of block-6-dist math claims → check candidates.
2. **Write** [parallel] — author the shortlist decks + `.expect.yaml` (with `netlist_bind`).
3. **Verify** [parallel adversarial] — three killer questions; Q3 load-bearing.
4. **Integrate** — fix findings, close seams, correct any spec/netlist bug surfaced, full gate stack.

## Decisions log
- 2026-05-31: picked block-6-dist over the quick baseline promotions (block-5/8 filter siblings) —
  distinct nonlinear physics (wavefold/clip), highest new-bug yield, and it closes the block-6
  HIGH-3 ref-divider coverage gap left by 0025. dist1 is representative; dist2/dist3 are identical.

## Stage 2 — writers (3 parallel) ✅ — 6 new decks + dist_clip [NV] note, all PASS
- **Group A (DRIVE chain):** drive_ref_divider (binds R243/R244=22k6 → ±1.195V — the 0025-fix gap),
  drive_iv_unity (binds R153/R155=20k → −1; parameterized so both Rs move the gain — avoids block-4's
  faked-ratio bug), drive_summer (binds R157–R160=100k → −1 each).
- **Group B (dist cells):** wf_fold (binds R25/R_f_wf=10k → V_out=2·V_clamp−V_in slope reversal),
  dist_cell_unity (binds R18–R21=10k → −1), dist_clip [NV] note (clamp levels in zener/diode part#).
- **Group C (CLIP):** clip_threshold (binds R186–R189 → ±4.0V vs plugin `>4.0f`). Plus the hysteresis
  investigation that flagged the stale R181 comment.
- Cleaned a stray `v(cout))` shell-redirect artifact (×2). No netlist↔spec divergence found.

## Stage 3 — verifiers (3 parallel adversarial) ✅ — live ngspice perturbation probes; ALL SOUND
- **Group A: all 3 SOUND, no defects.** drive_ref_divider guard CONFIRMED (R243→45k3 trips the bind —
  block-6 now has the regression guard block-4 got in 0025). drive_iv_unity does NOT inherit block-4's
  faked-`/20e3` bug (both R_in and R_f move the measurement).
- **Group B: all 3 SOUND, no defects.** wf_fold is the gold standard — the ×2 folder gain is genuinely
  realized from R25/R_f_wf (perturbation moves the fold AND trips the bind), disproving the
  "ideal-clamp + hardcoded ×2 = vacuous" risk. dist_clip's [NV] no-bind justification verified honest.
- **Group C: SOUND, all 4 binds load-bearing.** Independently confirmed the R181 "~50mV" comment is
  stale (real ≈0.95V input-referred @ 21Vpp = R177/R181·ΔVout, ~19× off). Used an isolated git worktree.
- **Coordination note:** the 3 verifiers shared one checkout and cross-restored each other's nets.yaml
  probes; final tree verified CLEAN at baseline + full gate re-run green before integrating. (Future:
  give concurrent perturbation reviewers separate worktrees.)

## Stage 4 — integrate ✅ (one finding fixed; gates green)
- **Fixed the stale comment:** R181 `~50mV @ ±12 swing` → `~0.95V input-referred @ ±10.5V/21Vpp =
  R177/R181·ΔVout` (dist2/dist3 carry no numeric, so only dist1 needed it). The 2.2M value is correct —
  only the comment was wrong.
- No netlist bug found in block-6-dist (unlike 0024/0025) — the 22k6 ref (the 0025 fix), the ±4V CLIP
  threshold, and the wavefold all verified correct. The run's products: the math-proof coverage + closing
  the block-6 ref-divider gap + the stale-comment fix.
- All 7 `--check` gates green; 7 block-6-dist1 decks pass (40 decks total).

## Gate checklist
- [x] Stage 1 derive → manifest (6 checks + dist_clip note; top = block-6 ref-divider gap)
- [x] Stage 2 write decks (3 parallel → 6 new + [NV] note)
- [x] Stage 3 verify-intent (3 adversarial → ALL SOUND; confirmed the stale hysteresis comment)
- [x] Stage 4 integrate (fixed the stale comment; all 7 gates green)
- [x] Update `specs/SPICE-COVERAGE.md` (block-6-dist1 BASELINE → FULL)
- [ ] PR `change/0027-spice-math-block6dist` → `dev`

## Outstanding (tracked in `specs/SPICE-COVERAGE.md`)
- dist2/dist3 are identical copies of dist1 (one representative deck stands for the repeat).
- Remaining BASELINE blocks (5/8/1/A + block-6 svf1/mix) still need the binds+verify promotion.
- [NV] items (THAT2180 6.1mV/dB DRIVE law, DRIVE knob→Ec+ dB map, zener/diode clamp absolutes) await bench.
