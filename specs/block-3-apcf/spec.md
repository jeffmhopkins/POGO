# Block 3: Triple Bandpass SVF Resonators

## Status
- Phase 1 (Audio Spec): [x] complete
- Phase 2 (Analog Model): [x] complete
- Phase 3 (Circuit Design): [x] complete

---

## Phase 1: Audio / Functional Specification

### Sonic Intent
Three independent 2-pole OTA-C state-variable filters in bandpass mode — one resonator per
formant group (F1/F2/F3). Each resonator produces a sharp, tuneable peak at its center
frequency, independently controllable in both frequency and Q/resonance.

Each group covers a distinct part of the vocal spectrum:
- **Group 1**: Low formant, F1 — centered around 200 Hz at 0 V
- **Group 2**: Mid formant, F2 — centered around 1.5 kHz at 0 V
- **Group 3**: High formant, F3 — centered around 6 kHz at 0 V

At low resonance (FB ≈ 0): each SVF acts as a broad bandpass shelf — gentle formant coloring.
At high resonance (FB near max): narrow, resonant peaks — distinctly vocal, "talking" character.
At maximum resonance: self-oscillation at the center frequency — clean sine tone output from each group.

Sweeping MASTER OFFSET moves all three formants together (vowel gesture). Independent FREQ
knobs set the vowel shape (F1/F2/F3 spacing determines the perceived vowel). STEREO WIDTH
drifts R channel formants relative to L, creating a wide, animated stereo field.

### Parameters

| Name | Range | Default | Taper | Description |
|---|---|---|---|---|
| FREQ 1 | f_ref=200 Hz at 0 V; ±5 V sweep | 0 V (200 Hz) | Logarithmic (1V/oct) | Center frequency of Group 1 (low formant F1) |
| FREQ 2 | f_ref=1500 Hz at 0 V; ±5 V sweep | 0 V (1.5 kHz) | Logarithmic (1V/oct) | Center frequency of Group 2 (mid formant F2) |
| FREQ 3 | f_ref=6000 Hz at 0 V; ±5 V sweep | 0 V (6 kHz) | Logarithmic (1V/oct) | Center frequency of Group 3 (high formant F3) |
| MASTER OFFSET | ±5 V | 0 | Linear | Shifts all 3 group frequencies simultaneously (1V/oct); master vowel sweep |
| FB 1 | 0 – 100% | 0% | Linear | Q/resonance for Group 1; 0% = flat (Q≈0.5), 100% = self-oscillation (Q≈50) |
| FB 2 | 0 – 100% | 0% | Linear | Q/resonance for Group 2 |
| FB 3 | 0 – 100% | 0% | Linear | Q/resonance for Group 3 |
| FB DIST BLEND | 0 – 100% | 0% | Linear | Blends post-distortion signal into SVF input: 0% = clean input only, 100% = post-distortion signal added |
| POLARITY | Switch: Positive / Off / Negative | Positive | N/A | Positive: SVF output sums normally; Off: SVF outputs silenced (dry pass only); Negative: SVF output phase-inverted before summing |
| STEREO WIDTH | 0 – 100% | 0% | Linear | Per-octave offset of R channel group frequencies vs. L |
| COMB BYPASS | 0 – 100% | 100% | Linear | Wet/dry mix: 0% = dry only (no SVF), 100% = full SVF wet signal |

### CV Modulation Targets

| Target | CV Range | Attenuverter | Notes |
|---|---|---|---|
| FREQ 1 | ±5 V (1V/oct) | Yes | Exponential; sweeps Group 1 center frequency |
| FREQ 2 | ±5 V (1V/oct) | Yes | Exponential; sweeps Group 2 center frequency |
| FREQ 3 | ±5 V (1V/oct) | Yes | Exponential; sweeps Group 3 center frequency |
| FB 1 | 0–10 V | Yes | Group 1 Q/resonance |
| FB 2 | 0–10 V | Yes | Group 2 Q/resonance |
| FB 3 | 0–10 V | Yes | Group 3 Q/resonance |
| FB DIST BLEND | 0–10 V | Yes | Post-distortion blend into SVF input |
| COMB BYPASS | 0–10 V | Yes | Wet/dry level |
| MASTER OFFSET | ±5 V (1V/oct) | Yes | Shifts all 3 center frequencies simultaneously |
| POLARITY | — | None | Switch only; no CV |

