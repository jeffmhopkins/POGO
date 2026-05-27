# aux: Bandpass Distortion Circuit (SC / HC / WF)

Design status: [ ] draft → [ ] reviewed → [ ] validated on prototype

## Overview

Three parallel distortion sub-circuits — soft clip (SC), hard clip (HC), and wavefold
(WF) — with a CD4053 analog multiplexer selecting the active mode. All three circuits
run simultaneously; the CD4053 simply steers the selected output. Mode selection is
global across all three BP groups, controlled by the BP_DIST switch on the panel.

Chosen because:
- Parallel pre-built paths eliminate mode-switch glitches (no transient when switching)
- CD4053 (triple 2-channel CMOS analog mux) is widely available in SOIC-16 and handles
  ±5V audio signals from a ±12V (or split ±5V virtual ground) supply
- Three independent distortion modes closely mirror the DSP Distortion.hpp modes
- One CD4053 per BP SVF group (3 total) allows independent per-group distortion levels
  while sharing a single mode-select control

## Schematic

![aux-distortion.svg](aux-distortion.svg)

ASCII fallback (one BP group, one channel shown):

```
 BP_SVF_OUT ──────────────┬──────────────────────────────────────────────┐
                           │                                              │
                    [DRIVE POT/CV]                                        │
                           │                                              │
           ┌───────────────┼───────────────────┐                         │
           │               │                   │                         │
           ▼               ▼                   ▼                         │
    ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐                  │
    │  SOFT CLIP  │ │  HARD CLIP  │ │    WAVEFOLD     │                  │
    │  (SC path)  │ │  (HC path)  │ │    (WF path)    │                  │
    │ tanh approx │ │ Schottky    │ │  op-amp fold    │                  │
    │ diode chain │ │ back-to-back│ │  network        │                  │
    └──────┬──────┘ └──────┬──────┘ └────────┬────────┘                  │
           │               │                  │                          │
           ▼               ▼                  ▼                          │
         Y_SC            Y_HC               Y_WF                         │
           │               │                  │                          │
           └───────────────┴──────────────────┘                          │
                                │                                        │
                     ┌──────────▼──────────┐                             │
                     │     CD4053 MUX      │                             │
                     │  (one per group)    │◄── BP_DIST switch           │
                     │  CH A: SC/HC select │    (2 control lines)        │
                     │  CH B: _/WF select  │                             │
                     │  CH C: spare        │                             │
                     └──────────┬──────────┘                             │
                                │                                        │
                          DIST_OUT ──────────────────────────────────────┘
                                                                         │
                                                                    (→ BP_MIX)
                                                                    (→ BP3_L/R_OUT tap)
```

## Transfer Function

### DSP Reference (Distortion.hpp)

All modes take a signal normalized to ±1, then scale back to ±5V:

```
Drive parameter interpretation:
  driveParam ∈ [0, 1]
  If driveParam ≤ 0.20: linear region (0→1× effective gain, no distortion processing)
  If driveParam > 0.20: d = (driveParam − 0.20) / 0.80  → d ∈ [0, 1]

Mode 0 — SOFT (tanh):
  drive = exp(d × 4) − 1      range: 0 → 53.6×
  y = tanh(drive × x) / tanh(drive)

Mode 1 — HARD (hard clip):
  g = 1 + d × 4               range: 1× → 5×
  y = clamp(g × x, −1, +1)

Mode 2 — FOLD (wavefold):
  y = asin(sin(π/2 × (1 + d × 4) × x)) × 2/π
  Range of fold gain: 1× → 5×; Buchla-style triangle-to-sine folder
```

### Analog Approximations

**SC (Soft Clip):**
The tanh approximation is implemented with an op-amp gain stage followed by a
soft-limiting network (two or three diodes in series on each rail). The diode-string
threshold sets the soft clipping onset; the gain before the diodes controls the drive.
True tanh is not achievable passively; the diode approximation produces a similar
S-curve with slightly different harmonic profile — audibly similar, simpler to build.

