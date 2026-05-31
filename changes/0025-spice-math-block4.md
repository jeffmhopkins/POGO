# 0025 — SPICE circuit-math validation: block-4 (VCA)

- **Lane:** B (tooling + test fixtures) **+ a real netlist fix** the SPICE-math gate surfaced
  (block-4 + block-6 DRIVE ±ref divider resistors — see "Bug found" below). Touches `nets.yaml` +
  `components.yaml` values (no plugin/panel/connectivity change).
- **Status:** OPEN
- **Opened:** 2026-05-31
- **Branch:** `change/0025-spice-math-block4` (stacked on `change/0024-spice-math-pilot` — inherits
  `netlist_bind` + the multi-agent pipeline guide).

## Intent

Second run of the multi-agent SPICE-math pipeline (`tools/SPICE-DECK-GUIDE.md` Part 2), on **block-4
(VCA)** — chosen to test that the methodology GENERALIZES to genuinely different physics, not a filter
sibling. block-4 is a dB-law (log-domain) THAT2180 VCA: current-in/current-out + I/V transimpedance,
the CV+OFS→symmetric-AMT→Ec+ control chain, and the HIGH-3 injection trim (change 0020). It stress-tests
the **[NV] pattern** hardest — the whole gain law hinges on the THAT2180's ~6.1 mV/dB control constant,
so the checks must verify trim AUTHORITY/RANGE, not absolutes.

Already covered (0023): `vca_ecplus.cir` (HIGH-3 Ec+ rheostat-vs-injection ±2dB authority).

## Pipeline (per the guide)
1. **Derive** [1 agent] — manifest of block-4 math claims → check candidates.
2. **Write** [parallel] — author the shortlist decks + `.expect.yaml` (with `netlist_bind`).
3. **Verify** [parallel adversarial] — three killer questions; Q3 (would it fail if the netlist were
   wrong?) load-bearing.
4. **Integrate** — fix findings, close seams, correct any spec/netlist bug surfaced, full gate stack.

## Manifest (Stage 1) — 11 candidates; 6 new checks + 2 integration retrofits

The **[NV] axis is the THAT2180 6.1 mV/dB control constant** — every *absolute* gain/Ec+→dB number is
[NV]. Checks are confined to four NV-safe classes: resistor RATIOS, dB-law SHAPE (equal Ec+ → equal dB),
trim AUTHORITY/RANGE, and TOPOLOGY/SIGN/PIVOT facts.

| id | claim | spice | nv | new? |
|---|---|---|---|---|
| **vca-amt-symmetric-unity** | AMT-center → V_ctrl=0 → unity for ANY OFS (the 0018 fix) | Y | — | **NEW (top)** |
| **vca-iv-unity** | I/V transimpedance −R_f/R_in = −1 (+ virtual-ground input-Z) | Y | — | **NEW** |
| **vca-cv-summer-ratio** | U63A unity inverting summer (R42/R43/R45) + U63B unity invert | Y | — | **NEW** |
| **vca-gain-law-shape** | dB-law log-linearity + unity anchor at Ec+=0 | Y | shape (abs [NV]) | **NEW** |
| **vca-vctrl-buffer-unity** | U97-A loaded unity pass-through g_ctrl≈0.984 | Y | — | **NEW (seam)** |
| **vca-ref-divider-level** | REF_P/N ≈ ±1.2V from R233/R234=45k3 | Y | — | **NEW** |
| vca-cv-protection-clamp | R9+BAT54S ±12.3V clamp | P | — | dedup vs block-A first |
| vca-ecplus-injection-authority | HIGH-3 ±2dB Ec+ trim | Y | range | ✅ vca_ecplus (NO BINDS) |
| vca-alt-shares-vctrl / -ofs-scaling | ALT mirror / OFS abs scaling | N/P | — | structural / Phase-3R — out |

**Not SPICE-able:** THAT2180 absolute dB law / 6.1mV/dB, effCV→Ec+ scaling + 5V pivot (Phase-3R),
pinouts, ALT shared-V_ctrl connectivity, sourcing/power/layout, THD/feedthrough datasheet specs.