### Signal Levels (I/O)
- Input: ±5 V audio (from Block 2; up to ±10.5 V in BOOST mode)
- Output: ±5 V nominal; resonant peaks can boost level at formant frequencies by up to Q× the
  input amplitude. At Q=50 and high input level, instantaneous peaks are clamped by op-amp rails.
  COMB BYPASS at less than 100% reduces wet contribution.
- COMB BYPASS = 0%: dry signal only, no SVF coloring

### Stereo Behavior
True stereo: independent L and R SVF circuits (3 groups × 2 channels = 6 SVF instances).
FREQ 1/2/3 and MASTER OFFSET apply identically to both channels.
STEREO WIDTH offsets R channel center frequencies: `f_R = f_L × 2^(WIDTH_V / 1V)`.
POLARITY and FB DIST BLEND apply identically to both channels.

### Edge Cases
- All three FB knobs at max with POLARITY=Positive: each group self-oscillates independently
  at its center frequency. Output is a chord of three sine tones at F1/F2/F3.
- POLARITY=Off: all SVF outputs muted; COMB BYPASS routes dry signal only regardless of FB.
- FB DIST BLEND at max with DRIVE high: distorted signal adds into SVF input, increasing
  the harmonic content entering each resonator for a more aggressive formant character.
- FREQ 1 and FREQ 2 converging (same CV): F1/F2 formants merge into one stronger peak.
  No circuit problem — just a different tonal character (rounder, single-peak vowel).

---

## Phase 2: Analog Behavior Model

### Transfer Function (2-pole Bandpass SVF)

```
H_BP(s) = (ω₀/Q) × s / (s² + (ω₀/Q) × s + ω₀²)
```

- At DC (s → 0): H_BP → 0 (blocks DC)
- At high frequency (s → ∞): H_BP → 0 (blocks high frequencies)
- At s = jω₀: |H_BP(jω₀)| = Q (resonance peak height, linear units)
- Formant bandwidth: BW = f₀ / Q (3 dB bandwidth)

SVF simultaneously provides LP, BP, and HP outputs; only BP is used here.

### Parameter-to-Behavior Mapping

**Frequency control (1V/oct, per group):**
```
f₀ = f_ref × 2^(V_ctrl / 1V)
```
- Group 1: f_ref = 200 Hz; at ±5 V: 6.25 Hz – 6.4 kHz
- Group 2: f_ref = 1500 Hz; at ±5 V: 46.9 Hz – 48 kHz (clamped to 20 kHz)
- Group 3: f_ref = 6000 Hz; at ±5 V: 187.5 Hz – 192 kHz (clamped to 20 kHz)

**MASTER OFFSET:** sums exponentially with each group's individual frequency CV:
```
f_n_eff = f_ref_n × 2^((V_freq_n + V_master_offset) / 1V)
```

**STEREO WIDTH:** adds a fixed offset to R channel only:
```
f_n_R = f_n_L × 2^(V_width / 1V)
```

**Q mapping:**
```
Q = 0.5 + fbParam × 49.5
```
- fbParam = 0 → Q = 0.5 (Butterworth, nearly flat Gaussian rolloff on each side)
- fbParam = 0.5 → Q ≈ 25 (sharp, narrow formant peak)
- fbParam → 1 → Q ≈ 50 (very narrow; near self-oscillation)
- Self-oscillation occurs at Q → ∞ (Iabc → 0 in hardware); unlimited in DSP model

**FB DIST BLEND (input mixing):**
```
V_svf_in = V_audio + blend × V_post_dist
```
Additive, not crossfade. At blend=1: distorted signal adds to clean input, increasing
harmonic content entering each resonator. This is not a feedback loop — it's additive input mixing.

**POLARITY (output inversion):**
```
V_group_sum = polarity × (V_group1 + V_group2 + V_group3)
  polarity = +1 (Positive), 0 (Off), −1 (Negative)
```

**COMB BYPASS (wet/dry):**
```
V_out = V_dry × (1 − bypass) + V_wet × bypass
  V_wet = sum of distorted per-group SVF outputs
```

### Combined Three-Group Output

The three BP outputs are summed (unity gain, no /3 normalization):
```
V_wet = Distortion(V_svf_group1) + Distortion(V_svf_group2) + Distortion(V_svf_group3)
```
COMB BYPASS level controls how much of this summed wet signal reaches the output.
At typical settings (groups at different frequencies), the sum magnitude is similar to
a single group since formant peaks are non-overlapping.

### OTA-C SVF Voltage Control

