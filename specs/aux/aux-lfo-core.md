# aux: LFO Core (Triangle Oscillator)

> ⚠️ **STALE** — Circuit library entry pending re-verification against current panel design (2026-05-28).

Design status: [ ] draft → [ ] reviewed → [ ] validated on prototype

## Overview

Analog triangle wave oscillator using an integrator + Schmitt trigger (comparator)
feedback loop. Produces a ±5V triangle wave over the range 0.05–20 Hz. Two independent
instances (LFO1, LFO2) are present on the control board. LFO1 has a normalled
connection to MOD_IN; LFO2 outputs to its own panel jack only.

Rate control (FINALIZED 2026-05-29): R_INT is **fixed** and the preset trimpot
attenuates the Schmitt square-wave drive into the integrator (wiper → R_INT), so
f ∝ wiper fraction k. A single 1 MΩ linear trimpot covers the full 0.05–20 Hz (400:1)
range this way — a plain rheostat cannot (a 1 MΩ pot only adds ~1 MΩ of series swing,
far short of the ≈590 kΩ→234 MΩ needed). The earlier "log-pot / THAT340-expo, Phase-3R
TBD" note is superseded: these are set-once presets, so taper law across rotation is
irrelevant and no expo converter is needed. See `specs/block-2/spec.md` §2/§3.

Chosen because:
- Integrator + comparator is the minimal, most reliable triangle oscillator topology
- No startup circuitry needed: positive feedback in the Schmitt trigger ensures the
  oscillator always starts (no stuck-at-zero states)
- Triangle output from the integrator is inherently available; square wave from the
  comparator output is a bonus (could be exposed as a gate/sync output if desired)
- TL072CDT is adequate for the LFO frequency range (20 Hz max); no HF op-amp needed

## Schematic


ASCII fallback (one LFO, component labels for LFO1):

```
 ┌─────────────────────────────────────────────────────────────────────┐
 │                      Triangle Oscillator Core                       │
 │                                                                     │
 │   ┌──── INTEGRATOR (TL072 half A) ────┐                            │
 │   │                                    │                            │
 │   │  [R_INT]    C_INT                  │                            │
 │   │  V_sq ──[──]──┬──(−)──[TL072]──┬──┴── V_tri                   │
 │   │               │   (+)= AGND    │                               │
 │   │               │                │ C_INT = 47nF (or per design)  │
 │   │               │                │                               │
 │   │               └────────────────┘                               │
 │   │                                                                 │
 │   └─────────────────────────────────────────────────────────────────┤
 │                                                                     │
 │   ┌──── SCHMITT TRIGGER (TL072 half B) ────┐                       │
 │   │                                         │                       │
 │   │         R_HYS                           │                       │
 │   │  V_sq ──[──]──┬──(+)──[TL072]──┬── V_sq (comparator output)   │
 │   │               │   (−) = V_tri  │                               │
 │   │               └────────────────┘ (positive feedback → Schmitt) │
 │   │                                                                 │
 │   │  V_sq swings between +Vsat ≈ +11V and −Vsat ≈ −11V           │
 │   │  Hysteresis thresholds: V_H = ±Vsat × R_HYS/(R_HYS + R_out)  │
 │   │  Set R_HYS so thresholds = ±5V for ±5V triangle swing         │
 │   │                                                                 │
 │   └─────────────────────────────────────────────────────────────────┤
 │                                                                     │
 │   Rate control:                                                     │
 │   RATE pot wiper ──────────────────────────────────► R_INT input   │
 │   (sets charge current into C_INT via R_INT)                       │
 │   → slower pot CW rotation → smaller R_INT → faster rate           │
 │                                                                     │
 │   LED:                                                              │
 │   V_tri ──[R_LED_LFO]──► LED_LFO (brightness tracks V_tri level)  │
 │                                                                     │
 └─────────────────────────────────────────────────────────────────────┘

 V_tri ──[R_out 1kΩ]──► LFO1_OUTPUT jack (±5V triangle)
```

## Transfer Function

### Oscillation Frequency

The integrator ramps V_tri at rate:

```
dV_tri/dt = −V_sq / (R_INT × C_INT)

The Schmitt trigger flips when V_tri reaches ±V_H (hysteresis threshold):
  V_H = V_sat × R_HYS / (R_HYS + R_fb_sq)   [voltage divider with positive feedback]

Time for one half-cycle (ramp from −V_H to +V_H):
  T/2 = (2 × V_H × R_INT × C_INT) / V_sat

Oscillation frequency:
  f = 1/T = V_sat / (4 × V_H × R_INT × C_INT)
  
  Since V_H = V_sat × R_HYS / (R_HYS + R_fb_sq):
  f = (R_HYS + R_fb_sq) / (4 × R_HYS × R_INT × C_INT)
  f ≈ 1 / (4 × R_INT × C_INT)   when R_fb_sq >> R_HYS
```

