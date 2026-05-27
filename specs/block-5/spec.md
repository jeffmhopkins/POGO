# Block 5: LP Filter 1
First 2-pole lowpass filter in the signal chain, with stereo tilt for independent L/R cutoff spread.

DSP source: `plugin/src/dsp/LPFilter.hpp`, `plugin/src/Pogo.cpp` (lines 399–408)

---

## 1. Intent

Block 5 is the first voltage-controlled tonal filter in the chain. It receives the signal from the
pre-LP1 VCA (Block VCA) and applies a 2-pole lowpass response with independent per-channel cutoff
control for stereo spread. At low resonance and high cutoff the block is transparent. As the cutoff
sweeps down, high-frequency content rolls off at 12 dB/oct. At high resonance a peak emerges at the
cutoff frequency; at maximum resonance the filter self-oscillates, producing a sine tone that tracks
1V/oct via the expo converter — making LP1 a playable oscillator.

The LP1_TILT parameter is the key differentiator from LP2 and HP: it creates stereo width by
spreading L and R cutoffs symmetrically in opposite directions. Positive tilt raises the L channel
cutoff while simultaneously lowering the R channel cutoff by the same amount, producing a living
stereo image from a mono source. At center (tilt = 0) both channels run identical cutoffs.

LP1's output feeds Block BP unless the ALT_BP_L/R jacks are patched, in which case the ALT signal
bypasses VCA and LP1 entirely and enters BP directly.

---

## 2. Theoretical Design and Topology

### DSP-to-analog mapping

The DSP model (LPFilter.hpp) implements Andrew Simper's trapezoidal-integrated 2-pole SVF. The
discretization relationship `g = tan(π·f₀/fs)` is the bilinear pre-warp; inverting it yields the
analog prototype cutoff frequency:

```
ω₀_analog = g_m / C      (OTA-C integrator unity-gain frequency)
f₀ = ω₀ / (2π) = g_m / (2π·C)
```

The DSP frequency law `f₀ = f_ref × 2^(cutoffV)` with `f_ref = 632 Hz` maps directly to the
exponential V/oct converter:

```
I_abc = I_ref × exp(V_ctrl / V_T)    → I_abc doubles per +1V
g_m = I_abc / (2·V_T)                → g_m doubles per +1V
ω₀ = g_m / C                        → f₀ doubles per +1V (one octave) ✓
```

At f_ref = 632 Hz with C = 47 nF (C0G):

```
g_m_ref = f_ref × 2π × C = 632 × 2π × 47nF = 186.3 µS
I_abc_ref = g_m_ref × 2·V_T = 186.3µS × 52mV = 9.69 µA
```

### Transfer function (analog prototype)

Second-order lowpass (see `aux/aux-ota-c-svf.md`):

```
H_LP(s) =        ω₀²
          ──────────────────────────
          s² + (ω₀/Q)·s + ω₀²
```

DSP Q law:  `Q = 0.5 × 4000^resParam`  (resParam ∈ [0,1])

```
resParam = 0.0 → Q = 0.50  (overdamped)
resParam = 0.5 → Q ≈ 31.6
resParam = 1.0 → Q ≈ 2000  (near self-oscillation)
```

Hardware Q law:  `Q = 52mV / (I_abc_q × R_in)`  with R_in = 100 kΩ

```
I_abc_q = 0.74 µA → Q = 0.70  (Butterworth, flat passband)
I_abc_q = 0.26 µA → Q = 2.00
I_abc_q → 0       → Q → ∞   (self-oscillation)
```

Note: DSP Q reaches 2000; hardware Q is intentionally limited to ~50 maximum for stability.
This is an accepted deviation — the musical behavior (sweep, resonance peak, self-oscillation
onset) is preserved; the exact maximum Q is a hardware calibration point, not a tonal defect.

### Stereo tilt

From Pogo.cpp lines 403–408:

```cpp
float lp1TiltV = params[LP1_TILT_PARAM].getValue() * 5.f   // [−1,+1] knob → ±5 V/oct
                 + modDest(LP1_TILT_INPUT, LP1_TILT_ATT_PARAM);
float bandL = lp1L.process(vcaOutL, lp1FreqBase + lp1TiltV, lp1Res, fs);
float bandR = lp1R.process(vcaOutR, lp1FreqBase - lp1TiltV, lp1Res, fs);
```

L and R cutoffs diverge symmetrically around the shared base frequency:

```
f_L = 632 Hz × 2^(V_freq + V_tilt)
f_R = 632 Hz × 2^(V_freq − V_tilt)
```

At V_tilt = +1V: f_L is one octave above f_R. At V_tilt = +5V: five-octave spread.

### Hardware tilt implementation