```
Approximate circuit transfer:
  V_in → [R_in] → op-amp (+gain stage) → [diode soft-clip network] → V_out
  At low drive: op-amp gain is low → well below diode threshold → linear
  At high drive: output clips softly against diode forward voltage stack
```

**HC (Hard Clip):**
Schottky diodes (BAT54S) back-to-back between output and GND (or between ±reference
voltages) hard-limit the output after an op-amp gain stage. Schottky V_f ≈ 0.3V;
two in series = ±0.6V clip threshold. Combined with scaling, maps to DSP ±1 range.

```
V_in → [R_in] → op-amp (+gain stage) → [BAT54S back-to-back clamp] → V_out
```

**WF (Wavefold):**
Buchla-style folder: a high-gain op-amp with feedback limiting; the asin(sin(x))
waveform is approximated by a triangle-generating feedback network. The fold gain
controls how far into the fold the input signal travels.

```
V_in → [R_in] → [high-gain op-amp with triangle-limiting feedback] → V_out
```

## Design Choices & Rationale

### Parallel Paths, MUX Output Selection

All three distortion circuits receive the same input simultaneously and process
it continuously. The CD4053 selects which output reaches the next stage. This:
- Avoids the pop/click of switching gain stages on and off
- Keeps the CD4053 in the signal path only for the selected mode, minimizing
  the on-resistance (Ron ≈ 200 Ω for CD4053) contribution to distortion
- Allows fast mode switching without muting — useful for live performance

### CD4053 Configuration

CD4053 (triple 2-channel analog MUX, SOIC-16):
- Three independent 2:1 multiplexer channels (A, B, C)
- Control pins S_A, S_B, S_C; INHIBIT pin (active low, tie to GND for always-on)
- With a 3-position switch and 2 digital control lines:
  - S_A selects SC vs HC (for channels A)
  - S_B selects fold-path enable/disable (for channel B)
  - All three CD4053 ICs (one per BP group) have S_A and S_B tied together →
    mode selection is global across BP1, BP2, BP3 simultaneously

BP_DIST switch: 3-position, produces 2 binary control lines:
  - Position 1 (SOFT): S_A=0, S_B=0
  - Position 2 (HARD): S_A=1, S_B=0
  - Position 3 (FOLD): S_A=0, S_B=1

### Signal Levels and CD4053 Supply

CD4053 must operate with audio signal swinging ±5V. For the CD4053 to pass ±5V
without signal-dependent Ron distortion, Vcc/Vee must bracket the signal range:
- Supply: Vcc = +12V, Vee = −12V (or Vdd = +5V, Vss = −5V with separate 5V regulators)
- Standard POGO ±12V supplies work; V_logic supply (V+ pin of CD4053) from +5V
  regulated rail or resistor divider from +12V with zener clamp
- INHIBIT pin tied to GND (active-low, so GND = not inhibited = MUX active)

### Oversampled Loop Context

The DSP runs the bandpass section at 2× oversampling. The distortion runs inside the
oversampled loop, meaning in hardware the distortion must operate at full signal bandwidth
(the oversampling is a DSP artifact to reduce aliasing from nonlinear operations).
Hardware naturally operates at continuous time, so no special bandwidth consideration
is needed beyond ensuring each distortion sub-circuit bandwidth exceeds 100 kHz.

### BP3_L/R_OUT Tap

The DSP taps the distortion output (before BP_MIX blend) for the BP3_L/R_OUT jacks.
In hardware, this tap point is at the CD4053 output node, before the BP_MIX summing
network. Route a buffered tap from each CD4053 output to the BP3_OUT jacks via a
unity-gain buffer (aux-unity-buffer, Variant A).

## Component Values (POGO-specific)

