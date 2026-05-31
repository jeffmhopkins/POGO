# aux: LED Breathing (NPN level-shift current source)

**Type:** `led` · part of the [aux circuit library](../../_LIBRARY.md)

Design status: [x] draft → [ ] reviewed → [ ] validated on prototype

## Overview

A **whole-cycle "breathing" LED driver** for a bipolar modulation signal. A single NPN
(MMBT3904) acts as a voltage-controlled current source: the bipolar triangle `V_tri` (±5 V) is
level-shifted onto the transistor base by a 3-resistor superposition network so the base sits
*below* the conduction knee at `V_tri = −5 V` (LED dark) and rises through the active region
toward `V_tri = +5 V` (LED bright). The LED is fed from +12 V through the transistor; the
emitter resistor `R_E` sets the full-scale current.

This realizes the plugin's LFO LED brightness law, which maps the whole ±5 V triangle to
0…1 brightness: `brightness = (lfoRaw + 1)·0.5` with `lfoRaw = V_tri/5` ⇒ `(V_tri + 5)/10`.
The level-shift converts the bipolar `V_tri` into a unipolar base voltage so the LED brightens
across the *entire* cycle (no half-wave gap), giving the smooth breathing indication.

> **[NV] — Vbe.** The transistor `Vbe` knee (≈0.6–0.7 V, temp-dependent) and finite β are
> unmeasured device constants. The sims pin the **base voltage** (from the modeled R19/R20/R21
> superposition — non-vacuous) and check the **I_LED range/shape** (cutoff near `V_tri = −5`,
> monotone rising to ~3 mA at `V_tri = +5`), NOT the absolute mA at any point.

## Schematic

```
   +12V ──► LED_anode ──► LED_cathode ──► Q collector
                                          Q emitter ──[ R_E 470Ω ]──► GND
   base level-shift (3-resistor superposition meeting at the base node):
     V_tri ──[ R_BTRI 51k ]──┐
     +12V  ──[ R_BBIAS 68k ]─┼──► Q base
     GND   ──[ R_BGND 10k ]──┘

   V_tri  −5 / 0 / +5 V  →  V_base  0.585 / 1.31 / 2.04 V  →  I_LED  ≈ 0 / 1.4 / 3.0 mA
```

## Transfer Function

```
Base voltage by superposition (base node ≈ open — high-β draws negligible base current):
  V_base = (V_tri/R_BTRI + 12/R_BBIAS) / (1/R_BTRI + 1/R_BBIAS + 1/R_BGND)
  with R_BTRI=51k, R_BBIAS=68k, R_BGND=10k → SumG = 134.31 µS:
    V_tri = −5 →  78.43 µA / SumG = 0.584 V   (< Vbe ⇒ Q cut off ⇒ LED dark)
    V_tri =  0 → 176.47 µA / SumG = 1.314 V
    V_tri = +5 → 274.51 µA / SumG = 2.044 V

LED current (emitter follower into R_E):
  I_LED ≈ I_E = max(0, V_base − Vbe)/R_E,  R_E = 470Ω,  Vbe ≈ 0.6 V  [NV]
    V_tri = −5 → 0 mA      (cutoff)
    V_tri =  0 → ~1.5 mA
    V_tri = +5 → ~3.1 mA
```

`V_base ≈ 0.146·V_tri + 1.314` — a linear level-shift of the triangle. The base voltage emerges
from the modeled R19/R20/R21 ratios (non-vacuous: change any of the three and V_base moves). The
absolute I_LED is `[NV]` on Vbe, so the deck checks the cutoff toe, the ~3 mA peak (loose), and
that the current rises **monotonically** over the cycle — the defining shape of the breathing law.

## Design Choices & Rationale

- **3-resistor superposition, not a single bias R:** the +12 V leg (R_BBIAS) lifts the base so
  the *whole* bipolar triangle lands in the active region above cutoff; the GND leg (R_BGND)
  pins the divider so V_base tracks V_tri with a gentle ~0.15 slope. The dark-point lands just
  below Vbe at `V_tri = −5`, so the LED visibly extinguishes at the trough.
- **NPN current source, not direct LED drive:** the transistor isolates the high-Z bias node
  from the LED, and R_E sets a clean current rather than relying on the LED's own I–V curve.
  Full-scale `I_E = (V_base,max − Vbe)/R_E ≈ (2.04 − 0.6)/470 ≈ 3 mA` — a comfortable LED level.
- **R_E = 470 Ω sets full-scale current:** lower R_E → brighter peak; chosen for ~3 mA. (In
  POGO this reuses the former half-wave limiter R9/R10, now repurposed as the emitter R.)
- **Few-percent rail tolerance only nudges the dark-point** (via the +12 V bias leg) and is
  cosmetically invisible.

## Component Values (POGO-specific)

| Ref (generic) | Part | Package | Value | Notes |
|---|---|---|---|---|
| Q | MMBT3904 | SOT-23 | — | NPN current source / emitter follower |
| R_BTRI | Resistor | 0603 | 51 kΩ | V_tri → base (superposition leg) |
| R_BBIAS | Resistor | 0603 | 68 kΩ | +12 V → base (lifts whole cycle above cutoff) |
| R_BGND | Resistor | 0603 | 10 kΩ | GND → base (pins the divider) |
| R_E | Resistor | 0603 | 470 Ω | Emitter R; sets full-scale ~3 mA |
| D_LED | LED 3 mm | THT | — | Indicator; fed from +12 V through Q |

(Generic representative values; live block-2 refs: R19/R20/R21 (base network), R9/R10 (R_E).)

## Performance Characteristics

| Parameter | Value | Condition |
|---|---|---|
| Base level-shift | V_base ≈ 0.146·V_tri + 1.31 | superposition of R19/R20/R21 |
| Dark-point | V_tri ≈ −5 V | V_base 0.584 < Vbe ⇒ Q off |
| Full-scale current | ~3 mA | V_tri = +5 V; R_E = 470 Ω [NV] |
| Current shape | monotone rising 0→~3 mA | whole-cycle breathing |
| Transistor dissipation | ≈26 mW | well within SOT-23 |

## Known Gotchas / Assembly Notes

- The base node is *lightly* loaded by base current (~I_E/β); for high-β MMBT3904 this is
  negligible vs the ~tens-of-µA divider currents, so the unloaded superposition is the bias
  point. Don't add a large load at the base.
- The dark-point depends on the +12 V leg; if the rail sags the trough may not fully extinguish
  — cosmetic only.
- The exact knee where the LED first lights is the [NV] Vbe; do not calibrate brightness to an
  absolute mA — the law is the *shape* `(V_tri+5)/10`, not a current target.

## Used By

| Block | Instance | Board | Notes |
|---|---|---|---|
| block-2 | LFO1 LED | utility | Whole-cycle breathing indicator for LFO1 triangle |
| block-2 | LFO2 LED | utility | Whole-cycle breathing indicator for LFO2 triangle |

Plugin law: `plugin/src/Pogo.cpp:508-509` — `lights[LFO1/2].setBrightness((lfoRaw+1)*0.5)`,
`lfoRaw = V_tri/5` ⇒ brightness `= (V_tri + 5)/10` over the whole cycle.
