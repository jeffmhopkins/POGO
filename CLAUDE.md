# POGO — Complex Stereo Eurorack Filter Module

## Project Purpose

POGO is a complex stereo Eurorack filter module with an extensive modulation architecture. The
VCV Rack 2 plugin in this repository is a software prototype used to validate audio design,
analog behavior, and circuit design decisions **before** hardware construction begins.

### Full Signal Chain

```
Stereo Input (L + R)
  ↓
[Block A]  Input Buffers + Protection       100Ω series, clamp diodes, unity-gain buffers
  ↓
[Block 1]  Pre-Gain Boost Switch            unity → 5× (~0–14 dB), switched gain stages
  ↓
[Block 2]  Envelope Follower                post-gain / pre-comb audio → envelope signal
           Envelope output jack             also normalizes into Mod Bus input
  ↓
[Block 3]  Triple 6-Stage All-Pass          stereo, 3 independent APF chains (phaser / comb)
           Comb Filter
  ↓
[Block 4]  Distortion                       3 selectable modes
  ↓
[Block 5]  LP Filter 1                      resonant, voltage-controlled
  ↓
[Block 6]  LP Filter 2                      resonant, voltage-controlled, different topology
  ↓
[Block 7]  HP Filter                        voltage-controlled
  ↓
[Block B]  Output Buffers                   low-impedance ~1kΩ outputs, DC-coupled
Stereo Output (L + R)

─────────────────────────────────────────────────────────────────────────────────────────
MODULATION SYSTEM (runs in parallel, feeds all blocks above)
─────────────────────────────────────────────────────────────────────────────────────────
Primary Mod Source Jack  (normalizes to Envelope Follower output when unplugged)
  ↓
Mod Bus Processor:
  AMOUNT knob  0.2× – 5×  (scales the mod signal)
  OFFSET knob  ±5 V        (DC offset added after scaling)
  ↓
Mod Bus Signal  (internal bus; also available as MOD BUS OUT jack for external patching)
  ↓
Each modulation destination receives:
  Mod Bus (normalled)  →  Individual Override Jack  →  Attenuverter knob  →  parameter CV input
```

---

## The Design-First Rule

**No plugin code, no DSP code, and no C++ is written until all six phases are complete.**
Per-block phases (1–3) gate per-block work. Module-level phases (4–5) gate all code.

The workflow is a strict gate:

```
Phase 1        Phase 2           Phase 3            Phase 4         Phase 5           Phase 6
Audio Spec  ──► Analog Behavior ──► Circuit Design ──► Panel Design ──► Board Layout ──► VCV Rack Code
                                     (per block)        (module)        (module)          (per block)
```

Going backward to refine earlier phases is expected. No Phase 6 code begins until Phases 1–3
are complete for every block AND Phase 4 (panel) and Phase 5 (layout) are complete.

Check `specs/STATUS.md` to see which blocks are ready and whether module-level phases are cleared.

---

## Repository Structure

