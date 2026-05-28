# Block 8: LP Filter 2
Second independent 2-pole lowpass filter, after HP, for stacked or layered LP filtering with separate CV.

DSP source: `plugin/src/dsp/LPFilter.hpp`, `plugin/src/Pogo.cpp` (lines 485–491)

---

## 1. Intent

Block 8 is the second lowpass filter in the chain and the last filter block before the output
buffers (Block B). It shares the same OTA-C SVF topology as LP1 but operates independently — its
own cutoff CV, resonance, and expo converter — so the two LP filters can be tuned to different
purposes simultaneously.

The most common uses are:

- **Stacked mode:** LP2 cutoff set below LP1 cutoff → combined 24 dB/oct slope, both cutoffs swept
  in parallel (or independently) for a steeper, more dramatic lowpass character.
- **Layered mode:** LP2 cutoff set above LP1 cutoff → dual-knee LP response, creating a compound
  transfer function with two shelf-like transition regions and a flat passband between them.
- **Bright default:** LP2_FREQ_PARAM defaults to +2V (≈ 2.5 kHz), placing LP2 well above LP1's
  default of 0V (632 Hz). In this configuration LP2 is effectively open, contributing only a
  gentle top-end softness, while LP1 dominates the filter sound.
- **Independent resonance:** LP2 resonance adds a second resonant peak at its own cutoff, creating
  a dual-peak spectral character when both LP1 and LP2 have significant Q.

LP2 has no stereo tilt — both L and R channels share one cutoff CV and one Q control, keeping
the hardware simpler and reserving the stereo-spread complexity for LP1 and BP_TILT.

LP2's output feeds Block B (output buffers → MAIN_L/R jacks) directly.

---

## 2. Theoretical Design and Topology

### DSP-to-analog mapping

LP2 uses the same LPFilter struct as LP1. From Pogo.cpp lines 486–491:

```cpp
float lp2FreqCv = params[LP2_FREQ_PARAM].getValue()
                  + modDest(LP2_FREQ_INPUT, LP2_FREQ_ATT_PARAM);
float lp2ResCv  = clamp(params[LP2_RES_PARAM].getValue()
                  + modDest(LP2_RES_INPUT, LP2_RES_ATT_PARAM) / 10.f, 0.f, 1.f);
float outL = lp2L.process(hpOutL, lp2FreqCv, lp2ResCv, fs);
float outR = lp2R.process(hpOutR, lp2FreqCv, lp2ResCv, fs);
```

The same `f₀ = f_ref × 2^(cutoffV)` law with `f_ref = 632 Hz` applies. The default
LP2_FREQ_PARAM = +2V shifts the reference point up by two octaves:

```
f₀_default = 632 Hz × 2^(+2) = 632 × 4 = 2528 Hz ≈ 2.5 kHz
```

This places LP2 above LP1 (632 Hz default) so that in the default patch state the module sounds
like a single LP1 filter — LP2 only becomes audibly active when its cutoff is swept down or when
LP1 is swept above LP2.

### Transfer function (analog prototype)

Identical to LP1 (see `aux/aux-ota-c-svf.md`):

```
H_LP(s) =        ω₀²
          ──────────────────────────
          s² + (ω₀/Q)·s + ω₀²
```

With Q law and Q range identical to LP1/HP:

```
Q = 52mV / (I_abc_q × 100kΩ)
I_abc_q = 0.74 µA → Q = 0.70  (Butterworth, default)
I_abc_q → 0       → Q → ∞    (self-oscillation)
```

**Accepted Q_min deviation:** DSP Q_min = 0.5 at resParam = 0; hardware Q_min = 0.70 (Butterworth).
See LP1 and `aux/aux-q-control.md` §Q_min deviation for full discussion.

### Cascaded response (LP1 + HP + LP2)

