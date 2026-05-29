# POGO — Stereo Filter Bank

**POGO** is a stereo filter bank module (48HP) being developed by Space Coast
Synthesizers. The VCV Rack 2 plugin in this repository is the **working software prototype**
and ground truth. Analog hardware design is reverse-engineered from it.

---

## What It Does

POGO routes stereo audio through a deeply modulated filter bank: a pre-gain stage, a
voltage-controlled VCA, a stereo LP filter with tilt (LP1), three independent bandpass
resonators (BP1/BP2/BP3) with per-group distortion, a HP filter, and a final LP filter (LP2).
A dual triangle LFO feeds a central mod bus with 19 CV destinations — every key parameter
is voltage-controllable.

**Signal chain (48HP topology):**

```
Stereo In → Input Buffer → Pre-Gain (1×/5×)
                                  ↓
                             Pre-LP1 VCA   ← mod bus, VCA_OFS floor
                                  ↓
                            LP Filter 1    ← FREQ, TILT (stereo spread), RES
                                  ↓
               ┌──────────────────────────────────────┐
               │        Triple Bandpass Filter Bank    │
               │  BP1 / BP2 / BP3 — 40 Hz – 4 kHz     │
               │  per-group: FREQ / FOCUS / DIST       │
               │  global: OFFSET / TILT / MIX          │
               │  BP3_L/R ──────────────────────────► BP3 out jacks
               └──────────────────────────────────────┘
                                  ↓
                             HP Filter     ← FREQ, RES
                                  ↓
                            LP Filter 2   ← FREQ, RES
                                  ↓
                           Output Buffer
                                  ↓
                             Stereo Out

LFO1 / LFO2  →  ±5V triangle, 0.05–20Hz
Mod Bus      →  19 CV destinations (each: override jack + attenuverter)
```

**Hardware target:** 48HP, ±12V Eurorack. Power budget ~190 mA per rail (estimate; under
revision as block-level estimates are refined).

---

## Project State

The plugin and panel are complete and CI-passing. Circuit design (Phase 3R) is complete
for all blocks, and **per-block KiCad schematics are transcribed and CI-gated for all 10
blocks** (data-driven generator, see below). Board layout (Phase 5R)
is in progress.

| Phase | Description | Status |
|---|---|---|
| Phase 1R | Extract functional spec from plugin code (all blocks) | ✅ Complete |
| Phase 2R | Analog behavior model (bilinear transform inverse) | ✅ Complete |
| Phase 3R | Circuit design + per-block KiCad schematics — 10/10 blocks; `components.yaml` finalized | ✅ Complete |
| Phase 4R | Panel — 48HP, DRC-clean, CI-verified | ✅ Complete |
| Phase 5R | Board layout — 48HP, architecture under review | 🔄 In Progress |
| Phase 6R | Code validation — CI green, signal-path smoke tests | ✅ Complete |

See `specs/STATUS.md` for per-block detail, and `kicad/SCHEMATIC-GEN-PLAN.md` for the
schematic rollout.

---

## Repository Structure

