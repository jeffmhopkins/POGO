# Block 5: LP Filter 1

## Status
- Phase 1 (Audio Spec): [x] complete
- Phase 2 (Analog Model): [x] complete
- Phase 3 (Circuit Design): [x] complete — SVF (OTA-C, LP output tapped)

---

## Phase 1: Audio / Functional Specification

### Sonic Intent
First voltage-controlled lowpass filter stage. Receives signal from the pre-LP1 VCA (Block VCA),
which gates or accents the signal before it enters this filter. Post-distortion tone shaping —
takes the rich harmonic content from the wavefolder/clipper and sculpts it into the desired texture.
At low resonance and high cutoff: transparent and clean. At high resonance and swept cutoff: classic
filter sweep. At maximum resonance: self-oscillation produces a sine-wave tone at the cutoff
frequency, which can be tuned via CV (1V/oct tracking).

The STEREO SPREAD OFFSET parameter creates stereo width by skewing the R channel cutoff relative
to L. This transforms a mono filter sweep into a wide, living stereo image.

LP1's output is also tapped as the BAND OUT jack pair (Block B), capturing the filtered signal
before it passes through LP2 and HP.

### Parameters

| Name | Range | Default | Taper | Description |
|---|---|---|---|---|
| CUTOFF | 20 Hz – 20 kHz | 2 kHz | Logarithmic (1V/oct) | Lowpass cutoff frequency (shared L and R baseline) |
| RESONANCE | 0 – 100% (self-osc) | 0% | Linear | Q from 0.5 to ∞; self-oscillation begins near 95–100% |
| STEREO SPREAD OFFSET | ±5 V equivalent | 0 V (center) | Linear (bipolar) | Skews R channel cutoff relative to L; positive = R cutoff shifts up; negative = R cutoff shifts down |

### CV Modulation Targets

| Target | CV Range | Attenuverter | Notes |
|---|---|---|---|
| CUTOFF | ±5 V (1V/oct) | Yes | Exponential mapping; sweeps full 20 Hz–20 kHz range |
| RESONANCE | 0–10 V | Yes | 10 V drives filter to self-oscillation |

### Signal Levels (I/O)
- Input: ±5 V audio from Block VCA (may be harmonically complex from Block 4 distortion)
- Output: ±5 V audio at low resonance; resonance boosts level near cutoff — may reach ±8 V
  at high resonance; stay within op-amp headroom (±10.5 V)
- BAND OUT tap: same signal as LP1 output (before LP2 input)

### Stereo Behavior
True stereo: independent L and R filter circuits.
CUTOFF and RESONANCE knobs apply equally to L and R (shared panel controls).
STEREO SPREAD OFFSET applies a DC offset to the R channel expo converter only, skewing R cutoff
up or down relative to L. At center (0V), both channels are identical.

### Edge Cases
- Self-oscillation: at RESONANCE = 100%, filter oscillates at the cutoff frequency. This is
  a musical feature — at this point CUTOFF knob and CV become a 1V/oct pitch control.
- CUTOFF at 20 Hz: heavy bass rolloff; effectively mutes most audio content. Useful for
  envelope-follower-driven filter sweeps that open the filter with transients.
- Hot input from distortion: at maximum distortion drive, signal may approach ±10 V. Filter
  must handle this without oscillating from input overload.
- STEREO SPREAD OFFSET at extreme: R and L cutoffs can diverge by several octaves. At extreme
  positive offset, R channel passes more high-frequency content; at extreme negative offset,
  R channel is darker than L.

---

## Phase 2: Analog Behavior Model

### Transfer Function (2-pole Butterworth LP)

```
H_LP(s) = ω₀² / (s² + (ω₀/Q) × s + ω₀²)
```

- ω₀ = 2π × f_cutoff (cutoff angular frequency)
- Q = quality factor; Butterworth: Q = 1/√2 ≈ 0.707 (flat passband)
- At Q = 1/√2: −3 dB at ω₀, 12 dB/octave rolloff above cutoff
- As Q increases: peak emerges at ω₀; at Q → ∞, peak → ∞ (self-oscillation)

### Frequency Response
- Passband: flat below ω₀
- Rolloff: 12 dB/octave (−40 dB/decade) above cutoff
- Resonance peak: emerges at f_cutoff when Q > 0.707; peak height = 20 log₁₀(Q / √(1 − 1/(4Q²))) dB above 0 dB reference