### ⚠️ Integration findings (pre-write, from the deriver)
1. **`vca_ecplus.cir` (from 0023) has NO `netlist_bind`** — hardcodes ±1.23V/10k/1M/500Ω literals →
   currently deck-literal-vs-spec, not netlist-vs-spec. **Retrofit binds (R235/R239/R233).**
2. **`vca_ecplus_full.cir` referenced in spec.md:167 + aux:6 but does NOT exist.** Reconcile the
   dangling reference (the new `vca-vctrl-buffer-unity` deck effectively reconstructs it).

### Stage 2 — writers (3 parallel) ✅ COMPLETE — 6 new decks + retrofit, all PASS
- **A:** amt_symmetric (0018 OFS-fix: V_ctrl=0 at AMT-center for any OFS; binds R42-R46), cv_summer (unity summer ratios).
- **B:** iv_unity (−R_f/R_in=−1, binds R7/R40=20k), gain_law_shape (dB log-linearity + unity anchor; NO bind — NV-correct).
- **C:** vctrl_buffer (U97-A loaded unity g_ctrl≈0.984; reconstructs the absent vca_ecplus_full.cir), ref_divider
  (±1.2V from R233/R234=45k3) + **retrofit: added netlist_bind to vca_ecplus.expect.yaml** (R235/R236=10k, R239/R240=1M
  — the binds RESOLVED, so the 0023 deck's old literals did match the netlist; now bound).
- Writers self-ran Q3 probes (R46→200k, R43→200k, R40→200k, R235→1M, R233→4k53 all fail correctly).
  8 block-4 decks pass; no netlist↔spec divergence found. Reconciles the dangling vca_ecplus_full.cir ref.

## 🔴 BUG FOUND (the headline result) — HIGH-3 ±ref divider mis-sized

`ref_divider.cir` (slice C) computed REF_P from the **actual netlist** and got **±0.32 V**, not the
**±1.2 V** spec.md:166 + the 0020 HIGH-3 design claim. **Root cause (my error in change 0020):** R233/R234
were sized **45.3 k** assuming a *single* 10 k pot bridges REF_P↔REF_N — but all **four** unity trims
(RV1/RV2/RV46/RV47) share the rails in **parallel** = **2.5 k**, dragging REF_P to 0.32 V. So the Ec+
injection-trim authority was only **~±0.5 dB**, not the intended **±2 dB**. The block-6 DRIVE refs had the
**same bug** (R243/244/249/250/255/256 = 45.3 k with 2 pots each = 5 k bridge).

**Fix (this change):**
- block-4: **R233/R234 45k3 → 11k3** (→ +1.195 V with the 2.5 k load). nets + components + BOM.
- block-6 dist1/2/3: **R243/244/249/250/255/256 45k3 → 22k6** (→ +1.2 V with the 5 k load). nets + components + BOM.
- `ref_divider.cir`/`.expect.yaml` now pin the corrected ±1.195 V and **bind R233=11k3** — so a regression
  back to 45k3 FAILS the gate. Verified: ref_p = 1.195 V ✓, all binds resolve, all 7 gates green.

This is the second real design error the SPICE-math methodology has found (after the 0024 spec/netlist
divergence) — and the first that corrects live netlist component values. Exactly the goal: the gate
proves the schematic's circuit math, and caught a value that didn't deliver its stated function.

### Stage 3 — verifiers (2 parallel adversarial) — RUNNING
Sharpest block-4 angles: (1) does gain_law_shape (NO bind, [NV]) genuinely fail when perturbed or is it
vacuous? (2) is vctrl_buffer's tolerance hiding a buffer-absent case? (3) does amt_symmetric's
value-independent ofs0 instance weaken the OFS-fix claim (the load-bearing one is ofs2)?

## Decisions log
- 2026-05-31: picked block-4 over block-5 (filter sibling, low new value) and block-6 (sprawling, most
  [NV] debt) — block-4 has distinct VCA physics + is self-contained + maximally exercises [NV] framing.

## Gate checklist
- [ ] Stage 1 derive → manifest
- [ ] Stage 2 write decks (parallel)
- [ ] Stage 3 verify-intent (parallel, adversarial)
- [ ] Stage 4 integrate + full gate stack green
- [ ] PR `change/0025-spice-math-block4` → `dev`
