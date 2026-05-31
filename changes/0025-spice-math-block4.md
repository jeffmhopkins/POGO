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

## Manifest (Stage 1)
_(pending deriver)_

## Decisions log
- 2026-05-31: picked block-4 over block-5 (filter sibling, low new value) and block-6 (sprawling, most
  [NV] debt) — block-4 has distinct VCA physics + is self-contained + maximally exercises [NV] framing.

## Gate checklist
- [ ] Stage 1 derive → manifest
- [ ] Stage 2 write decks (parallel)
- [ ] Stage 3 verify-intent (parallel, adversarial)
- [ ] Stage 4 integrate + full gate stack green
- [ ] PR `change/0025-spice-math-block4` → `dev`
