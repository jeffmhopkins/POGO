# POGO — Module Overview

## Description

POGO is a complex stereo Eurorack filter module. It processes stereo audio through a carefully
ordered signal chain combining a formant-style all-pass comb filter, three distortion modes, and
two independent lowpass stages plus a highpass stage — all with an extensive per-destination
modulation system rooted in an on-board envelope follower.

## Signal Chain

```
Stereo Input (L + R)  ←  ±5 V audio
  ↓
[Block A]  Input Buffers + Protection
           100Ω series + BAT54 clamp + unity-gain buffer on every input jack
  ↓
[Block 1]  Pre-Gain Boost
           Toggle switch: unity (1×) or boost (5×, ~14 dB)
           Applied equally to L and R
  ↓
[Block 2]  Envelope Follower
           Derives CV from post-gain audio; normalizes into Mod Bus input
           ENV OUT jack available as patch source
  ↓
[Block 3]  Triple 6-Stage All-Pass Comb Filter  (stereo)
           18 all-pass stages per channel (3 groups of 6)
           3 independent FREQ knobs + shared SPREAD + shared FREQ OFFSET
           Creates formant-like resonances across the full audio range
  ↓
[Block 4]  Distortion  (stereo)
           3 modes: Soft Clip / Hard Clip / Wavefold
           MODE switch + DRIVE knob; mode CV-selectable
  ↓
[Block 5]  LP Filter 1  (stereo, 2-pole Sallen-Key)
           Independent CUTOFF + RESONANCE + CV modulation
  ↓
[Block 6]  LP Filter 2  (stereo, 2-pole Sallen-Key — duplicate of LP1)
           Independent CUTOFF + RESONANCE + CV modulation
  ↓
[Block 7]  HP Filter  (stereo, 2-pole, self-oscillating)
           CUTOFF + RESONANCE + CV modulation
  ↓
[Block B]  Output Buffers (6 jacks total)
           LP2 AUX L / R  — tap at LP2 output (lowpass band, before HP)
           HP AUX L / R   — tap at HP output (highpass/bandpass, after HP)
           OUT L / R       — main stereo output (same tap as HP AUX, primary patch point)
           1 kΩ series + unity-gain buffer on every jack
Stereo Output (L + R)  →  ±5 V audio  (+ 4 aux bandpass outputs)

─────────────────────────────────────────────────────────────────────
MODULATION SYSTEM
─────────────────────────────────────────────────────────────────────
Envelope Follower output (ENV OUT)  ←  normalizes into:
Primary Mod Source Jack  (any CV/audio in)
  ↓
Mod Bus Processor:
  AMOUNT knob   0.2× – 5×
  OFFSET knob   ±5 V
  ↓
MOD BUS SIGNAL
  ↓ (to each destination via attenuverter + override jack)

Destinations (18 total):
  APF Master Offset     APF Freq 1 / 2 / 3     APF Feedback 1 / 2 / 3
  APF Blend     APF Dry/Wet     Distortion Drive 1 / 2 / 3
  LP1 Cutoff / Resonance     LP2 Cutoff / Resonance     HP Cutoff / Resonance
```

## Panel Width

**40 HP** (203.20 mm)

## Power Budget (estimates — update from measured values during bring-up)

| Block | +12 V | −12 V |
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
| Per-destination mod circuits (×14) | 30 mA | 30 mA |
| Block B: Output buffers | 5 mA | 5 mA |
| **Total estimate** | **~145 mA** | **~145 mA** |

## Eurorack Format

- 3U height (128.5 mm usable panel)
- 16-pin IDC power connector; red stripe = pin 1 = −12 V
- All audio: ±5 V (10 Vpp)
- CV: 0–10 V unipolar or ±5 V bipolar
- Gates: 10 V high
- 1V/oct: C4 = 0 V
