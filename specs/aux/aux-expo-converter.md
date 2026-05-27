# aux: Exponential Frequency Converter (V/Oct to Iabc)

Design status: [ ] draft → [ ] reviewed → [ ] validated on prototype

## Overview

Converts a linear control voltage (V/oct) to an exponential current (Iabc) suitable
for driving LM13700 OTA integrators in the OTA-C SVF. Implements the DSP relationship
f₀ = f_ref × 2^(V_ctrl) in the analog domain using the THAT340 matched NPN transistor
array for temperature-compensated exponential conversion.

Chosen because:
- THAT340 contains four matched NPN transistors with integrated temperature compensation
  (PTAT current source feedback), eliminating the need for an external tempco resistor
- One THAT340 per filter block drives both L and R channel OTA Iabc pins from a single
  expo core — L/R frequency tracking is guaranteed by using a single converter
- Standard V/oct architecture directly matches the DSP `f₀ = f_ref × 2^(cutoffV)` law
- On-chip matching eliminates the trimming needed with discrete transistor pairs

## Schematic


ASCII fallback:

```
  V_ctrl ──────────────────────────────────────────────────┐
                                                           │
  (freq pot + CV attenuation network; see block spec)      │
                                                           ▼
                                               ┌──────────────────────┐
  RV_1VOCT ──[R_VOCT]──────────────────────►  │   THAT340 (U_EXPO)   │
                                               │   SOIC-8             │
  RV_REF ──[R_REF]──[I_ref source]──────────► │                      │
                                               │  Q1: expo transistor │
                                               │  Q2: tempco sensor   │
                                               │  (internal PTAT)     │
                                               └──────────┬───────────┘
                                                          │
                                              I_abc (exponential current)
                                                          │
                              ┌───────────────────────────┤
                              │                           │
                         Iabc_L                      Iabc_R
                     (to OTA-A, OTA-B             (to OTA-A, OTA-B
                      of left channel SVF)         of right channel SVF)
```

Simplified circuit detail:

```
 +12V ──[R_IREF_A 750kΩ]──[RV_REF 500kΩ rheostat]──► base of Q_ref (THAT340 Q2)
                                                         collector → I_ref node
                                                         emitter → −12V (or GND through R_E)

 V_ctrl ──[R_VOCT]──────────────────────────────────► base of Q_expo (THAT340 Q1)
                                                       collector → I_abc output
                                                       emitter → shared with Q_ref emitter

 I_abc = I_ref × exp((V_ctrl − V_ref) / V_T)

 RV_REF (500kΩ rheostat in series with R_IREF_A 750kΩ): trims R_total (750kΩ–1250kΩ,
   nominal 1000kΩ at pot center = 250kΩ added) to set I_ref and f₀ at 0V CV.
   Range: ±25%; covers ±10.8% worst-case component tolerance with 2.3× margin.
 RV_1VOCT trims R_VOCT to set 1V/oct tracking slope
```

## Transfer Function

### DSP Law (reference)

```
f₀ = f_ref × 2^(V_ctrl)
```

where V_ctrl is in volts and represents octaves above f_ref.

### Analog Exponential Core

The THAT340 transistor pair produces:

```
I_abc = I_ref × exp(V_be_diff / V_T)

V_be_diff = V_ctrl × (R_f / R_VOCT)  (scaled by voltage divider / trim network)
I_T = kT/q = 26mV at 25°C  (PTAT — THAT340 compensates this automatically)
```

For 1V/oct (doubling per volt):

```
exp(ΔV / V_T) = 2^1  when ΔV = 1V
→ ΔV = V_T × ln(2) = 26mV × 0.693 = 18mV per octave

Since V_ctrl steps 1V per octave, the scaling network divides V_ctrl by:
  R_ratio = 18mV / 1V = 1/55.6  (i.e. 18mV reaches the transistor base per 1V at V_ctrl)
```

### Temperature Compensation

THAT340 integrates a PTAT bias network. As temperature rises, V_T increases, which
would reduce g_m and flatten tracking. The PTAT current increases proportionally with
temperature, maintaining constant V_be_diff / V_T across temperature. No external
tempco resistor is needed.

## Design Choices & Rationale

### THAT340 vs Discrete Pair + Tempco

A discrete matched NPN pair (e.g. SSM2210) plus a tempco resistor (3300 ppm/°C)
achieves comparable accuracy but requires:
- External tempco resistor mounted near the transistors (thermal coupling problem)
- More board area
- Additional trimming for initial matching

THAT340 solves all three issues on-chip. SOIC-8 footprint is compact.

### One Expo Converter per Filter Block (Shared L/R)

Both channels of each filter block are driven by a single expo converter output node.
This means:
- L and R always track the same frequency — no stereo mistuning from expo drift
- The LP1_TILT and BP_TILT CVs that create stereo spread (from DSP) cannot be
  reproduced by expo mismatch; they require separate expo converters or a summer
  offset circuit per channel
- Phase 3R must decide: shared expo (simplest, mono tracking) vs separate expo
  per channel (enables tilt CV hardware implementation)

Current spec: shared expo per block, document as Phase 3R open item for tilt.

### Trim Pots