When LP2 is stacked below LP1 (LP2_FREQ < LP1_FREQ), the combined response approaches 24 dB/oct.
Cascading two 2-pole stages with independent Q settings produces a 4th-order response that is
not a standard Butterworth or Linkwitz-Riley alignment; the exact shape depends on the ratio of
the two cutoff frequencies and both Q values. This is a feature, not a defect — it produces a
complex, tunable slope character.

When HP is active between LP1 and LP2, the combined LP1 + HP + LP2 response is a bandpass-like
envelope: HP sets a lower cutoff; LP2 sets an upper cutoff; LP1 shapes the overall entry into the
passband. This is a useful configuration for narrow-band spectral shaping downstream of the BP formant section.

### IC_Q_AB sharing with LP1

LP2 Q uses cell B of IC_Q_AB — the same LM13700 SOIC-16 package whose cell A provides LP1 Q.
This means LP1 and LP2 Q cells are on the same die; their I_abc_q signals are independently
driven by separate IRES_AMP circuits. Thermal coupling between cells A and B is negligible at the
operating Iabc (<1 µA, <10 µW per cell). See `aux/aux-q-control.md` §LM13700 Cell Sharing.

### Independent EXPO_LP2 converter

LP2 has its own THAT340 expo converter (EXPO_LP2), independently calibrated from EXPO_LP1. This
is required because LP2's default +2V offset means that the two filters are typically operating
at different points on the expo curve simultaneously. If they shared an expo converter, trimming
RV_REF for one would detune the other.

See `aux/aux-expo-converter.md` for full EXPO topology and calibration procedure.

### No stereo tilt

LP2 has no tilt parameter. Both lp2L and lp2R receive the same `lp2FreqCv` and `lp2ResCv` (Pogo.cpp
lines 490–491). Hardware: EXPO_LP2 drives L and R OTA Iabc pins in parallel from a single expo
output — identical to HP, simpler than LP1.

---

## 3. Physical Design

### Component derivations

**Integrator capacitors C1, C2 (per channel, ×2 channels = 4 total): 47 nF C0G/NP0 0603**

Same derivation as LP1 and HP:

```
f_ref = 632 Hz → I_abc_ref = 9.69 µA → g_m_ref = 186.3 µS → C = 47.0 nF
```

At default +2V CV: I_abc = 9.69µA × 2² = 38.8 µA → f₀ = 2528 Hz ✓. C0G/NP0 mandatory.

**Input resistors, SUM_AMP feedback, linearizing resistors, Q control:** Identical values to LP1
(100 kΩ, 100 kΩ, 1 kΩ, 1 MΩ respectively). See LP1 derivations in block-5/spec.md §3.

**LP2 does not produce an HP output used downstream** (output goes directly to Block B, LP output
only). The SUM_AMP HP_inv output is unused; the G = −1 HP buffer can be omitted or left
unpopulated on LP2. The TL072 half can be repurposed as an additional buffer or left spare.

### Calibration trim pots

| Ref | Value | Purpose | Procedure |
|---|---|---|---|
| RV_REF | 500 kΩ | f_ref calibration | Apply 0V CV; trim until f₀ = 632 Hz; in series with R_IREF_A 1 MΩ; set to ~238 kΩ (47.6% CW) |
| RV_1VOCT | 20 kΩ | 1V/oct tracking | Apply +5V CV; trim until f₀ = 632 × 32 = 20.2 kHz |
| RV_QMAX | 100 kΩ | Self-osc onset | Full CW resonance; trim for stable self-oscillation |

Calibration is independent of LP1. Perform LP2 calibration with LP1 set to a known passing state
(bypass or transparent settings) so LP2 output is observable at MAIN_L/R.

### Signal routing

```
Block HP out L  →  LP2_L SVF (SUM_AMP + OTA-A1 + OTA-A2)  →  LP2 out L  →  Block B in L  →  MAIN_L
Block HP out R  →  LP2_R SVF (SUM_AMP + OTA-B1 + OTA-B2)  →  LP2 out R  →  Block B in R  →  MAIN_R

LP2_FREQ_PARAM (−5 to +5 V, default +2V) + LP2_FREQ_INPUT (attenuated by LP2_FREQ_ATT_PARAM)
  →  V_ctrl  →  EXPO_LP2  →  I_abc (shared L+R)

LP2_RES_PARAM (0 to 1, default 0) + LP2_RES_INPUT / 10  →  IRES_AMP_LP2  →  I_abc_q via IC_Q_AB cell B
```

