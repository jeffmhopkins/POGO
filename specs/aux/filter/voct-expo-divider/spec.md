# aux: V/oct Base Divider (V_T·ln2 per octave)

**Type:** `filter` · primitive — used by [expo-converter](../expo-converter/spec.md) (which is used by block-5 / block-7 / block-8 / block-6) · part of the [aux circuit library](../../_LIBRARY.md)

Design status: [x] draft → [ ] reviewed → [ ] validated on prototype

## Overview

The passive input divider that sits **in front of** the exponential converter and scales the
1 V/oct control voltage down to the base voltage the transistor expo pair actually needs:
`V_T·ln2 = 17.92 mV per octave` at room temperature. A BJT (the THAT340 expo transistor)
doubles its collector current for every `V_T·ln2` of base-emitter voltage change. The DSP law
is `f0 = f_ref·2^cutoffV` (1 V/oct, `LPFilter.hpp:20` / `HPFilter.hpp:18`), so 1 V at the CV
input must arrive at the transistor base as exactly `V_T·ln2` for the octave to double the
frequency. This primitive owns that scaling ratio; the [expo-converter](../expo-converter/spec.md)
composes it with the transistor pair that performs the actual exponentiation.

The divider is a series resistor `R_VOCT` from the (buffered) CV into the base node, with a
shunt leg `R_T` to ground. The ratio `R_T/(R_VOCT+R_T)` sets mV/oct. In POGO the shunt leg is a
**tempco resistor** (Vishay TFPT, +4110 ppm/K) so the −1/T drift of `V_T` (the transistor's own
`V_T·ln2` slope shrinks as temperature rises) is cancelled by the divider ratio rising with
temperature — the THAT340 has **no** internal tempco, so the compensation must live here.

Chosen because:
- A passive resistive divider is the simplest way to land 1 V on the ≈18 mV/oct base scale; no
  active stage in the pitch path means no added offset/noise on the most sensitive node.
- Making the shunt leg the tempco resistor folds temperature compensation into the same two
  parts — no separate compensation network.