### Parameter-to-Behavior Mapping

**1V/oct cutoff control (shared L+R baseline):**
```
ω₀_L = ω_ref × 2^(V_cv / 1V)

where ω_ref = 2π × f_ref  (f_ref = frequency at V_cv = 0V)
```

**STEREO SPREAD OFFSET (R channel only):**
```
ω₀_R = ω_ref × 2^((V_cv + V_spread) / 1V)

where V_spread = STEREO SPREAD OFFSET pot voltage (bipolar, ±5 V range)
```

At V_spread = 0 V (center detent): ω₀_R = ω₀_L — identical cutoff.
At V_spread = +1 V: R channel cutoff is one octave above L.
At V_spread = −1 V: R channel cutoff is one octave below L.
Practical range: ±5 V → ±5 octave spread (±2 octave is the musical sweet spot).

At V_cv = 0 V: f_cutoff_L = f_ref (set by calibration trim pot)
At V_cv = +1 V: f_cutoff_L = 2 × f_ref (one octave up)
With a ±5 V range: 10 octave sweep (2^10 = 1024× frequency range).
Choose f_ref ≈ 630 Hz so that ±5 V spans 20 Hz (−5 V) to ~20 kHz (+5 V).

**Resonance to Q:**
```
Q = Q_max × RESONANCE_normalized

Q_max → ∞ at self-oscillation; practical limit: Q ≈ 50 at RESONANCE = 95%
```

---

## Phase 3: Circuit Design

### Topology: State-Variable Filter (OTA-C), LP output tapped

Two LM13700 OTA cells act as the integrators in the SVF core. The summing amplifier uses a
TL074. Q (resonance) is controlled by a third LM13700 OTA cell in the BP feedback path —
the OTA output current injects directly into the SUM_AMP virtual-ground input node, giving
voltage-controlled Q independently of cutoff. Tapping V_LP gives the 2-pole lowpass output.

```
V_in ──[R_in]──(−) SUM_AMP ──(out)──[OTA1 integrator]──(out)── V_BP
                  (+)=GND               │                          │
                                        C1                         │
                                        │                       [OTA2 integrator]──(out)── V_LP
                                       GND                         │
                                                                   C2
                                                                   │
                                                                  GND

V_HP = SUM_AMP output = V_in − V_LP − (1/Q) × V_BP

Resonance feedback:
V_BP ──[linearizing diodes]──► LP1_Q_OTA IN+
                                LP1_Q_OTA IN− → GND
                                LP1_Q_OTA Iabc ←── inverting Iabc driver (see below)
                                LP1_Q_OTA I_out ──► directly into SUM_AMP (−) virtual ground node
```

Q formula (derived from KCL at SUM_AMP virtual-ground node, all resistors = R_in = 100 kΩ):
  ω₀/Q = g_m_Q × R_in × ω₀  →  Q = 1 / (g_m_Q × R_in) = 52 mV / (Iabc × 100 kΩ)

  More Iabc → more BP damping at virtual ground → LOWER Q (flatter). Self-oscillation at Iabc → 0.
  The RESONANCE control MUST decrease Iabc as it turns clockwise.

  At Iabc = 0.74 µA: Q ≈ 0.7  (Butterworth — flat, no resonance peak)
  At Iabc = 0.10 µA: Q ≈ 5    (moderate resonance peak)
  At Iabc ≈ 10 nA:   Q ≈ 52   (near self-oscillation onset)

Inverting Iabc driver (RESONANCE CV must decrease Iabc as it increases):
  One spare TL072 half (IRES_AMP) configured as an inverting summer:

  V_bias = +0.74 V (derived from +12 V via resistor divider R_a/R_b, op-amp buffered)
  V_bias ──[R_f]──(−) IRES_AMP
  V_RES_scaled ──[R_f]──(−)       V_RES_scaled = RESONANCE_CV × (0.74 V / 10 V) via divider
  (+) = GND; feedback R_f

  V_Iabc = V_bias − V_RES_scaled
  R_Iabc = 1 MΩ from V_Iabc node to LP1_Q_OTA Iabc pin

  At RESONANCE=0:   V_Iabc = +0.74 V → Iabc = 0.74 µA (Q ≈ 0.7, flat)
  At RESONANCE=100%: V_Iabc → 0 V   → Iabc → 0 (Q → ∞, self-oscillation)
  Small clamp diode (anode GND, cathode V_Iabc) prevents negative Iabc if CV overshoots.
  RV_LP1_QMAX adjusts V_bias to set the flat Q and self-oscillation onset point.

