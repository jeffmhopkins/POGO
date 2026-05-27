# Block 7: HP Filter
2-pole highpass filter placed between the bandpass section and LP2, for sub-bass removal or resonant low-end sculpting.

DSP source: `plugin/src/dsp/HPFilter.hpp`, `plugin/src/Pogo.cpp` (lines 477–483)

---

## 1. Intent

Block 7 sits immediately after the triple bandpass section (Block BP) and before LP2 (Block 8).
Its primary role is sub-bass management: at its default setting (−3V CV ≈ 80 Hz, Q = 0.5) it
silently removes infrasonic and very low bass content that accumulated through the VCA, LP1, and BP
stages without audibly thinning the sound. Sweeping the cutoff upward brings the highpass knee into
the audible bass range, thinning the low end progressively. At high resonance, a pronounced low-
frequency peak forms at the cutoff frequency; sweeping this into the 80–300 Hz range produces a
resonant bass thump or kick-drum-like low-end emphasis.

At self-oscillation HP generates a sine tone in the low-frequency range, independently controlled
from LP1's self-oscillation, creating dual-oscillator behavior within the filter chain.

Unlike LP1, HP has no stereo tilt parameter — both L and R channels share a single cutoff CV so
the HP response is mono-symmetric. This simplifies the hardware (one expo converter, no tilt
summer or inverting buffer).

---

## 2. Theoretical Design and Topology

### DSP-to-analog mapping

HPFilter.hpp uses the identical Simper trapezoidal SVF state update as LPFilter.hpp, with F_REF
= 632 Hz. The only difference is the output tap:

```cpp
return -(x - k * v1 - v2);   // HP = −(x − k·v1 − v2), negated
```

The negation compensates for the hardware SUM_AMP inversion. The standard SVF produces:

```
HP = x − (1/Q)·v₁ − v₂
```

The SUM_AMP (inverting summing configuration) computes −HP. A G = −1 inverting unity-gain
buffer on the HP output node restores polarity. Two inversions cancel:

```
SUM_AMP output:   HP_inv = −(x − k·v₁ − v₂)
HP output buffer: HP_out = −HP_inv = +(x − k·v₁ − v₂)
DSP return value: -(x - k*v1 - v2) = −(x − k·v₁ − v₂)
```

The DSP negation models the SUM_AMP inversion before the correcting buffer is applied. In practice
the DSP and hardware outputs have the same polarity — no phase discrepancy. See
`aux/aux-ota-c-svf.md` §SUM_AMP Inversion and HP Polarity.

### Transfer function (analog prototype)

Second-order highpass:

```
H_HP(s) =        s²
          ──────────────────────────
          s² + (ω₀/Q)·s + ω₀²
```

With the same exponential cutoff law as LP1/LP2 (`f₀ = 632 Hz × 2^(V_ctrl)`) and Q formula
(`Q = 52mV / (I_abc_q × 100kΩ)`).

Default CV: HP_FREQ_PARAM default = −3V → f₀ = 632 Hz × 2^(−3) = 79 Hz ≈ 80 Hz.

DSP Q law:  `Q = 0.5 × 4000^resParam`  — same exponential law as LP1/LP2.
Hardware Q range: 0.70 (Butterworth, I_abc_q = 0.74 µA) to ~50 (near self-oscillation).

### Frequency derivation at default setting

```
V_ctrl = −3 V
f₀ = 632 Hz × 2^(−3) = 632 / 8 = 79.0 Hz
ω₀ = 2π × 79 = 496 rad/s
```

At this frequency and Q = 0.7 the HP rolls off everything below ~79 Hz at 12 dB/oct. The
rolloff at 20 Hz is −20×log₁₀((79/20)²) ≈ −23.9 dB — infrasonic content is effectively removed.

### No stereo tilt

HP has no tilt parameter. The single EXPO_HP converter drives both L and R OTA Iabc pins in
parallel. Both channels always share the same f₀ and the same Q. This is consistent with the
DSP: hpOutL and hpOutR are computed with the same `hpFreqCv` and `hpResCv` (Pogo.cpp lines
482–483).