- A series trim (`RV_1VOCT`) in the `R_VOCT` leg lets the 1 V/oct slope be calibrated to absorb
  `V_T` and resistor tolerance (the trim authority is the design's real V/oct guarantee).

## Schematic

ASCII (the base divider; tilt-summing leg shown dashed for the tilt-bearing blocks):

```
   V_freq (buffered CV, 1 V/oct) ──[R_VOCT 49.9k]──[RV_1VOCT trim]──┬───► expo base (Q1)
                                                                    │
                          ±V_tilt ──[R_TILT (=R_VOCT+RV_mid)]┄┄┄┄┄┄┄┤   (optional 1:1 octave sum)
                                                                    │
                                                          R_T ┌─────┴─────┐
                                              (tempco shunt)  │  1 kΩ      │  Vishay TFPT
                                                  +4110 ppm/K │  to GND    │  (no THAT340 tempco)
                                                              └─────┬─────┘
                                                                    │
                                                                   GND

   Base voltage delivered:  V_base = V_freq · R_T/(R_VOCT_total + R_T)
   Slope target:            V_base/V_freq = V_T·ln2 / 1 V = 17.92 mV/V  (1 octave per volt)
```

The expo transistor's collector current is then `Iabc = I_ref·exp(V_base/V_T)`. With
`V_base = V_T·ln2` per input volt, `Iabc` doubles per volt → `f0` doubles per volt
(`gm = Iabc/2V_T`, corner `f = gm/2πC`, see [gm-c-integrator](../gm-c-integrator/spec.md)).

## Transfer Function

```
Resistive divider:   V_base = V_freq · R_T / (R_VOCT_total + R_T)

Octave-doubling requirement (the BJT law I_c = I_ref·exp(V_be/V_T)):
   I_c doubles  ⇔  ΔV_be = V_T·ln2
   V_T = kT/q = 25.85 mV at 25 °C (298 K)
   V_T·ln2 = 25.85 mV × 0.69315 = 17.92 mV   (per octave)

Slope target (1 V/oct):
   V_base / V_freq = V_T·ln2 / 1 V = 17.92 mV/V

Divider ratio that achieves it:
   R_T / (R_VOCT_total + R_T) = 0.01792
   → with R_T = 1 kΩ:  R_VOCT_total + R_T = 1000/0.01792 = 55.80 kΩ  → R_VOCT_total ≈ 54.8 kΩ
   (POGO: R_VOCT 49.9k + RV_1VOCT trim ≈ 4.9k at mid-travel → ≈54.8 kΩ; trim absorbs V_T spread.)
```

Octave ratios (value-independent — the constant cancels): for input `n` volts,
`Iabc(n)/Iabc(0) = exp(n·V_T·ln2/V_T) = 2^n`. So +1 V → ×2, +2 V → ×4, +3 V → ×8.

### Temperature compensation

`V_T·ln2` is **proportional to absolute temperature** (PTAT): the mV/oct the transistor needs
*grows* +0.33 %/°C. The fixed-ratio divider would deliver a constant mV/oct, so tracking would
drift. Making `R_T` a +3300–3500 ppm/°C tempco part (POGO: Vishay TFPT +4110 ppm/K) raises the
divider ratio with temperature to match — the slope trim absorbs the ~20 % TCR excess. The
THAT340 contributes tight `V_BE` matching, **not** tempco.

## Design Choices & Rationale

- **Passive divider, no buffer in the slope path** — the CV is buffered *before* this divider;
  the divider itself adds no offset/noise to the pitch node. Output drives a high-impedance
  transistor base, so the divider is not loaded.
- **Shunt leg = tempco resistor** — folds V/oct temperature compensation into the divider. The
  THAT340 has no internal PTAT compensation (corrected in change 0020), so without this the base
  saw the full V/oct swing and the expo railed.
- **R_VOCT = 49.9k + RV_1VOCT trim** — 49.9k centers the slope at 17.92 mV/oct with the trim at
  mid-travel; ±10 % trim range covers `V_T` drift + resistor tolerance. (The aux spec table once
  read 47k; the live blocks use 49.9k — change 0020 §A. See Reconciliation note in the
  expo-converter spec.)
- **Tilt sum at the base** — tilt-bearing blocks (block-5 LP1, block-6 BP) sum `±V_tilt` into
  this node through a series R equal to `R_VOCT+RV_mid`, so the offset adds 1:1 in octaves
  (passive sum at the low-Z base node). Non-tilt blocks (HP, LP2) omit it.

## Component Values (POGO-specific)

Representative / generic — a primitive carries no netlist refs.

| Ref (generic) | Part | Package | Value | Notes |
|---|---|---|---|---|
| R_VOCT | Resistor | 0603 | 49.9 kΩ | Series V/oct scaling R (block table: R110/R86); 1% |
| RV_1VOCT | Bourns 3224W | SMD trim | 20 kΩ (≈4.9k mid) | 1 V/oct slope trim; absorbs V_T + tolerance |
| R_T | Vishay TFPT | 0603 | 1 kΩ, +4110 ppm/K | Shunt/tempco leg; sets ratio AND temp-compensates |
| R_TILT | Resistor | 0603 | ≈54.9 kΩ | (tilt blocks only) 1:1 octave tilt sum into base |

### Slope Derivation (representative)

```
V_T·ln2 @ 25 °C = 25.85 mV × 0.69315 = 17.92 mV/oct
Ratio = 17.92 mV / 1 V = 0.01792
R_T = 1 kΩ → R_VOCT_total = R_T/ratio − R_T = 1000/0.01792 − 1000 = 54.80 kΩ
            ≈ 49.9k (R_VOCT) + 4.9k (RV_1VOCT mid)
```

## Performance Characteristics

| Parameter | Value | Condition |
|---|---|---|
| Slope | 17.92 mV/oct | V_T·ln2 @ 25 °C |
| V/oct law | f0 = f_ref·2^V | after expo, 1 V/oct |
| Octave ratio | ×2 per +1 V | value-independent |
| Tempco target | +3300–3500 ppm/°C | met by TFPT +4110 ppm/K shunt |
| Slope trim range | ±10 % | RV_1VOCT 20 kΩ |

## Known Gotchas / Assembly Notes

- Buffer the CV **before** this divider — loading the panel pot wiper directly de-scales it.
- The base node is high-impedance and pitch-critical: short, shielded trace; no stray C.
- The shunt MUST be a tempco resistor (TFPT), not a plain resistor — a fixed shunt leaves the
  V/oct drifting +0.33 %/°C (the THAT340 does not compensate; change 0020 §A).
- Slope is set by the **ratio**, not the absolute resistor values — but keep R_T small (1 kΩ) so
  the divider output impedance stays low at the base.
- Tilt sum (if present) must use a series R equal to the V_freq series so it adds 1:1 in octaves;
  an unequal R mistracks the stereo spread.

## Used By

| User | Instance | Notes |
|---|---|---|
| aux/filter/expo-converter | base divider | Composes this divider in front of the THAT340 expo pair |
| block-5 | EXPO_LP1 base | R_VOCT=49.9k, R_T=TFPT 1k (R229), tilt sum present (R55) |
| block-7 | EXPO_HP base | R110 49.9k, R_E 1k, R229 TFPT 1k; no tilt (shared L/R expo) |
| block-8 | EXPO_LP2 base | R86 49.9k, R_E 1k, R230 TFPT 1k; no tilt |
| block-6 | EXPO_BP1/2/3 base | per-channel L/R expo, tilt sum present |