Setting V_H = ±5V for ±5V triangle output:
```
V_H = V_sat × R_HYS / (R_HYS + R_fb_sq) = 5V
With V_sat ≈ 11V:
  R_HYS / (R_HYS + R_fb_sq) = 5/11 = 0.455
  → R_HYS = R_fb_sq × 0.455/0.545 = 0.83 × R_fb_sq
  e.g. R_HYS = 82 kΩ, R_fb_sq = 100 kΩ
```

### DSP Reference (LFO)

```
speedHz = 0.05 × 400^speedParam    speedParam ∈ [0, 1]
f range: 0.05 Hz (min) → 20 Hz (max)   [ratio = 400]

Triangle output:
  V_LFO = ±5V triangle, −5V at phase=0, +5V at phase=0.5
```

### Frequency Range Derivation

```
Required: f_min = 0.05 Hz, f_max = 20 Hz (ratio = 400:1)

f = 1 / (4 × R_INT × C_INT)

At f_max (R_INT = R_min):
  R_min = 1 / (4 × f_max × C_INT) = 1 / (4 × 20 × 47nF) = 266 kΩ

At f_min (R_INT = R_max):
  R_max = 1 / (4 × f_min × C_INT) = 1 / (4 × 0.05 × 47nF) = 106 MΩ

The ratio R_max/R_min = 400 matches the DSP ratio. A single 1 MΩ pot cannot
cover this range linearly. Two approaches:

Option A — Log-taper pot (preferred for simplicity):
  A 1 MΩ log-taper pot provides a 10:1 or 100:1 taper depending on the pot curve.
  End resistors on CW and CCW ends trim the effective range to 266 kΩ – 106 MΩ.
  True 400:1 range may require custom end-resistor tuning.

Option B — THAT340 expo converter:
  Same architecture as aux-expo-converter; V/Hz tracking.
  More accurate exponential taper; harder to calibrate.
  Enables V/oct or V/Hz LFO sync if a SYNC input is added later.
  Phase 3R decision: prefer Option A unless sync is required.
```

## Design Choices & Rationale

### Integrator + Schmitt Trigger (Astable)

This is the minimal triangle oscillator: two op-amp halves (one TL072CDT), plus
R_INT, C_INT, R_HYS, R_fb_sq. The integrator produces the triangle; the Schmitt
trigger produces the control square wave that drives the integrator. The feedback
loop is inherently stable and always starts oscillating.

Alternatives considered:
- XR2206 function generator IC: single IC, but requires PLCC/CDIP package, difficult
  to source reliably in 2026
- Wien bridge oscillator: produces sine, not triangle; requires AGC for amplitude
  stability; more complex
- CMOS timer (555): produces sawtooth, not triangle; extra conversion stage needed

Integrator + comparator is well-understood, reproducible, and easily tunable.

### Two Independent LFOs

LFO1 and LFO2 are separate oscillator circuits on the same board, sharing only the
power supply. This allows:
- Independent RATE pots and CV inputs
- Phase independence (they free-run at separate rates)
- LFO1 normalized to MOD_IN without disturbing LFO2

Two TL072CDT ICs (one per LFO) plus passive networks. Total area budget: two
standard LFO footprints ~10 × 15 mm each on the control board.

### LED Brightness Tracking

The LFO LED uses the triangle wave to modulate brightness:
```
LED current ∝ (V_tri + 5V) / 2   (shifted and scaled to 0–5V range)
R_LED = (V_LED − V_f) / I_LED_nominal
  at V_LED = 5V: R_LED = (5 − 2) / 2mA = 1.5 kΩ → use 1.5 kΩ
```
The LED glows brightest at the positive peak and goes dark at the negative peak,
giving a breathing-lamp effect that shows LFO rate and phase visually.

A half-wave rectifier (1N4148W diode) is placed between V_tri and LED anode so the
LED only drives on the positive half-cycle, producing a pulsing rather than
breathing effect. Phase 3R to choose: breathing (no diode, DC bias resistor) or
pulsing (half-wave rectified). Document as open item.

### Expo Taper vs Log Pot (Phase 3R Open Item)

The DSP rate taper is 0.05 × 400^x — a genuine exponential curve spanning 400:1
frequency ratio. A log-taper pot spans approximately 10:1 to 100:1 depending on the
pot quality. To accurately reproduce the DSP taper:
- Log pot + end resistors: achieves approximately 400:1 with careful end resistor
  selection; acceptable for most applications
- THAT340 expo converter: exact exponential; adds ~1 THAT340 + trim circuit per LFO;
  enables future CV-over-rate (V/Hz or V/oct sync)

Phase 3R must choose. Document both options in block-2/spec.md.

## Component Values (POGO-specific)