### HP output polarity and the double-inversion

```
Signal flow (hardware, one channel):
  x  →  R_IN_SUM (100kΩ)  →  SUM_AMP (−)  →  HP_inv = −(x − k·v₁ − v₂)
  HP_inv  →  G=−1 inv buffer  →  HP_out = +(x − k·v₁ − v₂)
  HP_out  →  Block LP2 input

DSP (software):
  return -(x - k * v1 - v2)   ← sign matches SUM_AMP output, before buffer correction
```

The DSP negation is deliberate: it models the intermediate SUM_AMP state. The hardware G = −1
buffer corrects it. Net output polarity is non-inverted relative to the input in both domains.

See `aux/aux-ota-c-svf.md`, `aux/aux-expo-converter.md`, `aux/aux-q-control.md`.

---

## 3. Physical Design

### Component derivations

**Integrator capacitors C1, C2 (per channel, ×2 channels = 4 total): 47 nF C0G/NP0 0603**

Same derivation as LP1:

```
f_ref = 632 Hz → g_m_ref = 186.3 µS → C = 47.0 nF
```

C0G/NP0 mandatory for pitch-stable self-oscillation.

**Input resistors R_IN_SUM (per channel):** 100 kΩ.

**Linearizing resistors R_LIN_A, R_LIN_B:** 1 kΩ per OTA cell per channel.

**Q control resistor R_Iabc (per channel):** 1 MΩ — converts V_ires to I_abc_q.
At V_ires = 0.74 V: I_abc_q = 0.74 µA → Q = 0.70 (Butterworth).

**HP output buffer resistors R_HP_IN, R_HP_FB:** 100 kΩ each — unity-gain inverting buffer
(R_in = R_f = 100 kΩ). Places the HP output at low impedance with correct polarity for LP2 input.

**EXPO_HP I_ref network R_IREF_A + RV_REF:** R_IREF_A = 1 MΩ (fixed 0603) in series with RV_REF = 500 kΩ
(rheostat), midpoint R_total = 1250 kΩ at pot center → I_ref ≈ 9.6 µA. Calibration target: 9.69 µA
at 0V CV → RV_REF ≈ 238 kΩ (47.6% of travel) for f_ref = 632 Hz.
With V_ctrl = −3V at default: I_abc = 9.69µA × 2^(−3) = 1.21 µA → f₀ ≈ 79 Hz ✓.

### Q control IC sharing

IC_Q_C (LM13700, SOIC-16): cell A = HP Q cell. Cell B is spare (unused by HP; available for
utility functions or future use). The HP Q cell drives both L and R channel I_abc_q pins in
parallel — one IRES_AMP output sets both channels' Q simultaneously.

### Calibration trim pots

| Ref | Value | Purpose | Procedure |
|---|---|---|---|
| RV_REF | 500 kΩ | f_ref calibration | Apply 0V CV; trim until f₀ = 632 Hz; in series with R_IREF_A 1 MΩ; set to ~238 kΩ (47.6% CW) |
| RV_1VOCT | 20 kΩ | 1V/oct tracking | Apply +5V CV; trim until f₀ = 632 × 32 = 20.2 kHz |
| RV_QMAX | 100 kΩ | Self-osc onset | Full CW resonance; trim for clean stable self-oscillation |

### Signal routing

```
Block BP out L  →  HP_L SVF (SUM_AMP + OTA-A1 + OTA-A2 + HP inv buffer)  →  HP out L  →  Block LP2 in L
Block BP out R  →  HP_R SVF (SUM_AMP + OTA-B1 + OTA-B2 + HP inv buffer)  →  HP out R  →  Block LP2 in R

HP_FREQ_PARAM (−5 to +5 V, default −3V) + HP_FREQ_INPUT (attenuated by HP_FREQ_ATT_PARAM)
  →  V_ctrl  →  EXPO_HP  →  I_abc (shared L+R)

HP_RES_PARAM (0 to 1, default 0) + HP_RES_INPUT / 10  →  IRES_AMP  →  I_abc_q (shared L+R)
```