- R_IREF_A (0603, 750 kΩ) + RV_REF (Bourns 3224W 500 kΩ SMD rheostat): together set I_ref
  to hit the target f_ref at 0V CV. R_IREF_A is the fixed lower bound; RV_REF sweeps total
  from 750 kΩ (CCW, RV_REF=0) to 1250 kΩ (CW, RV_REF=500 kΩ), nominal at pot center
  (250 kΩ added) = 1000 kΩ. Gives ±25% adjustment range — sufficient to cover ±10.8%
  worst-case component tolerance (R_IREF_A ±5% + integrator cap ±5%) with 2.3× margin.
  Previous design (1 MΩ fixed + 100 kΩ series rheostat) gave only +9.1% range — insufficient
  to correct downward-shifted f_ref.
- RV_1VOCT (Bourns 3224W 20 kΩ SMD): adjusts the V_ctrl scaling ratio. ±10% range covers
  typical V_T drift and tolerance in R_VOCT; doubled from 10 kΩ for wider trim margin.

Calibration procedure:
1. Apply 0V CV, trim RV_REF until output frequency = f_ref (listen or measure)
2. Apply +5V CV, trim RV_1VOCT until output frequency = f_ref × 2^5
3. Repeat 1–2 two iterations to convergence

## Component Values (POGO-specific)

| Ref (generic) | Part | Package | Value | Notes |
|---|---|---|---|---|
| U_EXPO | THAT340S14-U | SOIC-8 | — | Matched NPN quad; use Q1+Q2 for expo pair |
| R_IREF_A | Resistor | 0603 | 750 kΩ | Fixed lower bound of I_ref network; R_total = R_IREF_A + RV_REF (nom 1000 kΩ → ~12 µA) |
| RV_REF | Bourns 3224W | SMD | 500 kΩ | f_ref trim rheostat; R_total range 750 kΩ–1250 kΩ; ±25% trim range |
| R_VOCT | Resistor | 0603 | 56 kΩ | Nominal V/oct scaling resistor |
| RV_1VOCT | Bourns 3224W | SMD | 20 kΩ | 1V/oct tracking trim; ±10% range |
| R_E | Resistor | 0603 | 1 kΩ | Emitter degeneration; stabilizes quiescent point |
| C_IREF | Ceramic bypass | 0603 | 100 nF | Bypass on I_ref node to suppress HF on expo output |
| C_VCC, C_VEE | Ceramic bypass | 0603 | 100 nF | Per IC supply pin |

### f_ref Values by Block

| Block | f_ref (DSP) | Target Iabc at 0V |
|---|---|---|
| block-5 LP1 | 632 Hz | 9.69 µA |
| block-6 LP2 | 632 Hz | 9.69 µA |
| block-7 HP | 632 Hz | 9.69 µA |
| block-3 BP1 | 200 Hz | 3.06 µA |
| block-3 BP2 | 1500 Hz | 23.0 µA |
| block-3 BP3 | 6000 Hz | 91.9 µA |

Iabc derived from: Iabc = f_ref × 2π × C / (1/(2V_T)) = f_ref × 2π × 47nF × 52mV

For BP blocks the same expo architecture applies; only RV_REF trim setpoint differs.

## Performance Characteristics

| Parameter | Value | Condition |
|---|---|---|
| V/oct tracking | ±1 cent | After trimming, 20°C |
| Tracking temp drift | <3 cents/°C | THAT340 on-chip compensation |
| f₀ range | 20 Hz – 20 kHz | ±5V CV span |
| I_abc range | 0.31 µA – 307 µA | Corresponds to 20 Hz – 20 kHz |
| f_ref accuracy (trimmed) | ±1% | After RV_REF calibration |
| Supply current | <1 mA | THAT340 + resistor network |

## Known Gotchas / Assembly Notes

- THAT340 Q1 and Q2 must be thermally coupled — they are on the same die, so package
  placement matters only for external heat sources; keep away from power resistors
- I_ref node (THAT340 collector of reference transistor) is high-impedance; any
  capacitive coupling here will modulate frequency. Keep trace short and shielded
- R_VOCT is the most sensitive trim-affecting component; use 1% tolerance resistors
  for all components in the V_ctrl signal path
- V_ctrl signal path must be buffered before reaching the expo input; do not load
  the panel pot wiper directly (use a TL072 voltage follower)
- Iabc output traces to OTA Iabc pins should be short; Iabc is a current, so some
  length is tolerable, but keep trace capacitance <10 pF to avoid HF on bias
- One THAT340 per filter block means 5 THAT340 ICs total (LP1, LP2, HP, BP1, BP2/BP3
  could share if f_ref is similar — but BP1/BP2/BP3 have different f_ref values,
  so each needs its own converter; total = 5 expo converters for 5 filter blocks)
- Tilt CV (LP1_TILT, BP_TILT) requires per-channel frequency offset; if using a
  single shared expo, tilt must be implemented as a summing offset at the expo
  input before the Q1 base — document this as an open item in Phase 3R

## Used By

| Block | Instance | Board | Notes |
|---|---|---|---|
| block-5 | EXPO_LP1 | Control | f_ref = 632 Hz; drives LP1_L and LP1_R OTA Iabc |
| block-8 | EXPO_LP2 | Control | f_ref = 632 Hz; drives LP2_L and LP2_R OTA Iabc |
| block-7 | EXPO_HP | Control | f_ref = 632 Hz; drives HP_L and HP_R OTA Iabc |
| block-6 | EXPO_BP1 | Control | f_ref = 200 Hz; drives BP1_L and BP1_R OTA Iabc |
| block-6 | EXPO_BP2 | Control | f_ref = 1500 Hz; drives BP2_L and BP2_R OTA Iabc |
| block-6 | EXPO_BP3 | Control | f_ref = 6000 Hz; drives BP3_L and BP3_R OTA Iabc |