```
POGO/
├── CLAUDE.md
├── specs/                        ← Complete this FIRST, before any src/ files
│   ├── STATUS.md                 ← Master phase-completion checklist (the gate document)
│   ├── module-overview.md        ← Full signal chain, panel layout, power budget
│   ├── mod-architecture.md       ← Modulation system spec (all phases 1–3)
│   ├── panel-design/             ← Phase 4 deliverables (module-level)
│   │   ├── panel-notes.md        ← HP width, control placement, board split decision, labels
│   │   └── panel.svg             ← Panel layout SVG (source for VCV Rack + manufacturing)
│   ├── board-layout/             ← Phase 5 deliverables (module-level)
│   │   └── layout-notes.md       ← Board split, ground strategy, placement rules, connector pinout
│   ├── block-A-input-buffer/
│   │   ├── spec.md               ← Phase 1–3 documentation
│   │   └── schematic.svg         ← Circuit schematic
│   ├── block-1-pregain/
│   │   ├── spec.md
│   │   └── schematic.svg
│   ├── block-2-envelope-follower/
│   │   ├── spec.md
│   │   └── schematic.svg
│   ├── block-3-apcf/
│   │   ├── spec.md
│   │   └── schematic.svg
│   ├── block-4-distortion/
│   │   ├── spec.md
│   │   └── schematic.svg
│   ├── block-5-lp1/
│   │   ├── spec.md
│   │   └── schematic.svg
│   ├── block-6-lp2/
│   │   ├── spec.md
│   │   └── schematic.svg
│   ├── block-7-hp/
│   │   ├── spec.md
│   │   └── schematic.svg
│   ├── block-B-output-buffer/
│   │   ├── spec.md
│   │   └── schematic.svg
│   └── shared/
│       ├── cv-input-protection.md    ← Standard CV jack → buffer circuit (reused by all blocks)
│       ├── power-filtering.md        ← Standard power decoupling (applied per board)
│       └── parts-master-list.md      ← Consolidated BOM across all blocks
├── design/                       ← HTML design documents (one per block; created after specs/)
│   ├── index.html
│   ├── block-A-input-buffer.html
│   ├── block-1-pregain.html
│   ├── block-2-envelope-follower.html
│   ├── block-3-apcf.html
│   ├── block-4-distortion.html
│   ├── block-5-lp1.html
│   ├── block-6-lp2.html
│   ├── block-7-hp.html
│   ├── block-B-output-buffer.html
│   └── mod-architecture.html
├── plugin.json                   ← slug: "POGO", version: "2.x.x"
├── Makefile                      ← include $(RACK_DIR)/plugin.mk
├── src/                          ← Only created after specs/ is complete for a block
│   ├── plugin.hpp
│   ├── plugin.cpp
│   ├── Pogo.cpp
│   └── dsp/
│       ├── InputBuffer.hpp       ← Block A
│       ├── PreGain.hpp           ← Block 1
│       ├── EnvelopeFollower.hpp  ← Block 2
│       ├── AllPassComb.hpp       ← Block 3
│       ├── Distortion.hpp        ← Block 4
│       ├── LPFilter.hpp          ← Blocks 5 & 6
│       ├── HPFilter.hpp          ← Block 7
│       └── ModBus.hpp            ← Modulation architecture
└── res/
    └── Pogo.svg
```

---

## Phase 1: Audio / Functional Specification

Complete **all** of the following for a block before starting Phase 2. Record answers in
`specs/block-N-name/spec.md`.

### Sonic intent
- What does this block do perceptually? What is its musical purpose?
- What reference hardware or classic circuit behavior inspired this block?
- What are the "sweet spots" a musician would reach for?
- What does it sound like at minimum, maximum, and mid settings?

### Parameter specification
For every user-facing control, document:
- Name, unit, range (min / max / default), taper (linear / exponential / log)
- Plain-English description of what turning it does
- What happens at the absolute limit in each direction?
- Musical interactions between parameters

### CV modulation targets
- Which parameters are CV-controllable?
- CV range: unipolar (0–10 V) or bipolar (±5 V)?
- Does each CV input have a front-panel attenuverter?
- Full modulation swing (e.g., "CV sweeps cutoff from 20 Hz to 20 kHz")

### Signal levels at I/O
- Expected input amplitude from the previous stage
- Expected output amplitude into the next stage
- What happens when a hot signal overdrives this stage?

### Stereo behavior
- True stereo (independent L/R signal paths) or dual-mono?
- Parameters linked or independent per channel?
- Does this block intentionally create or widen stereo?

---

## Phase 2: Analog Behavior Modeling

Model the *ideal* analog behavior before choosing any circuit. Record in `specs/block-N-name/spec.md`.

### Transfer function
- Write the s-domain (Laplace) transfer function for linear blocks.
  Example — first-order all-pass stage: `H(s) = (s − ω₀) / (s + ω₀)`
- For nonlinear blocks, describe the input–output curve mathematically:
  - Soft clip: `y = tanh(drive · x) / tanh(drive)`
  - Hard clip: `y = clamp(x, −V_th, +V_th)`
  - Wavefold: `y = fold(x, fold_threshold)`

### Frequency response
- Filter slope in dB/octave, passband ripple, stopband attenuation
- For APF/comb: number, depth, and approximate placement of notches across the audio band
- Describe the Bode diagram (magnitude AND phase response)

### Dynamic / time-domain behavior
- Response time to parameter changes (risk of zipper noise?)
- Self-oscillation ring-out time for resonant filters
- Envelope follower attack / release time constants

### Parameter-to-behavior mapping
- Exact mathematical relationship from each parameter to the transfer function
- 1V/oct exponential: `ω₀ = ω_ref × 2^(V/1V)` where ω_ref is the reference frequency at 0 V
- Resonance to Q factor; Q → ∞ at the self-oscillation boundary

