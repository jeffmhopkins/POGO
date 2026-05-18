# Block 3: Triple 6-Stage All-Pass Comb Filter (APCF)

## Status
- Phase 1 (Audio Spec): [x] complete
- Phase 2 (Analog Model): [x] complete
- Phase 3 (Circuit Design): [x] complete

---

## Phase 1: Audio / Functional Specification

### Sonic Intent
Three independent groups of 6 first-order all-pass stages cascaded in series per stereo channel
— 18 all-pass stages total per channel. Mixed with the dry signal, they create the classic phaser
comb: a sweep of notches and peaks across the frequency spectrum. With three independent groups
tuned to different frequency ranges, the comb pattern spreads across the full audio band, producing
rich, formant-like resonances — like a vowel filter that breathes with modulation.

Each group covers a different zone:
- **Group 1**: Low formant (~100 Hz – 1 kHz)
- **Group 2**: Mid formant (~500 Hz – 5 kHz)
- **Group 3**: High formant (~2 kHz – 20 kHz)

With feedback, each group develops a distinct resonant peak at its center frequency. Sweeping
SPREAD opens or closes the distance between the three formants. Sweeping FREQ OFFSET moves all
three together like a filter sweep. STEREO WIDTH drifts the R channel's formants relative to L,
creating a shifting, spacious stereo field.

At minimum DRY/WET (fully dry): comb effect is off, signal passes through unchanged.
At maximum DRY/WET (fully wet): all 18 stages always in circuit; maximum notch depth.
At mid DRY/WET: classic phaser blend — notches audible but dry content preserved.

### Parameters

| Name | Range | Default | Taper | Description |
|---|---|---|---|---|
| FREQ 1 | 20 Hz – 2 kHz center | 200 Hz | Logarithmic | Center frequency of Group 1 (low formant) |
| FREQ 2 | 200 Hz – 8 kHz center | 1.5 kHz | Logarithmic | Center frequency of Group 2 (mid formant) |
| FREQ 3 | 1 kHz – 20 kHz center | 6 kHz | Logarithmic | Center frequency of Group 3 (high formant) |
| SPREAD | 0 – 100% | 50% | Linear | Multiplies spacing between groups; 0% collapses all groups to same frequency |
| FREQ OFFSET | ±5 V equivalent | 0 | Linear | Shifts all 3 groups up or down together; acts as a master sweep |
| FEEDBACK 1 | 0 – 95% | 0% | Linear | Resonance depth of Group 1; >95% risks instability |
| FEEDBACK 2 | 0 – 95% | 0% | Linear | Resonance depth of Group 2 |
| FEEDBACK 3 | 0 – 95% | 0% | Linear | Resonance depth of Group 3 |
| STEREO WIDTH | 0 – 100% | 0% | Linear | Frequency offset of R channel groups relative to L; 0% = mono, 100% = maximum stereo spread |
| DRY/WET | 0 – 100% | 50% | Linear | Blend from fully dry to fully wet (phase-shifted) signal |

### CV Modulation Targets

| Target | CV Range | Attenuverter | Notes |
|---|---|---|---|
| FREQ 1 | ±5 V (1V/oct) | Yes | Sweeps Group 1 center frequency exponentially |
| FREQ 2 | ±5 V (1V/oct) | Yes | Sweeps Group 2 center frequency exponentially |
| FREQ 3 | ±5 V (1V/oct) | Yes | Sweeps Group 3 center frequency exponentially |
| FEEDBACK (all) | 0–10 V | Yes | Single CV controls all three feedback depths together |
| DRY/WET | 0–10 V | Yes | Sweeps blend from dry to wet |

### Signal Levels (I/O)
- Input: ±5 V audio (from Block 2; up to ±10.5 V if Block 1 is in BOOST mode)
- Output: ±5 V audio (all-pass stages are unity gain by definition; no signal level change)
- With feedback: resonance can increase apparent level at the formant frequencies by several dB;
  keep output stage headroom at ±10 V