| Ref (generic) | Part | Package | Value | Notes |
|---|---|---|---|---|
| U_MUX_BP1 | CD4053BM96 | SOIC-16 | — | BP1 group mux; one per BP group |
| U_MUX_BP2 | CD4053BM96 | SOIC-16 | — | BP2 group mux |
| U_MUX_BP3 | CD4053BM96 | SOIC-16 | — | BP3 group mux |
| U_SC | TL072CDT | SOIC-8 | — | SC path gain + diode network op-amp |
| U_HC | TL072CDT | SOIC-8 | — | HC path gain stage |
| U_WF | TL072CDT | SOIC-8 | — | WF fold op-amp |
| D_HC_P, D_HC_N | BAT54S | SOT-23 | — | HC back-to-back Schottky clamp |
| D_SC_1..4 | 1N4148W | SOD-123 | — | SC diode string (2 per rail, 4 total) |
| R_SC_in | Resistor | 0603 | 10 kΩ | SC input resistor |
| R_HC_in | Resistor | 0603 | 10 kΩ | HC input resistor |
| R_WF_in | Resistor | 0603 | 10 kΩ | WF input resistor |
| R_DRIVE | Pot + CV | — | 100 kΩ | Drive control per group (panel pot + CV sum) |
| C_VCC, C_VEE | Ceramic bypass | 0603 | 100 nF | Per CD4053 and op-amp supply pin |

### Drive Gain Mapping

```
DSP: drive = exp(d × 4) − 1 → max = exp(4) − 1 ≈ 53.6×

Hardware SC gain: set by R_in and R_f of gain stage.
At max drive: gain ≈ 50× → R_f / R_in = 50 → R_in = 10kΩ, R_f = 470kΩ (with switch
  or pot to vary gain from 1× to 50×; pot in feedback path sets variable gain)
```

## Performance Characteristics

| Parameter | Value | Condition |
|---|---|---|
| Distortion range (SC) | 0 to ~50× pre-gain | exp law; diode soft clip |
| Distortion range (HC) | 1× to 5× pre-gain | Linear gain, hard clip |
| Distortion range (WF) | 1× to 5× fold gain | Triangle-to-fold waveshaping |
| Mode-switch transient | None (parallel paths) | CD4053 glitch < 10 ns |
| CD4053 Ron | ~200 Ω | At ±12V supply |
| Signal bandwidth | >100 kHz | All paths |
| Supply current | ~8 mA | All 3 groups + MUX ICs |

## Known Gotchas / Assembly Notes

- CD4053 Ron (200 Ω) in series with the signal; this is typically insignificant
  when the next stage input impedance is ≥10 kΩ (Ron contributes <2% attenuation)
- CD4053 V_logic supply: if using 3.3V or 5V logic from a regulator, ensure the
  CMOS level on control pins meets CD4053 logic thresholds at the supply voltage used
- Distortion circuits all reference the same GND; ensure no ground loops between
  BP group sub-circuits (star ground topology at each group)
- SC diode string: 1N4148W forward voltage varies with current; actual clipping
  threshold will be drive-dependent (diode V_f increases at higher current).
  This is part of the soft-clip character and is desirable.
- HC path: BAT54S forward voltage ~0.3V → clip at ~0.6V differential. With a 5V
  audio signal and gain = 5×, output clips at 0.6V/5 = 0.12V_in → severe clipping
  at moderate signal levels. This is correct behavior for hard clip mode.
- WF path: feedback network design for asin(sin(x)) approximation requires careful
  phase margin analysis; the fold op-amp must remain stable with the feedback
  network across all fold gain settings. Phase 3R must verify stability.
- BP3_L/R_OUT tap buffer: the unity buffer must be placed after the CD4053 output
  to ensure it taps the selected (post-distortion) signal, not the raw SVF output

## Used By

| Block | Instance | Board | Notes |
|---|---|---|---|
| block-6 | DIST_BP1_L/R | Control | BP1 group SC/HC/WF + CD4053; both channels |
| block-6 | DIST_BP2_L/R | Control | BP2 group SC/HC/WF + CD4053; both channels |
| block-6 | DIST_BP3_L/R | Control | BP3 group SC/HC/WF + CD4053; BP3_OUT tap here |
