# aux: Exponential Frequency Converter (V/Oct to Iabc)

**Type:** `filter` · part of the [aux circuit library](../../_LIBRARY.md)
**Composes:** [voct-expo-divider](../voct-expo-divider/spec.md) (the V/oct base divider — delivers V_T·ln2 = 17.92 mV/oct to the expo pair)

> ✅ **Re-verified 2026-05-30** (content rewritten 2026-05-29) against the locked plugin via
> block-5. THAT340 V/oct→Iabc converter; `f0 = f_ref·2^V` (1 V/oct). The per-channel-expo
> decision (one THAT340 per channel for true stereo tilt) is current. Shared by LP1/LP2/HP/BP.
> 🔧 **Change 0020:** added the missing **V/oct base divider** — series R_VOCT (≈49.9k) + a **Vishay TFPT 1k +4110ppm/K tempco** shunt to GND (the THAT340 has NO internal tempco). Without it the base saw full V/oct and railed. Tilt (LP1/BP) sums passively at this node via an equal series R. SPICE: specs/block-5/sim/expo_voct.cir, lp1_tilt_passive.cir.

Design status: [x] draft → [ ] reviewed → [ ] validated on prototype

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
                                               │   SOIC-14             │
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
 +12V ──[R_IREF_A 1MΩ]──[RV_REF 500kΩ rheostat]──► base of Q_ref (THAT340 Q2)
                                                       collector → I_ref node
                                                       emitter → −12V (or GND through R_E)

 V_ctrl ──[R_VOCT 49.9kΩ]──[RV_1VOCT]─────────────► base of Q_expo (THAT340 Q1)
                                                     collector → I_abc output
                                                     emitter → shared with Q_ref emitter

 I_abc = I_ref × exp((V_ctrl − V_ref) / V_T)

 RV_REF (500kΩ rheostat in series with R_IREF_A 1MΩ): trims R_total (1000kΩ–1500kΩ,
   midpoint 1250kΩ at pot center = 250kΩ added → I_ref = 9.6µA nominal).
   All filter block calibration targets (9.21–10.78 µA) fall within 20–80% of pot travel.
 RV_1VOCT (in series with R_VOCT 49.9kΩ + R_E 1kΩ): at RV_1VOCT = 7.5kΩ (37.5% travel),
   total = 55.5kΩ → 1V/oct ratio = 1kΩ/55.5kΩ = 18.0 mV/V = V_T×ln(2) exactly.
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

⚠️ **Corrected (change 0020):** the THAT340 is a plain matched-NPN/PNP array — it does **NOT** have an
internal PTAT/tempco network (the claim above is wrong). The −1/T drift of V_BE/V_T in the V/oct
divider must be compensated by an **external +3300–3500 ppm/°C tempco resistor**; POGO uses a **Vishay
TFPT (+4110 ppm/K)** as the divider's shunt leg (the trimmable V/oct slope absorbs the ~20% TCR excess).
The THAT340's value is its tight **V_BE matching** (low offset between the expo and reference
transistors), not temperature compensation.

## Design Choices & Rationale

### THAT340 vs Discrete Pair + Tempco

A discrete matched NPN pair (e.g. SSM2210) plus a tempco resistor (3300 ppm/°C)
achieves comparable accuracy but requires:
- External tempco resistor mounted near the transistors (thermal coupling problem)
- More board area
- Additional trimming for initial matching

THAT340 solves all three issues on-chip. SOIC-14 footprint is compact.

### One Expo Converter per Filter Block (Shared L/R)

Both channels of each filter block are driven by a single expo converter output node.
This means:
- L and R always track the same frequency — no stereo mistuning from expo drift
- The LP1_TILT and BP_TILT CVs that create stereo spread (from DSP) cannot be
  reproduced by expo mismatch; they require separate expo converters or a summer
  offset circuit per channel
- Phase 3R must decide: shared expo (simplest, mono tracking) vs separate expo
  per channel (enables tilt CV hardware implementation)

RESOLVED 2026-05-29: tilt-bearing blocks (LP1 block-5, BP block-6) use **one expo
converter per channel** (two THAT340 per block, each fed V_freq ± V_tilt) for true
octave-accurate L/R spread. Non-tilt blocks (HP block-7, LP2 block-8) keep a single
shared expo (mono L/R tracking).

### Trim Pots

