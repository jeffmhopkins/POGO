# POGO — Stereo Triple Comb Filter

**POGO** is a complex stereo Eurorack filter module being developed by Space Coast Synthesizers.
This repository contains the complete hardware design specification (Phases 1–5) and the
VCV Rack 2 software prototype (Phase 6, in progress) used to validate the design before
hardware construction begins.

---

## What It Does

POGO routes stereo audio through three independent 6-stage all-pass comb filter chains,
each with its own frequency, feedback depth, and distortion drive control. The output
feeds a resonant LP filter stack (LP1 + LP2), then an HP filter — the full signal chain
is voltage-controlled and deeply modulatable.

**Signal chain:**

```
Stereo In → Input Buffer → Pre-Gain → Envelope Follower
                                              ↓
                          ┌───────────────────────────────┐
                          │   Triple 6-Stage APF Comb     │
                          │   (3 independent groups,       │
                          │    each: Freq / FB / Drive)    │
                          └───────────────────────────────┘
                                              ↓
                                        Distortion
                          (Soft Clip / Hard Clip / Wavefold)
                                              ↓
                                       Pre-LP1 VCA
                                              ↓
                                    LP Filter 1 (resonant)
                                       BAND OUT ──────────► LP1 L/R jacks
                                              ↓
                                    LP Filter 2 (resonant)
                                              ↓
                                       HP Filter
                                              ↓
                                     Output Buffer
                                              ↓
                                       Stereo Out
```

**Modulation system:** The envelope follower drives a central mod bus with independent
attenuverters and override jacks for 19 CV destinations — every key parameter is
voltage-controllable.

**Hardware target:** 40 HP, 3-board split (control + utility + combined audio),
±12 V Eurorack power, ~167 mA per rail.

---

## Project State

All hardware design phases are complete. The VCV Rack software prototype is now being
implemented block by block.

| Phase | Description | Status |
|---|---|---|
| Phase 1 | Audio / functional specification (all blocks) | ✅ Complete |
| Phase 2 | Analog behavior model (all blocks) | ✅ Complete |
| Phase 3 | Circuit design (all blocks) | ✅ Complete |
| Phase 4 | Panel design — 40 HP layout, all controls placed | ✅ Complete |
| Phase 5 | Board layout — 3-board split, connector pinouts | ✅ Complete |
| Phase 6 | VCV Rack 2 plugin — DSP complete, UI/integration refinement | 🔄 In Progress |

### Phase 6 Development Stages

| Stage | Description | Status |
|---|---|---|
| Stage 0 | Scaffold: plugin.json, Makefile, all params/IOs registered, blank panel | ✅ Done |
| Stage 1 | Block A + B: input/output buffers | ✅ Done |
| Stage 2 | Block 1: Pre-gain (switched 1× / 5×) | ✅ Done |
| Stage 3 | Block 2: Envelope follower (0–10 V CV) | ✅ Done |
| Stage 4 | Blocks 5/6/7: LP1, LP2, HP filters (OTA-C SVF, bilinear transform) | ✅ Done |
| Stage 5 | Block VCA: Pre-LP1 VCA (THAT 2180 gain law) | ✅ Done |
| Stage 6 | Block 3: Triple APF comb filter (6-stage per-group all-pass chain) | ✅ Done |
| Stage 7 | Block 4: Distortion (soft clip / hard clip / wavefold, 2× oversampled) | ✅ Done |
| Stage 8 | Mod architecture: mod bus processor + 19 attenuverter destinations | ✅ Done |
| Stage 9 | Full integration and signal-chain verification | 🔄 In Progress |

---

## Repository Structure

```
POGO/
├── specs/                         ← Hardware design documentation (Phases 1–5)
│   ├── STATUS.md                  ← Master phase-completion checklist
│   ├── module-overview.md         ← Full signal chain and power budget
│   ├── mod-architecture.md        ← Modulation system spec
│   ├── kicad-process.md           ← KiCad generation + PCB layout workflow
│   ├── panel-design/              ← Phase 4: 40 HP panel layout
│   │   ├── panel-notes.md
│   │   └── panel.svg              ← Authoritative panel layout SVG (source for PCB placement)
│   ├── board-layout/              ← Phase 5: 3-board split, connector pinouts
│   │   └── layout-notes.md        ← Full CN_CTRL_1/2/3 and STK_AUDIO_L/R pinouts
│   ├── block-*/spec.md            ← Per-block specifications (Phases 1–3)
│   └── shared/
│       ├── cv-input-protection.md ← Standard CV jack → buffer circuit
│       ├── power-filtering.md     ← Standard power decoupling per board
│       └── noise-audit.md         ← IC-level noise & inter-block impedance audit (2026-05-24)
├── kicad/                         ← KiCad 7 schematic generation
│   ├── kicad_common.py            ← Shared generator infrastructure (symbols, pin coords, emitters)
│   ├── generate_control_board.py  ← Control board schematic generator
│   ├── validate_schematic.py      ← Control board validator (9 checks, 326 pin assignments)
│   ├── generate_utility_board.py  ← Utility board schematic generator
│   ├── validate_utility_board.py  ← Utility board validator (7 checks, 477 coord-verified pins)
│   ├── pogo-control-board.kicad_sch  ← Generated artifact
│   ├── pogo-utility-board.kicad_sch  ← Generated artifact
│   └── pogo.kicad_pro             ← KiCad 7 project file
├── design/                        ← HTML design documents (one per block + panel)
├── src/                           ← VCV Rack plugin source (Phase 6)
│   ├── plugin.hpp / plugin.cpp
│   ├── Pogo.cpp                   ← Module definition, params/IOs, panel widget
│   └── dsp/                       ← DSP classes (all blocks implemented)
│       ├── InputBuffer.hpp        ← Block A
│       ├── PreGain.hpp            ← Block 1
│       ├── EnvelopeFollower.hpp   ← Block 2
│       ├── AllPassComb.hpp        ← Block 3
│       ├── Distortion.hpp         ← Block 4
│       ├── VcaBlock.hpp           ← Block VCA
│       ├── LPFilter.hpp           ← Blocks 5 & 6
│       ├── HPFilter.hpp           ← Block 7
│       └── ModBus.hpp             ← Mod architecture
├── res/
│   └── Pogo.svg                   ← Panel SVG for VCV Rack
├── .github/workflows/
│   └── build.yml                  ← CI: Linux/Windows/macOS plugin builds + KiCad validation
├── plugin.json
└── Makefile
```