### Nonlinearity and saturation
- At what signal amplitude does saturation become audible?
- Symmetrical or asymmetrical clipping? (asymmetric → even harmonics; symmetric → odd)

### Analog imperfections to model (optional but desirable)
- Component tolerance effects on center frequency / gain
- Thermal drift on expo converter
- Noise floor / SNR target for this stage

---

## Phase 3: Analog Circuit Design

Only enter after Phase 2 is complete. Record in `specs/block-N-name/spec.md` and
`specs/block-N-name/schematic.svg`.

### Topology selection
Name the topology and explain why it was chosen over alternatives:
- Sallen-Key: simple, low noise, easy to design
- State-variable filter (SVF): multimode LP/BP/HP outputs, inherently stable
- OTA-based ladder: voltage-controlled cutoff, self-oscillation (AS3320 / V2164)
- Buchla wavefolder: cascaded op-amp fold stages for complex harmonics

### Component philosophy
- **SMD preferred** throughout; through-hole only where mechanical reliability demands it
- **Passives:** 0603 (best balance of density and hand-solderability)
- **Op-amps (SOIC-8/14):** TL072 (general purpose), LM4562 (low noise), NE5532 (audio)
- **OTAs (SOIC-16):** LM13700 (general), AS3320 (dedicated filter IC with resonance), V2164 (quad, low noise)
- **Analog switches (SOIC-14/16):** CD4066, DG408 for CV-selected gain or routing
- **Protection diodes (SOT-23):** BAT54 dual Schottky for rail clamping at all inputs

### Trim pot recommendations
Identify trim pots for every block:

| Purpose | Typical Range | Recommended Part |
|---|---|---|
| Frequency / cutoff calibration | ±20% of nominal R | Bourns 3296W (multiturn, TH) |
| Expo converter offset null | ±100 mV | Bourns 3296W |
| L/R gain match | ±2 dB | Bourns 3224W (SMD) |
| CV input scaling | ×0.8 – ×1.2 | Bourns 3224W |
| Distortion threshold | ±2 V | Bourns 3296W |
| Envelope follower output level | 0–10 V range | Bourns 3296W |
| Mod bus zero-offset null | ±500 mV | Bourns 3224W |

### IC / component selection
List specific part numbers and justify each (GBW, noise floor, slew rate, rail requirements).

### Component value derivations
Show R and C calculations from the Phase 2 transfer function.
Example: for ω₀ = 2π × 1000 Hz with C = 10 nF → R = 1/(ω₀ × C) = 15.9 kΩ → use 15.8 kΩ (E96)
or adjust via trim pot.

### Power draw estimate for this block
- +12 V: ___ mA
- −12 V: ___ mA
(Running total goes in `specs/module-overview.md` power budget table)

### Schematic requirements
Every `schematic.svg` must show:
- All IC pin numbers; supply pins with decoupling caps placed at each pin
- Signal levels annotated at key nodes
- All front-panel controls: jacks (with normalling), pots, switches, and their circuit effect
- All trim pots: reference designator, value, and adjustment note
- CV input path: `jack → 100Ω series → BAT54 clamp to ±12 V → attenuverter → summing node`
- All feedback paths clearly labeled
- Both L and R signal paths (or label if shared)

### Known circuit challenges
Document: temperature sensitivity of expo converter, ground loops in stereo path, HF oscillation
risk in high-gain stages, crosstalk between L/R in shared IC packages.

---

## HTML Design Document Per Block (`design/`)

After `specs/block-N-name/spec.md` is complete, create the corresponding `design/block-N-name.html`.
Each HTML file must contain four sections:

1. **Block Diagram** — inline SVG or ASCII showing signal flow with voltage levels at I/O
2. **Schematic** — inline SVG or `<img>` linking to `../specs/block-N-name/schematic.svg`;
   must include all ICs, passives, jacks, knobs, trim pots, power pins, and protection circuits
3. **Parts List** — HTML table: Reference | Part Number | Package | Value | Qty | Notes
4. **Design Notes** — Phases 1–3 summary inline: sonic intent, transfer function, topology
   rationale, trim pot adjustment procedures, known issues

---

## `specs/STATUS.md` — The Gate Document

This is the single source of truth. No Phase 6 (code) work begins until:
- All per-block rows show ✅ for Phases 1–3, **and**
- The module-level Phase 4 (Panel) and Phase 5 (Layout) checkboxes are ✅.