Identical to LP1/LP2/HP filters — same expo converter relationship:
```
ω₀ = g_m / C,    g_m = I_abc / (2 × V_T)
I_abc = I_ref × e^(V_ctrl / V_T)    (THAT340 expo converter)
```
1V/oct: +1 V on V_ctrl doubles I_abc → doubles g_m → doubles ω₀ → one octave up.

---

## Phase 3: Circuit Design

### Topology: OTA-C State-Variable Filter in Bandpass Mode

**Identical circuit to LP1/LP2/HP filters** (same LM13700 integrators, same TL072/TL074 summing
amp, same THAT340 expo converter, same Q VCA / IRES_AMP inverting driver). Only the output tap
differs: LP1/LP2 tap the second integrator (V_LP); Block 3 taps the first integrator (V_BP).

Per group, per channel:
```
V_in ──[R_in=100kΩ]──(−) SUM_AMP ──► V_HP ──[OTA1 integrator]──► V_BP
                        (+)=GND                    │
                                                   C1
                                                   │
                                       [OTA2 integrator] ──► V_LP
                                                   │
                                                   C2
                                                   │
                                                  GND

BP output = V_BP (first integrator output, tapped before second integrator)
V_HP = SUM_AMP output = V_in − (1/Q)×V_BP − V_LP
```

Q VCA (resonance control), same as LP1:
```
V_BP ──[linearizing diodes]──► Q_OTA IN+
Q_OTA Iabc ◄── inverting Iabc driver (IRES_AMP; same as LP1)
Q_OTA I_out ──► SUM_AMP (−) virtual-ground node

Q = 52 mV / (Iabc × R_in)  (R_in = 100 kΩ)
At Iabc = 0.74 µA: Q ≈ 0.7 (flat)
At Iabc → 0:       Q → ∞ (self-oscillation at center frequency)
RESONANCE must DECREASE Iabc as FB knob turns CW — same inverting IRES_AMP as LP1.
```

### Integrator Capacitor Values

Caps sized to place f_ref at the OTA nominal I_abc = 10 µA operating point:
```
C = g_m / ω₀_ref = 192 µS / (2π × f_ref)
```

| Group | f_ref | Calculated C | Chosen C | Part |
|---|---|---|---|---|
| Group 1 (F1) | 200 Hz | 152.9 nF | **150 nF** (C0G 0603) | Murata GRM188 |
| Group 2 (F2) | 1500 Hz | 20.4 nF | **22 nF** (C0G 0603) | Murata GRM188 |
| Group 3 (F3) | 6000 Hz | 5.1 nF | **4.7 nF** (C0G 0603) | Murata GRM188 |

Both integrator capacitors (C1 = C2) use the same value per group.
The 1V/oct trim pot (RV_Gn_1VOCT) corrects small deviations from these nominal values.

**Note on old APF values**: The old topology used 33 nF / 6.8 nF / 1.5 nF for six APF stages
with a different ω₀_max derivation. These values are no longer applicable to the SVF integrators.

### IC / Component Selection

Per stereo pair (L+R):

| Reference | Part Number | Package | Qty | Notes |
|---|---|---|---|---|
| G1_OTA_L, G1_OTA_R | LM13700M | SOIC-16 | 2 | Group 1 integrators: cell A = integrator 1, cell B = integrator 2 |
| G2_OTA_L, G2_OTA_R | LM13700M | SOIC-16 | 2 | Group 2 integrators |
| G3_OTA_L, G3_OTA_R | LM13700M | SOIC-16 | 2 | Group 3 integrators |
| IC_Q_G1G2_L | LM13700M | SOIC-16 | 1 | Group 1+2 Q VCA: cell A = G1 L, cell B = G2 L |
| IC_Q_G1G2_R | LM13700M | SOIC-16 | 1 | Group 1+2 Q VCA: cell A = G1 R, cell B = G2 R |
| IC_Q_G3_L | LM13700M | SOIC-16 | 1 | Group 3 Q VCA: cell A = G3 L; cell B = spare |
| IC_Q_G3_R | LM13700M | SOIC-16 | 1 | Group 3 Q VCA: cell A = G3 R; cell B = spare |
| SUM_L, SUM_R | TL074CDT | SOIC-14 | 2 | SVF summing amps (3 per channel; 1 quad per channel) |
| EXPO_G1 | THAT340 | SOIC-8 | 1 | Matched NPN pair for Group 1 expo converter |
| EXPO_G2 | THAT340 | SOIC-8 | 1 | Matched NPN pair for Group 2 expo converter |
| EXPO_G3 | THAT340 | SOIC-8 | 1 | Matched NPN pair for Group 3 expo converter |
| C_int_G1 | C0G/NP0 | 0603 | 4 | 150 nF integrator caps (C1_L, C2_L, C1_R, C2_R) |
| C_int_G2 | C0G/NP0 | 0603 | 4 | 22 nF integrator caps |
| C_int_G3 | C0G/NP0 | 0603 | 4 | 4.7 nF integrator caps |
| C_iabc | C0G/NP0 | 0402 | 18 | 10 nF Iabc bypass caps — 1 per OTA cell per channel (9 integrator cells × 2 channels = 18); place within 2 mm of Iabc pin. See noise-audit H3 |
| SW_POL | 3-pos panel switch | Panel | 1 | POLARITY: Positive / Off / Negative |
| R_pol_bleed | — | 0603 | 1 | 10 kΩ bleeder to GND at POLARITY Off contact. Prevents switch leakage at output summing node. See noise-audit H4 |

