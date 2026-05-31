# aux: Unity-Gain Buffer (Non-Inverting and Inverting)

> ✅ **Re-verified 2026-05-30** (change 0018). G=+1 unity follower; HP output is a unity follower (no G=−1 buffer).

Design status: [ ] draft → [ ] reviewed → [ ] validated on prototype

## Overview

Voltage follower (G=+1) and inverting unity-gain buffer (G=−1) using OPA1612 or TL072CDT
dual op-amps. Used throughout POGO for impedance conversion, signal routing, and the HP
output polarity correction required by the OTA-C SVF summing amplifier.

Two variants documented here:
- **Variant A (non-inverting):** G=+1 voltage follower; input to (+), feedback from output to (−)
- **Variant B (inverting unity):** G=−1; (+) to GND, R_in = R_f (e.g. 10 kΩ each)

IC selection:
- OPA1612: input noise 1.1 nV/√Hz — used at module audio input (Block A) where noise matters
- TL072CDT: input noise ~18 nV/√Hz — adequate for all other buffer instances

## Schematic


ASCII fallback:

```
Variant A — Non-Inverting (G = +1):

                 ┌───────────────────┐
  V_in ──────────┤ (+)  TL072/OPA1612 ├─────────────────── V_out
                 │ (−)◄──────────────┤
                 └───────────────────┘

  Input Z = ~1 TΩ (JFET input)
  Output Z = ~50 Ω (op-amp) + 1 kΩ (series R_out)

  V_in ──[R_out 1kΩ]──► Jack/Load
         (1kΩ limits short-circuit current to ≤12 mA from ±12V rail)


Variant B — Inverting Unity (G = −1):

                     R_in (10kΩ)          R_f (10kΩ)
  V_in ──────────────[────────]──┬──(−)──[────────]──┬── V_out = −V_in
                                 │                    │
                            (+)──┴─ GND               │ (feedback)
                                 │
                          TL072/OPA1612

  V_in ──[R_out 1kΩ]──► Jack/Load (if driving an output jack)
```

## Transfer Function

### Variant A (Non-Inverting)

```
V_out = V_in

Bandwidth: f_−3dB ≈ GBW / (1 + G) = GBW / 2
TL072 GBW = 3 MHz → f_−3dB ≈ 1.5 MHz (well above audio)
OPA1612 GBW = 80 MHz → f_−3dB ≈ 40 MHz
```

### Variant B (Inverting Unity)

```
V_out = −(R_f / R_in) × V_in = −V_in   (when R_f = R_in)

Closed-loop gain: G_CL = −1
Bandwidth: f_−3dB = GBW / (1 + 1) = GBW / 2   (same as non-inverting)
```

Input impedance of Variant B = R_in = 10 kΩ (lower than Variant A; note the source
must drive R_in without significant loading).

## Design Choices & Rationale

### OPA1612 at Input and Gain Stages; TL072 for Unity Buffers

The OPA1612 (input noise 1.1 nV/√Hz) is used where noise is established or amplified:
the Block A input buffers and any **gain stage** that lifts the noise floor (e.g. Block 1
pre-gain U2/U3 at 5×, and the Block 6 stages that use OPA1612). At those points the lower
noise is audible after downstream gain.

For plain **unity buffers** further down the chain — where audio is already at signal-path
levels (±5 V) and gain = +1 adds no further amplification — the TL072CDT (18 nV/√Hz) is
adequate, and using OPA1612 there would add cost/power without audible benefit. The choice
is therefore per-role (gain/input → OPA1612; unity buffer → TL072), not a blanket
"OPA1612 only at Block A." (See `components.yaml` for the locked per-ref part choices.)

### 1 kΩ Series Output Resistor

```
Short-circuit protection: I_max = Vcc / R_out = 12V / 1kΩ = 12 mA
This limits op-amp output stage dissipation during brief shorts (e.g. patching).
1 kΩ with typical load of 10 kΩ causes ≈ 0.1 dB insertion loss — inaudible.
The 1 kΩ is not used on internal nodes (only on jacks and between-board connections).
```

### Clamp Diodes at Module Input (Block A)

The input buffer (OPA1612, non-inverting) is preceded by:
- 100 Ω series resistor
- BAT54S Schottky clamp diodes to ±12V rails (actually ±11V after forward drop)

This clamps the OPA1612 input to safe levels before any signal processing. The unity
buffer output does not need output clamping; the downstream signal stays within
±11V due to op-amp supply limiting.

### HP Output Buffer — unity follower (NOT inverting)

The OTA-C SVF SUM_AMP (see aux-ota-c-svf) produces the HP tap already at its output node:
  HP_inv = −(x − k·v₁ − v₂)

The plugin `HPFilter::process` deliberately **returns this same negated value**
(`return -(x - k*v1 - v2)`), so the SUM_AMP node *equals* the plugin output. The hardware
therefore takes that node through a **unity non-inverting follower (G=+1)** for drive
isolation only — `HP_out = HP_inv`, matching the plugin. Do **not** add a second inversion:
an earlier G=−1 buffer here double-inverted and phase-flipped HP vs the plugin (bug fixed in
change 0018; the inverting-buffer resistors were removed). See aux-ota-c-svf §SUM_AMP
Inversion and HP Polarity.