Template:

```markdown
# POGO Design Status

## Per-Block Phases (1–3)

| Block                        | Phase 1: Audio Spec | Phase 2: Analog Model | Phase 3: Circuit | Phase 6: Code |
|------------------------------|---------------------|-----------------------|------------------|---------------|
| Mod Architecture             | [ ]                 | [ ]                   | [ ]              | [ ]           |
| Block A: Input Buffer        | [ ]                 | [ ]                   | [ ]              | [ ]           |
| Block 1: Pre-Gain            | [ ]                 | [ ]                   | [ ]              | [ ]           |
| Block 2: Envelope Follower   | [ ]                 | [ ]                   | [ ]              | [ ]           |
| Block 3: Triple APF Comb     | [ ]                 | [ ]                   | [ ]              | [ ]           |
| Block 4: Distortion          | [ ]                 | [ ]                   | [ ]              | [ ]           |
| Block 5: LP Filter 1         | [ ]                 | [ ]                   | [ ]              | [ ]           |
| Block 6: LP Filter 2         | [ ]                 | [ ]                   | [ ]              | [ ]           |
| Block 7: HP Filter           | [ ]                 | [ ]                   | [ ]              | [ ]           |
| Block B: Output Buffer       | [ ]                 | [ ]                   | [ ]              | [ ]           |

## Module-Level Phases (gate for all Phase 6 code)

- [ ] **Phase 4: Panel Design** — HP width finalized, all controls placed, sub-panel
      board decision made, silk-screen layout approved
      → `specs/panel-design/panel-notes.md` + `specs/panel-design/panel.svg`
- [ ] **Phase 5: Board Layout** — board split strategy decided, ground plane approach
      defined, component placement rules documented, connector strategy finalized
      → `specs/board-layout/layout-notes.md`

Last updated: YYYY-MM-DD
```

---

## `specs/block-N-name/spec.md` — Template

```markdown
# Block N: [Name]

## Status
- Phase 1 (Audio Spec): [ ] complete
- Phase 2 (Analog Model): [ ] complete
- Phase 3 (Circuit Design): [ ] complete

---

## Phase 1: Audio / Functional Specification

### Sonic Intent
...

### Parameters
| Name | Range | Default | Taper | Description |
|------|-------|---------|-------|-------------|

### CV Modulation Targets
...

### Signal Levels (I/O)
...

### Stereo Behavior
...

### Edge Cases
...

---

## Phase 2: Analog Behavior Model

### Transfer Function
...

### Frequency Response
...

### Nonlinearity / Saturation Model
...

### Parameter-to-Behavior Mapping
...

### Analog Imperfections to Model
...

---

## Phase 3: Circuit Design

### Topology and Rationale
...

### IC / Component Selection
| Reference | Part Number | Package | Value | Qty | Notes |
|-----------|-------------|---------|-------|-----|-------|

### Component Value Derivations
...

### Trim Pots
| Reference | Range | Purpose | Adjustment Procedure |
|-----------|-------|---------|----------------------|

### Power Draw Estimate
- +12 V: ___ mA
- −12 V: ___ mA

### Schematic Notes (see schematic.svg)
...

### Known Circuit Challenges
...
```

---

## Modulation Architecture

### Envelope Follower (Block 2)

Source: post-gain / pre-comb audio — **two independent followers, one per channel**

**Audio spec:**
- Converts audio amplitude to a 0–10 V CV signal
- ATTACK: 0.1 ms – 200 ms (shared knob for L and R)
- RELEASE: 5 ms – 2 s (shared knob for L and R)
- ENV OUT L jack: buffered left-channel envelope (0–10 V)
- ENV OUT R jack: buffered right-channel envelope (0–10 V)
- MOD SOURCE SEL switch (3-position): selects which envelope normalizes into the mod bus
  - L = ENV OUT L only
  - max(L,R) = diode-OR (BAT54) of both envelopes, buffered — tracks the louder channel at any moment
  - avg(L,R) = (ENV_L + ENV_R) / 2 via equal resistor divider into unity-gain buffer

**Analog behavior:**
- Full-wave precision rectifier → RC peak detector (separate attack/release diode paths)
- τ_attack = ATTACK knob value; τ_release = RELEASE knob value
- Output amplifier scales rectified peak to 0–10 V

