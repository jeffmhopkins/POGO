# 0024 — SPICE circuit-math validation pilot (block-7 HP)

- **Lane:** B (tooling + test fixtures). Adds SPICE decks + a deck-authoring guide; no DSP, panel,
  `components.yaml` connectivity, or nets change.
- **Status:** OPEN
- **Opened:** 2026-05-31
- **Branch:** `change/0024-spice-math-pilot` (stacked on `change/0023-spice-coverage`).

## Intent

Pilot a **multi-agent methodology** for making "every circuit-math reference in the schematic is
valid" provable, on ONE representative block (**block-7, HP filter** — richest self-contained block:
expo converter, gm-C SVF, Q-control, polarity, calibration math; mono + single-sheet, no cross-block
shared cells). If it works, generalize to the other blocks in follow-ups.

The principle (see `tools/SPICE-DECK-GUIDE.md`): the **deck encodes the netlist's values**, the
**`.expect.yaml` encodes the spec/plugin's intended math**, so a netlist↔spec divergence FAILS the
gate — turning the spec's circuit math into executable, falsifiable checks.

## Pipeline (stages)

1. **Derive** [1 agent] — read spec + netlist + plugin DSP + aux; emit a structured manifest of every
   math claim → check candidate (claim, source line, plugin_ref, spice-able?, [NV]?, proposed
   model/measurement/expected-from-spec/tolerance, already-covered?). Prioritized shortlist.
2. **Write** [parallel agents] — each authors a subset of the shortlist decks + `.expect.yaml`,
   following the guide; runs `build_spice.py --run block-7` to confirm PASS.
3. **Verify-intent** [parallel agents] — adversarially check each new deck: (a) does the deck *compute*
   what its assertion claims? (b) does the assertion *match the spec's math* (not copied from deck
   output)? (c) would it actually FAIL if the netlist value were wrong? Report defects.
4. **Integrate / final review** [orchestrator] — reconcile verifier findings, fix, run the full gate
   stack, commit.

## Deliverables
- `tools/SPICE-DECK-GUIDE.md` (the shared authoring + verification-philosophy reference). ✅ written.
- New `specs/block-7/sim/*.cir` + `*.expect.yaml` covering the derived math claims (target: every
  spice-able, derivable claim in block-7 has a passing, falsifiable check).
- This change file records the manifest, the per-stage agent outputs, and the non-spice-able claims
  acknowledged out of scope.

## Manifest (Stage 1 output) — 12 candidates; 7 new checks to author

| id | claim | spice | nv | covered? |
|---|---|---|---|---|
| hp-fref | gm-C corner = 632Hz @ Iabc 9.69µA, C=47nF | Y | nv | ✅ ota_svf_loop |
| hp-voct-slope | V/oct base divider = 17.92 mV/oct centered | Y | — | ✅ expo_voct |
| **hp-svf-hp-transfer** | 2-pole HP: +12dB/oct LF, 0dB passband, corner=f₀, peak≈Q | Y | — | **NEW (top)** |
| **hp-polarity** | HP_OUT = −(x−k·v1−v2) via inv-summer+unity follower; bug=2nd inversion | Y | — | **NEW** |
| **hp-sumamp-vground** | inv virtual-ground summer, R_f/R_in=1, v(−)≈0 | Y | — | **NEW** |
| **hp-voct-octave** | 1V/oct end-to-end: f₀ ratios 1:8 (−3V), 32× (+5V) | Y(beh) | ratios nv-free | **NEW** |
| **hp-qbutterworth** | R_Iabc 100k → Iabc 0.7µA, Q≈0.74; 1M@0V bug = 10.8µA | Y | nv→range | **NEW (mirror)** |
| **hp-ires-summer** | IRES_AMP inv summer ratios + monotone res→Q sign | Y | — | **NEW** |
| **hp-iref-target** | I_ref leg R_total 1000–1500k; 9.69µA setpoint at 47.6% travel | P | nv→range | **NEW** |
| hp-rlin-range | OTA ±lin range = VT+Iabc·R_LIN/2 | P | nv | skip (low falsifiability) |
| hp-d12-clamp | V_ires clamp | P | nv | **DEFER** — clamp polarity is an open §D item |
| hp-mono-tracking | one HP_IABC net → both channels | N | — | out (structural/DRC) |

**Not SPICE-able (acknowledged):** pinouts (generate_schematic pin-coverage), IC/package sharing +
sourcing (BOM), layout/placement, power budget, mono fan-out connectivity.

**⚠️ Spec↔netlist divergence found:** `spec.md:152-153` still says R_Iabc=1MΩ / V_ires=0.74V (pre-0020);
netlist R104/R105=100k + aux §D carry the fix. The `hp-qbutterworth` deck derives `expect` from the
netlist/aux math; the stale §3 line is corrected during integration (Stage 4).

### Writer slices (parallel)
- **A:** hp-svf-hp-transfer, hp-polarity (structural + sign; most complex)
- **B:** hp-sumamp-vground, hp-ires-summer (inverting-summer ratio checks)
- **C:** hp-voct-octave, hp-qbutterworth (mirror), hp-iref-target (expo/Q bias)

## Decisions log
- 2026-05-31: pilot scope limited to block-7 (one block) per the user; methodology proven here before
  generalizing. Stacked on 0023 so the gate infra is present; 0023 (#53) merges independently.

## Gate checklist
- [ ] Stage 1 derive → manifest
- [ ] Stage 2 write decks (parallel)
- [ ] Stage 3 verify-intent (parallel, adversarial)
- [ ] Stage 4 integrate + full gate stack green
- [ ] PR `change/0024-spice-math-pilot` → `dev`