**Component count reduction vs. old APF topology:**
- LM13700: 8 total (was 20 including COMB BYPASS VCA — COMB BYPASS now handled by simple wet/dry mix)
- TL072/TL074: 2 per channel (was 9+ per channel)
- THAT340: 3 (unchanged)
- Capacitors: 12 integrator caps total (was 36 APF stage caps + 36 22pF HF-suppress + 36 10nF Iabc bypass)

### Trim Pots

| Reference | Range | Purpose | Adjustment |
|---|---|---|---|
| RV_G1_1VOCT | ±20% | Group 1 expo 1V/oct calibration | Step FREQ 1 by +1 V; verify center frequency doubles |
| RV_G2_1VOCT | ±20% | Group 2 expo 1V/oct calibration | Same |
| RV_G3_1VOCT | ±20% | Group 3 expo 1V/oct calibration | Same |
| RV_G1_REF | ±20% | Group 1 f_ref at 0 V | Adjust until center freq at 0 V CV = 200 Hz |
| RV_G2_REF | ±20% | Group 2 f_ref at 0 V | Adjust until center freq at 0 V CV = 1500 Hz |
| RV_G3_REF | ±20% | Group 3 f_ref at 0 V | Adjust until center freq at 0 V CV = 6000 Hz |
| RV_G1_QMAX | V_bias trim | Group 1 self-oscillation onset | Set FB to max; verify clean sine at center frequency; trim for stable onset |
| RV_G2_QMAX | V_bias trim | Group 2 self-oscillation onset | Same |
| RV_G3_QMAX | V_bias trim | Group 3 self-oscillation onset | Same |

### Power Draw Estimate
- 8× LM13700 integrators + Q VCAs: ~32 mA
- 2× TL074 summing amps: ~4 mA
- 3× THAT340 expo converters: ~3 mA
- +12 V: ~25 mA | −12 V: ~25 mA

(Significant reduction from old 55 mA per rail — Block 3 is no longer the power-dominant block.)

### Known Circuit Challenges
- **BP output level at high Q**: `|H_BP(jω₀)| = Q` — at Q=50, resonant peak is 50× the input
  amplitude at that frequency. With ±5 V input, peak can reach ±250 V (clamped by op-amp rails
  before that). Design summing amp headroom for ±12 V rail clamping at max Q; COMB BYPASS at
  less than 100% in typical use.
- **Independent expo calibration**: Three separate THAT340 expo converters must be calibrated
  independently (RV_Gn_REF + RV_Gn_1VOCT). Same procedure as LP1/LP2/HP.
- **Q VCA self-oscillation stability**: SVF is inherently stable at any Q (unlike APF feedback
  which required FB_MAX clamp). No resistor floor needed — full range up to self-oscillation is safe.
- **Group 1 large caps (150 nF)**: 150 nF C0G at 0603 is available (e.g., Murata GRM188R71E154K)
  but verify sourcing before PCB layout. Alternatively use two 68 nF in parallel (both C0G 0603).
- **FB DIST BLEND is additive, not crossfade**: Post-distortion signal adds to (not replaces)
  the clean input. At blend=1 with full DRIVE, the SVF input level can be 2× the normal level —
  ensure SUM_AMP R_in handles this without excessive headroom loss.
- **Crosstalk L/R**: same routing rule as LP filters — route L and R signal traces on separate
  PCB layers with GND plane between them.
- **GND stitching at group boundaries**: add 3× GND stitching via array between each group's
  OTA cluster on the audio board (same rule as LP1/LP2 boundary, noise-audit M5).