**Circuit:**
- Full-wave precision rectifier: TL074 + 1N4148WS diodes (one TL074 per channel)
- Attack RC via charge diode; release RC via discharge diode (independent time constants)
- Trim pots: ENV SCALE L and ENV SCALE R (0 V = silence, 10 V = full-scale ±5 V Eurorack audio)

### Mod Bus Processor

- PRIMARY MOD SOURCE jack normalizes to the ENV selected by MOD SOURCE SEL when unplugged
- AMOUNT knob: 0.2× – 5× gain
- OFFSET knob: ±5 V added after scaling
- MOD BUS OUT jack: buffered output available for external patching
- Circuit: inverting summer op-amp (scaled mod signal + offset pot) + inverter + output buffer
- Trim pot: zero-offset null (output = 0 V when AMOUNT = center and input = 0 V)

### Per-Destination Modulation Circuit

```
MOD BUS  →  100Ω + BAT54 clamp  →  ATTENUVERTER (−1× to +1×)  →  parameter CV summing node
                                          ↑
                         OVERRIDE JACK ───┘  (tip-switching; disconnects mod bus when patched)
```

### Modulation Destinations

| Destination | Block | CV Range | Notes |
|---|---|---|---|
| Pre-Gain level | 1 | 0–10 V → 1×–5× | electronic gain switching |
| APF Chain 1 Freq | 3 | ±5 V, 1V/oct | |
| APF Chain 2 Freq | 3 | ±5 V, 1V/oct | |
| APF Chain 3 Freq | 3 | ±5 V, 1V/oct | |
| APF Feedback 1 | 3 | 0–10 V | Group 1 independent |
| APF Feedback 2 | 3 | 0–10 V | Group 2 independent |
| APF Feedback 3 | 3 | 0–10 V | Group 3 independent |
| APF Blend | 3 | 0–10 V | feedback source crossfade; active when SOURCE = Blend |
| APF Dry/Wet | 3 | 0–10 V | |
| Distortion Drive 1 | 4 | 0–10 V | Group 1 chain |
| Distortion Drive 2 | 4 | 0–10 V | Group 2 chain |
| Distortion Drive 3 | 4 | 0–10 V | Group 3 chain |
| LP1 Cutoff | 5 | ±5 V, 1V/oct | |
| LP1 Resonance | 5 | 0–10 V | 10 V = self-oscillation |
| LP2 Cutoff | 6 | ±5 V, 1V/oct | |
| LP2 Resonance | 6 | 0–10 V | |
| HP Cutoff | 7 | ±5 V, 1V/oct | |
| HP Resonance | 7 | 0–10 V | |

---

## Eurorack / Doepfer Hardware Requirements

### Power Connector

Standard Eurorack 16-pin IDC (Doepfer A-100 compatible):
- **Red stripe = pin 1 = −12 V.** Orient red stripe toward the −12 V label on the bus board.
- Pins 1–2: −12 V | Pins 3–10: GND | Pins 11–12: +5 V (unreliable — regulate on-module if needed) | Pins 13–16: +12 V
- Verify against the Doepfer A-100 construction details (doepfer.de) and your busboard before PCB layout.
- 10-pin shrouded header is also acceptable for this module (omits +5 V and CV/Gate bus pins).

### Power Filtering (required on every PCB)

- **100 nF ceramic cap** on each rail at every IC supply pin (not just at the header)
- **10 µF (or 47 µF) electrolytic** on each rail at the power header
- **Ferrite bead** (600 Ω at 100 MHz, e.g., Murata BLM18AG601SN1D, 0603) in series on each rail between the bus connector and the board for HF noise isolation

### Reverse Polarity Protection (required)

- Preferred: series Schottky diode (BAT85, SOD-80) on each rail — ~0.3 V drop
- Alternative: polyfuse + diode
- Add a red power-indicator LED (with current-limiting resistor) across the +12 V rail

### Power Budget

| Block | +12 V est. | −12 V est. |
|---|---|---|
| Block A: Input buffers | 5 mA | 5 mA |
| Block 1: Pre-Gain | 5 mA | 5 mA |
| Block 2: Envelope Follower | 10 mA | 10 mA |
| Block 3: Triple APF Comb | 25 mA | 25 mA |
| Block 4: Distortion | 15 mA | 15 mA |
| Block 5: LP Filter 1 | 15 mA | 15 mA |
| Block 6: LP Filter 2 | 15 mA | 15 mA |
| Block 7: HP Filter | 10 mA | 10 mA |
| Mod Bus Processor | 10 mA | 10 mA |
| Per-destination mod (×14) | 30 mA | 30 mA |
| Block B: Output buffers | 5 mA | 5 mA |
| **Total estimate** | **~145 mA** | **~145 mA** |

