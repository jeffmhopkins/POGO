# 0025 — SPICE circuit-math validation: block-4 (VCA)

- **Lane:** B (tooling + test fixtures). SPICE decks only; no DSP, panel, `components.yaml`
  connectivity, or nets change.
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

### Writer slices (parallel)
- **A:** vca-amt-symmetric-unity, vca-cv-summer-ratio (the U63 control-chain topology/ratio — most complex)
- **B:** vca-iv-unity (+input-Z), vca-gain-law-shape (audio path + dB-law shape)
- **C:** vca-vctrl-buffer-unity, vca-ref-divider-level (HIGH-3 seam) + **retrofit netlist_bind into vca_ecplus**

## Decisions log
- 2026-05-31: picked block-4 over block-5 (filter sibling, low new value) and block-6 (sprawling, most
  [NV] debt) — block-4 has distinct VCA physics + is self-contained + maximally exercises [NV] framing.

## Gate checklist
- [ ] Stage 1 derive → manifest
- [ ] Stage 2 write decks (parallel)
- [ ] Stage 3 verify-intent (parallel, adversarial)
- [ ] Stage 4 integrate + full gate stack green
- [ ] PR `change/0025-spice-math-block4` → `dev`
