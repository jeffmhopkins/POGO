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
| Design + convention (this doc, dir layout, `.expect.yaml` schema) | **0021** | in progress |
| `tools/build_spice.py` runner + migrate `specs/sim/` → per-block `sim/`; land gate **advisory** | 0022 (proposed) | not started |
| Author decks for all blocks; promote gate to **blocking**; graduate 0020 `[NV]` values | 0023 (proposed) | not started |

## Meanwhile (interim, change 0020)

0020 validates its CV-conditioning fixes with **ad-hoc decks under `specs/sim/`** (flat scratch dir),
run by hand with `ngspice -b`. These are the seed decks the 0022 runner will migrate into per-block
`sim/` folders and wrap with `.expect.yaml` assertions. Already proved value: the first deck
(`specs/sim/expo_voct.cir`) caught a 2.1× error in a proposed expo-divider value before it reached
any netlist.

## Convention (target)

```
specs/block-N/sim/
├── <subcircuit>.cir          # self-contained ngspice deck
├── <subcircuit>.expect.yaml  # measurement → expected value + tolerance + plugin_ref
└── README.md                 # coverage + plugin-law mapping
```

The runner skips cleanly (xfail) when `ngspice` is absent, so non-SPICE dev/CI legs still pass.