---

## KiCad Schematic Generation

All EDA files are generated from the specs — no hand-drawn schematics. Each board has a
Python generator script in `kicad/` that emits a valid KiCad 7 `.kicad_sch` file; the script
is the authoritative source and the `.kicad_sch` is the artifact.

### Board order

| Board | Generator | Status | Notes |
|---|---|---|---|
| Control board | `generate_control_board.py` | ✅ Complete | Jacks, pots, switches, IDC connectors |
| Utility board | `generate_utility_board.py` | ✅ Complete | Mod bus, attenuverters, THAT340 expo converters |
| Combined audio board | `generate_audio_combined.py` | ⬜ Next | All analog ICs — L-channel left half, R-channel right half, 4 mm center GND strip |

### Running the control board generator

```bash
cd kicad
python3 generate_control_board.py
# → writes pogo-control-board.kicad_sch
# → automatically runs validate_schematic.py and prints a pass/fail report
```

The generated schematic contains **78 components** — 28 jacks, 43 pots/sliders, 4 switches,
and 3 IDC connectors (CN1 34-pin, CN2 40-pin, CN3 24-pin) — connected entirely via global
net labels (no drawn wires). Three nets are intentionally single-occurrence:
`SPARE_CN2_28`, `SPARE_CN2_40`, `SPARE_CN3_24`.

### Validating a schematic