Measure actual draw during bring-up and update `specs/module-overview.md`.

### Input and Output Buffering

**Every jack input (audio and CV):**
```
Jack tip  →  100 Ω series  →  BAT54 dual Schottky (SOT-23) clamp to ±12 V  →  unity-gain buffer op-amp  →  internal node
```
- 100 Ω limits short-circuit current and protects source modules
- BAT54 clamps incoming signal to ±12 V rails
- Unity-gain non-inverting buffer (half of TL072 or TL071): input impedance ~1 MΩ

**Every jack output (audio and CV):**
```
Internal signal  →  1 kΩ series  →  Jack tip
```
- 1 kΩ limits cable-load current and prevents oscillation into capacitive loads
- Do not put capacitors in series on audio outputs

**Normalling:**
- Use tip-switching TS jack sockets (Thonkiconn PJ301M-12 or equivalent)
- Normalled source connects to the sleeve switching lug; disconnects when cable is inserted

### Mechanical Specifications

| Parameter | Value |
|---|---|
| Panel height (usable) | 128.5 mm (3U) |
| 1 HP | 5.08 mm |
| POGO estimated width | 28–34 HP (finalized in panel design phase) |
| Mounting hole size | M3 |
| Mounting hole centers | 5.1 mm from top and bottom edges |
| Max PCB depth from panel face | 35 mm (Doepfer A-100); up to 60 mm in deep cabinets |
| Preferred SMD passive size | 0603 |
| Preferred IC packages | SOIC-8 (dual op-amp), SOIC-14 (quad op-amp), SOT-23 (discrete) |

---

## Phase 4: Panel Design

Complete once — at the module level — after all per-block Phase 3 work is done for at least
the majority of blocks, so control counts and positions are stable.

Deliverables: `specs/panel-design/panel-notes.md` and `specs/panel-design/panel.svg`.

### HP Width and Control Placement

- Finalize the HP count (estimated 28–34 HP; 1 HP = 5.08 mm).
- Lay out all front-panel elements: audio jacks, CV jacks, knobs, switches, LEDs.
- Eurorack spacing rules:
  - Jacks: minimum 8 mm center-to-center (Thonkiconn body = 8 mm wide, needs ≥ 1 mm gap).
  - Pots: 9 mm PCB-mount body needs ≥ 11 mm center-to-center in a row.
  - Switches: sub-mini toggle needs ≥ 8 mm center-to-center.
  - Mounting holes: M3, 5.1 mm from top and bottom panel edges, centered in adjacent HP columns.
- Group controls logically by block — a musician should be able to read the panel top-to-bottom
  and recognize the signal flow.
- Reserve space for silk-screen labels: every jack and knob needs a label; budget ~4 mm height
  per label line above or below the control.
- Document each control's panel position as (HP column, mm from top) in `panel-notes.md`.

### Sub-Panel / Multi-Board Decision

At POGO's complexity (28–34 HP, ~30 panel controls), a two-PCB approach is strongly preferred:

**Control board (panel-mounted PCB):**
- Mounts directly behind the panel using jack nuts and pot hardware.
- Carries: all Thonkiconn jacks, all pots, all switches, all panel LEDs.
- Thin board (1.0 mm or 1.2 mm) to minimize stack depth.
- Connects to the audio board(s) via a right-angle 2.54 mm pin header or ribbon cable.

**Audio board(s):**
- Hangs behind the control board on standoffs.
- Carries all ICs, passive components, CV processing, filter circuits.
- No panel hardware — all through-hole items are on the control board.

Single-board alternative (all components on one PCB):
- Simpler assembly and fewer connectors, but the board must reach all panel controls.
- Works for simpler modules (< 16 HP, < 12 controls); not recommended for POGO.
- Pot and jack positions constrain IC and passive placement, leading to longer signal traces.

Document the chosen approach with a block diagram showing board boundaries and the
connector pinout between boards in `panel-notes.md`.

### Labeling and Silk-Screen

