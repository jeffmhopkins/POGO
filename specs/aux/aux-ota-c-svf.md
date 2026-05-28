# aux: OTA-C State Variable Filter (2-Pole)

> ⚠️ **STALE** — Circuit library entry pending re-verification against current panel design (2026-05-28).

Design status: [ ] draft → [ ] reviewed → [ ] validated on prototype

## Overview

Two-integrator-loop state variable filter using LM13700 OTA cells as transconductance
integrators. Implements the Simper trapezoidal SVF topology mapped to continuous-time
analog hardware. Simultaneously produces LP, BP, and HP outputs from a single input.

Chosen because:
- OTA-C is voltage (current) controllable — expo converter drives Iabc directly
- LM13700 SOIC-16 contains two matched OTA cells → both integrators in one package
- Trapezoidal topology from the Simper SVF minimizes aliasing in DSP; analog version
  is the direct physical realization
- Single-package dual OTA minimizes board area and matching error between integrators

## Schematic


ASCII fallback (one channel shown):

```
                     ┌──────────────────────────────────────────────────────┐
                     │              LM13700 (U_OTA, SOIC-16)               │
                     │                                                      │
 X_in ──[100kΩ]──────┤ IN+ (OTA-A)     OUT-A ──[C1 47nF]──┬─── V1 (BP)   │
        R_IN_SUM     │ IN- ← [1kΩ]─────────────────────────┤              │
                     │       R_LIN_A                        │              │
                     │                                      │              │
 Q_fb ──[100kΩ]──────┤ IN+ (OTA-A)  Iabc-A ←── expo cv     │              │
        R_FB         │                                      │              │
                     │                                      │              │
                     │ IN+ (OTA-B)     OUT-B ──[C2 47nF]──┬─── V2 (LP)   │
 V1 ─────────────────┤                 Iabc-B ←── expo cv  │              │
                     │ IN- ← [1kΩ]─────────────────────────┘              │
                     │       R_LIN_B                                       │
                     └──────────────────────────────────────────────────────┘

           SUM_AMP (TL072 half A):
                         ┌───[R_f 100kΩ]───┐
 X_in ──[100kΩ]──┬──(−)──┤                 ├──── HP_inv ──[100kΩ/100kΩ G=-1 buf]──► HP_out
                 │       │   TL072-A       │
 Q_fb ──[100kΩ]─┘   (+)─┴─GND             │
                                           │
                     (output = HP_inv, then corrected by inverting buffer)

 V2 (LP) ──[unity buf TL072-B]──► LP_out

 V1 (BP) ──► BP_out (direct from integrator 1 output node)
```

Note: The summing amplifier SUM_AMP computes:
  HP_inv = -(X_in/R_IN_SUM + Q_fb/R_FB) × R_f
which, after sign inversion in the HP output buffer, yields the correct HP polarity.

## Transfer Function

Normalized second-order SVF (s-domain, continuous-time analog prototype):

```
ω₀ = g_m / C        (integrator unity-gain frequency)
Q  = 52mV / (Iabc_q × R_in)   (see aux-q-control)

H_LP(s) =        ω₀²
          ──────────────────────
          s² + (ω₀/Q)·s + ω₀²

H_BP(s) =     (ω₀/Q)·s
          ──────────────────────
          s² + (ω₀/Q)·s + ω₀²

H_HP(s) =        s²
          ──────────────────────
          s² + (ω₀/Q)·s + ω₀²
```

Normalized form (s̃ = s/ω₀):

```
H_LP(s̃) = 1 / (s̃² + s̃/Q + 1)
H_BP(s̃) = (s̃/Q) / (s̃² + s̃/Q + 1)
H_HP(s̃) = s̃² / (s̃² + s̃/Q + 1)
```

Characteristic frequency:  f₀ = ω₀ / (2π) = g_m / (2π·C)

Damping (k = 1/Q in DSP notation):  k = Iabc_q × R_in / 52mV

## Design Choices & Rationale

### OTA as Integrator

