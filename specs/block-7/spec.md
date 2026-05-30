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

> ✅ **Re-verified 2026-05-30** against the locked plugin (change 0018). Topology matches LP1
> (2-pole Simper SVF, V/oct, self-oscillation). **Polarity bug fixed:** the HP output is now a
> unity non-inverting follower on the SUM_AMP node (was a spurious G=−1 inverting buffer that
> phase-flipped HP_OUT vs the plugin). **Q collapsed to one LM13700** (cell A=L, cell B=R) per
> the LP1/LP2 precedent (was two ICs).

### DSP-to-analog mapping

HPFilter.hpp uses the identical Simper trapezoidal SVF state update as LPFilter.hpp, with F_REF
= 632 Hz. The only difference is the output tap:

```cpp
return -(x - k * v1 - v2);   // HP = −(x − k·v1 − v2), negated
```

The negation is deliberate: the hardware SUM_AMP (inverting summing configuration) computes
`HP_inv = −(x − k·v₁ − v₂)` at its **output node**, and the plugin pre-negates so its return value
**equals that node directly**. The intended HP tap is therefore the SUM_AMP output node itself —
taken through a **unity non-inverting follower** (OPA1612 half B) purely for drive isolation, with
**no further inversion**:

```
SUM_AMP output node:   HP_inv = −(x − k·v₁ − v₂)
HP output follower:    HP_out = HP_inv          (G = +1, unity)
DSP return value:      -(x - k*v1 - v2)         = HP_inv   ✓ same polarity
```

This mirrors LP1 exactly: there `LPFilter` returns un-negated `+v2` and the hardware uses a unity
follower on v2. (An earlier HP revision used a G=−1 *inverting* buffer here, which double-inverted
and made HP_OUT phase-opposite the plugin — corrected in change 0018; R100–R103 removed.) See
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

**Accepted Q_min deviation:** DSP Q_min = 0.5 at resParam = 0; hardware Q_min = 0.70
(Butterworth). Hardware cannot produce Q < 0.70 without LM13700 low-Iabc nonlinearity.
Practical effect: absent slightly-overdamped region below 0.707; CCW-stop position yields
maximally flat response. Audibly negligible; accepted.

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

### HP output polarity

```
Signal flow (hardware, one channel):
  x  →  R_IN_SUM (100kΩ)  →  SUM_AMP (−)  →  HP_inv = −(x − k·v₁ − v₂)   ← HP tap node
  HP_inv  →  unity follower (G=+1)  →  HP_out = HP_inv = −(x − k·v₁ − v₂)
  HP_out  →  Block LP2 input

DSP (software):
  return -(x - k * v1 - v2)   = HP_inv   ← identical to the hardware HP tap node ✓
```

The plugin pre-negates so its return equals the SUM_AMP output node; the unity follower passes
that node through unchanged → hardware HP_OUT matches the plugin exactly. (No second inversion —
the earlier G=−1 buffer was a double-inversion bug, fixed in change 0018.)

See `aux/aux-ota-c-svf.md`, `aux/aux-expo-converter.md`, `aux/aux-q-control.md`.

---

## 3. Physical Design

> ✅ **Re-verified 2026-05-30** against the locked plugin (change 0018). Values verified vs
> the §2 model; HP output buffer corrected to a unity follower (R100–R103 removed); HP Q
> collapsed to one LM13700 (U51 cell A=L, cell B=R; U52 removed); RV18 (Q_max) = 100 kΩ.

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

**HP output buffer:** unity-gain **non-inverting follower** (OPA1612 half B; out→in−, SUM_AMP
node→in+). No resistors — it isolates the SUM_AMP node from the LP2 input load without changing
polarity (the SUM_AMP node is already the correct HP tap; see §2). *(Was an inverting buffer with
R_HP_IN/R_HP_FB = 100 kΩ — removed in change 0018; that double-inverted vs the plugin.)*