- Use a monospace or condensed sans-serif font — legibility at small sizes matters more
  than aesthetics (standard: Eurorack modules use 1.5–2 mm cap height for labels).
- Label conventions:
  - ALL CAPS for control names (ATTACK, CUTOFF, DRIVE).
  - Lowercase or mixed for units and qualifiers (ms, Hz, oct).
  - Arrow symbols (▲ ▼) or +/− for attenuverter center-detent indication.
  - Position indicator marks (dots or lines) on switch silk-screen to show positions.
- Group labels visually by block; use a thin horizontal line or gap between blocks.
- Color coding (anodized aluminum panels): standard POGO palette TBD. FR4 PCB panels
  support white silk-screen on black or green solder mask — no anodize cost.
- Panel file formats needed:
  - `panel.svg` — authoritative source, used to generate VCV Rack panel and manufacturing files.
  - DXF (from SVG): for CNC aluminum panel cutting (Schaeffer, Front Panel Express).
  - Gerber (if FR4 panel): export from KiCad panel footprint for PCB panel manufacturing (JLCPCB, PCBWay).

---

## Phase 5: Board Layout

Complete at the module level before any Phase 6 code is written. Layout decisions affect
which signals need to be software-accessible (debug test points) and confirm power budget.

Deliverables: `specs/board-layout/layout-notes.md`.

### Single Board vs Multi-Board Split

Document the chosen strategy (see Phase 4 sub-panel decision above) and define board boundaries:

| Board | Contents | Approx size | Connects to |
|---|---|---|---|
| Control board | All jacks, pots, switches, LEDs | ~(HP × 5.08 mm) × 80 mm | Audio board via header |
| Audio board | All ICs, passives, filter circuits | ~100 mm × 110 mm | Control board + Eurorack bus |

If further splitting (e.g., separate LP/HP board): document split point and inter-board signals.

### Ground Plane Strategy

- **Single analog ground plane** on the audio board bottom layer — preferred for an all-analog module.
- **Star ground** topology: all ground returns converge at a single point near the Eurorack power
  connector. Do not daisy-chain ground through IC packages.
- **Chassis ground**: connect panel ground (jack sleeves, pot chassis) to circuit ground at one
  point only — typically a solder jumper near the power header. Chassis ≠ signal ground.
- **No split digital/analog plane**: POGO is fully analog; a split plane is unnecessary and
  can introduce discontinuities under traces that cross the split.
- On the control board, use a ground fill on the bottom layer tied to the connector's GND pin;
  it carries only return currents from panel controls, not audio signals.

### Component Placement Rules

Apply these rules in KiCad (or equivalent) before routing:

1. **Decoupling caps within 1 mm of each IC supply pin** — place before routing power traces.
2. **Ferrite beads and bulk caps at the power header** — place first; route power from there.
3. **Envelope follower and high-gain stages away from power rails** — minimum 5 mm separation
   between the ENV rectifier input traces and any switching supply or ferrite bead.
4. **Filter IC pairs (LP1 + LP2, or each OTA bank) adjacent** — matched thermal environment
   reduces cutoff frequency drift between matched stages.
5. **CV input protection (100Ω + BAT54) placed immediately after the connector footprint** —
   protection must be the first thing a signal encounters after entering the board.
6. **Trim pots accessible without desoldering** — place on the top edge or a clearly reachable
   area; document each trim pot location in `layout-notes.md` with an adjustment procedure.
7. **No audio signal traces under power traces** — route audio on the bottom layer, power on
   the top (or use separate copper pours); keep parallel runs < 5 mm.

### Connector Strategy

**Eurorack power header:**
- 16-pin shrouded IDC header (or 10-pin if +5 V and gate bus are not needed).
- Place at the top or bottom center of the audio board, within 20 mm of the board edge.
- Red stripe (−12 V, pin 1) orientation: mark clearly on silk-screen with a triangle or arrow.
- Ferrite bead on each rail in series between header and board power plane.

**Control board ↔ Audio board connector:**
- 2.54 mm right-angle pin header on the audio board; mating socket on control board.
- Group signals by type: GND first, then +12 V / −12 V, then audio signals, then CV signals.
- Keep connector ≤ 40 pins; if more signals are needed, use two connectors.
- Document the full pinout in `layout-notes.md` — this becomes the integration test spec.

