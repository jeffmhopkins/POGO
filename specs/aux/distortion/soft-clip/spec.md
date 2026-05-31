# aux: Soft-Clip Cell (SC)

**Type:** `distortion` · part of the [aux circuit library](../../_LIBRARY.md)

Design status: [ ] draft → [ ] reviewed → [ ] validated on prototype

The soft-clip waveshaper: an op-amp gain stage feeding a series **1N4148W diode chain**
(2 diodes per rail) that soft-limits the signal at **±Vth ≈ ±1.4 V**, producing the
tanh-approximation S-curve. One of the three parallel per-band distortion cells steered by
the CD4053 mux (see [distortion/overview](../overview/spec.md)).

## Overview

The plugin's SOFT mode (`Distortion.hpp::processNorm`, mode 0) is `y = Vth·tanh(G·v/Vth)`
with `Vth = 0.28` (= 1.4 V / 5 V at the ×5 audio scaling). True tanh is not realizable
passively; the analog cell approximates it with a gain stage whose output is shunted by a
**diode soft-limiting network** — two 1N4148W in series per polarity, antiparallel across the
feedback / to ground. As the signal approaches the forward-voltage stack (2 × V_f ≈ 1.4 V) the
diodes begin to conduct, gently rolling the gain off into a smooth saturation knee that closely
resembles the tanh S-curve. Below threshold the diodes are off and the stage is linear; the
DRIVE VCA ahead of the cell (`G`) sets how hard the signal is pushed into the knee.

Unlike hard-clip, the onset is *gradual* (the diode V_f rises incrementally with current), and
unlike wavefold the slope never reverses — the output asymptotes toward ±Vth.

## Schematic

ASCII (one channel; the diode network is the soft-limiter):

```
 V_drive (from DRIVE VCA)
     │
   [R_in 10k]
     │
     o───────────────[R_f 10k]──────────────┐   (closed-loop gain stage)
     │                                       │
  (−)│                          ┌── D_SC_1 ──┴── D_SC_2 ──┐  (2× 1N4148W, +rail)
     ▼      ┌────────┐          │                          │
    ─┤ TL072 ├──── V_out ───────o                          │  soft-limit: across R_f
  (+)▲      └────────┘          │                          │  (or to V_out node)
     │                          └── D_SC_3 ──┬── D_SC_4 ──┘  (2× 1N4148W, −rail)
    GND                                      │
                                            ─┴─  antiparallel pair, ±(2·V_f) ≈ ±1.4 V
```

- Below |V_out| < 1.4 V: diodes off → clean linear gain (set by R_f/R_in and the DRIVE VCA).
- Above ±1.4 V: the diode stack conducts, the incremental gain collapses → soft saturation,
  output asymptotes to ±Vth ≈ ±1.4 V (the tanh ceiling).

## Transfer Function

DSP (ground truth, `Distortion.hpp:33-37`, normalized ±1 domain):

```
Vth = 0.28                        (= 1.4 V / 5 V)
G   = (p ≤ 0.20) ? p/0.20 : exp((p−0.20)/0.80 · 4)     drive gain, 0 → ~55×
y   = Vth · tanh(G · v / Vth)
```

At the ×5 audio scaling the bound is **±Vth·5 = ±1.4 V**. The analog diode soft-clip
realizes the same ceiling with a different (but audibly similar) harmonic profile:

```
Analog (representative):
  V_out_clean = −(R_f/R_in)·V_drive       (linear, below knee)
  |V_out| → 2·V_f(1N4148W) ≈ 1.4 V        (soft ceiling, above knee)
```

The clip ceiling is a **device constant** ([NV] — set by the 1N4148W forward voltage stack,
not a bindable resistor). The library sim checks the *design-intent* ceiling = plugin
`Vth × 5 V = 1.4 V`, and that the linear region passes below the knee.

## Design Choices & Rationale

- **Two diodes per rail** (not one): a single 1N4148W (~0.7 V) would clip at ±0.7 V — too low.
  The 2-in-series stack reaches ±1.4 V, matching the plugin's `Vth=0.28` × 5 V exactly.
- **1N4148W** (SOD-123, fast switching) for a clean, repeatable V_f and >100 kHz bandwidth so
  the harmonics generated are not bandwidth-limited in the audio band.
- **Diode soft-clip over a true tanh shaper:** the diode-knee S-curve is far simpler than an
  active translinear tanh cell and is audibly equivalent for this application; the incremental
  V_f rise gives the characteristic gentle onset.
- DRIVE is set by the **THAT2180 VCA ahead** of the cell (see aux/vca/vca-cell), not by this
  stage — the cell's R_f/R_in is unity so it does not set the clip level, only the DRIVE does.

## Component Values (POGO-specific)

| Ref (generic) | Part | Package | Value | Notes |
|---|---|---|---|---|
| U_SC | TL072CDT | SOIC-8 (½) | — | SC gain / soft-limit op-amp |
| R_SC_in | Resistor | 0603 | 10 kΩ | SC input resistor |
| R_SC_f | Resistor | 0603 | 10 kΩ | SC feedback resistor (R_f = R_in → unity cell gain) |
| D_SC_1..2 | 1N4148W | SOD-123 | — | +rail soft-clip pair (2× series → +1.4 V) |
| D_SC_3..4 | 1N4148W | SOD-123 | — | −rail soft-clip pair (2× series → −1.4 V) |

## Performance Characteristics

| Parameter | Value | Condition |
|---|---|---|
| Soft-clip ceiling | ±1.4 V | 2× 1N4148W per rail (= plugin Vth 0.28 × 5 V) |
| Onset | gradual (tanh-like knee) | diode V_f rises incrementally with current |
| Slope reversal | none | output asymptotes to ±Vth (vs wavefold) |
| Bandwidth | >100 kHz | small-signal |

## Known Gotchas / Assembly Notes

- 1N4148W forward voltage varies with current, so the effective threshold is mildly
  drive-dependent — this is part of the soft-clip character and is desirable.
- The cell op-amp gain is unity (R_f = R_in); clip onset is set by the DRIVE VCA ahead, not
  by this stage. Do not add gain here or the clip level will not match the plugin.

## Used By

| Block | Instance | Board | Notes |
|---|---|---|---|
| distortion/overview | SC path | — | one of three parallel cells → CD4053 mux |
| block-6 | DIST_BP1_L/R (SC) | Control | BP1 group soft-clip cell, both channels |
| block-6 | DIST_BP2_L/R (SC) | Control | BP2 group soft-clip cell, both channels |
| block-6 | DIST_BP3_L/R (SC) | Control | BP3 group soft-clip cell, both channels |