### Stereo Behavior
True stereo: independent signal paths for L and R through all 18 stages per channel.
FREQ 1/2/3 knobs and SPREAD control both channels identically.
STEREO WIDTH offsets R channel group frequencies: `ω_R = ω_L × 2^(WIDTH_V / 1V)` where WIDTH_V
is a small positive or negative voltage derived from the WIDTH knob.
DRY/WET applies identically to both channels.

### Edge Cases
- FEEDBACK at maximum (95%): near-self-oscillation; output level rises sharply. The 95% hard
  limit in the circuit must be enforced by a resistor floor in the feedback path — do not allow
  full 100% positive feedback.
- DRY/WET at 0%: signal bypasses phase-shift influence. The all-pass stages are still in the
  signal path but their output is muted from the mix; the dry signal is passed directly. In the
  hardware implementation, DRY/WET is an XFade between unprocessed and processed — when fully
  dry, no op-amp noise from the wet path reaches the output.
- SPREAD at 0%: all three groups are set to the same frequency; the three sets of notches align,
  producing a deeper but narrower comb effect at one frequency region.

---

## Phase 2: Analog Behavior Model

### Transfer Function

**Single 1st-order all-pass stage:**
```
H_APF(s) = (s − ω₀) / (s + ω₀)
```
- Magnitude: |H_APF(jω)| = 1 for all ω (unity gain — all-pass)
- Phase: φ(ω) = π − 2 arctan(ω / ω₀)
  - At ω → 0:   φ = π   (180° phase shift)
  - At ω = ω₀:  φ = π/2 (90° phase shift)
  - At ω → ∞:   φ = 0   (0° phase shift)

**Six cascaded APF stages (one group), same center frequency ω₀:**
```
H_6(s) = [(s − ω₀) / (s + ω₀)]^6
```
- Magnitude: still unity for all ω
- Phase: φ_6(ω) = 6 × [π − 2 arctan(ω / ω₀)]

**Notch locations in the phaser output:**
When H_6 is mixed with the dry signal (V_dry + V_wet), cancellation occurs where phase shift = (2n+1)π:
```
6 × [π − 2 arctan(ω_notch / ω₀)] = (2n+1)π
arctan(ω_notch / ω₀) = (5 − 2n)π / 12
ω_notch_n = ω₀ × tan((5 − 2n)π / 12)
```
For 6 stages (at equal DRY/WET), this produces 3 notch pairs across the spectrum.

**Three groups, each with independent ω₀:**
```
Group 1: ω₀_1 = 2π × f₁,   f₁ controlled by FREQ 1 + FREQ OFFSET + modulation
Group 2: ω₀_2 = 2π × f₂,   f₂ controlled by FREQ 2 + FREQ OFFSET + modulation
Group 3: ω₀_3 = 2π × f₃,   f₃ controlled by FREQ 3 + FREQ OFFSET + modulation
```

SPREAD scales the distances:
```
f₁_eff = f₁_base × 2^(−SPREAD × k)
f₂_eff = f₂_base   (reference, unaffected)
f₃_eff = f₃_base × 2^(+SPREAD × k)
```
where k is a scaling factor set so that at SPREAD = 100%, the groups are maximally spread
(Group 1 near 20 Hz, Group 3 near 20 kHz).

**FREQ OFFSET:** shifts all three groups simultaneously by adding an exponential offset:
```
f_n_eff = f_n_base × 2^(V_offset / 1V)
```
This is a 1V/octave exponential relationship applied to all three groups in common.

**STEREO WIDTH:** offsets R channel frequencies by a fixed ratio:
```
f_n_R = f_n_L × 2^(V_width / 1V)
```
At WIDTH = 50%, approximately +2 semitones offset. At WIDTH = 100%, approximately +5 semitones.

### Feedback (Resonance) Model

Each group has a feedback path with gain g (0 ≤ g < 1):
```
V_out_group = H_6(s) × [V_in + g × V_out_group]
V_out_group = H_6(s) × V_in / (1 − g × H_6(s))
```
The feedback boosts the resonance at the notch frequencies. At g → 1, the denominator approaches
zero at the notch frequencies → self-oscillation. Circuit must limit g to ≤ 0.95 via resistor floor.