**Jack-to-board:**
- Use PCB-mount Thonkiconn (PJ301M-12) — direct solder to control board, no flying leads.
- Pot PCB-mount variant (Alpha 9mm or equivalent) — solder direct to control board.
- Sub-mini toggle switches: use PCB-mount right-angle variant to keep flush with the control board.

---

## Phase 6: DSP / VCV Rack Plugin Implementation

Only begin after `specs/STATUS.md` shows ✅ for Phases 1–3 on all blocks **and** Phase 4 and
Phase 5 are complete at the module level.

### Mapping analog model to digital

- Apply **bilinear transform** to s-domain transfer functions to get z-domain IIR filter
- Frequency pre-warping: `ω_digital = (2/T) × tan(ω_analog × T/2)`
- For nonlinear stages (distortion, saturation): use **2× or 4× oversampling** to suppress aliasing
- Reference the Phase 2 transfer function in a comment above the DSP class

### VCV Rack SDK conventions

- `#include <rack.hpp>` only — never include Rack sub-headers directly
- Define `ParamId`, `InputId`, `OutputId`, `LightId` enums in every Module; end each with `NUM_*`
- Constructor must call `config(NUM_PARAMS, NUM_INPUTS, NUM_OUTPUTS, NUM_LIGHTS)` then
  `configParam` / `configInput` / `configOutput` / `configLight` for each element
- All audio DSP runs in `void process(const ProcessArgs& args) override`
- `inputs[ID].getVoltage()` to read; `outputs[ID].setVoltage(v)` to write
- `args.sampleRate` (Hz) and `args.sampleTime` (seconds = 1 / sampleRate)
- `dsp::FREQ_C4` = 261.626 Hz (middle C at 0 V in 1V/oct)
- Panel asset: `asset::plugin(pluginInstance, "res/Pogo.svg")`

### Eurorack voltage standards (apply to every I/O)

| Signal type | Voltage range |
|---|---|
| Audio | ±5 V (10 Vpp) |
| Unipolar CV | 0–10 V |
| Bipolar CV | ±5 V |
| Gate (high) | 10 V |
| Trigger threshold | ~0.1 V low / ~2 V high |
| 1V/oct pitch | 1 V/octave; C4 = 0 V |

### Registering a new module

1. Create `src/ModuleName.cpp` with `struct ModuleName : Module` and `struct ModuleNameWidget : ModuleWidget`
2. Declare `extern Model* modelModuleName;` in `plugin.hpp`
3. Define `Model* modelModuleName = createModel<ModuleName, ModuleNameWidget>("ModuleName");` in `plugin.cpp`
4. Call `p->addModel(modelModuleName);` inside `init()`
5. Add the module slug to the `modules` array in `plugin.json`
6. Create `res/ModuleName.svg` for the panel

---

## Build & Test Workflow

```bash
export RACK_DIR=/path/to/Rack-SDK    # set once per shell session
make                                  # build plugin shared library
make clean                            # remove build artifacts
Rack -d                               # run VCV Rack in dev mode (loads plugin from cwd)
```

If the module does not appear in the VCV Rack Module Browser after `Rack -d`, check `log.txt`
in the Rack user folder for load errors.

For cross-platform distributable builds targeting Linux, macOS, and Windows from a single Linux
host, use the [rack-plugin-toolchain](https://github.com/VCVRack/rack-plugin-toolchain)
Docker image.

---

## Where to Start

1. Read `specs/STATUS.md` — if empty, begin filling in `specs/module-overview.md` with the full
   signal chain, estimated panel width, and power budget.
2. Work through blocks in signal-chain order: A → 1 → 2 → mod architecture → 3 → 4 → 5 → 6 → 7 → B.
   For each block: complete Phase 1 → Phase 2 → Phase 3 in `specs/block-N-name/spec.md` and
   `schematic.svg`, then create the HTML design doc in `design/`.
3. When all (or nearly all) per-block Phase 3 work is stable, begin **Phase 4: Panel Design**:
   create `specs/panel-design/panel-notes.md` and `specs/panel-design/panel.svg`.
4. After Phase 4 is complete, begin **Phase 5: Board Layout**:
   create `specs/board-layout/layout-notes.md`.
5. Only after STATUS.md shows ✅ for Phases 1–3 on all blocks AND Phase 4 AND Phase 5:
   create `src/dsp/*.hpp` for each block (Phase 6).
6. After all blocks are coded: integrate in `src/Pogo.cpp`, build, and test in VCV Rack.
