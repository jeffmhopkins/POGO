# POGO — Stereo Filter Bank

**POGO** is a stereo filter bank module (48HP) being developed by Space Coast
Synthesizers. The VCV Rack 2 plugin in this repository is the **working software prototype**
and ground truth. Analog hardware design is reverse-engineered from it.

---

## What It Does

POGO routes stereo audio through a deeply modulated filter bank: a pre-gain stage, a
voltage-controlled VCA, a stereo LP filter with tilt (LP1), three independent bandpass
resonators (BP1/BP2/BP3) with per-group distortion, a HP filter, and a final LP filter (LP2).
A dual triangle LFO feeds a central mod bus with 18 attenuverter CV destinations (plus a raw
VCA normal) — every key parameter is voltage-controllable.

**Signal chain (48HP topology):**

```
   IN  (L / R)
    │
    ▼
   Input Buffer
    │
    ▼
   Pre-Gain         ──  1× / 5× switch
    │
    ▼
   Pre-LP1 VCA      ──  mod bus · VCA_OFS floor
    │
    ▼
   LP Filter 1      ──  FREQ · TILT (stereo spread) · RES
    │
    ▼
   Triple Bandpass  ──  BP1 · BP2 · BP3   (each ~50 Hz – 3.2 kHz, F_REF 400 Hz)
    │                   per-group : FREQ · FOCUS (Q) · DIST (drive)
    ├───────────────►   BP3_L / BP3_R out jacks   (pre-mix tap)
    │                   global    : OFFSET · TILT · MIX
    ▼
   HP Filter        ──  FREQ · RES
    │
    ▼
   LP Filter 2      ──  FREQ · RES
    │
    ▼
   Output Buffer
    │
    ▼
   OUT (L / R)

   ── modulation (parallel to the signal path) ──────────────────────────
   LFO1 / LFO2   →   ±5 V triangle, 0.05–20 Hz   (LFO1 normals into the mod bus)
   Mod Bus       →   18 attenuverter destinations (override jack + attenuverter) + VCA raw normal
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

See `specs/STATUS.md` for per-block detail, and `tools/SCHEMATIC-GEN-PLAN.md` for the
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
├── tools/                         ← Build scripts (panel + components + schematic)
│   ├── panel-data.yaml            ← SOURCE OF TRUTH for all panel positions
│   ├── build_panel.py             ← panel CLI: --check/--resource/--design/--cpp/--mfr
│   ├── panel_svg.py · panel_rules.py · panel_cpp.py · panel_editor.py · panel_kicad.py
│   ├── components.py · build_components.py · footprint_svg.py · fetch_datasheets.py  ← components/BOM
│   ├── generate_schematic.py     ← schematic generator (nets → .kicad_sch)
│   ├── symbols.py · kicad_common.py  ← symbol loader/emitter + generic s-expr primitives
│   ├── SCHEMATIC-GEN-PLAN.md      ← schematic rollout plan / gate doc
│   └── panel-tool-guide.md
│
├── docs/                          ← GitHub Pages site + generated viewers
│   ├── plugin-topology.md         ← Authoritative 48HP plugin spec
│   ├── index.html · panel.html · bom.html · ci.html · change-process.html  ← site pages
│   ├── netlist.html               ← Interactive netlist viewer (generated; drift-gated)
│   ├── panel-debug.html           ← Interactive panel layer viewer (generated)
│   └── panel-editor.html          ← Interactive panel layout editor
│
├── specs/                         ← Hardware design documentation
│   ├── STATUS.md                  ← Phase completion checklist
│   ├── module-overview.md         ← Signal chain, power budget
│   ├── components.yaml            ← Per-ref design manifest (700+ rows; block→ref→part)
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
├── components/                    ← Component SOURCING (catalog + footprints + symbols + datasheets)
│   ├── parts/<slug>/              ← Per-part: component.yaml (selects symbol + footprint primitive,
│   │                                MPN, datasheet) + datasheet.pdf
│   ├── footprints/*.pretty        ← Vendored KiCad footprint primitives (resolve as POGO_*)
│   ├── footprints.yaml            ← panel-type → footprint binding
│   ├── symbols/<token>.yaml       ← Authored KiCad symbol primitives (one file per nets `sym:` token)
│   └── README.md
│
├── kicad/                         ← Generated KiCad artifacts (output only; generators in tools/)
│   ├── pogo-block-*.kicad_sch     ← Generated schematics (per block; block-6 split into 7 sections)
│   ├── pogo-bom.csv               ← Manufacturing BOM
│   ├── fp-lib-table               ← Generated; maps POGO_* → components/footprints/
│   └── pogo.kicad_pro             ← KiCad project (placeholder root; real board = Phase 5R)
│
├── changes/                       ← Per-change records (changes/NNNN-<slug>.md) + _TEMPLATE.md
│
└── .github/workflows/build.yml    ← CI: Linux/Win/macOS .vcvplugin builds + 6 --check gates
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
open docs/panel-debug.html
```

---

## KiCad Schematic Generation

Schematics are **data-driven and generated per block**. Each block's netlist source lives
with its spec (`specs/<block>/<block>.nets.yaml`) listing parts and name-based nets;
`tools/generate_schematic.py` emits a byte-stable `kicad/pogo-<block>.kicad_sch`. All 10
blocks (A, B, 1–8) are transcribed and verified; block-6 (triple BP + distortion) is split
into 7 section sheets (`block-6-{svf1,svf2,svf3,dist1,dist2,dist3,mix}`), and the shared
Q-VCAs (U9/U10) are hosted on block-5's sheet (dual-owned by block-5/block-8, no separate
sheet). (Authored netlist in `specs/`, generated schematic in `kicad/` — linked by `--check`,
not by directory adjacency.)

```bash
# Regenerate all block schematics
python3 tools/generate_schematic.py

# CI gate: validate (pin coverage + structural re-parse + short detection + byte drift)
python3 tools/generate_schematic.py --check

# Regenerate one block (block-6 sections are addressed individually)
python3 tools/generate_schematic.py --block block-6-mix
```

Connectivity is by net name, so per-block sheets merge at board level by matching boundary
nets. Symbols/pinouts are authored per-token in `components/symbols/<token>.yaml` and emitted by
`tools/symbols.py` (datasheet-cited; `--check` self-tests them). Vendored footprints
live in `components/footprints/*.pretty` (resolved via the generated `kicad/fp-lib-table`). The
manufacturing BOM (`kicad/pogo-bom.csv`) is generated from `specs/components.yaml` + the
`components/` registry. See `tools/SCHEMATIC-GEN-PLAN.md` for the rollout and per-block notes.

> The 40HP-era board generators and validators have been removed (the data-driven per-block
> generator above supersedes them). A real board-level KiCad project is Phase 5R.

---

## Building the Plugin

### Via GitHub Actions (recommended — no local setup)

Every push to `main`, `dev`, or a `change/**` / `claude/**` branch (and every PR) triggers
Linux x64 + Windows x64 + macOS builds plus the six `--check` gates (`components.py`,
`fetch_datasheets.py`, `build_components.py`, `generate_schematic.py`, `build_panel.py`,
`build_netlist_viz.py`) and the Python↔JS DRC parity test.

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
