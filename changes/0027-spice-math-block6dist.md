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

## Candidate claims (pre-derive sketch — the deriver produces the authoritative manifest)
- **wf-folder-reflection** — Buchla folder V_out = 2·V_clamp − V_in: non-inv G=+2 from R25/R_f_wf=10k
  (1+R_f/R_g) → the signature wavefold topology. Bind R25, R_f_wf.
- **dist-cell-unity** — HC/SC op-amp gain stages unity inverting: R20/R21=10k (HC), R18/R19=10k (SC).
  The clip *onset* is set by the DRIVE VCA ahead, not these cells. Bind the pairs.
- **drive-iv-unity** — DRIVE VCA I/V transimpedance −R155/R153 = −20k/20k = −1 (mirrors block-4). Bind.
- **drive-summer-unity** — DRIVE control summer R157/158/159/160 = 100k unity (knob+CV+bias). Bind.
- **drive-ref-divider** — HIGH-3 ±ref ±1.2V from R243/R244=22k6 (the 0025 fix; block-6 was unchecked). Bind R243.
- **clip-threshold-4v** — ±4V CLIP window divider R186/R187 = 20k/10k → +12·10/30 = +4V (R188/189 → −4V).
  Plugin BP1_CLIP_LIGHT threshold ±4V. Bind R186, R187.
- **dist_clip retrofit** — audit + bind what's bindable (the clamp thresholds are zener/diode-Vf → [NV]).
- [NV] DRIVE Ec+ injection authority (THAT2180 6.1mV/dB) — same as block-4; trim-authority only.

## Pipeline (per the guide)
1. **Derive** [1 agent] — structured manifest of block-6-dist math claims → check candidates.
2. **Write** [parallel] — author the shortlist decks + `.expect.yaml` (with `netlist_bind`).
3. **Verify** [parallel adversarial] — three killer questions; Q3 load-bearing.
4. **Integrate** — fix findings, close seams, correct any spec/netlist bug surfaced, full gate stack.

## Decisions log
- 2026-05-31: picked block-6-dist over the quick baseline promotions (block-5/8 filter siblings) —
  distinct nonlinear physics (wavefold/clip), highest new-bug yield, and it closes the block-6
  HIGH-3 ref-divider coverage gap left by 0025. dist1 is representative; dist2/dist3 are identical.

## Gate checklist
- [ ] Stage 1 derive → manifest
- [ ] Stage 2 write decks (parallel)
- [ ] Stage 3 verify-intent (parallel adversarial)
- [ ] Stage 4 integrate (fix findings; all 7 gates green)
- [ ] Update `specs/SPICE-COVERAGE.md` (block-6-dist1 BASELINE → FULL)
- [ ] PR `change/0027-spice-math-block6dist` → `dev`

## Outstanding (tracked in `specs/SPICE-COVERAGE.md`)
- dist2/dist3 are identical copies of dist1 (one representative deck stands for the repeat).
- Remaining BASELINE blocks (5/8/1/A + block-6 svf1/mix) still need the binds+verify promotion.
- [NV] items (THAT2180 6.1mV/dB DRIVE law, DRIVE knob→Ec+ dB map, zener/diode clamp absolutes) await bench.