**EXPO_HP I_ref network R_IREF_A + RV_REF:** R_IREF_A = 1 MΩ (fixed 0603) in series with RV_REF = 500 kΩ
(rheostat), midpoint R_total = 1250 kΩ at pot center → I_ref ≈ 9.6 µA. Calibration target: 9.69 µA
at 0V CV → RV_REF ≈ 238 kΩ (47.6% of travel) for f_ref = 632 Hz.
With V_ctrl = −3V at default: I_abc = 9.69µA × 2^(−3) = 1.21 µA → f₀ ≈ 79 Hz ✓.

### Q control IC sharing

One LM13700 (U51, SOIC-16) provides both channels' Q: **cell A = L Q, cell B = R Q**. Since HP
resonance is mono (same resParam both channels), one IRES_AMP output (V_ires) drives both cells'
I_abc_q in parallel (via R104/R105) — both channels' Q track together. *(Change 0018: was two
LM13700s, U51/U52, each using only cell A; collapsed to one IC matching the LP1/LP2 shared-Q
precedent — U52 removed.)*

**No spare Q cell:** both cells of U51 are now active (cell A = L Q, cell B = R Q), so no
spare-cell termination is needed (change 0018). The only unused U51 pins are the Darlington
buffer / diode-bias pins (per the OTA-C SVF convention), left as no-connects.

### Calibration trim pots

| Ref | Value | Purpose | Procedure |
|---|---|---|---|
| RV_REF | 500 kΩ | f_ref calibration | Apply 0V CV; trim until f₀ = 632 Hz; in series with R_IREF_A 1 MΩ; set to ~238 kΩ (47.6% CW) |
| RV_1VOCT | 20 kΩ | 1V/oct tracking | Apply +5V CV; trim until f₀ = 632 × 32 = 20.2 kHz |
| RV_QMAX | 100 kΩ | Self-osc onset | Full CW resonance; trim for clean stable self-oscillation |

### Signal routing

```
Block BP out L  →  HP_L SVF (SUM_AMP + OTA1 + OTA2 + HP follower)  →  HP out L  →  Block LP2 in L
Block BP out R  →  HP_R SVF (SUM_AMP + OTA1 + OTA2 + HP follower)  →  HP out R  →  Block LP2 in R

HP_FREQ_PARAM (−5 to +5 V, default −3V) + HP_FREQ_INPUT (attenuated by HP_FREQ_ATT_PARAM)
  →  V_ctrl  →  EXPO_HP  →  I_abc (shared L+R)

HP_RES_PARAM (0 to 1, default 0) + HP_RES_INPUT / 10  →  IRES_AMP  →  I_abc_q (shared L+R)
```

### Board assignment

Audio board. Place HP_L and HP_R SVF circuits between the BP output nodes and the LP2 input nodes.
EXPO_HP (THAT340) placed centrally; U51 (Q) adjacent to HP OTA sections. The HP follower
(G = +1 unity, OPA1612 half B) should be close to the SUM_AMP to minimize trace capacitance on
the HP_inv node.

### Power Draw Estimate

- 2× LM13700M (HP L/R integrators): ~4 mA × 2 = 8 mA  (TI: 4 mA typ per package)
- 1× IC_Q_C LM13700M (HP Q VCA): ~4 mA
- 2× OPA1612 (SUM_AMP L/R, dual SOIC-8): 5.5 mA × 2 = 11 mA  (Iq = 2.75 mA/channel × 2 ch/IC)
- 1× TL072CDT (IRES_AMP): ~3 mA  (TI: 1.4 mA/ch × 2 = 2.8 mA)
- 1× THAT340S14-U (EXPO_HP): ~1 mA
- **+12V: ~27 mA | −12V: ~27 mA**

---

## 4. Component Requirements

Component set: see the generated BOM `kicad/pogo-bom.csv` (rows with `Block = block-7`),
sourced from `specs/components.yaml` (the per-ref design manifest) and enriched by the
`components/` registry (MPN, footprint, datasheet). Verification status: `specs/STATUS.md`.