### Frequency Response (Combined Output)

With DRY/WET at 50%:
```
V_output = 0.5 × V_dry + 0.5 × V_wet
```
At a notch frequency: V_wet = −V_dry (phase = π + 0° from double inversion in 6 even-order stages
at appropriate ω_notch), so cancellation produces a deep notch. With feedback, the peaks between
notches are emphasized.

### OTA-Based Voltage Control

Each all-pass stage uses an OTA (one cell of LM13700) as the variable element:
```
ω₀ = g_m / C_apf
g_m = I_abc / (2 × V_T)    where V_T ≈ 26 mV at room temperature
     = I_abc × 19.2 (A/A)
```
So `ω₀ = (I_abc × 19.2) / C_apf`

The control voltage (from the FREQ knob + CV) is converted to an exponential current I_abc via
an expo converter. This gives the 1V/octave exponential frequency sweep.

---

## Phase 3: Circuit Design

### Topology
OTA-based first-order all-pass stages. Each stage uses one OTA cell of an LM13700 (dual OTA,
SOIC-16) plus one op-amp half. Six stages per group, three groups, two channels = 36 OTA cells
and 36 op-amp halves total.

**IC count per channel:**
- 18 OTA cells needed → 9× LM13700 per channel → 18× LM13700 total (L + R)
- 18 op-amp halves for all-pass stages per channel → 9× TL072 per channel → 18× TL072 total
- 3× expo converter circuits (one per group, shared L/R since L and R track same ω₀)
- 3× op-amp for expo converters → ~2× TL072 (with 2 halves spare)
- 3× feedback summing amplifiers (one per group, L and R separate) → 3× TL072 per channel
- DRY/WET crossfader: VCA-based or resistive; 1× per channel

Total approximate IC count: 18× LM13700, ~24× TL072/TL074, expo transistors.
This block is the most component-dense block in the module. Plan for 2–3 PCBs.

#### Single All-Pass Stage (per OTA cell)

```
V_in ──┬──[R_ref]──(−) TL072A ──── V_out
       │                 (+)◄────────┤
       └──[OTA_out]──[C_apf]────────┘

OTA (LM13700 cell):
  (+in): V_in
  (−in): GND (or virtual ground via buffer)
  (Iabc): exponential control current from expo converter
  (out): OTA output current → charges C_apf
```

Standard inverting all-pass op-amp topology with OTA as the time-constant element:
- R_ref: fixed reference resistor (sets passband gain balance)
- C_apf: sets frequency range; C_apf = g_m / ω₀_max

**Component values (example for Group 1, range 100 Hz – 1 kHz):**
- ω₀_max = 2π × 1000 = 6283 rad/s
- g_m at I_abc_max ≈ 500 µA: g_m = 500µA / (2 × 26mV) = 9.6 mS
- C_apf = g_m / ω₀_max = 9.6 mS / 6283 = 1.53 nF → use 1.5 nF (C0G 0603)
- R_ref = 1/g_m at nominal I_abc = 10 kΩ to 100 kΩ range (set empirically)

For Group 2 (500 Hz – 5 kHz): C_apf ≈ 300 pF
For Group 3 (2 kHz – 20 kHz): C_apf ≈ 75 pF (use 68 pF or 82 pF)

#### Expo Converter (per group)

```
V_freq (from knob + CV sum) → [expo transistor pair] → I_abc → LM13700 Iabc pin
```
- Use matched NPN transistor pair (THAT340 or LM394) for temperature-stable expo conversion
- Trim pot for 1V/oct tracking calibration
- Reference current: set by resistor from +12 V to expo transistor base

#### Feedback Path (per group)

```
V_out_group_6 ──[R_fb_fixed]──┬──(−) summing amp ──► V_fb_sum → Group input
                               │
V_in ──[R_in_fixed]────────────┘

FEEDBACK knob sets: R_fb_pot in parallel with R_fb_fixed → effective feedback ratio g
```
Minimum feedback resistor (end-stop) ensures g never exceeds ~0.95.

#### DRY/WET Crossfader