The tilt CV arrives at a shared summing node. An inverting buffer (TL072, G = −1) generates
−V_tilt from +V_tilt. The L expo converter input receives V_freq + V_tilt; the R expo converter
input receives V_freq + (−V_tilt) = V_freq − V_tilt. A trim pot (RV_LP1_TILT_NULL) nulls the
center-detent error to < 5 mV so both channels are matched when the tilt knob is at center.

Both L and R expo converters are separate THAT340 instances? No — one THAT340 (EXPO_LP1) drives
both channels from a single expo output node. The tilt offset is summed into the V_ctrl voltage
before the THAT340 input, as a per-channel summer: the L channel V_ctrl summer adds +V_tilt; the
R channel V_ctrl summer adds −V_tilt. The THAT340 itself is shared (single expo core per block
per `aux/aux-expo-converter.md`).

See `aux/aux-ota-c-svf.md`, `aux/aux-expo-converter.md`, `aux/aux-q-control.md`.

### ALT path bypass

When ALT_BP_L and/or ALT_BP_R are patched, Block BP receives the ALT signal directly. LP1 and
the VCA are bypassed for those channels. LP1 continues to process its input (the VCA output)
but its output is ignored in the signal chain until the ALT jacks are unpatched.

---

## 3. Physical Design

### Component derivations

**Integrator capacitors C1, C2 (per channel, ×2 channels = 4 total):**

```
Target f_ref = 632 Hz at I_abc = 9.69 µA
g_m = 9.69µA / 52mV = 186.3 µS
C = g_m / ω₀_ref = 186.3µS / (2π × 632) = 47.0 nF → use 47 nF C0G/NP0 0603
```

C0G/NP0 mandatory — X7R drifts with temperature and voltage, causing audible pitch drift.

**Input resistors R_IN_SUM (per channel):** 100 kΩ — sets the g_m reference scale and provides
the virtual-ground termination for the SUM_AMP.

**Linearizing resistors R_LIN_A, R_LIN_B (per OTA cell, per channel):** 1 kΩ — extends the OTA
linear range from ±26 mV to ±(26mV + I_abc × 1kΩ/2) ≈ ±31 mV at 10 µA.

**I_ref network R_IREF_A + RV_REF:** 1 MΩ (R_IREF_A, fixed 0603) in series with 500 kΩ (RV_REF, rheostat)
gives R_total 1000 kΩ–1500 kΩ, midpoint 1250 kΩ at pot center → I_ref ≈ 9.6 µA.
Calibration target 9.69 µA requires R_total = 1238 kΩ → RV_REF ≈ 238 kΩ (47.6% of travel).
Covers worst-case component stack (R_IREF_A ±5% + C_int ±5%) within pot range. See aux-expo-converter.md.

**Q control resistors R_Iabc:** 1 MΩ per channel — converts V_ires (from IRES_AMP) to I_abc_q.
At V_ires = 0.74 V: I_abc_q = 0.74 µA → Q = 0.70 (Butterworth).

**Tilt summer resistors (R_TILT_SUM_L, R_TILT_SUM_R, R_TILT_INV):** 100 kΩ each — the tilt
pot wiper (+V_tilt) feeds L expo summer directly. The inverting half of TL072 (G = −1) generates
−V_tilt for the R expo summer. Summing resistors set 1:1 ratio between V_freq and ±V_tilt at
each expo input.

**Trim pot RV_LP1_TILT_NULL:** 10 kΩ Bourns 3224W SMD — nulls the center-detent tilt offset
so both channels match at tilt = 0. Adjust for equal L and R cutoff (matching sine frequency
at self-oscillation).

### Calibration trim pots

| Ref | Value | Purpose | Procedure |
|---|---|---|---|
| RV_REF | 500 kΩ | f_ref calibration | Apply 0V CV; trim until f₀ = 632 Hz; in series with R_IREF_A 750 kΩ |
| RV_1VOCT | 20 kΩ | 1V/oct tracking | Apply +5V CV; trim until f₀ = 632 × 2⁵ = 20.2 kHz |
| RV_QMAX | 100 kΩ | Self-osc onset | Turn RES to max; trim for clean stable self-oscillation at full CW |
| RV_LP1_TILT_NULL | 10 kΩ | Tilt center null | Tilt knob at center; trim until L and R cutoffs match |

### Signal routing

```
Block VCA out L  →  LP1_L SVF (SUM_AMP-A + OTA-A1 + OTA-A2)  →  LP1 out L  →  Block BP in L
Block VCA out R  →  LP1_R SVF (SUM_AMP-B + OTA-B1 + OTA-B2)  →  LP1 out R  →  Block BP in R

ALT_BP_L patched: LP1 out L is bypassed; ALT_BP_L → Block BP in L
ALT_BP_R patched: LP1 out R is bypassed; ALT_BP_R → Block BP in R (normalles to ALT_BP_L if only L patched)
```

