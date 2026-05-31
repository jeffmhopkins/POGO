# 0022 — SPICE behavioral runner + per-block deck migration (implements 0021)

- **Lane:** B (build-system / tooling). Adds a test runner + test fixtures + an **advisory** CI gate;
  no DSP, no panel geometry, no `components.yaml` connectivity, no nets change.
- **Status:** OPEN
- **Opened:** 2026-05-31
- **Branch:** `change/0022-spice-runner` off `dev`.

## Intent

Implement the harness **designed** in change 0021: a runner (`tools/build_spice.py`) that executes
per-block ngspice decks against `.expect.yaml` assertions, and migrate change-0020's flat scratch
decks (`specs/sim/*.cir`) into per-block `sim/` folders with assertions. Land the gate **advisory**
(non-blocking) per the 0021 rollout; promote to blocking once every block has coverage (0023).

## What landed

### Runner — `tools/build_spice.py`
- `--list` — enumerate decks + coverage (checked vs scratch).
- `--run BLOCK` — run one block's decks, verbose measured-vs-expected.
- `--check` — CI gate: every deck with a sibling `.expect.yaml` must pass all assertions.
  - **Skips cleanly (exit 0) when `ngspice` is absent** — non-SPICE dev boxes / CI legs still pass.
  - Exit 0 also when there are no assertion files yet (nothing to verify).
- **Contract:** each deck's `.control` block emits measurements via ngspice `print <name>` (and
  `meas`), producing stdout lines `name = value`. The runner parses those (case-insensitive — ngspice
  lowercases vector names) and compares to the `.expect.yaml`. The deck owns the computation; the yaml
  owns the assertion (simpler + more robust than a yaml-side expression mini-language).

### Assertion schema (`specs/<block>/sim/<deck>.expect.yaml`)
```yaml
deck: expo_voct.cir
description: ...
plugin_ref: "plugin/src/dsp/... (the DSP law this validates)"
measurements:
  - name: mv_mid        # must match a `print <name>` in the deck
    expect: 17.92
    tol_pct: 3          # or tol_abs: 0.5 ; or expect: true (boolean: deck prints 1/0)
```

### Decks migrated (flat `specs/sim/` → per-block `sim/`, made runner-ready)
| Block | Deck | Validates (change 0020 finding) |
|---|---|---|
| block-5 | expo_voct | §A expo V/oct divider slope + trim authority (17.92 mV/oct centered) |
| block-5 | ota_svf_loop | §C OTA tap DC offset (1.26 V buggy → 0 fixed) + f_ref 632 Hz |
| block-5 | q_cell | §D/M5 Iabc bias (10.8 µA bug → 0.7 µA fixed, Q≈0.74) |
| block-5 | lp1_tilt_passive | §B passive tilt sum = 1:1 octave weight (saved a TL072) |
| block-3 | modbus_depth | §H mod depth 3% (bug) → 99% (fix) |
| block-4 | vca_ecplus | HIGH-3 Ec+ trim: rheostat 0.004 dB (useless) vs injection ±2 dB |
| block-6-mix | bp3_normal | §G BP3 R→L normal: (L+R)/2 bug → clean L |

7 checked decks, all pass. The remaining flat scratch decks (intermediate exploration —
lp1_tilt_sum, modbus_hiZ, modbus_load, vca_ecplus_full, wf_phase) were removed; their findings are
captured in `changes/0020-cv-conditioning-fixes.md`.

### CI
- Added to the primary Linux job in `.github/workflows/build.yml` after the netlist-viz gate:
  install ngspice + `build_spice.py --check`, **advisory** (`|| ::warning::`) per 0021. Promote to
  blocking in 0023 once coverage is complete.

## Verification
- `python3 tools/build_spice.py --check` → OK (7 decks). `--list`/`--run` work.
- ngspice-absent path → SKIP, exit 0 (verified).
- The six existing `--check` gates + parity unaffected (no source/nets/components change).

## Future work (0023, proposed)
- Author decks for the remaining blocks (A/1/2/B + block-6 svf/dist/clip). Promote the gate to blocking.
- Graduate change-0020's [NV] items to verified assertions once bench/datasheet numbers land.

## Decisions log
- 2026-05-31: deck contract = `print <name>` lines (deck computes, yaml asserts) — simpler/robister
  than a yaml expression DSL. Runner matches names case-insensitively (ngspice lowercases output).
- 2026-05-31: gate lands **advisory** (non-blocking) per the 0021 rollout; flat scratch decks removed
  (migrated or findings-captured).

## Gate checklist
- [ ] CI green on the branch (advisory SPICE gate runs; six existing gates unaffected)
- [ ] PR `change/0022-spice-runner` → `dev`