```
POGO/
├── plugin/                        ← VCV Rack 2 plugin
│   ├── Makefile / plugin.json
│   ├── src/
│   │   ├── Pogo.cpp               ← Module: params, process(), widget
│   │   └── dsp/                   ← DSP classes (all blocks)
│   └── res/
│       └── Pogo.svg               ← Panel SVG (generated — do not hand-edit)
│
├── tools/                         ← Panel build system
│   ├── panel-data.yaml            ← SOURCE OF TRUTH for all panel positions
│   ├── build_panel.py             ← CLI: --check --resource --design --cpp --list
│   ├── panel_svg.py / panel_rules.py / panel_cpp.py
│   └── panel-tool-guide.md
│
├── docs/
│   └── plugin-topology.md         ← Authoritative 48HP plugin spec
│
├── specs/                         ← Hardware design documentation
│   ├── STATUS.md                  ← Phase completion checklist
│   ├── module-overview.md         ← Signal chain, power budget
│   ├── components.yaml            ← Per-ref design manifest (476 entries; block→ref→part)
│   ├── analog-design-review.md    ← Trim pots, parts availability, noise analysis
│   │
│   ├── aux/                       ← Circuit design library (shared building blocks)
│   │   ├── aux-ota-c-svf.md       ← OTA-C SVF (LM13700M + OPA1612 SUM_AMP)
│   │   ├── aux-expo-converter.md  ← THAT340S14-U V/oct expo converter
│   │   ├── aux-q-control.md       ← LM13700 resonance control
│   │   ├── aux-vca-cell.md        ← THAT 2180 VCA cell
│   │   ├── aux-unity-buffer.md    ← Unity-gain buffer
│   │   ├── aux-distortion.md      ← SC/HC/WF cells + CD4053 mux
│   │   ├── aux-attenuverter.md    ← Bipolar pot + inverter (mod bus destinations)
│   │   ├── aux-mod-bus-core.md    ← Inverting summer + distribution buffer
│   │   ├── aux-lfo-core.md        ← Triangle oscillator core
│   │   ├── aux-cv-protection.md   ← 100Ω + BAT54S clamp
│   │   └── aux-power-filter.md    ← Board power filtering
│   │
│   ├── block-A/spec.md            ← Input Buffers (OPA1612, BAT54S clamp)
│   ├── block-1/spec.md            ← Pre-Gain (OPA1612, 1×/5× switch + ALT path)
│   ├── block-2/spec.md            ← Dual LFO (triangle, 0.05–20 Hz)
│   ├── block-3/spec.md            ← Mod Bus (19 destinations, attenuverters)
│   ├── block-4/spec.md            ← VCA (THAT 2180, AMT + OFS)
│   ├── block-5/spec.md            ← LP Filter 1 (OTA-C SVF, stereo tilt)
│   ├── block-6/spec.md            ← Triple BP + Distortion (3× SVF + SC/HC/WF)
│   ├── block-7/spec.md            ← HP Filter (OTA-C SVF)
│   ├── block-8/spec.md            ← LP Filter 2 (OTA-C SVF, independent)
│   ├── block-B/spec.md            ← Output Buffers
│   │
│   ├── panel-design/panel-notes.md
│   ├── board-layout/layout-notes.md
│   └── archive/40hp-era-2026-05/  ← Superseded 40HP specs
│
├── components/                    ← Component SOURCING (catalog + footprints + datasheets)
│   ├── parts/<slug>/              ← Per-part: component.yaml (footprint, MPN, datasheet) + datasheet.pdf
│   ├── footprints/*.pretty        ← Vendored KiCad footprint libs (resolve as POGO_*)
│   ├── footprints.yaml            ← panel-type → footprint bindings
│   └── README.md
│
├── kicad/                         ← KiCad generator + generated artifacts
│   ├── generate_schematic.py      ← specs/block-*/*.nets.yaml → .kicad_sch (--check: coverage + structural + drift)
│   ├── gen_block6.py              ← Block-6 netlist generator (3-group repetition)
│   ├── kicad_common.py            ← Symbol library + pin helpers (datasheet-verified)
│   ├── pogo-*.kicad_sch           ← Generated schematics (one per block)
│   ├── pogo-bom.csv               ← Manufacturing BOM
│   ├── fp-lib-table               ← Generated; maps POGO_* → components/footprints/
│   ├── pogo.kicad_pro             ← KiCad project (placeholder root; real board = Phase 5R)
│   └── SCHEMATIC-GEN-PLAN.md      ← Schematic rollout plan / per-block gate doc
│
├── changes/                       ← Per-change records (changes/NNNN-<slug>.md) + _TEMPLATE.md
│
├── design/
│   └── panel-debug.html           ← Interactive panel layer viewer (keepouts, DRC)
│
└── .github/workflows/build.yml    ← CI: Linux/Win/macOS .vcvplugin builds + 5 --check gates
```

---

## Panel Build System

The panel is data-driven. **Never hand-edit SVG files.**

