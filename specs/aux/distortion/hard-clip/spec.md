# aux: Hard-Clip Cell (HC)

**Type:** `distortion` · part of the [aux circuit library](../../_LIBRARY.md)

Design status: [ ] draft → [ ] reviewed → [ ] validated on prototype

The hard-clip waveshaper: an op-amp gain stage feeding a pair of **back-to-back
BZX84C5V1 zeners** that brick-wall-limit the signal at **±5.8 V** (= zener V_Z 5.1 V +
forward V_F 0.7 V), matching the plugin's **±1.16 normalized** hard clip at the ×5 audio
scaling. One of the three parallel per-band distortion cells steered by the CD4053 mux
(see [distortion/overview](../overview/spec.md)).

## Overview

The plugin's HARD mode (`Distortion.hpp::hardClip`, mode 1) is `y = clamp((1+4d)·v, ±1.16)`
— a linear gain (1×→5×, set by drive `d`) followed by a hard clamp to **±1.16 normalized**.
At the ×5 audio scaling that clamp is **±1.16 × 5 = ±5.8 V**. The analog cell realizes the
brick-wall with **two BZX84C5V1 zeners anode-to-anode**: on each excursion one zener is in
reverse breakdown (V_Z ≈ 5.1 V) while the other conducts forward (V_F ≈ 0.7 V), giving a
symmetric clamp at **±(5.1 + 0.7) = ±5.8 V**.

Schottky diodes (~±0.6 V) would clip far too early; zeners are chosen *precisely* to reach
the ±5.8 V rail the plugin specifies. Below ±5.8 V the cell is a clean (unity) gain stage;
the DRIVE VCA ahead of the cell pushes the signal into the fixed threshold, so DRIVE — not
the clamp — controls the clip onset.

## Schematic

ASCII (one channel; the zener pair is the brick-wall limiter):

```
 V_drive (from DRIVE VCA)
     │
   [R_in 10k]
     │
     o───────────────[R_f 10k]──────────────┐   (closed-loop gain stage)
     │                                       │
  (−)│      ┌────────┐                       │
     ▼      │ TL072  ├──── V_out ────────────o──────── HC_out
  (+)▲──GND └────────┘                       │
     │                          D_HC_Z1 ──►|─┤   BZX84C5V1, back-to-back (anode-to-anode)
                                D_HC_Z2 ──|◄─┘   one in breakdown (5.1V) + one fwd (0.7V)
                                            │
                                           GND
                                  V_clip = ±(V_Z + V_F) = ±5.8 V
```

- Below |V_out| < 5.8 V: zeners off → clean linear gain (set by R_f/R_in and the DRIVE VCA).
- Above ±5.8 V: the back-to-back zeners conduct → output hard-clamps at ±5.8 V (brick wall).

## Transfer Function

DSP (ground truth, `Distortion.hpp:12-16`, normalized ±1 domain):

```
g = 1 + d·4                       (drive gain, 1× → 5×)
y = clamp(g · v, −1.16, +1.16)    (hard clip at ±1.16 normalized)
```

At the ×5 audio scaling the clamp is **±1.16 × 5 = ±5.8 V**. The analog realizes the same
brick wall with the zener stack:

```
Analog (representative):
  V_out_clean = −(R_f/R_in)·V_drive       (linear, below clamp)
  |V_out| → V_Z + V_F ≈ 5.1 + 0.7 = 5.8 V (hard ceiling, above clamp)
```

The clip level is a **device constant** ([NV] — set by the BZX84C5V1 zener V_Z + 1N4148-class
forward V_F, not a bindable resistor). The library sim checks the *design-intent* clamp =
plugin `1.16 × 5 V = 5.8 V`, and that the normalized back-conversion = 1.16.

## Design Choices & Rationale

- **Zeners, not Schottky/silicon diodes:** the target clamp is ±5.8 V; a silicon-diode stack
  would need ~8 diodes per rail. Two BZX84C5V1 back-to-back reach ±5.8 V with one part per
  rail and a clean, repeatable breakdown knee.
- **BZX84C5V1** (SOT-23, V_Z 5.1 V nominal): V_Z + forward V_F = 5.1 + 0.7 = 5.8 V matches the
  plugin's ±1.16 normalized clamp at the ×5 scaling. (Plugin comment cites this exact stack.)
- **Brick-wall vs soft knee:** the zener breakdown is much sharper than a diode forward knee,
  giving the aggressive odd-harmonic "fuzz" character distinct from the soft-clip cell.
- DRIVE is set by the **THAT2180 VCA ahead** of the cell (see aux/vca/vca-cell), not by this
  stage — the cell's R_f/R_in is unity so it does not set the clip level, only DRIVE does.

## Component Values (POGO-specific)

| Ref (generic) | Part | Package | Value | Notes |
|---|---|---|---|---|
| U_HC | TL072CDT | SOIC-8 (½) | — | HC gain stage op-amp |
| R_HC_in | Resistor | 0603 | 10 kΩ | HC input resistor |
| R_HC_f | Resistor | 0603 | 10 kΩ | HC feedback resistor (R_f = R_in → unity cell gain) |
| D_HC_Z1, D_HC_Z2 | BZX84C5V1 | SOT-23 | — | back-to-back zener clamp (anode-to-anode) → ±5.8 V |

## Performance Characteristics

| Parameter | Value | Condition |
|---|---|---|
| Hard-clip level | ±5.8 V | BZX84C5V1 V_Z 5.1 V + V_F 0.7 V (= plugin 1.16 × 5 V) |
| Normalized clamp | ±1.16 | = ±5.8 V / 5 V (plugin `hardClip` clamp) |
| Onset | sharp (brick wall) | zener breakdown knee |
| Bandwidth | >100 kHz | small-signal |

## Known Gotchas / Assembly Notes

- BZX84C5V1 V_Z has a tolerance (typ ±5 %); the ±5.8 V clamp can vary ±0.3 V part-to-part.
  This is acceptable for a distortion effect — the DRIVE VCA dominates the audible character.
- The cell op-amp gain is unity (R_f = R_in); clip onset is set by the DRIVE VCA ahead, not
  by this stage. Do not add gain here or the clip level will not match the plugin.
- Zener capacitance (a few pF) is negligible in the audio band; the >100 kHz cell bandwidth is
  set by the op-amp, not the clamp.

## Used By

| Block | Instance | Board | Notes |
|---|---|---|---|
| distortion/overview | HC path | — | one of three parallel cells → CD4053 mux |
| block-6 | DIST_BP1_L/R (HC) | Control | BP1 group hard-clip cell, both channels |
| block-6 | DIST_BP2_L/R (HC) | Control | BP2 group hard-clip cell, both channels |
| block-6 | DIST_BP3_L/R (HC) | Control | BP3 group hard-clip cell, both channels |