Tilt routing:

```
LP1_TILT knob wiper  →  R_TILT_SUM_L (100kΩ) →  L expo summer (+V_tilt addend)
                     →  TL072 G=−1 inv buffer  →  R_TILT_SUM_R (100kΩ) →  R expo summer (−V_tilt addend)
LP1_TILT_INPUT jack + LP1_TILT_ATT attenuverter  →  same tilt bus (sums into V_tilt before distribution)
```

### Board assignment

Audio board. Place LP1_L and LP1_R SVF circuits adjacent to Block VCA outputs. EXPO_LP1
(THAT340) placed centrally between L and R expo summer inputs to equalize trace lengths for
I_abc routing. IC_Q_AB placed between LP1 and LP2 OTA sections (shared Q VCA).

### Power Draw Estimate

- 2× LM13700M (LP1 L/R integrators): ~3 mA × 2 = 6 mA
- 1× IC_Q_AB LM13700M (shared LP1+LP2 Q VCA, counted here): ~3 mA
- 2× OPA1612 (SUM_AMP L/R, dual SOIC-8): 5.5 mA × 2 = 11 mA  (Iq = 2.75 mA/channel × 2 ch/IC)
- 1× TL072CDT (IRES_AMP + tilt inverter): ~2 mA
- 1× THAT340S14-U (EXPO_LP1): ~1 mA
- **+12V: ~23 mA | −12V: ~23 mA**

Note: IC_Q_AB is shared with block-8 (LP2 Q cell B). It is counted once here (block-5).
Block-8 power estimate excludes IC_Q_AB accordingly.

---

## 4. Component Requirements