- R_IREF_A (0603, 1 MΩ) + RV_REF (Bourns 3224W 500 kΩ SMD rheostat): together set I_ref
  to hit the target f_ref at 0V CV. R_IREF_A is the fixed lower bound; RV_REF sweeps total
  from 1000 kΩ (CCW, RV_REF=0) to 1500 kΩ (CW, RV_REF=500 kΩ), midpoint at pot center
  (250 kΩ added) = 1250 kΩ → I_ref ≈ 9.6 µA. All block calibration targets (9.21–10.78 µA)
  fall within 20–80% of pot travel. Covers worst-case tolerance stack (R_IREF_A ±5% +
  integrator cap ±5%) within the trim range for all blocks.
  Previous design (1 MΩ fixed + 100 kΩ series rheostat) gave only +9.1% one-direction range.
- RV_1VOCT (Bourns 3224W 20 kΩ SMD): adjusts the V_ctrl scaling ratio. ±10% range covers
  typical V_T drift and tolerance in R_VOCT; doubled from 10 kΩ for wider trim margin.

Calibration procedure:
1. Apply 0V CV, trim RV_REF until output frequency = f_ref (listen or measure)
2. Apply +5V CV, trim RV_1VOCT until output frequency = f_ref × 2^5
3. Repeat 1–2 two iterations to convergence

## Component Values (POGO-specific)

| Ref (generic) | Part | Package | Value | Notes |
|---|---|---|---|---|
| U_EXPO | THAT340S14-U | SOIC-14 | — | Matched NPN quad; use Q1+Q2 for expo pair |
| R_IREF_A | Resistor | 0603 | 1 MΩ | Fixed lower bound of I_ref network; R_total at midpoint = 1250 kΩ → ~9.6 µA |
| RV_REF | Bourns 3224W | SMD | 500 kΩ | f_ref trim rheostat; R_total range 1000 kΩ–1500 kΩ; all block targets within 20–80% travel |
| R_VOCT | Resistor | 0603 | 49.9 kΩ | V/oct scaling R (change 0020 §A; was 47k); the 1V/oct trim centres the divider on V_T×ln(2)=17.92 mV/oct |
| RV_1VOCT | Bourns 3224W | SMD | 20 kΩ | 1V/oct tracking trim; ±10% range |
| R_E | Resistor | 0603 | 1 kΩ | Emitter degeneration; stabilizes quiescent point |
| C_IREF | Ceramic bypass | 0603 | 100 nF | Bypass on I_ref node to suppress HF on expo output |
| C_VCC, C_VEE | Ceramic bypass | 0603 | 100 nF | Per IC supply pin |

### f_ref Values by Block

| Block | f_ref (DSP) | C_int | Target I_abc at 0V |
|---|---|---|---|
| block-5 LP1 | 632 Hz  | 47 nF  | 9.69 µA  |
| block-8 LP2 | 632 Hz  | 47 nF  | 9.69 µA  |
| block-7 HP  | 632 Hz  | 47 nF  | 9.69 µA  |
| block-6 BP1 | 400 Hz | 68 nF | 8.89 µA |
| block-6 BP2 | 400 Hz | 68 nF | 8.89 µA |
| block-6 BP3 | 400 Hz | 68 nF | 8.89 µA |

I_abc_ref = f_ref × 2π × C_int × 52mV  (C_int varies per block; see block spec)
All blocks target I_abc_ref ≈ 9–11 µA — C_int is chosen to achieve this consistent operating range.

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
- All three BP bands share f_ref = 400 Hz (change 0018); per-band tilt is realized with a
  **per-channel** L/R expo (2 THAT340/band) rather than one shared converter, so the THAT340
  count is higher than one-per-block — see the generated BOM for the exact count.
- Tilt CV (LP1_TILT, BP_TILT) requires per-channel frequency offset; if using a
  single shared expo, tilt must be implemented as a summing offset at the expo
  input before the Q1 base — document this as an open item in Phase 3R

## Used By

| Block | Instance | Board | Notes |
|---|---|---|---|
| block-5 | EXPO_LP1 | Control | f_ref = 632 Hz; drives LP1_L and LP1_R OTA Iabc |
| block-8 | EXPO_LP2 | Control | f_ref = 632 Hz; drives LP2_L and LP2_R OTA Iabc |
| block-7 | EXPO_HP | Control | f_ref = 632 Hz; drives HP_L and HP_R OTA Iabc |
| block-6 | EXPO_BP1 | Control | f_ref = 400 Hz; per-channel L/R expo (true BP tilt) → BP1 OTA Iabc |
| block-6 | EXPO_BP2 | Control | f_ref = 400 Hz; per-channel L/R expo (true BP tilt) → BP2 OTA Iabc |
| block-6 | EXPO_BP3 | Control | f_ref = 400 Hz; per-channel L/R expo (true BP tilt) → BP3 OTA Iabc |