### Board assignment

Audio board. Place HP_L and HP_R SVF circuits between the BP output nodes and the LP2 input nodes.
EXPO_HP (THAT340) placed centrally; IC_Q_C adjacent to HP OTA sections. The HP inv buffer
(G = −1 TL072 half) should be close to the SUM_AMP to minimize trace capacitance on the
HP_inv node.

### Power Draw Estimate

- 2× LM13700M (HP L/R integrators): ~4 mA × 2 = 8 mA  (TI: 4 mA typ per package)
- 1× IC_Q_C LM13700M (HP Q VCA): ~4 mA
- 2× OPA1612 (SUM_AMP L/R, dual SOIC-8): 5.5 mA × 2 = 11 mA  (Iq = 2.75 mA/channel × 2 ch/IC)
- 1× TL072CDT (IRES_AMP): ~3 mA  (TI: 1.4 mA/ch × 2 = 2.8 mA)
- 1× THAT340S14-U (EXPO_HP): ~1 mA
- **+12V: ~27 mA | −12V: ~27 mA**

---

## 4. Component Requirements

| Ref | Part | Package | Value | Qty | Board | Block | Function |
|---|---|---|---|---|---|---|---|
| U_OTA_HP_L | LM13700M | SOIC-16 | — | 1 | audio | block-7 | HP L-channel integrators (cells A+B = OTA-A1+OTA-A2) |
| U_OTA_HP_R | LM13700M | SOIC-16 | — | 1 | audio | block-7 | HP R-channel integrators (cells A+B = OTA-B1+OTA-B2) |
| IC_Q_C | LM13700M | SOIC-16 | — | 1 | audio | block-7 | Q VCA: cell A = HP Q (L+R); cell B = spare |
| U_SUM_HP_L | OPA1612 | SOIC-8 | — | 1 | audio | block-7 | L-ch: half A = SUM_AMP, half B = HP inverting output buffer; 1.1 nV/√Hz |
| U_SUM_HP_R | OPA1612 | SOIC-8 | — | 1 | audio | block-7 | R-ch: half A = SUM_AMP, half B = HP inverting output buffer; pin-compatible with TL072CDT |
| U_IRES_HP | TL072CDT | SOIC-8 | — | 1 | audio | block-7 | Half A = IRES_AMP (Q control); half B = spare / utility |
| EXPO_HP | THAT340S14-U | SOIC-14 | — | 1 | audio | block-7 | Expo V/oct converter; f_ref = 632 Hz; drives HP L+R Iabc |
| C1_L, C2_L | C0G cap | 0603 | 47 nF | 2 | audio | block-7 | HP L integrator caps (C0G/NP0 mandatory) |
| C1_R, C2_R | C0G cap | 0603 | 47 nF | 2 | audio | block-7 | HP R integrator caps (C0G/NP0 mandatory) |
| R_IN_L, R_IN_R | resistor | 0603 | 100 kΩ | 2 | audio | block-7 | SUM_AMP input resistors |
| R_FB_L, R_FB_R | resistor | 0603 | 100 kΩ | 2 | audio | block-7 | SUM_AMP feedback / Q feedback input resistors |
| R_LIN_A_L, R_LIN_B_L | resistor | 0603 | 1 kΩ | 2 | audio | block-7 | L-ch OTA linearizing resistors |
| R_LIN_A_R, R_LIN_B_R | resistor | 0603 | 1 kΩ | 2 | audio | block-7 | R-ch OTA linearizing resistors |
| R_f_L, R_f_R | resistor | 0603 | 100 kΩ | 2 | audio | block-7 | SUM_AMP feedback resistors |
| R_HP_IN_L, R_HP_IN_R | resistor | 0603 | 100 kΩ | 2 | audio | block-7 | HP output inverting buffer R_in (R_in = R_f = 100kΩ) |
| R_HP_FB_L, R_HP_FB_R | resistor | 0603 | 100 kΩ | 2 | audio | block-7 | HP output inverting buffer R_f |
| R_Iabc_L | resistor | 0603 | 1 MΩ | 1 | audio | block-7 | Q VCA V→I: L-ch V_ires to IC_Q_C cell-A Iabc |
| R_Iabc_R | resistor | 0603 | 1 MΩ | 1 | audio | block-7 | Q VCA V→I: R-ch V_ires to IC_Q_C cell-A Iabc |
| R_QBIAS | resistor | 0603 | 100 kΩ | 1 | audio | block-7 | IRES_AMP bias input (sets Butterworth Iabc) |
| R_QINV | resistor | 0603 | 100 kΩ | 1 | audio | block-7 | IRES_AMP resonance CV input resistor |
| R_f_q | resistor | 0603 | 100 kΩ | 1 | audio | block-7 | IRES_AMP feedback resistor |
| R_IREF_A | resistor | 0603 | 1 MΩ | 1 | audio | block-7 | EXPO_HP fixed I_ref network R; in series with RV_REF; R_total at midpoint = 1250 kΩ → 9.6 µA |
| R_VOCT | resistor | 0603 | 47 kΩ | 1 | audio | block-7 | EXPO_HP V/oct scaling R (1% tolerance); with R_E=1kΩ and RV_1VOCT≈7.5kΩ → 18.0 mV/V 1V/oct ratio |
| R_E | resistor | 0603 | 1 kΩ | 1 | audio | block-7 | EXPO_HP emitter degeneration |
| RV_REF | Bourns 3224W | SMD | 500 kΩ | 1 | audio | block-7 | EXPO_HP f_ref trim rheostat; in series with R_IREF_A; range ±25% |
| RV_1VOCT | Bourns 3224W | SMD | 20 kΩ | 1 | audio | block-7 | EXPO_HP 1V/oct tracking trim; ±10% range |
| RV_QMAX | Bourns 3224W | SMD | 100 kΩ | 1 | audio | block-7 | HP Q max / self-oscillation onset trim |
| D_IRES | BAT54 | SOT-23 | — | 1 | audio | block-7 | Clamp V_ires ≥ 0 (prevents reverse Iabc into IC_Q_C) |
| C_IREF | C0G cap | 0603 | 100 nF | 1 | audio | block-7 | EXPO_HP I_ref node bypass |
| C_IABC_L, C_IABC_R | C0G cap | 0402 | 10 nF | 2 | audio | block-7 | Integrator OTA Iabc pin bypass (HF noise filter) |
| C_IABC_Q | C0G cap | 0402 | 10 nF | 1 | audio | block-7 | IC_Q_C cell-A Iabc pin bypass |
| C_VCC_OTA_L, C_VEE_OTA_L | cap, X7R | 0603 | 100 nF | 2 | audio | block-7 | U_OTA_HP_L supply decoupling |
| C_VCC_OTA_R, C_VEE_OTA_R | cap, X7R | 0603 | 100 nF | 2 | audio | block-7 | U_OTA_HP_R supply decoupling |
| C_VCC_SUM_L, C_VEE_SUM_L | cap, X7R | 0603 | 100 nF | 2 | audio | block-7 | U_SUM_HP_L supply decoupling |
| C_VCC_SUM_R, C_VEE_SUM_R | cap, X7R | 0603 | 100 nF | 2 | audio | block-7 | U_SUM_HP_R supply decoupling |
| C_VCC_IRES, C_VEE_IRES | cap, X7R | 0603 | 100 nF | 2 | audio | block-7 | U_IRES_HP supply decoupling |
| C_VCC_EXPO, C_VEE_EXPO | cap, X7R | 0603 | 100 nF | 2 | audio | block-7 | EXPO_HP THAT340 supply decoupling |
