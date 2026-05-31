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

## Manifest (Stage 1 output)
_(pending deriver agent)_

## Decisions log
- 2026-05-31: pilot scope limited to block-7 (one block) per the user; methodology proven here before
  generalizing. Stacked on 0023 so the gate infra is present; 0023 (#53) merges independently.

## Gate checklist
- [ ] Stage 1 derive → manifest
- [ ] Stage 2 write decks (parallel)
- [ ] Stage 3 verify-intent (parallel, adversarial)
- [ ] Stage 4 integrate + full gate stack green
- [ ] PR `change/0024-spice-math-pilot` → `dev`