### Board assignment

Audio board. LP2 should be placed between the HP output nodes and Block B. EXPO_LP2 (THAT340)
is a separate IC from EXPO_LP1, placed adjacent to LP2's V_ctrl summing network.
IC_Q_AB is shared with LP1 and should be placed between the two filter sections so traces to
both cell A (LP1 Q) and cell B (LP2 Q) are of comparable length.

### Power Draw Estimate

- 2× LM13700M (LP2 L/R integrators): ~4 mA × 2 = 8 mA  (TI: 4 mA typ per package)
- (IC_Q_AB shared with block-5 — counted in block-5 power estimate, not here)
- 2× OPA1612 (SUM_AMP L/R, dual SOIC-8): 5.5 mA × 2 = 11 mA  (Iq = 2.75 mA/channel × 2 ch/IC)
- 1× TL072CDT (IRES_AMP): ~3 mA  (TI: 1.4 mA/ch × 2 = 2.8 mA)
- 1× THAT340S14-U (EXPO_LP2): ~1 mA
- **+12V: ~23 mA | −12V: ~23 mA**

---

## 4. Component Requirements

| Ref | Part | Package | Value | Qty | Board | Block | Function |
|---|---|---|---|---|---|---|---|
| U_OTA_LP2_L | LM13700M | SOIC-16 | — | 1 | audio | block-8 | LP2 L-channel integrators (cells A+B = OTA-A1+OTA-A2) |
| U_OTA_LP2_R | LM13700M | SOIC-16 | — | 1 | audio | block-8 | LP2 R-channel integrators (cells A+B = OTA-B1+OTA-B2) |
| IC_Q_AB | LM13700M | SOIC-16 | — | (shared with block-5) | audio | block-5/8 | Q VCA shared: cell A = LP1 Q (L+R), cell B = LP2 Q (L+R) |
| U_SUM_LP2_L | OPA1612 | SOIC-8 | — | 1 | audio | block-8 | L-ch: half A = SUM_AMP, half B = LP output buffer; 1.1 nV/√Hz |
| U_SUM_LP2_R | OPA1612 | SOIC-8 | — | 1 | audio | block-8 | R-ch: half A = SUM_AMP, half B = LP output buffer; pin-compatible with TL072CDT |
| U_IRES_LP2 | TL072CDT | SOIC-8 | — | 1 | audio | block-8 | Half A = IRES_AMP (Q control); half B = spare / utility |
| EXPO_LP2 | THAT340S14-U | SOIC-14 | — | 1 | audio | block-8 | Expo V/oct converter; f_ref = 632 Hz; drives LP2 L+R Iabc; independent of EXPO_LP1 |
| C1_L, C2_L | C0G cap | 0603 | 47 nF | 2 | audio | block-8 | LP2 L integrator caps (C0G/NP0 mandatory) |
| C1_R, C2_R | C0G cap | 0603 | 47 nF | 2 | audio | block-8 | LP2 R integrator caps (C0G/NP0 mandatory) |
| R_IN_L, R_IN_R | resistor | 0603 | 100 kΩ | 2 | audio | block-8 | SUM_AMP input resistors |
| R_FB_L, R_FB_R | resistor | 0603 | 100 kΩ | 2 | audio | block-8 | SUM_AMP feedback / Q feedback input resistors |
| R_LIN_A_L, R_LIN_B_L | resistor | 0603 | 1 kΩ | 2 | audio | block-8 | L-ch OTA linearizing resistors |
| R_LIN_A_R, R_LIN_B_R | resistor | 0603 | 1 kΩ | 2 | audio | block-8 | R-ch OTA linearizing resistors |
| R_f_L, R_f_R | resistor | 0603 | 100 kΩ | 2 | audio | block-8 | SUM_AMP feedback resistors |
| R_Iabc_L | resistor | 0603 | 1 MΩ | 1 | audio | block-8 | Q VCA V→I: L-ch V_ires to IC_Q_AB cell-B Iabc |
| R_Iabc_R | resistor | 0603 | 1 MΩ | 1 | audio | block-8 | Q VCA V→I: R-ch V_ires to IC_Q_AB cell-B Iabc |
| R_QBIAS | resistor | 0603 | 100 kΩ | 1 | audio | block-8 | IRES_AMP_LP2 bias input (sets Butterworth Iabc) |
| R_QINV | resistor | 0603 | 100 kΩ | 1 | audio | block-8 | IRES_AMP_LP2 resonance CV input resistor |
| R_f_q | resistor | 0603 | 100 kΩ | 1 | audio | block-8 | IRES_AMP_LP2 feedback resistor |
| R_IREF_A | resistor | 0603 | 1 MΩ | 1 | audio | block-8 | EXPO_LP2 fixed I_ref network R; in series with RV_REF; R_total at midpoint = 1250 kΩ → 9.6 µA |
| R_VOCT | resistor | 0603 | 47 kΩ | 1 | audio | block-8 | EXPO_LP2 V/oct scaling R (1% tolerance); with R_E=1kΩ and RV_1VOCT≈7.5kΩ → 18.0 mV/V 1V/oct ratio |
| R_E | resistor | 0603 | 1 kΩ | 1 | audio | block-8 | EXPO_LP2 emitter degeneration |
| RV_REF | Bourns 3224W | SMD | 500 kΩ | 1 | audio | block-8 | EXPO_LP2 f_ref trim rheostat; in series with R_IREF_A; range ±25% |
| RV_1VOCT | Bourns 3224W | SMD | 20 kΩ | 1 | audio | block-8 | EXPO_LP2 1V/oct tracking trim; ±10% range |
| RV_QMAX | Bourns 3224W | SMD | 100 kΩ | 1 | audio | block-8 | LP2 Q max / self-oscillation onset trim |
| D_IRES | BAT54 | SOT-23 | — | 1 | audio | block-8 | Clamp V_ires ≥ 0 (prevents reverse Iabc into IC_Q_AB cell B) |
| C_IREF | C0G cap | 0603 | 100 nF | 1 | audio | block-8 | EXPO_LP2 I_ref node bypass |
| C_IABC_L, C_IABC_R | C0G cap | 0402 | 10 nF | 2 | audio | block-8 | Integrator OTA Iabc pin bypass (HF noise filter) |
| C_IABC_Q_L, C_IABC_Q_R | C0G cap | 0402 | 10 nF | 2 | audio | block-8 | IC_Q_AB cell-B Iabc pin bypass |
| C_VCC_OTA_L, C_VEE_OTA_L | cap, X7R | 0603 | 100 nF | 2 | audio | block-8 | U_OTA_LP2_L supply decoupling |
| C_VCC_OTA_R, C_VEE_OTA_R | cap, X7R | 0603 | 100 nF | 2 | audio | block-8 | U_OTA_LP2_R supply decoupling |
| C_VCC_SUM_L, C_VEE_SUM_L | cap, X7R | 0603 | 100 nF | 2 | audio | block-8 | U_SUM_LP2_L supply decoupling |
| C_VCC_SUM_R, C_VEE_SUM_R | cap, X7R | 0603 | 100 nF | 2 | audio | block-8 | U_SUM_LP2_R supply decoupling |
| C_VCC_IRES, C_VEE_IRES | cap, X7R | 0603 | 100 nF | 2 | audio | block-8 | U_IRES_LP2 supply decoupling |
| C_VCC_EXPO, C_VEE_EXPO | cap, X7R | 0603 | 100 nF | 2 | audio | block-8 | EXPO_LP2 THAT340 supply decoupling |
