# SPICE behavioral-validation harness — plan

> **Status: PLANNED (design only).** Full design + rationale live in
> `changes/0021-spice-block-unit-tests.md`. This file is the short pointer the rest of the repo
> links to. No runner exists yet; do not assume a `build_spice.py` gate is wired.

## One-paragraph summary

The six `--check` gates verify *artifact self-consistency* (yaml↔sch, DRC, BOM, registry,
netlist-viz drift) but say nothing about whether a netlist actually **behaves** like the plugin DSP
it claims to implement. The SPICE harness closes that gap: each block gets a `sim/` folder of
ngspice decks (`*.cir`) plus assertion files (`*.expect.yaml`) that pin measured behavior (V/oct
slope, f_ref, Q range, clip thresholds, mod-bus depth, VCA gain law) to the plugin ground truth. A
future `tools/build_spice.py --check` becomes the 7th CI gate (advisory first, then blocking).

## Status / rollout

| Stage | Change | State |
|---|---|---|
| Design + convention (this doc, dir layout, `.expect.yaml` schema) | **0021** | ✅ done (merged) |
| `tools/build_spice.py` runner + migrate `specs/sim/` → per-block `sim/`; land gate **advisory** | **0022** | ✅ done (7 decks: block-3/4/5/6-mix) |
| Author decks for all blocks; promote gate to **blocking**; graduate 0020 `[NV]` values | 0023 (proposed) | not started |

## History (change 0020 → 0022)

0020 validated its CV-conditioning fixes with ad-hoc decks under a flat `specs/sim/` scratch dir
(the first deck caught a 2.1× expo-divider value error before it reached any netlist — and SPICE went
on to catch 5 bad values across the change). **Change 0022 migrated the keeper decks into per-block
`sim/` folders with `.expect.yaml` assertions and landed the advisory `build_spice.py --check` gate;
the flat scratch dir is gone.**

## Convention (now live)

```
specs/block-N/sim/
├── <subcircuit>.cir          # self-contained ngspice deck
├── <subcircuit>.expect.yaml  # measurement → expected value + tolerance + plugin_ref
└── README.md                 # coverage + plugin-law mapping
```

The runner skips cleanly (xfail) when `ngspice` is absent, so non-SPICE dev/CI legs still pass.