| Ref (generic) | Part | Package | Value | Notes |
|---|---|---|---|---|
| U_LFO1 | TL072CDT | SOIC-8 | — | Half A = integrator; half B = Schmitt trigger |
| U_LFO2 | TL072CDT | SOIC-8 | — | Half A = integrator; half B = Schmitt trigger (LFO2) |
| C_INT | C0G ceramic | 0603 | 47 nF | Integrator cap; C0G for frequency stability |
| R_INT | Log-taper pot | 9mm T18 | 1 MΩ | RATE pot; sets oscillation frequency |
| R_CW_END | Resistor | 0603 | 270 kΩ | CW end resistor; limits R_INT min (f_max = 20 Hz) |
| R_CCW_END | Resistor | 0603 | 10 MΩ | CCW end resistor; limits R_INT max (f_min ~0.05 Hz) |
| R_HYS | Resistor | 0603 | 82 kΩ | Schmitt trigger hysteresis; sets ±5V threshold |
| R_fb_sq | Resistor | 0603 | 100 kΩ | Schmitt trigger feedback resistor |
| R_LED_LFO | Resistor | 0603 | 1.5 kΩ | LFO LED current limit |
| LED_LFO | LED | 0603 | warm white | LFO indicator; brightness tracks triangle |
| D_LED | 1N4148W | SOD-123 | — | Optional half-wave rectifier for pulsing LED mode |
| R_out_LFO | Resistor | 0603 | 1 kΩ | Output series protection to LFO jack |
| C_VCC, C_VEE | Ceramic bypass | 0603 | 100 nF | Per TL072 supply pin |

### Component Values Derivation Summary

```
C_INT = 47 nF (C0G)
R_INT_effective range: 266 kΩ (f = 20 Hz) to 106 MΩ (f = 0.05 Hz)
  Achievable with 1 MΩ log pot + R_CW_END = 270 kΩ (in parallel):
    R_min ≈ 270 kΩ || 1 MΩ = 213 kΩ → f_max = 1/(4 × 213k × 47n) = 25 Hz ✓ (a little fast, trimmed OK)
    R_max ≈ 1 MΩ + R_CCW_END = up to full pot + 10 MΩ → f_min ≈ 0.05 Hz ✓

Schmitt trigger thresholds:
  V_H = 5V (target)
  R_HYS = 82 kΩ, R_fb_sq = 100 kΩ
  V_H = 11V × 82/(82+100) = 11 × 0.451 = 4.96V ≈ 5V ✓
```

## Performance Characteristics

| Parameter | Value | Condition |
|---|---|---|
| Frequency range | 0.05 – 20 Hz | Full RATE pot sweep |
| Frequency taper | ~log (anti-log pot) | Log-taper pot + end resistors |
| Output amplitude | ±5V triangle | ±12V supply, V_H calibrated |
| Output waveform | Triangle | Integrator output |
| Frequency stability | ±1% / °C | C0G cap; TL072 offset drift |
| Startup | Always oscillates | Schmitt trigger positive feedback |
| Supply current | ~3 mA per LFO | TL072 × 2 + passives |

## Known Gotchas / Assembly Notes

- C_INT must be C0G (NP0): X7R capacitor frequency coefficient will cause audible
  pitch drift in the LFO rate as the module warms up
- TL072 integrator output can clip if V_H is set incorrectly (if the comparator
  doesn't flip before the integrator rail): verify V_H < V_sat (≈11V) in simulation
  before committing component values
- The integrator (−) input is a virtual ground node; keep R_INT trace short and
  away from digital control lines to avoid noise injection into LFO rate
- Power-on: the Schmitt trigger may power up in either state; the integrator will
  immediately start ramping in whichever direction. This is normal — no startup
  circuit is needed
- LFO1 normalling to MOD_IN: use a PJ301M-12 tip-switching jack at MOD_INPUT;
  LFO1_OUT connects to the NC contact. LFO1 output jack is a separate connection
  on the same TL072 output buffer (a unity-gain buffer may be needed to drive both
  the normalling path and the panel jack simultaneously without loading the oscillator)
- At minimum rate (0.05 Hz), the period is 20 seconds. Any TL072 input bias current
  will cause DC drift on C_INT over this timescale:
  TL072 I_bias ≈ 50 pA; drift = I_bias / C_INT × T = 50pA / 47nF × 20s = 21 mV
  → acceptable (triangle swings ±5V = 10V total; 21 mV < 0.2% error)
- R_CCW_END (10 MΩ): a 10 MΩ 0603 resistor is available but tolerance is typically
  ±5%; this controls the minimum LFO rate accuracy. The minimum rate is not
  critical to calibrate precisely.
- Two LFO oscillators on the same board: layout them far from each other and from
  the LP filter frequency CV inputs to prevent LFO rate injection via stray coupling

## Used By

| Block | Instance | Board | Notes |
|---|---|---|---|
| block-2 | LFO1_OSC | Control | LFO1; normalled to MOD_IN NC contact |
| block-2 | LFO2_OSC | Control | LFO2; output to LFO2_OUTPUT jack only |
| block-3 | LFO1 source | Control | When MOD_IN unpatched, LFO1 feeds mod bus |
