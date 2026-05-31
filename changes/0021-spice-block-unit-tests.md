# 0021 — SPICE per-block unit-test build-check harness (DESIGN DOC / future tooling)

- **Lane:** C (trivial/docs) — this change only **documents the planned harness**; it does NOT
  build it or add a CI gate. No DSP math, no `panel-data.yaml` geometry, no `components.yaml`
  connectivity, no nets change.
- **Status:** OPEN
- **Opened:** 2026-05-30
- **Branch:** `change/0021-spice-block-unit-tests` off `dev`.

## Intent

During change 0020 (CV-conditioning fixes) we began validating analog sub-circuits with local
ngspice runs and found it immediately valuable — the very first deck caught a **2.1× error** in a
proposed expo-divider value before it could reach 8 netlist instances. This change captures that
practice as a **designed, repeatable harness**: each block carries a `sim/` unit-test folder whose
SPICE decks + expected-result assertions can later be ingested by a build check (a 7th `--check`
gate), the same way `generate_schematic.py --check` / `build_panel.py --check` work today.

**This change is the design + convention only.** Implementation (the runner, the CI wiring, the
per-block decks) is explicitly deferred and tracked as future work below. Meanwhile, 0020 continues
to use ad-hoc decks under `specs/sim/`; 0021 defines where those settle.

## Why a harness (not just ad-hoc decks)

- The six existing `--check` gates verify **artifact self-consistency** (yaml↔sch, DRC, BOM,
  registry) but **nothing about analog behavior**. A netlist can be DRC-clean and pass every gate
  while delivering 3% mod depth or a railed expo — exactly the class of bug the 0020 adversarial
  review found.
- SPICE closes that gap: a deck per sub-circuit asserts the *behavior* (V/oct slope, f_ref, Q range,
  clip threshold, mod-bus depth, VCA gain law) against the **plugin DSP** ground truth.
- Per-block folders keep decks next to the nets they validate and let the runner map failures to a
  block, mirroring the existing per-block `.nets.yaml` → `.kicad_sch` structure.

## Proposed design

### Directory convention
```
specs/block-N/sim/                         (or specs/block-6-<sec>/sim/ for the split sections)
├── <subcircuit>.cir         ngspice deck (self-contained; models the sub-circuit)
├── <subcircuit>.expect.yaml assertions (measurement → expected value + tolerance)
└── README.md                what each deck covers + how it maps to the plugin law
```
- During 0020, decks live in the flat `specs/sim/` scratch dir; 0021's runner migration moves them
  into the per-block `sim/` folders and adds the `.expect.yaml` assertions.

### Assertion file (proposed schema)
```yaml
# specs/block-5/sim/expo_voct.expect.yaml
deck: expo_voct.cir
description: LP1 expo V/oct base divider slope + trim authority
plugin_ref: "plugin/src/dsp/LPFilter.hpp f0 = f_ref*2^cv"
measurements:
  - name: base_mv_per_volt_mid_trim
    spice: "v(b)*1000 @ RWIP=5000"
    expect: 17.92          # V_T*ln2
    tol_pct: 12            # trim authority absorbs the rest
  - name: trim_spans_target
    spice: "min<=17.92<=max over RWIP sweep 0..10k"
    expect: true
```

### Runner (proposed) — `tools/build_spice.py`
- `--check` (CI gate): for every `*.cir` with a sibling `*.expect.yaml`, run `ngspice -b`, parse the
  measured values, compare to `expect ± tol`, exit non-zero on any miss. Skips cleanly (xfail, not
  fail) when `ngspice` is absent so non-SPICE dev boxes/CI legs still pass.
- `--run BLOCK`: run one block's decks and print measured-vs-expected.
- `--list`: enumerate decks + coverage.
- Output: a per-deck PASS/FAIL table; on `--check` failure, the block + measurement + Δ.

### CI integration (proposed, deferred)
- Add ngspice to the CI image; add `build_spice.py --check` as a **7th gate** alongside the six in
  CLAUDE.md "Invariants". Gate is **advisory-then-blocking**: land it advisory (report-only) until
  every block has decks, then promote to blocking.
- `[NV]` (needs-verify) values from 0020 become **tracked SPICE assertions** here — the harness is
  how an `[NV]` graduates to verified.

### Scope of decks to author (future work, per block)
| Block | Sub-circuit decks |
|---|---|
| 5,7,8 | expo V/oct slope+trim · OTA-C loop (f_ref, Q range, DC offset) · Q-cell Iabc vs V_ires |
| 4 | THAT2180 gain law (Ec+ mV/dB) · I/V transimpedance stability · VCA_OFS/AMT control |
| 6-svf1/2/3 | BP f_ref (68nF→400Hz) · Q ceiling (no self-osc) · tilt ×0.22 |
| 6-dist1/2/3 | SC/HC/WF clip thresholds vs Distortion.hpp · DRIVE VCA law · CLIP ±4V |
| 3 | mod-bus depth (the C2 bug) · SCALE/OFFSET law · clamp ±10V |
| 2 | LFO rate range 0.05–20Hz · breathing-LED law |
| 1,A,B | pre-gain 5× · clamp ±11V · buffer unity |

## Deliverables of THIS change (0021)
- [x] This design doc (`changes/0021-spice-block-unit-tests.md`).
- [x] A short pointer `tools/SPICE-PLAN.md` linking here as the spec for the future gate.
- [x] A note in `CLAUDE.md` "Enforcement note" that a SPICE behavioral gate is planned (7th
      `--check`), with this change as its design.
- **No runner, no decks migrated, no CI change** — those are 0022+ implementation changes.

## Future-work tracking (NOT in 0021)
- **0022 (proposed):** implement `tools/build_spice.py` + `.expect.yaml` schema + migrate 0020's
  `specs/sim/` decks into per-block `sim/` folders; land the gate advisory.
- **0023 (proposed):** author decks for all blocks; promote the gate to blocking; graduate 0020's
  `[NV]` values to verified assertions.

## Decisions log
- 2026-05-30: user requested a commit workflow that runs SPICE sims on netlists, with a per-block
  unit-test folder ingestible by build checks. Captured as a design doc now (Lane C); 0020 keeps
  using local ad-hoc `specs/sim/` decks meanwhile; implementation deferred to 0022/0023.

## Gate checklist
- [ ] CI green on the branch (docs-only; existing six gates unaffected)
- [ ] PR `change/0021-spice-block-unit-tests` → `dev`
