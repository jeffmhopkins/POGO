# SPICE behavioral-check coverage tracker

Living status of the per-block SPICE math-validation effort. The gate
(`tools/build_spice.py --check`, blocking since 0023) runs every deck listed here.
Methodology + how to extend: `tools/SPICE-DECK-GUIDE.md`.

**Last updated:** 2026-05-31 (change 0025) · **28 decks across 11 block dirs, all passing.**

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
| **block-5** LP1 | 4 | 🟡 BASELINE | expo, OTA loop, q_cell, tilt-passive. **No netlist_bind; not verified.** Filter sibling of block-7 — pipeline would mostly mirror. |
| **block-8** LP2 | 2 | 🟡 BASELINE | expo, OTA loop (mirrors block-5/7). No binds. |
| **block-3** Mod Bus | 1 | 🟡 BASELINE | modbus_depth (§H). No binds; summer/SCALE/OFFSET law unchecked. |
| **block-A** Input | 1 | 🟡 BASELINE | input_clamp (unity + BAT54S). No binds. |
| **block-1** Pre-Gain | 1 | 🟡 BASELINE | pregain (5× + clip). No binds. |
| **block-6-svf1** | 1 | 🟡 BASELINE | bp_fref (68nF→400Hz vs 47nF trap). No binds. Representative for svf2/svf3. |
| **block-6-dist1** | 1 | 🟡 BASELINE | dist_clip (HC/WF/SC thresholds). No binds. Representative for dist2/dist3. |
| **block-6-mix** | 1 | 🟡 BASELINE | bp3_normal (§G). No binds. |
| **block-2** LFO | 0 | ⚪ NONE | time-domain rate law (0.05–20Hz) — needs a transient deck. |
| **block-B** Output | 0 | ⚪ NONE | output buffers — same unity-follower physics as block-A input_clamp (low new value). |
| block-6-svf2/svf3 | 0 | ⚪ (covered by svf1) | identical to svf1 — one representative deck stands for the repeat. |
| block-6-dist2/dist3 | 0 | ⚪ (covered by dist1) | identical to dist1. |

## Outstanding work (prioritized)

### A. Promote BASELINE → FULL (add netlist_bind + adversarial verify)
The 0022/0023 decks predate `netlist_bind` (built in 0024) and were never adversarially verified — so
they are deck-literal-vs-spec, not netlist-vs-spec, and may harbor the same gaps the verify stage found
in block-4 (a hardcoded value that wouldn't catch a netlist regression). Retrofit binds + run the verify
stage on each:
- [ ] **block-5** (LP1) — 4 decks. Highest priority of the baselines (most decks, resonant loop).
- [ ] **block-3** (Mod Bus) — modbus_depth; also AUTHOR the SCALE/OFFSET/summer-law decks (only depth covered).
- [ ] **block-8** (LP2) — 2 decks.
- [ ] **block-1, block-A** — 1 deck each (add binds: pregain R3/R4; input_clamp R-prot).
- [ ] **block-6-svf1 / dist1 / mix** — add binds; the svf/dist decks should bind the 68nF cap, the
      zener/diode thresholds, the BP3 buffer Rs.

### B. New blocks (⚪ → coverage)
- [ ] **block-2 LFO** — transient deck for the 0.05–20Hz rate law (the one time-domain block; deferred since 0023).
- [ ] **block-B** — only if a distinct claim beyond block-A's clamp is wanted (low priority).

### C. Deferred / [NV] items awaiting bench measurement (cannot close in-env)
These are documented in the relevant change files; they need real hardware/datasheet numbers before a
deck can assert an absolute (today only trim-authority/ratio/shape is checkable):
- [ ] **block-7/5/8 Q-cell** — the IRES_AMP **negative-V_ires drive + clamp polarity** (R_Iabc=100k done;
      the bias-network drive into the −10.8V window is Phase-3R; see 0020 §D, 0024).
- [ ] **block-4/6 VCA Ec+** — the absolute **THAT2180 6.1 mV/dB** constant (only ±2dB *authority* checked).
- [ ] **block-6 DRIVE** — the knob→Ec+ dB law + CLIP ±4V threshold trim (Phase-3R).
- [ ] **block-7 D12 clamp** — V_ires clamp polarity is an open §D item (deck deferred until the bias redesign closes).
- [ ] **THAT340 tempco** — external +3300ppm; the V/oct slope deck checks trim-centering, not the absolute TCR.

### D. Known real fixes already applied (for the record)
- ✅ **0024:** built `netlist_bind` (the gate wasn't netlist-bound); fixed stale spec.md:152 (R_Iabc 1M→100k).
- ✅ **0025:** fixed the HIGH-3 ±ref divider — R233/R234 45k3→11k3 (block-4) + R243…R256 45k3→22k6
      (block-6 DRIVE); the 45k3 gave ±0.32V (~±0.5dB authority) not the intended ±1.2V/±2dB.

## How to pick the next block
Prefer **distinct physics** + **analog-critical** + **self-contained**. Done: block-7 (filter), block-4
(VCA). Next-best new physics: **block-3 mod-bus** (summing/distribution) or **block-6 dist** (nonlinear
clip/fold). Baselines (block-5/8) are quick FULL-promotions but lower new-bug yield (filter siblings).
