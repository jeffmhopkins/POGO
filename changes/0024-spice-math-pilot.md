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

### Stage 2 — writers (3 parallel agents) ✅ COMPLETE — 7 new decks, all PASS
- **A:** hp_transfer (2-pole HP: +12dB/oct, 0dB passband, corner=632Hz via arg(H)=+90° marker, peak=Q=6.02dB),
  hp_polarity (HP_OUT sign vs HPFilter.hpp:40 + in-deck bug regression guard).
- **B:** sumamp_vground (R_f/R_in=R_f/R_FB=−1, v(−)≈0), ires_summer (unity ratios + monotone res→Q sign).
- **C:** voct_octave (1V/oct ratios 0.125/32, NV-free), q_cell (§D 10.8µA bug → 0.7µA fix, Q=0.74),
  iref_target [NV] (R_total trim authority 1000/1238/1500k).
- **Both slice C and the deriver independently confirmed the stale `spec.md:152-153` (R_Iabc=1MΩ).**
  All 9 block-7 decks pass (2 pre-existing + 7 new); global gate green at 22 decks.
- Author notes: ngspice-42 mangles bare `>`/`<` in `let` → booleans via B-source ternary (now in the guide).

### Stage 3 — verifiers (2 parallel adversarial agents) — RUNNING
Three killer questions per deck: (Q1) does the deck compute what it claims? (Q2) is `expect` independently
spec-derived, not copied? (Q3) **would it FAIL if the netlist value were wrong** — i.e. is the deck bound
to block-7's real R/C values, or a generic textbook circuit that passes vacuously? Key target: does
`q_cell.cir` actually bind to R104/R105=100k such that it would have caught the 1M→100k regression?

### Stage 3 — verifiers (2 adversarial agents) ✅ — FOUND AN ARCHITECTURAL FLAW
The verify stage is the headline result. Both agents ran ngspice + perturbation probes (Q3):
- **SOUND for the defect they guard:** hp_polarity (inverting follower → fails), hp_transfer (LP/BP
  mistap → fails), sumamp_vground (Rf=200k → gain −2 fails), ires_summer. Genuinely non-vacuous.
- **🔴 ARCHITECTURAL FINDING (both agents, confirmed in code):** **decks hand-transcribe netlist values
  as literals; `build_spice.py` never read `nets.yaml`** — so the gate was *deck-literal-vs-spec*, NOT
  *netlist-vs-spec*. A silent regression (R104 100k→1M) would PASS GREEN. The two decks whose sole job
  was pinning a netlist resistor (q_cell, iref_target) pinned a hardcoded literal — the guide's core
  premise was *architecturally unmet*. This is the real product of the pilot: the multi-agent verify
  stage caught a design flaw in the gate itself.
- Minor: hp_transfer `peak_db` is a vacuous topology discriminator (LP/BP/HP all = Q at f0); ires_summer
  prose over-claims "→ Q↑" (the [NV] link). Noted.

### Stage 4 — integrate ✅
1. **Closed the binding gap (the fix):** added **`netlist_bind`** to `build_spice.py` + a netlist-value
   parser (handles `100k`/`47nF`/`1M`/R-notation `49k9`). An `.expect.yaml` now declares
   `netlist_bind: {R_Iabc_L: "R104=100k"}`; the runner resolves the ref from `nets.yaml` and **FAILS if
   the deck's literal ≠ the netlist's value.** Added binds to all value-pinning decks (q_cell,
   iref_target, expo_voct, ota_svf_loop, sumamp_vground, ires_summer, hp_transfer).
   **PROVEN:** temporarily reverting R104→1M in the netlist now **FAILS** q_cell's bind (the exact
   regression the verifier said passes green); restoring it passes. Guide updated to require `netlist_bind`.
2. **Fixed the spec bug the methodology found:** `spec.md:152-153` R_Iabc 1MΩ→**100kΩ** + the −10.8 V
   Iabc-pin model (the first concrete defect this SPICE-math process surfaced + corrected).
3. Full gate stack green (all 7 `--check` + parity, 0 schematic FAILs; 22 SPICE decks).

## Decisions log
- 2026-05-31: pilot scope limited to block-7 (one block) per the user; methodology proven here before
  generalizing. Stacked on 0023 so the gate infra is present; 0023 (#53) merges independently.
- 2026-05-31: **headline = the methodology + the architectural finding**, not the 7 decks (user). The
  verify stage proved its worth by finding that the gate wasn't actually netlist-bound; the fix
  (`netlist_bind`) makes the harness deliver on its premise.

## Gate checklist
- [x] Stage 1 derive → manifest (caught the stale spec line pre-emptively)
- [x] Stage 2 write decks (3 parallel agents → 7 decks, all PASS)
- [x] Stage 3 verify-intent (2 adversarial agents → found the netlist-binding architectural flaw)
- [x] Stage 4 integrate (built `netlist_bind`, proved the regression now fails, fixed the spec bug)
- [ ] PR `change/0024-spice-math-pilot` → `dev`