### STEREO SPREAD OFFSET Circuit

The STEREO SPREAD OFFSET knob provides a bipolar DC voltage applied only to the R channel
expo converter input:

```
V_ctrl_L = CUTOFF knob + CUTOFF CV (shared)
V_ctrl_R = CUTOFF knob + CUTOFF CV + V_spread   (V_spread = STEREO SPREAD OFFSET)
```

Implementation:
- Bipolar pot (STEREO SPREAD OFFSET): CW end = +5 V ref, CCW end = −5 V ref, wiper → R expo summing node
- Small summing op-amp stage before the R channel expo converter adds V_spread to V_ctrl
- Trim pot (RV_LP1_SPREAD_NULL) nulls the center-detent position to exactly V_spread = 0 V
- L channel expo converter input has no SPREAD OFFSET connection

### Signal Flow and Transfer Functions

```
H_LP(s) = ω₀² / (s² + ω₀/Q × s + ω₀²)    ← primary output (to LP2 and BAND OUT)
H_BP(s) = ω₀ × s / (s² + ω₀/Q × s + ω₀²) ← aux jack (optional)
H_HP(s) = s² / (s² + ω₀/Q × s + ω₀²)      ← aux jack (optional)
```

### Voltage Control of ω₀

```
ω₀ = g_m / C,   g_m = I_abc / (2 × V_T)
I_abc = I_ref × e^(V_ctrl / V_T)    (expo converter, THAT340 matched pair)
```

1V/oct: each +1 V on V_ctrl doubles I_abc → doubles g_m → doubles ω₀ → one octave up.

### Component Value Derivations

Target range: 20 Hz – 20 kHz (10 octaves, ±5 V at 1V/oct → 2^10 = 1024×).
Choose f_ref = 630 Hz at V_ctrl = 0 V so that −5 V gives ~20 Hz and +5 V gives ~20 kHz.

At nominal I_abc = 10 µA:
```
g_m = 10 µA / (2 × 26 mV) = 192 µS
C = g_m / ω₀_ref = 192 µS / (2π × 630) = 48.5 nF → use 47 nF (C0G 0603)
```

Both integrator capacitors C1 = C2 = 47 nF.

### IC / Component Selection

| Reference | Part Number | Package | Qty | Notes |
|---|---|---|---|---|
| LP1_OTA_L, LP1_OTA_R | LM13700M | SOIC-16 | 2 | Dual OTA; both cells = 2 integrators per channel |
| LP1_SUM_L, LP1_SUM_R | TL074CDT | SOIC-14 | 2 | Summing amp + HP/BP/LP output buffers (1 per channel) |
| IC_Q_AB_L | LM13700M | SOIC-16 | 1 (combined audio, L-channel) | Cell A = LP1 L Q VCA; cell B = LP2 L Q VCA (shared with LP2) |
| IC_Q_AB_R | LM13700M | SOIC-16 | 1 (combined audio, R-channel) | Cell A = LP1 R Q VCA; cell B = LP2 R Q VCA (shared with LP2) |
| LP1_EXPO | THAT340 | SOIC-8 | 1 | Matched NPN pair for expo converter (L+R share one expo) |
| C1_L, C2_L, C1_R, C2_R | C0G/NP0 | 0603 | 4 | 47 nF integrator capacitors |
| R_in_L, R_in_R | — | 0603 | 2 | 100 kΩ summing amp input resistor |
| C_iabc_int_L, C_iabc_int_R | C0G/NP0 | 0402 | 2 | 10 nF bypass from LP1 integrator OTA Iabc pin to GND; place within 2 mm of Iabc pin. Filters HF noise on expo current from ribbon cable (see noise-audit.md H3) |
| C_iabc_q_L, C_iabc_q_R | C0G/NP0 | 0402 | 2 | 10 nF bypass from IC_Q_AB_L/R cell A Iabc pin to GND; same placement rule |
| RV_SPREAD_OFFSET | Bipolar pot | 9mm | 1 | STEREO SPREAD OFFSET; CW = +5 V, CCW = −5 V, wiper → R expo summer |
| R_spread, R_ctrl_R | — | 0603 | 2 | Summing resistors at R expo summer input; **0.1% tolerance** — mismatch adds semitone error per volt |
| C_VCC, C_VEE | — | 0603 | 100 nF | 8 | Decoupling, 2 per IC × 4 ICs |