```bash
# Edit panel layout
edit tools/panel-data.yaml

# Rebuild SVG + debug HTML
python3 tools/build_panel.py

# DRC check (CI gate — must pass before commit)
python3 tools/build_panel.py --check

# Get C++ widget positions for Pogo.cpp
python3 tools/build_panel.py --cpp

# Interactive layer viewer (keepouts, footprints, DRC overlays)
open design/panel-debug.html
```

---

## KiCad Schematic Generation

Schematics are **data-driven and generated per block**. Each block's netlist source lives
with its spec (`specs/<block>/<block>.nets.yaml`) listing parts and name-based nets;
`kicad/generate_schematic.py` emits a byte-stable `kicad/pogo-<block>.kicad_sch`. All 10
blocks + the shared-Q sheet are transcribed and verified. (Authored netlist in `specs/`,
generated schematic in `kicad/` — linked by `--check`, not by directory adjacency.)

```bash
# Regenerate all block schematics
python3 kicad/generate_schematic.py

# CI gate: validate (pin coverage + structural re-parse + short detection + byte drift)
python3 kicad/generate_schematic.py --check

# Regenerate one block
python3 kicad/generate_schematic.py --block block-6
```

Connectivity is by net name, so per-block sheets merge at board level by matching boundary
nets. Symbols/pinouts in `kicad/kicad_common.py` are datasheet-verified. Vendored footprints
live in `components/footprints/*.pretty` (resolved via the generated `kicad/fp-lib-table`). The
manufacturing BOM (`kicad/pogo-bom.csv`) is generated from `specs/components.yaml` + the
`components/` registry. See `kicad/SCHEMATIC-GEN-PLAN.md` for the rollout and per-block notes.

> The 40HP-era board generators and validators have been removed (the data-driven per-block
> generator above supersedes them). A real board-level KiCad project is Phase 5R.

---

## Building the Plugin

### Via GitHub Actions (recommended — no local setup)

Every push to `main`, `dev`, or a `change/**` / `claude/**` branch (and every PR) triggers
Linux x64 + Windows x64 + macOS builds plus the five `--check` gates (`components.py`,
`fetch_datasheets.py`, `build_components.py`, `generate_schematic.py`, `build_panel.py`).

1. Go to **Actions → Build VCV Rack Plugin**
2. Click the latest run → scroll to **Artifacts**
3. Download `POGO-linux-x64-<run_number>`

```bash
# Install artifact
unzip POGO-linux-x64-*.zip -d ~/.rack2/plugins/
# Launch VCV Rack — POGO appears in the module browser
```

### Locally (requires Rack SDK)

```bash
export RACK_DIR=~/Rack-SDK
cd plugin
make dep
make dist
```

---

## Design Documentation

Hardware specs live in `specs/`. Paradigm: **code-first reverse engineering** — the working
plugin is the ground truth; specs are extracted from it.

- **Phase 1R**: Functional spec extracted from plugin code (params, signal flow, DSP math)
- **Phase 2R**: Analog behavior model (bilinear transform inverse, component values)
- **Phase 3R**: Circuit design (topology, IC selection, component values, BOM, KiCad schematics)

These Phase 1R–6R milestones are the **whole-project maturity track**.

## How Changes Are Made

Day-to-day work follows a gated, plugin-first process (full detail in `CLAUDE.md` →
"Git Workflow & Change Process"):

- **One `change/<slug>` branch per change → PR to `dev`.** Never commit directly to
  `dev`/`main`. Each non-trivial change is recorded in a persistent `changes/NNNN-<slug>.md`.
- **Pick a lane:** **A** behavioral (DSP/panel that changes what you hear — full Steps 0–8,
  gates G1–G6), **B** hardware-only (plugin already locked; spec/nets/components/schematic —
  enter at the spec step), **C** trivial (docs/tests/typos — no change file).
- **The plugin leads.** Intent → plugin + panel → verify in VCV Rack → **lock** plugin/panel
  → spec → schematic topology → netlist/BOM. Spec and schematic follow the locked plugin;
  they never lead it. If schematic work uncovers a plugin bug, that spawns a separate Lane A
  change.

The Phase 1R–6R milestones above and these per-change Steps 0–8 are orthogonal: one change
runs Steps 0–8 and advances a block toward its 1R–6R status.