`validate_schematic.py` parses the generated `.kicad_sch` using
[kiutils](https://github.com/mvnmgrx/kiutils) and runs nine checks, verifying 326 individual
pin assignments:

| Check | What it catches |
|---|---|
| Component counts | Wrong number of J / RV / SW / CN components |
| Duplicate refs | Two symbols claiming the same reference designator |
| Floating nets | Single-occurrence global labels (unexpected unconnected nets) |
| Required nets | Missing signal, wiper, CV, switch, or power nets by name |
| MODBUS_NORM count | Must appear exactly 20× (19 SW lugs + 1 CN2 pin) |
| Jack pin assignments | Tip / sleeve / SW-lug net per J1–J28 |
| Pot pin assignments | CCW / wiper / CW net per RV1–RV43 |
| Switch pin assignments | All throws and common per SW1–SW4 |
| Connector pinouts (CN1/2/3) | All 34+40+24 = 98 connector pins vs. layout-notes.md §5 |

```bash
# Run standalone (requires: pip3 install kiutils)
cd kicad
python3 validate_schematic.py
# or against any schematic:
python3 validate_schematic.py path/to/other.kicad_sch
```

The validator exits 0 on pass, 1 on any error — suitable for CI. The generator calls it
automatically, so a broken generator change fails immediately.

**What this does not cover:** ERC pin-type conflicts, short circuits between power rails, and
missing power pin connections on ICs. For those, open the schematic in KiCad 7 and run
`Tools → Electrical Rules Checker`. Expected ERC output: three "pin unconnected" warnings
for the intentional spare pins — nothing else.

### Validating the utility board

`validate_utility_board.py` uses a different approach from the control board validator: it
monkey-patches `generate_utility_board.build_schematic()` to capture every expected
`(component, net, x, y)` tuple from the generator itself, then verifies each one exists at
that exact coordinate in the generated `.kicad_sch`. This catches pin swaps, wrong nets, and
connector mis-wiring — not just net occurrence counts.

```bash
cd kicad
python3 generate_utility_board.py   # → writes pogo-utility-board.kicad_sch
python3 validate_utility_board.py pogo-utility-board.kicad_sch
```

Coverage: **477 pin assignments** across 28 components (CN6/CN1/CN2/CN3, STK_L/STK_R, U1–U22).

### Shared infrastructure (`kicad_common.py`)

`kicad_common.py` is imported by every board generator. It provides:

- **`begin_schematic()` / `end_schematic()` / `write_schematic()`** — file skeleton and output
- **`sym_power()` / `sym_idc()` / `sym_rpot()` / `sym_r()` / `sym_c()`** — passive lib symbols
- **`sym_tl072()` / `sym_lm4562()` / `sym_ne5532()` / `sym_tl074()`** — op-amp lib symbols
- **`sym_lm13700()` / `sym_that340()` / `sym_that2180()` / `sym_cd4053()`** — IC lib symbols
- **`*_pins(ox, oy)`** — pin coordinate helpers for every component type
- **`place_symbol()` / `connect_pin()` / `power_sym()` / `global_label()`** — emitters
- **`place_idc34/40/24/16()`** — IDC connector placement with net map

### Connector architecture

```
Control board ──CN1 (34-pin)──► Utility board   power rails + audio I/O + 19 CV jack tips
              ──CN2 (40-pin)──►                  attenuverter wipers + switch outputs
              ──CN3 (24-pin)──►                  main parameter wipers (FREQ/FB/DRIVE/filter Qs)
```

Key design decisions captured in the schematic:

- **`NET_MODBUS_NORM`**: All 19 CV override jack switch lugs are wired together on the
  control board PCB to a single net. The utility board drives this net (post-AMOUNT/OFFSET
  mod bus output) via CN2 pin 39 — one connector pin instead of 19.
- **`NET_ENV_NORM`**: MOD IN jack SW lug is driven by the utility board's selected ENV output
  (CN2 pin 38) so the mod source normalizes to the envelope when no cable is plugged.
- **Switch commons**: SP3T and SPDT switch commons tie directly to +12V power symbols on the
  control board (no connector pin). Only position outputs and the GAIN common go to CN2.

### PCB Layout

PCB layout uses KiCad natively with a hybrid routing strategy: critical paths (power rails,
I_abc signal traces) are hand-routed; remaining traces are auto-routed. Component placement
is generated by `kicad/generate_control_pcb.py` from positions in `kicad/layouts/` which
are derived from `specs/panel-design/panel.svg`.

See `specs/kicad-process.md` for the full generation methodology, ERC validation steps,
and the PCB layout workflow.

---

## Building

### Via GitHub Actions (no local setup required)

Every push to `main`, `dev`, or any `claude/**` branch triggers an automatic build. The workflow
downloads the Rack 2.6 SDK from `vcvrack.com` and compiles the plugin on an Ubuntu runner —
no local SDK installation or Docker setup is needed.

**To get a build artifact:**

1. Go to the **Actions** tab in this repository
2. Click the latest **Build VCV Rack Plugin** run
3. Scroll to **Artifacts** at the bottom
4. Download `POGO-linux-x64-<run_number>`

**To install the downloaded plugin:**

```bash
# Unzip the artifact into your Rack plugins folder
unzip POGO-linux-x64-*.zip -d ~/.rack2/plugins/
# Launch VCV Rack — POGO will appear in the module browser
```

**To trigger a build manually** (without pushing code):

1. Go to **Actions → Build VCV Rack Plugin**
2. Click **Run workflow** → **Run workflow**

### Locally (requires Rack SDK)

```bash
# 1. Download the Rack SDK from https://vcvrack.com/downloads
#    and extract it (e.g. to ~/Rack-SDK)

# 2. Build the plugin
export RACK_DIR=~/Rack-SDK
make -j$(nproc) dist

# 3. Install for development testing
ln -s $(pwd) ~/.rack2/plugins/POGO

# 4. Launch Rack in dev mode (loads plugins from the plugins folder)
Rack -d
```

---

## Design Documentation

Full hardware specifications live in `specs/`. Each block has a `spec.md` covering:
- **Phase 1**: Sonic intent, parameter ranges, CV targets, signal levels
- **Phase 2**: Transfer functions, analog behavior model, bilinear transform notes
- **Phase 3**: Circuit topology, component values, IC selection, trim pots

HTML design documents in `design/` synthesize each block's three phases into a single
readable page with block diagrams, schematics, parts lists, and design notes.

Key design decisions documented:
- OTA-C state-variable filter (LM13700) with correct Q = 2V_T / (Iabc × R_in) formula
  and inverted Iabc driver (more RESONANCE → less Iabc → higher Q → self-oscillation)
- All-pass comb filter capacitor values: 33 nF / 6.8 nF / 1.5 nF (Groups 1/2/3)
- Modulation bus: 19 destinations, each with override jack and bipolar attenuverter
- 3-board hardware split: control + utility + combined audio (L-channel left half, R-channel right half)

---

## Hardware Notes

POGO is designed for hardware construction after the VCV Rack prototype validates the DSP.
Circuit specs:
- **ICs**: LM13700 OTA (15 per channel), THAT 2180 VCA, THAT340 expo converters, LM4562 (Block A), NE5532 (Block 1), TL072/TL074 op-amps
- **Power**: ±12 V Eurorack, ~167 mA per rail
- **Format**: 40 HP, 3U, 3-PCB split
- **CV protection**: 100 Ω series + BAT54S clamp on every input jack (see `specs/shared/cv-input-protection.md`)