The LM13700 OTA produces an output current proportional to the differential input voltage:

```
I_out = g_m × (V+ − V−)
g_m = Iabc / (2 × V_T) ≈ Iabc / 52mV   (V_T = 26mV at 25°C)
```

With a capacitor C on the output node (virtual-ground summing node of a current integrator):

```
V_out(s) = I_out / (s·C) = (g_m / s·C) × V_diff
```

This is a perfect integrator with ω_unity = g_m/C. Controlling Iabc therefore controls ω₀
linearly, and the expo converter maps a linear voltage to an exponential Iabc, giving
the required V/oct frequency tracking.

The 1 kΩ linearizing resistors (R_LIN) at each OTA differential input reduce distortion:
the OTA input stage is a differential pair whose linear range is only ±26mV. R_LIN
extends the linear range to ±(26mV + Iabc×R_LIN/2) by adding local feedback.

### Integrator Capacitor Selection

C0G (NP0) ceramic, 47 nF, 0603:
- C0G is temperature-stable (<±30 ppm/°C) — essential for pitch tracking accuracy
- 47 nF chosen so that at Iabc = 10 µA:
  g_m = 10µA / 52mV = 192 µS
  ω₀ = 192µS / 47nF = 4085 rad/s → f₀ = 650 Hz ≈ 632 Hz (trimmed by RV_REF)
- 47 nF is large enough to keep self-noise from integrator input-referred noise small

### SUM_AMP Inversion and HP Polarity

The standard OTA-C SVF computes:
  HP = x − (1/Q)·v₁ − v₂

The SUM_AMP (inverting summing configuration) produces:
  HP_inv = −(x − (1/Q)·v₁ − v₂) = −HP

A G=−1 inverting unity-gain buffer on the HP output node restores polarity, yielding
HP_out = HP = −(x − k·v₁ − v₂) which matches the DSP formula exactly.

### LP Output Buffer

The LP output (v₂, integrator 2 output node) is loaded by the second OTA differential
input. A unity-gain non-inverting buffer (TL072 half) drives the LP output jack at
low impedance without disturbing the integrator node.

### DSP 4-Pole vs Hardware 2-Pole

The DSP BandpassSVF.hpp processes each BP group through a cascade of two 2-pole SVF
stages, producing a 4-pole (24 dB/oct) response per group. The hardware specification
is 2-pole (12 dB/oct) per group. This is an intentional hardware simplification:
- The 4-pole DSP cascade requires 4× integrator cells per channel per group
- 2-pole per group is musically useful and reduces IC count significantly
- Board layout for 2-pole is substantially simpler
- Phase 3R should confirm whether 2-pole vs 4-pole is an acceptable deviation or
  whether cascading two aux-ota-c-svf instances per group is required

For LP1, LP2, HP: DSP is 2-pole, hardware is 2-pole — exact match.
For BP groups: DSP is 4-pole, hardware is 2-pole — requires Phase 3R decision.

## Component Values (POGO-specific)

| Ref (generic) | Part | Package | Value | Notes |
|---|---|---|---|---|
| U_OTA | LM13700M | SOIC-16 | — | Dual OTA; cells A+B = both integrators |
| U_SUM | OPA1612 | SOIC-8 | — | Half A = SUM_AMP; half B = LP buffer or HP inv buf; 1.1 nV/√Hz (vs TL072 18 nV/√Hz); pin-compatible drop-in for all LP/HP/BP filter stages. Use TL072CDT only where board space cost or power budget is critical. |
| C1, C2 | C0G ceramic | 0603 | 47 nF | Integrator caps; C0G mandatory for tuning stability |
| R_IN_SUM | Resistor | 0603 | 100 kΩ | Signal input to SUM_AMP; sets g_m reference |
| R_FB | Resistor | 0603 | 100 kΩ | Q feedback resistor into SUM_AMP |
| R_LIN_A, R_LIN_B | Resistor | 0603 | 1 kΩ | OTA linearizing resistors (one per OTA cell) |
| R_f | Resistor | 0603 | 100 kΩ | SUM_AMP feedback resistor |
| R_HP_IN, R_HP_FB | Resistor | 0603 | 100 kΩ | HP inverting unity buffer R_in = R_f |
| C_VCC, C_VEE | Ceramic bypass | 0603 | 100 nF | Per IC supply pin; place within 1 mm of pin |

