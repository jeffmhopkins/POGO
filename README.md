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

**Hardware target:** 40 HP, 4-board split (control + utility + left audio + right audio),
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
| Phase 5 | Board layout — 4-board split, connector pinouts | ✅ Complete |
| Phase 6 | VCV Rack 2 plugin — **Stage 0 scaffold done; DSP next** | 🔄 In Progress |

### Phase 6 Development Stages

| Stage | Description | Status |
|---|---|---|
| Stage 0 | Scaffold: plugin.json, Makefile, all params/IOs registered, blank panel | ✅ Done |
| Stage 1 | Block A + B: input/output buffers, clean pass-through test | ⬜ Next |
| Stage 2 | Block 1: Pre-gain (switched 1× / 5×) | ⬜ |
| Stage 3 | Block 2: Envelope follower (0–10 V CV) | ⬜ |
| Stage 4 | Blocks 5/6/7: LP1, LP2, HP filters (OTA-C SVF, bilinear transform) | ⬜ |
| Stage 5 | Block VCA: Pre-LP1 VCA (THAT 2180 gain law) | ⬜ |
| Stage 6 | Block 3: Triple APF comb filter (6-stage per-group all-pass chain) | ⬜ |
| Stage 7 | Block 4: Distortion (soft clip / hard clip / wavefold, 2× oversampled) | ⬜ |
| Stage 8 | Mod architecture: mod bus processor + 19 attenuverter destinations | ⬜ |
| Stage 9 | Full integration and signal-chain verification | ⬜ |

---

## Repository Structure

```
POGO/
├── specs/                    ← Hardware design documentation (Phases 1–5)
│   ├── STATUS.md             ← Master phase-completion checklist
│   ├── module-overview.md    ← Full signal chain and power budget
│   ├── mod-architecture.md   ← Modulation system spec
│   ├── panel-design/         ← Phase 4: 40 HP panel layout
│   ├── board-layout/         ← Phase 5: 4-board split, connector pinouts
│   ├── block-*/spec.md       ← Per-block specifications (Phases 1–3)
│   └── shared/               ← Reusable circuit standards (CV protection, power)
├── design/                   ← HTML design documents (one per block)
├── src/                      ← VCV Rack plugin source (Phase 6)
│   ├── plugin.hpp / plugin.cpp
│   ├── Pogo.cpp              ← Module definition, all params/IOs, widget
│   └── dsp/                  ← DSP classes (one per block, added per stage)
├── res/
│   └── Pogo.svg              ← Panel SVG for VCV Rack
├── .github/workflows/
│   └── build.yml             ← GitHub Actions CI build
├── plugin.json
└── Makefile
```

---

## Building

### Via GitHub Actions (no local setup required)

Every push to `main` or any `claude/**` branch triggers an automatic build. The workflow
downloads the latest stable Rack 2 SDK from GitHub Releases and compiles the plugin on an
Ubuntu runner — no local SDK installation or Docker setup is needed.

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
- 4-board hardware split: control + utility + left audio + right audio

---

## Hardware Notes

POGO is designed for hardware construction after the VCV Rack prototype validates the DSP.
Circuit specs:
- **ICs**: LM13700 OTA (15 per audio board), THAT 2180 VCA, THAT340 expo converters, TL072/TL074 op-amps
- **Power**: ±12 V Eurorack, ~167 mA per rail
- **Format**: 40 HP, 3U, 4-PCB split
- **CV protection**: 100 Ω series + BAT54S clamp on every input jack (see `specs/shared/cv-input-protection.md`)