### Trim Pots

| Reference | Range | Purpose | Adjustment |
|---|---|---|---|
| RV_LP1_REF | f_ref ±20% | 1V/oct reference frequency | Adjust until C4 (0 V CV) = 630 Hz at LP1 output |
| RV_LP1_1VOCT | 1V/oct ±5% | Expo converter tracking calibration | One-octave step: +1 V CV should double cutoff frequency |
| RV_LP1_QMAX | Q 10–50 | Maximum resonance / self-oscillation onset | Turn RESONANCE to max; verify clean, stable sine output |
| RV_LP1_SPREAD_NULL | ±100 mV | STEREO SPREAD OFFSET center-detent null | Set SPREAD OFFSET to center; trim until R channel cutoff = L channel cutoff |

### Power Draw Estimate
- 2× LM13700 (integrators) + 1× LM13700 (Q VCA, shared with LP2) + 2× TL074: ~15 mA
- +12 V: ~15 mA | −12 V: ~15 mA

### Schematic Notes
- LP1 Q VCA uses one cell of IC_Q_AB (LM13700); the other cell handles LP2 Q — both in the
  same channel half of the combined audio board. No V2164 IC needed for LP1.
- Block VCA L/R (THAT 2180) is in each channel half immediately upstream of LP1; no IC sharing.
- Audio signal: Block VCA output → LP1 SUM_AMP → OTA1 → OTA2 → LP output → LP2 + BAND OUT.
- STEREO SPREAD OFFSET summing node: place close to the R channel expo converter input.
- BAND OUT tap taken at the LP1 LP output buffer, before LP2 input.
- IC_Q_AB placement: place adjacent to LP1 OTAs and LP2 OTAs (Q VCA serves both filters).

### Known Circuit Challenges
- **Expo converter temperature drift**: THAT340 matched pair required for stable 1V/oct tracking. Calibrate at room temperature; verify at 10°C and 40°C extremes during bring-up.
- **Self-oscillation amplitude**: at Q → ∞, output amplitude limited by OTA/op-amp rail clipping. BAT54 anti-parallel diodes across SUM_AMP feedback resistor prevent hard clipping.
- **LM13700 Q VCA Iabc range**: R_Iabc = 1 MΩ; at maximum resonance, Iabc → 0 (self-oscillation). RV_LP1_QMAX trims V_bias and therefore the flat-response Iabc and self-oscillation onset. Too high V_bias → Q too low at minimum resonance setting; too low → self-oscillation onset too early.
- **L/R resonance matching**: L and R use separate LM13700 cells (one IC per channel) driven by the same RESONANCE CV. LM13700 cells on different dies will match slightly less well than V2164 cells on the same die; the calibrated Iabc operating point should keep mismatch inaudible.
- **STEREO SPREAD OFFSET center null**: the bipolar pot must pass exactly 0 V at center detent. RV_LP1_SPREAD_NULL compensates for mechanical offset.
- **SPREAD OFFSET interaction with CUTOFF CV**: V_spread sums into the R expo converter input alongside the shared CUTOFF CV. Summing resistors (R_spread and R_ctrl in the R expo summer) must be **0.1% tolerance** to preserve 1V/oct tracking on the R channel. Any mismatch adds a constant semitone error per volt of CV. Specify 0.1% in the parts table.
- **OTA-C noise at high Q (accepted limitation — D1)**: at Q → ∞ (Iabc → 0), LM13700 input noise current (~10 pA/√Hz) reflected through the high-impedance integrator capacitor raises the noise floor. This is inherent to OTA-C topology and is not fixable without a fundamentally different filter architecture. At self-oscillation onset, the oscillating sine tone dominates and masks the elevated noise floor. See noise-audit.md D1.
- **LP1/LP2 Q-VCA thermal coupling (accepted limitation — D2)**: LP1 Q uses IC_Q_AB cell A; LP2 Q uses cell B of the same IC die. At the nominal Iabc operating point (<1 µA), each cell dissipates <10 µW — thermal coupling between cells is negligible and does not cause audible Q drift between LP1 and LP2. See noise-audit.md D2.
