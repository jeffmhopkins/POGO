# POGO aux — circuit-design library

A **typed, SPICE-verified library of reusable analog building blocks**, factored out of the POGO
blocks so future modules can iterate from proven sub-circuits. Each entry lives at
`specs/aux/<type>/<name>/` and holds a `spec.md` (topology + transfer function + component rationale +
"Used By") and a `sim/` folder of ngspice decks that verify its math.

## Library sim convention (differs from block sims)
Block sims (`specs/block-*/sim/`) use **`netlist_bind`** to pin a deck literal to the block's actual
netlist value (netlist-vs-spec). Library sims are **generic** — there is no netlist behind a library
block — so they use **hardcoded representative values** (NO `netlist_bind`) and verify the *transfer
math / topology* (the textbook law). They are auto-discovered and run by `build_spice.py --check` (the
runner globs `specs/**/sim/*.cir`); a broken library deck fails CI.

## Layering: primitives → composed cells
The library is two-tier. **Primitives** are the smallest reusable element (one op-amp section, one
gm-C section, one divider); they hold the canonical transfer function + sim. **Composed cells** wire
primitives together and sim only the composition behavior, referencing their primitives via
"**Composes:**". This keeps the math in one place.

## Taxonomy

| Type | Entries | Role |
|---|---|---|
| **filter** | gm-c-integrator·, voct-expo-divider·, ota-c-svf, expo-converter, q-control | OTA-C SVF + V/oct + resonance |
| **vca** | vca-cell, ref-injection-trim | THAT2180 dB-law VCA + Ec+ trim |
| **distortion** | overview, soft-clip, hard-clip, wavefolder | per-band SC/HC/WF + CD4053 mux |
| **modulation** | inverting-summer·, schmitt-trigger·, lfo-core, mod-bus-core, attenuverter | LFO, mod bus, attenuverters |
| **utility** | unity-buffer, cv-protection, power-filter, output-buffer, clip-detector | buffers, protection, power, I/O, CLIP |
| **led** | led-breathing | NPN current-source brightness driver |

`·` = primitive. Entries without `·` are composed cells (or self-contained).

## Status (build-out is phased — changes 0030/0031/0032)
- **0030 (this change):** moved the 11 existing aux into the typed tree (dropped the `aux-` prefix);
  swept all live references. No sims yet on the moved entries.
- **0031 (planned):** author `sim/` decks for the 11 moved entries + reconcile each spec against the
  current block/netlist/plugin (catch staleness).
- **0032 (planned):** author the new extracted entries (marked NEW below) + their sims; wire the
  "Composes:" cross-links.

### Entry status
| Entry | Source | Sims | Notes |
|---|---|---|---|
| filter/ota-c-svf | existing | 0031 | composed (gm-c-integrator) |
| filter/expo-converter | existing | 0031 | composed (voct-expo-divider) |
| filter/q-control | existing | 0031 | LM13700 Iabc→Q |
| filter/gm-c-integrator | **NEW 0032** | 0032 | primitive |
| filter/voct-expo-divider | **NEW 0032** | 0032 | primitive |
| vca/vca-cell | existing | 0031 | composed |
| vca/ref-injection-trim | **NEW 0032** | 0032 | HIGH-3 ±ref + R_ec/R_inj (block-4 + block-6) |
| distortion/overview | existing | 0031 | parallel paths + CD4053 mux |
| distortion/soft-clip | **NEW 0032** | 0032 | tanh diode chain |
| distortion/hard-clip | **NEW 0032** | 0032 | back-to-back zener ±5.8V |
| distortion/wavefolder | **NEW 0032** | 0032 | Buchla folder 2·Vclamp−Vin |
| modulation/lfo-core | existing | 0031 | composed (integrator + schmitt) |
| modulation/mod-bus-core | existing | 0031 | composed (inverting-summer) |
| modulation/attenuverter | existing | 0031 | composed (inverting-summer + bipolar divider) |
| modulation/inverting-summer | **NEW 0032** | 0032 | primitive |
| modulation/schmitt-trigger | **NEW 0032** | 0032 | primitive |
| utility/unity-buffer | existing | 0031 | primitive |
| utility/cv-protection | existing | 0031 | 100Ω + BAT54S |
| utility/power-filter | existing | 0031 | board power filtering |
| utility/output-buffer | **NEW 0032** | 0032 | buffer + 1k series + ±11V clamp (block-B) |
| utility/clip-detector | **NEW 0032** | 0032 | window comparator + hysteresis + diode-OR (block-6) |
| led/led-breathing | **NEW 0032** | 0032 | NPN level-shift current source (block-2) |

## How to add a library block
1. `specs/aux/<type>/<name>/spec.md` — use the template in `CLAUDE.md` (§"aux/ Library Template").
   Add a `**Type:**` line and, for a composed cell, a `**Composes:**` line.
2. `specs/aux/<type>/<name>/sim/<claim>.cir` + `.expect.yaml` — hardcoded-value decks per
   `tools/SPICE-DECK-GUIDE.md`; NO `netlist_bind`; `op`/bounded `tran`/`ac`. `--check` auto-runs them.
3. Reconcile against any block that uses it (the "Used By" table) so the library and the live design agree.
