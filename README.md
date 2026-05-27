# POGO — Complex Stereo Eurorack Filter

**POGO** is a complex stereo Eurorack filter module (48HP) being developed by Space Coast
Synthesizers. The VCV Rack 2 plugin in this repository is the **working software prototype**
and ground truth. Analog hardware design is reverse-engineered from it.

---

## What It Does

POGO routes stereo audio through a deeply modulated filter chain: a pre-gain stage, a
voltage-controlled VCA, a stereo LP filter with tilt EQ (LP1), three independent 4-pole
bandpass resonators (BP1/BP2/BP3) with per-group distortion, a HP filter, and a final LP
filter (LP2). A dual triangle LFO feeds a central mod bus with 22 CV destinations — every
key parameter is voltage-controllable.

**Signal chain (48HP topology):**

```
Stereo In → Input Buffer → Pre-Gain (1×/5×)
                                  ↓
                             Pre-LP1 VCA   ← mod bus, VCA_OFS floor
                                  ↓
                            LP Filter 1    ← FREQ, TILT (stereo spread), RES
                                  ↓
               ┌──────────────────────────────────────┐
               │       Triple Bandpass SVF (2× OS)    │
               │  BP1: 200Hz  BP2: 1.5kHz  BP3: 6kHz  │
               │  per-group: FREQ / FOCUS / DIST       │
               │  global: OFFSET / TILT / POL / MIX   │
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
Mod Bus      →  22 CV destinations (each: override jack + attenuverter)
```

**Hardware target:** 48HP, ±12V Eurorack. Board architecture under review
(3-board vs 2-board split). Power budget ~190 mA per rail (estimate).

---

## Project State

The plugin and panel are complete and CI-passing. Hardware design documentation is being
reverse-engineered from the working plugin (code-first paradigm).

| Phase | Description | Status |
|---|---|---|
| Phase 1R | Extract functional spec from plugin code (all blocks) | 🔄 In Progress |
| Phase 2R | Analog behavior model (bilinear transform inverse) | ⬜ Not Started |
| Phase 3R | Circuit design (constrained by Phase 2R) | ⬜ Not Started |
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
│   ├── mod-architecture.md        ← 22-destination mod bus spec
│   ├── block-LFO/                 ← Dual triangle LFO
│   ├── block-A-input-buffer/
│   ├── block-1-pregain/
│   ├── block-VCA/
│   ├── block-5-lp1/
│   ├── block-3-triple-bp/         ← Triple bandpass SVF
│   ├── block-4-distortion/
│   ├── block-7-hp/
│   ├── block-6-lp2/
│   ├── block-B-output-buffer/
│   ├── panel-design/panel-notes.md
│   ├── board-layout/layout-notes.md
│   ├── shared/                    ← CV protection, noise audit, power filtering
│   ├── kicad-process.md
│   └── archive/40hp-era-2026-05/  ← Superseded 40HP specs
│
├── kicad/                         ← KiCad schematic generation
│   ├── generate_control_board.py
│   ├── generate_utility_board.py
│   ├── validate_schematic.py
│   └── validate_utility_board.py
│
├── design/
│   └── panel-debug.html           ← Interactive panel layer viewer (keepouts, DRC)
│
└── .github/workflows/build.yml    ← CI: Linux/Win/macOS builds + KiCad + panel DRC
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

EDA files are code-generated — no hand-drawn schematics. CI validates every push.

| Board | Generator | Validator | Status |
|---|---|---|---|
| Control board | `generate_control_board.py` | `validate_schematic.py` (9 checks, 326 pins) | ✅ CI-passing |
| Utility board | `generate_utility_board.py` | `validate_utility_board.py` (7 checks, 477 pins) | ✅ CI-passing |
| Audio board | — | — | ⬜ Not started (awaiting Phase 3R) |

```bash
cd kicad
python3 generate_control_board.py   # writes + validates pogo-control-board.kicad_sch
python3 generate_utility_board.py   # writes pogo-utility-board.kicad_sch
python3 validate_utility_board.py pogo-utility-board.kicad_sch
```

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
- **Phase 3R**: Circuit design (topology, IC selection, component values)

See `CLAUDE.md` for the full development paradigm and workflow.