Linear voltage-controlled crossfade using a dual VCA (e.g., V2164 quad VCA, 1 cell each
for L-wet and L-dry; second pair for R-wet and R-dry):
- V2164 is a quad VCA in SOIC-16; 2 cells for L (dry + wet), 2 cells for R (dry + wet)
- DRY/WET knob → complementary control voltages to dry and wet cells
- 1× V2164 per stereo pair

#### STEREO WIDTH

A simple exponential offset applied to the R channel expo converter reference only:
- WIDTH knob → small DC offset voltage added to V_freq_R only (not V_freq_L)
- Op-amp summer adds WIDTH_V to the R expo converter input
- WIDTH = 0: R exp is same as L → mono
- WIDTH max: R expo input is shifted, R ω₀ is higher (or lower) by several semitones

### IC / Component Selection (key ICs)

| Reference | Part Number | Package | Qty | Notes |
|---|---|---|---|---|
| OTA_x | LM13700M | SOIC-16 | 18 | Dual OTA; 1 per 2 APF stages; 9 per channel |
| APF_AMP_x | TL072CDT | SOIC-8 | 18 | Dual op-amp; 1 per 2 APF stages; 9 per channel |
| EXPO_x | THAT340 or LM394 | SOIC-8 | 3 | Matched NPN pair for expo converter (1 per group) |
| VCA_x | V2164D | SOIC-16 | 1 | Quad VCA for DRY/WET crossfader (L+R in one IC) |
| MIX_AMP_x | TL074CDT | SOIC-14 | 2 | Quad op-amp for summing, feedback, width offset circuits |
| C_apf_G1 | C0G / NP0 | 0603 | 12 | 1.5 nF (6 per channel × 2 channels) for Group 1 |
| C_apf_G2 | C0G / NP0 | 0603 | 12 | 300 pF for Group 2 |
| C_apf_G3 | C0G / NP0 | 0603 | 12 | 68–82 pF for Group 3 |

### Trim Pots

| Reference | Range | Purpose | Adjustment Procedure |
|---|---|---|---|
| RV_1VOCT_G1 | ±20% | Group 1 expo converter 1V/oct calibration | Sweep FREQ 1 CV by 1V; verify exact octave change in notch frequency |
| RV_1VOCT_G2 | ±20% | Group 2 expo converter 1V/oct calibration | Same |
| RV_1VOCT_G3 | ±20% | Group 3 expo converter 1V/oct calibration | Same |
| RV_FB_MAX_1 | 0.90–0.99 | Max feedback limit for Group 1 | Set so oscillation onset is just barely reachable |
| RV_FB_MAX_2 | 0.90–0.99 | Max feedback limit for Group 2 | Same |
| RV_FB_MAX_3 | 0.90–0.99 | Max feedback limit for Group 3 | Same |

### Power Draw Estimate
- 18× LM13700: ~3.4 mA per IC = ~61 mA
- 18× TL072 + ~4× TL074: ~30 mA
- 1× V2164: ~10 mA
- +12 V: ~55 mA | −12 V: ~55 mA (significant — plan thermal management)

### Known Circuit Challenges
- **IC count**: 18 LM13700 + 18 TL072 is large. Plan 2–3 stacked PCBs with ribbon cable.
- **Expo converter matching**: THAT340 or LM394 matched pair required for stable 1V/oct tracking across temperature; a single transistor from a general-purpose part will drift.
- **HF oscillation**: OTA stages at high Iabc (high frequency) can self-oscillate due to parasitic capacitance. Add small (22 pF) capacitors at each OTA output node and keep traces short.
- **Crosstalk L/R**: L and R share the same group frequencies but have separate OTA signal paths. Route L and R ground planes separately; do not route L signal adjacent to R signal on PCB.
- **Calibration burden**: 6 trim pots (3 expo converters + 3 feedback limits) must be calibrated per unit. Document the calibration procedure clearly in the assembly guide.
- **Sallen-Key note**: This spec uses OTA all-pass stages (not Sallen-Key). Sallen-Key is not suitable for voltage-controlled all-pass — OTA is the correct topology here.