| Ref | Part | Package | Value | Qty | Board | Block | Function |
|---|---|---|---|---|---|---|---|
| U_OTA_LP1_L | LM13700M | SOIC-16 | — | 1 | audio | block-5 | LP1 L-channel integrators (cells A+B = OTA-A1+OTA-A2) |
| U_OTA_LP1_R | LM13700M | SOIC-16 | — | 1 | audio | block-5 | LP1 R-channel integrators (cells A+B = OTA-B1+OTA-B2) |
| IC_Q_AB | LM13700M | SOIC-16 | — | 1 | audio | block-5/8 | Q VCA shared: cell A = LP1 Q (L+R), cell B = LP2 Q (L+R) |
| U_SUM_LP1_L | OPA1612 | SOIC-8 | — | 1 | audio | block-5 | L-ch: half A = SUM_AMP, half B = LP output buffer; 1.1 nV/√Hz vs TL072 18 nV/√Hz |
| U_SUM_LP1_R | OPA1612 | SOIC-8 | — | 1 | audio | block-5 | R-ch: half A = SUM_AMP, half B = LP output buffer; pin-compatible with TL072CDT |
| U_TILT_INV | TL072CDT | SOIC-8 | — | 1 | audio | block-5 | Half A = tilt inverter (G=−1) for R-channel; half B = IRES_AMP |
| EXPO_LP1 | THAT340S14-U | SOIC-14 | — | 1 | audio | block-5 | Expo V/oct converter; f_ref = 632 Hz; drives LP1 L+R Iabc |
| C1_L, C2_L | C0G cap | 0603 | 47 nF | 2 | audio | block-5 | LP1 L integrator caps (C0G/NP0 mandatory) |
| C1_R, C2_R | C0G cap | 0603 | 47 nF | 2 | audio | block-5 | LP1 R integrator caps (C0G/NP0 mandatory) |
| R_IN_L, R_IN_R | resistor | 0603 | 100 kΩ | 2 | audio | block-5 | SUM_AMP input resistors (signal in) |
| R_FB_L, R_FB_R | resistor | 0603 | 100 kΩ | 2 | audio | block-5 | SUM_AMP feedback / Q feedback input resistors |
| R_LIN_A_L, R_LIN_B_L | resistor | 0603 | 1 kΩ | 2 | audio | block-5 | L-ch OTA linearizing resistors (1 per OTA cell) |
| R_LIN_A_R, R_LIN_B_R | resistor | 0603 | 1 kΩ | 2 | audio | block-5 | R-ch OTA linearizing resistors |
| R_f_L, R_f_R | resistor | 0603 | 100 kΩ | 2 | audio | block-5 | SUM_AMP feedback resistors |
| R_HP_L, R_HP_R | resistor | 0603 | 100 kΩ | 2 | audio | block-5 | HP inverting buffer R_in = R_f (not used for LP output; reserved) |
| R_TILT_SUM_L | resistor | 0603 | 100 kΩ | 1 | audio | block-5 | Tilt summer resistor, L expo input (+V_tilt) |
| R_TILT_SUM_R | resistor | 0603 | 100 kΩ | 1 | audio | block-5 | Tilt summer resistor, R expo input (−V_tilt from inverter) |
| R_TILT_INV_IN | resistor | 0603 | 100 kΩ | 1 | audio | block-5 | Tilt inverter input resistor (R_in of G=−1 buffer) |
| R_TILT_INV_FB | resistor | 0603 | 100 kΩ | 1 | audio | block-5 | Tilt inverter feedback resistor (R_f of G=−1 buffer) |
| R_Iabc_L | resistor | 0603 | 1 MΩ | 1 | audio | block-5 | Q VCA V→I: L-ch V_ires to IC_Q_AB cell-A Iabc |
| R_Iabc_R | resistor | 0603 | 1 MΩ | 1 | audio | block-5 | Q VCA V→I: R-ch V_ires to IC_Q_AB cell-A Iabc |
| R_QBIAS | resistor | 0603 | 100 kΩ | 1 | audio | block-5 | IRES_AMP bias input resistor (sets Butterworth Iabc) |
| R_QINV | resistor | 0603 | 100 kΩ | 1 | audio | block-5 | IRES_AMP resonance CV input resistor |
| R_f_q | resistor | 0603 | 100 kΩ | 1 | audio | block-5 | IRES_AMP feedback resistor |
| R_IREF_A | resistor | 0603 | 1 MΩ | 1 | audio | block-5 | EXPO_LP1 fixed I_ref network R; in series with RV_REF; R_total at midpoint = 1250 kΩ → 9.6 µA |
| R_VOCT | resistor | 0603 | 47 kΩ | 1 | audio | block-5 | EXPO_LP1 V/oct scaling R (1% tolerance); with R_E=1kΩ and RV_1VOCT≈7.5kΩ → 18.0 mV/V 1V/oct ratio |
| R_E | resistor | 0603 | 1 kΩ | 1 | audio | block-5 | EXPO_LP1 emitter degeneration |
| RV_REF | Bourns 3224W | SMD | 500 kΩ | 1 | audio | block-5 | EXPO_LP1 f_ref trim rheostat; in series with R_IREF_A; range ±25% |
| RV_1VOCT | Bourns 3224W | SMD | 20 kΩ | 1 | audio | block-5 | EXPO_LP1 1V/oct tracking trim; ±10% range |
| RV_QMAX | Bourns 3224W | SMD | 100 kΩ | 1 | audio | block-5 | LP1 Q max / Butterworth point trim |
| RV_LP1_TILT_NULL | Bourns 3224W | SMD | 10 kΩ | 1 | audio | block-5 | Tilt center-detent null (L=R at tilt=0) |
| D_IRES | BAT54 | SOT-23 | — | 1 | audio | block-5 | Clamp V_ires ≥ 0 (prevents reverse Iabc) |
| C_IREF | C0G cap | 0603 | 100 nF | 1 | audio | block-5 | EXPO_LP1 I_ref node bypass |
| C_IABC_L, C_IABC_R | C0G cap | 0402 | 10 nF | 2 | audio | block-5 | Integrator OTA Iabc pin bypass (HF noise filter) |
| C_IABC_Q_L, C_IABC_Q_R | C0G cap | 0402 | 10 nF | 2 | audio | block-5 | IC_Q_AB cell-A Iabc pin bypass |
| C_VCC_OTA_L, C_VEE_OTA_L | cap, X7R | 0603 | 100 nF | 2 | audio | block-5 | U_OTA_LP1_L supply decoupling |
| C_VCC_OTA_R, C_VEE_OTA_R | cap, X7R | 0603 | 100 nF | 2 | audio | block-5 | U_OTA_LP1_R supply decoupling |
| C_VCC_SUM_L, C_VEE_SUM_L | cap, X7R | 0603 | 100 nF | 2 | audio | block-5 | U_SUM_LP1_L supply decoupling |
| C_VCC_SUM_R, C_VEE_SUM_R | cap, X7R | 0603 | 100 nF | 2 | audio | block-5 | U_SUM_LP1_R supply decoupling |
| C_VCC_TILT, C_VEE_TILT | cap, X7R | 0603 | 100 nF | 2 | audio | block-5 | U_TILT_INV supply decoupling |
| C_VCC_EXPO, C_VEE_EXPO | cap, X7R | 0603 | 100 nF | 2 | audio | block-5 | EXPO_LP1 THAT340 supply decoupling |