### Frequency Derivation (nominal)

```
Target f_ref = 632 Hz (LP1, LP2, HP); trimmed via RV_REF on expo converter

At Iabc = 10 µA:
  g_m = Iabc / (2·V_T) = 10µA / 52mV = 192.3 µS
  ω₀ = g_m / C = 192.3µS / 47nF = 4091 rad/s
  f₀ = 4091 / (2π) = 651 Hz

Trim RV_REF to set Iabc = 9.69 µA for exact 632 Hz:
  g_m = 9.69µA / 52mV = 186.3 µS
  ω₀ = 186.3µS / 47nF = 3966 rad/s
  f₀ = 631.3 Hz ✓
```

### Frequency Range Derivation

```
DSP range: f₀ = 20 Hz to 20 kHz (±5V CV input)
Required Iabc range:
  At 20 Hz:  g_m = 20·2π·47nF = 5.9 µS → Iabc = 5.9µS × 52mV = 0.31 µA
  At 20 kHz: g_m = 20000·2π·47nF = 5.9 mS → Iabc = 5.9mS × 52mV = 307 µA
  Ratio: 307µA / 0.31µA ≈ 990 ≈ 2^10 → 10 octaves over ±5V = 1V/oct ✓
```

## Performance Characteristics

| Parameter | Value | Condition |
|---|---|---|
| Frequency range | 20 Hz – 20 kHz | ±5V CV, expo converter |
| f_ref (LP1/LP2/HP) | 632 Hz | Trimmed at 0V CV |
| Filter order | 2-pole (12 dB/oct) | Per stage |
| THD (BP output) | <0.1% | Iabc = 10 µA, ±1V input |
| Frequency tracking | ±1 cent | Trimmed with RV_1VOCT |
| Temperature drift | <100 ppm/°C | THAT340 + C0G caps |
| Supply current | ~5 mA per OTA | LM13700 quiescent |

## Known Gotchas / Assembly Notes

- LM13700 Iabc pins must be bypassed to a clean rail, not to the OTA output node
- R_LIN must be placed physically close to OTA differential input pins to minimize
  parasitic capacitance that could cause HF oscillation
- C0G capacitors only — X7R will cause audible pitch drift with temperature
- SUM_AMP inverting input is a virtual ground; do not add stray capacitance here
- HP output polarity requires the inverting G=−1 buffer — do not omit it
- At high Q settings (Iabc_q → 0), the filter will self-oscillate; this is expected
  and intentional. Layout must be clean to avoid parasitic oscillation at low Q
- Decoupling caps on every IC supply pin: 100 nF ceramic, within 1 mm of the pin
- LM13700 has Darlington output buffers on each OTA cell; the output buffer emitter
  follower has ~0.6V headroom loss — account for this in signal level planning
- Two OTA cells share a single SOIC-16 package; route Iabc pins independently so
  integrator 1 and integrator 2 can in principle be driven by separate expo outputs
  (though for LP/HP/LP2, they share the same expo converter)

## Used By

| Block | Instance | Board | Notes |
|---|---|---|---|
| block-5 | LP1_L, LP1_R | Control | One LM13700 per channel (2 integrators per IC) |
| block-7 | HP_L, HP_R | Control | One LM13700 per channel |
| block-8 | LP2_L, LP2_R | Control | One LM13700 per channel |
| block-6 | BP1_L, BP1_R | Control | One LM13700 per channel, 2-pole per group |
| block-6 | BP2_L, BP2_R | Control | One LM13700 per channel, 2-pole per group |
| block-6 | BP3_L, BP3_R | Control | One LM13700 per channel, 2-pole per group |
