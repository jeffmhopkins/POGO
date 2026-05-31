# aux: Wavefolder Cell (WF)

**Type:** `distortion` · part of the [aux circuit library](../../_LIBRARY.md)

Design status: [ ] draft → [ ] reviewed → [ ] validated on prototype

The Buchla-style triangle folder: a passive **±Vth ≈ ±1.4 V** diode clamp feeds the (+)
input of a **G = +2 non-inverting** stage while the raw signal drives the (−) input, giving
`V_out = 2·V_clamp − V_in`. Below ±Vth the output tracks the input (slope +1); above ±Vth
the output **slope reverses** (slope −1) — a true fold, not gain compression. One of the
three parallel per-band distortion cells steered by the CD4053 mux
(see [distortion/overview](../overview/spec.md)).

## Overview

The plugin's FOLD mode (`Distortion.hpp::wavefold`, mode 2) is
`y = Vth·asin(sin(π/2/Vth · (1+4d)·v))·2/π` with `Vth = 0.28` (= 1.4 V / 5 V). The
`asin(sin(·))` is a triangle wave — a signal that reflects (folds) every time it crosses ±Vth.
The analog cell realizes the **first fold exactly** with a passive clamp + a precision
subtractor: the clamp pins V_clamp at ±Vth past threshold while the raw signal still rises, so
the `2·V_clamp − V_in` law reflects the output back. Multiple reflections at high drive come
from the input swinging across many ±Vth windows.

This is the **signature** distortion cell: unlike SC (asymptotes to ±Vth) and HC (clamps at a
rail), the WF output **slope genuinely reverses** past threshold.

## Schematic

ASCII (one channel; passive clamp + G=+2 non-inverting folder):

```
 V_in (from DRIVE VCA / pre-gain stage)
   │
   ├──[R_clamp 10k]──┬── V_clamp ───────────────────►(+)  ┌────────┐
   │                 │                                    │ TL072  ├──── V_out
   │            D_WF_1/2 ──►|── (+rail, 2× 1N4148W)       │  (B)   │
   │            D_WF_3/4 ──|◄── (−rail, 2× 1N4148W)  (−)──┤        │
   │                 │                              │ └────────┘
   │                GND                             │
   └──────────────────[R_g 10k]────────────────────o──[R_f 10k]──► V_out
                                                    (feedback)

 Passive clamp:  V_clamp = V_in            |V_in| ≤ Vth
                 V_clamp = ±Vth            |V_in| > Vth   (Vth = 2·V_f ≈ 1.4 V)

 Non-inverting folder (R_g = R_f → G = 1+R_f/R_g = 2):
   V_out = V_clamp·(1 + R_f/R_g) − V_in·(R_f/R_g) = 2·V_clamp − V_in
```

- |V_in| ≤ Vth: V_clamp = V_in → V_out = 2·V_in − V_in = V_in (slope +1, linear).
- |V_in| > Vth: V_clamp pins at ±Vth → V_out = ±2·Vth − V_in (slope −1, the fold).

## Transfer Function

DSP (ground truth, `Distortion.hpp:18-25`, normalized ±1 domain):

```
Vth = 0.28                                       (= 1.4 V / 5 V)
y_pre = (1 + d·4) · v                             (fold-depth gain, 1× → 5×)
y = Vth · asin(sin(π/2/Vth · y_pre)) · 2/π        (triangle fold; reflects at ±Vth)
```

The analog cell realizes the same fold (in the ×5 V domain, Vth = 1.4 V) via the subtractor:

```
Analog (per fold):
  V_out = 2·V_clamp − V_in
  V_clamp = clamp(V_in, ±1.4 V)     (passive 2×1N4148W-per-rail clamp)
```

The fold **threshold** ±1.4 V is a device constant ([NV] — set by the 1N4148W forward-voltage
stack, not a bindable resistor). The fold **slope reversal** is set by the folder **gain ratio**
`G = 1 + R_f/R_g = 2` (R_g = R_f); the library sim derives the +2 gain from the R_g/R_f values
(not hardcoded ×2) so the reflection point is non-vacuously pinned to the resistor topology.

## Design Choices & Rationale

- **G = +2 non-inverting (R_g = R_f):** the `2·V_clamp − V_in` law requires exactly gain 2 on
  the clamped node and gain 1 on the raw input — R_g = R_f makes both true simultaneously. Any
  R_f/R_g ≠ 1 moves the fold reflection point and breaks the triangle symmetry.
- **Passive clamp at (+):** 2× 1N4148W per rail (Vth = 2·V_f ≈ 1.4 V) matches the plugin's
  `Vth = 0.28` × 5 V exactly. The clamp has no active elements, so it does not affect loop
  stability — the folder is a standard G=+2 non-inverting stage.
- **True fold vs compression:** the slope **reverses** past threshold (output decreases as input
  increases), producing the dense odd-harmonic Buchla spectrum — distinct from SC/HC, which only
  flatten.
- DRIVE / fold-depth is set by the **THAT2180 VCA + pre-gain stage ahead** of the folder (see
  aux/vca/vca-cell); at high drive the input swings across many ±Vth windows for multiple folds.

## Component Values (POGO-specific)

| Ref (generic) | Part | Package | Value | Notes |
|---|---|---|---|---|
| U_WF | TL072CDT | SOIC-8 (½) | — | WF folder op-amp (non-inverting G=+2) |
| R_clamp | Resistor | 0603 | 10 kΩ | passive-clamp series R (limits diode current at threshold) |
| R_g | Resistor | 0603 | 10 kΩ | folder (−) input R |
| R_f | Resistor | 0603 | 10 kΩ | folder feedback R; **R_g = R_f → G = +2** |
| D_WF_1..2 | 1N4148W | SOD-123 | — | +rail clamp pair (2× series → +1.4 V) |
| D_WF_3..4 | 1N4148W | SOD-123 | — | −rail clamp pair (2× series → −1.4 V) |

## Performance Characteristics

| Parameter | Value | Condition |
|---|---|---|
| Fold threshold (Vth) | ±1.4 V | 2× 1N4148W per rail (= plugin Vth 0.28 × 5 V) |
| Folder gain | G = +2 | R_g = R_f (sets the 2·V_clamp − V_in reflection) |
| Below Vth | slope +1 (linear) | V_out = V_in |
| Above Vth | slope −1 (fold) | V_out = ±2·Vth − V_in |
| Bandwidth | >100 kHz | small-signal |

## Known Gotchas / Assembly Notes

- The folder **must** be G = +2 (R_g = R_f). If R_f/R_g drifts, the reflection point moves and the
  fold is no longer symmetric — the library sim pins this by deriving the +2 from R_g/R_f.
- 1N4148W V_f rises with clamp current, so Vth shifts mildly with drive (≈1.24 V at low drive →
  ≈1.44 V at max drive). This is part of the fold character and is accepted.
- The clamp at (+) is purely passive (no active elements) → no loop-stability impact; the folder
  has the phase margin of a standard G=+2 non-inverting stage.

## Used By

| Block | Instance | Board | Notes |
|---|---|---|---|
| distortion/overview | WF path | — | one of three parallel cells → CD4053 mux |
| block-6 | DIST_BP1_L/R (WF) | Control | BP1 group wavefold cell, both channels |
| block-6 | DIST_BP2_L/R (WF) | Control | BP2 group wavefold cell, both channels |
| block-6 | DIST_BP3_L/R (WF) | Control | BP3 group wavefold cell, both channels |
