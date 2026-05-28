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
for all blocks; board layout (Phase 5R) is in progress.

| Phase | Description | Status |
|---|---|---|
| Phase 1R | Extract functional spec from plugin code (all blocks) | ✅ Complete |
| Phase 2R | Analog behavior model (bilinear transform inverse) | ✅ Complete |
| Phase 3R | Circuit design — all 10 blocks + components.yaml finalized | ✅ Complete |
| Phase 4R | Panel — 48HP, DRC-clean, CI-verified | ✅ Complete |
| Phase 5R | Board layout — 48HP, architecture under review | 🔄 In Progress |
| Phase 6R | Code validation — CI green, signal-path smoke tests | ✅ Complete |

See `specs/STATUS.md` for per-block detail.

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
│   ├── components.yaml            ← Global component registry (265 entries)
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
│   ├── block-A/spec.md            ← Input Buffers (LM4562)
│   ├── block-1/spec.md            ← Pre-Gain (NE5532D, 1×/5× switch)
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
├── kicad/                         ← KiCad schematics — STALE (40HP era)
│   ├── README-STALE.md            ← Do not regenerate until Phase 5R complete
│   ├── generate_control_board.py  ← 40HP era — not current topology
│   ├── generate_utility_board.py  ← 40HP era — not current topology
│   └── validate_*.py              ← 40HP era — KiCad CI step is disabled
│
├── design/
│   └── panel-debug.html           ← Interactive panel layer viewer (keepouts, DRC)
│
└── .github/workflows/build.yml    ← CI: Linux/Win/macOS builds + panel DRC check
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

The KiCad generators (`kicad/generate_*.py`) are **40HP-era and stale** — they reference
the old block topology and are not compatible with the current 48HP design. The KiCad
validation step in CI is currently disabled. New schematics will be generated in Phase 5R
once board architecture is finalized.

See `kicad/README-STALE.md` for details.

---

## Building the Plugin

### Via GitHub Actions (recommended — no local setup)

Every push to `main` or `dev` triggers Linux x64 + Windows x64 + macOS builds.

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
- **Phase 3R**: Circuit design (topology, IC selection, component values, BOM)

See `CLAUDE.md` for the full development paradigm and workflow.