### IC Pairing

TL072CDT (SOIC-8) contains two op-amp halves. Pairing strategy:
- SUM_AMP (Variant A buffer, one half) + HP inverting buffer (Variant B, other half) → 1× TL072
- LP output buffer (Variant A) can share an IC with a nearby low-gain function
- Block A: OPA1612 (SOIC-8) for both L and R input buffers (one IC total)
- Block B: TL072 for both L and R output buffers (one IC total)

## Component Values (POGO-specific)

| Ref (generic) | Part | Package | Value | Notes |
|---|---|---|---|---|
| U_BUF_A | OPA1612AIDR | SOIC-8 | — | Block A input buffers only (noise critical: 1.1 nV/√Hz) |
| U_BUF_B | TL072CDT | SOIC-8 | — | All other buffer instances |
| R_in | Resistor | 0603 | 10 kΩ | Variant B: inverting input; R_in = R_f |
| R_f | Resistor | 0603 | 10 kΩ | Variant B: feedback; R_f = R_in → G = −1 |
| R_out | Resistor | 0603 | 1 kΩ | Series output protection; only at jacks |
| R_in_A (Block A) | Resistor | 0603 | 100 Ω | Input series protection before OPA1612 |
| D_in (Block A) | BAT54S | SOT-23 | — | Input clamp; anode/cathode to ±12V rails |
| C_VCC, C_VEE | Ceramic bypass | 0603 | 100 nF | Per IC supply pin; within 1 mm of pin |

### Noise Budget (Block A OPA1612)

```
Input noise density: 1.1 nV/√Hz
Audio bandwidth: 20 kHz
Integrated noise: 1.1 nV/√Hz × √(20000) = 1.1 × 141 = 155 nV_rms ≈ 0.16 µV_rms

SNR at ±5V (5V_rms) audio input:
  SNR = 20 × log10(5V / 155nV) ≈ 150 dB

This is well below thermal noise from source impedance (100 Ω source at 300K):
  V_n = √(4kTR × BW) = √(4 × 4.1e-21 × 100 × 20000) = 57 nV_rms
→ Source thermal noise dominates; OPA1612 choice is well-matched.
```

## Performance Characteristics

| Parameter | Value | Condition |
|---|---|---|
| Gain (Variant A) | +1.000 (0 dB) | G = 1, unity |
| Gain (Variant B) | −1.000 (0 dB) | G = −1, inverting unity |
| Bandwidth | >1.5 MHz (TL072) | Both variants |
| Input impedance (Var A) | >1 GΩ | TL072 (JFET) / OPA1612 (bipolar, high-Z) |
| Input impedance (Var B) | 10 kΩ | Set by R_in |
| Output impedance | ~50 Ω + 1 kΩ series | At jack |
| Signal range | ±11V | ±12V supply |
| Short-circuit protection | 12 mA max | Via 1 kΩ R_out |
| Input noise (Block A) | 1.1 nV/√Hz | OPA1612 |
| Input noise (other) | ~18 nV/√Hz | TL072CDT |

## Known Gotchas / Assembly Notes

- Supply decoupling: 100 nF ceramic on each supply pin, placed within 1 mm of the pin;
  without this, TL072 can oscillate at ~3 MHz with capacitive loads
- Variant B R_in = R_f matching is important for G = −1 accuracy; use 1% resistors
- OPA1612 quiescent current is 5.5 mA/package (2.75 mA/channel); TL072 is ~3 mA/package —
  both are acceptable at ±12V Eurorack rails; factor OPA1612 Iq into Block A power budget
- TL072 input common-mode range does not include the negative rail; at ±12V supply,
  inputs must stay above −11V to avoid phase reversal — this is fine for audio signals
  but note it if unity buffers appear near the rail for bias circuits
- The 100 Ω series resistor and BAT54S at Block A form the CV input protection; this
  same pattern is reused at all CV input jacks (see aux-cv-protection.md)
- R_out (1 kΩ) at output jacks: omit on internal signal nodes to avoid unnecessary
  insertion loss and HF roll-off with capacitive loads (e.g., cable capacitance
  30 pF: f_−3dB = 1/(2π × 1kΩ × 30pF) = 5.3 MHz — fine for audio)

## Used By

| Block | Instance | Board | Notes |
|---|---|---|---|
| block-A | BUF_L, BUF_R | audio | OPA1612; non-inverting G=+1 |
| block-B | BUF_L, BUF_R | audio | TL072; non-inverting G=+1; 1kΩ output |
| block-5 | LP1_OUT buffer | audio | OPA1612 half; G=+1 unity follower on v2 (LP1 output) |
| block-7 | HP output follower | audio | OPA1612 half; G=+1 unity follower on the SUM_AMP node (no inversion) |
| block-8 | LP2_OUT_BUF | audio | TL072 half; G=+1 for LP2 output |
| block-6 | BP_OUT_BUF × 3 | audio | TL072; G=+1 for each BP group output |
