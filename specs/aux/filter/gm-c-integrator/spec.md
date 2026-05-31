# aux: gm-C Integrator (OTA Transconductor + Cap)

**Type:** `filter` · primitive — used by [ota-c-svf](../ota-c-svf/spec.md) (which is used by block-5 / block-7 / block-8 / block-6) · part of the [aux circuit library](../../_LIBRARY.md)

Design status: [x] draft → [ ] reviewed → [ ] validated on prototype

## Overview

The atomic first-order section of the OTA-C state-variable filter: a single
transconductor (OTA cell) driving an integrating capacitor. The OTA converts a
differential input voltage to an output current `I = gm·V_diff`; that current charges a
cap `C` on the output node, producing a continuous-time integrator whose unity-gain
frequency — and equivalently the corner of the 1st-order low-pass formed when the node is
fed back — is `f = gm/(2π·C)`.

This primitive owns the canonical `f = gm/(2π·C)` law. The composed
[ota-c-svf](../ota-c-svf/spec.md) wires **two** of these integrators into a
two-integrator loop; the SVF's `ω₀ = gm/C` is just this primitive's corner read at each
of its two integrator nodes.

Chosen because:
- An OTA's `I_out = gm·V_diff` makes `gm` (hence the corner) **current-controllable** —
  the expo converter drives `Iabc`, and `gm = Iabc/(2·V_T)`, giving 1 V/oct frequency
  control directly.
- The LM13700 (SOIC-16) packs two matched OTA cells, so a 2-integrator SVF fits one IC
  with well-matched `gm` between the two sections.
- C0G integrating caps make the corner temperature-stable, which the OTA's `gm`
  (temperature-dependent through `V_T`) is not — pitch stability comes from the cap.

## Schematic

ASCII (one gm-C integrator, wired as a 1st-order LP by feeding the node back to IN−):

```
                 Iabc (from expo converter; sets gm = Iabc/(2·V_T))
                  │
                  ▼
  V_in ──[R_LIN 1kΩ]──┤IN+  ┌──────────┐
                       │     │   OTA    │ I_out = gm·(V+ − V−)
                       │     │ (LM13700 │
            ┌──────────┤IN−  │  cell)   ├───┬──────► V_out  (integrator node)
            │          └─────└──────────┘   │
            │                               │
            └───────────────────────────────┤   (V_out fed back to IN− → 1st-order LP)
                                            │
                                       [C 47nF]
                                            │
                                           GND
```

- As a **pure integrator** (open loop, IN− at AC ground): `V_out = (gm/sC)·V_in` —
  unity-gain (0 dB) crossover at `f = gm/(2πC)`.
- As a **1st-order LP** (V_out fed to IN−, as drawn): `H(s) = 1/(1 + s·C/gm)` — −3 dB
  corner at the same `f = gm/(2πC)`. The SVF uses both forms (one integrator per state
  variable, closed by the loop).

`R_LIN` (1 kΩ) is the OTA input linearizing resistor — it widens the OTA's ±26 mV
differential linear range; it does **not** enter the corner law.

## Transfer Function

```
OTA:            I_out = gm · (V+ − V−),     gm = Iabc / (2·V_T) ≈ Iabc / 52mV   (V_T = 26mV @25°C)

Integrator:     V_out(s) = I_out / (s·C) = (gm / sC) · V_diff
                → unity-gain frequency  ω_unity = gm/C      i.e.  f = gm/(2π·C)

1st-order LP    H(s) = 1 / (1 + s·C/gm)
(node fed back):  −3 dB corner  f = gm/(2π·C)
                  phase = −90° at the integrator unity-gain frequency (−45° at the LP corner)
```

`f = gm/(2π·C)` is the corner. It is set by **two independent quantities** — `gm` (a
property of the transconductor / `Iabc`) and `C` (the cap). Changing either moves the
corner; that independence is what makes the law non-vacuous (see the sim note).

## Design Choices & Rationale

- **OTA-C over RC**: an RC corner is `1/(2πRC)` — fixed by a resistor. Replacing `1/R`
  with `gm` makes the corner electronically tunable over the full audio decade band via
  `Iabc`, which is the whole point of a voltage-controlled filter.
- **C = 47 nF, C0G**: representative POGO value for the LP/HP/LP2 blocks (block-6 BP uses
  68 nF). C0G (NP0) has <±30 ppm/°C drift — the cap must be stable because `gm` already
  drifts with temperature through `V_T`; the cap is the anchor for pitch tracking.
- **gm range**: `gm = Iabc/(2·V_T)`. POGO's `Iabc` spans ≈0.31 µA–307 µA (≈10 octaves),
  giving `gm` ≈ 6 µS–5.9 mS and, with C = 47 nF, `f` ≈ 20 Hz–20 kHz — exactly the DSP
  `f0 = f_ref·2^cutoffV`, ±5 V CV span.
- **R_LIN = 1 kΩ**: linearizes the OTA diff-pair (±26 mV → wider) without affecting the
  corner. Distortion concern, not a frequency concern.

## Component Values (POGO-specific)

| Ref (generic) | Part | Package | Value | Notes |
|---|---|---|---|---|
| OTA cell | LM13700M (one of two cells) | SOIC-16 | — | `gm = Iabc/(2·V_T)`; Iabc from expo converter |
| C | C0G ceramic | 0603 | 47 nF | Integrating cap; C0G mandatory for tuning stability (block-6 uses 68 nF) |
| R_LIN | Resistor | 0603 | 1 kΩ | OTA input linearizing resistor; not in the corner law |
| C_byp | Ceramic | 0603 | 100 nF | Iabc/supply bypass to a clean rail (not to the integrator node) |

### Corner Derivation (representative)

```
At Iabc = 10 µA, C = 47 nF:
  gm = 10µA / 52mV = 192.3 µS
  f  = gm/(2π·C) = 192.3µS / (2π·47nF) = 651 Hz   (POGO trims Iabc to 9.69µA → 632 Hz)
```

## Performance Characteristics

| Parameter | Value | Condition |
|---|---|---|
| Corner law | `f = gm/(2π·C)` | continuous-time |
| Integrator phase | −90° | at unity-gain frequency |
| Corner tuning range | 20 Hz – 20 kHz | Iabc 0.31 µA–307 µA, C = 47 nF |
| Temperature drift | C0G <30 ppm/°C | cap; gm drifts via V_T (compensated upstream by expo tempco) |

## Known Gotchas / Assembly Notes

- The corner moves with **either** `gm` or `C`; never derive one of the two from the
  target frequency when validating, or the check becomes self-fulfilling.
- Iabc bypass goes to a clean rail, **not** to the integrator output node (the node is the
  state variable; loading it shifts the corner / adds loss).
- `gm` is temperature-dependent (`V_T`); the integrator corner therefore drifts unless the
  expo converter's tempco compensates upstream — see [expo-converter](../expo-converter/spec.md).
- R_LIN must sit close to the OTA input pins to avoid parasitic-C HF oscillation.

## Used By

| User | Instance | Notes |
|---|---|---|
| aux/filter/ota-c-svf | both integrators | Composes 2× gm-C integrator into the 2-integrator loop; `ω₀ = gm/C` |
| block-5 | LP1_L / LP1_R | C = 47 nF, f_ref = 632 Hz |
| block-7 | HP_L / HP_R | C = 47 nF, f_ref = 632 Hz |
| block-8 | LP2_L / LP2_R | C = 47 nF, f_ref = 632 Hz |
| block-6 | BP1/2/3 L/R | C = 68 nF, f_ref = 400 Hz |
