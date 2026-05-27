# Block 6: Triple Bandpass + Distortion
Three independent 2-pole OTA-C SVF bandpass resonators (formant filters F1/F2/F3) with per-group drive and a global distortion mode switch; runs at 2× oversampling.

DSP source: `plugin/src/dsp/BandpassSVF.hpp`, `plugin/src/dsp/Distortion.hpp`, `plugin/src/Pogo.cpp` (lines 410–475)

---

## 1. Intent

Three bandpass resonators tuned to low (F1 ~200 Hz), mid (F2 ~1500 Hz), and high (F3 ~6000 Hz) formant regions. Together they act as a talking/formant filter, vowel shape sculptor, or comb-like resonator bank.

**BP_OFFSET** shifts all three groups together (master frequency offset); each group also has an independent FREQ offset relative to its f_ref. **BP_TILT** spreads L and R independently — L gets +tiltV, R gets −tiltV, creating stereo width by separating the formant positions in each channel.

**BP_MIX** dry/wet blend allows dialing from pure LP1 output (dry) to full formant stack (wet). At 50% (default) the formants add to the underlying LP1 texture.

**Distortion** runs inside the oversampled loop, post-SVF, pre-mix. One global `BP_DIST` switch selects Soft Clip / Hard Clip / Wavefold across all three groups simultaneously. Per-group `DRIVE` controls the distortion depth independently. The BP3 post-distortion tap (before mix) is available at `BP3_L/R_OUT` jacks.

**ALT path**: `ALT_BP_L/R` jacks feed the BP input directly (bypassing VCA + LP1), with `GAIN_BP3` pre-gain (1× or 5×). When ALT jacks are patched, BP processes the ALT signal instead of the LP1 output.

**2× oversampling** is applied to the full BP + distortion section to reduce aliasing from the nonlinear distortion stages.

---

## 2. Theoretical Design and Topology

### SVF Groups (3 independent resonators)

Each group is a 2-pole state-variable filter (BP output only). DSP uses 4-pole (two cascaded 2-pole stages per group) for testing; **hardware spec is 2-pole per group** (one OTA-C SVF per group per channel):

```
H_BP(s) = (ω₀/Q · s) / (s² + ω₀/Q · s + ω₀²)
```

Peak at s = jω₀: |H_BP| = 1/Q (before normalization); DSP normalizes by 1/Q² so peak gain = 1/Q regardless of Q setting. Hardware: resistor network at SUM_AMP input achieves 1/Q² normalization (see Physical Design).

**f_ref per group** (at 0V CV):
| Group | f_ref | Formant |
|---|---|---|
| BP1 | 200 Hz | Low vowel body (F1) |
| BP2 | 1500 Hz | Mid vowel / consonant (F2) |
| BP3 | 6000 Hz | High formant / sibilance (F3) |

**Frequency control:**
```
f₀ = f_ref[i] × 2^(BP_OFFSET + BP_FREQ_i + BP_TILT × ±1)
```
where BP_TILT applies +tiltV on L channel, −tiltV on R channel.

**Q control:**
```
DSP: Q = 0.5 × 400^qParam  (range 0.5–200; does NOT self-oscillate by design)
Hardware: Q = 52mV / (Iabc × R_in)
```
BP Q maximum is ~200 at hardware (Iabc → minimum before instability threshold). Self-oscillation is suppressed — BP groups are resonators, not oscillators.

### Distortion (inside oversampled loop)

Three modes selected by `BP_DIST` (global switch, 0/1/2):

**Soft Clip (mode 0):**
```
drive = exp(d × 4) − 1       (0 to ~54×)
y = tanh(drive × x) / tanh(drive)
```
At d=0: unity. At d=1: heavy saturation. Preserves dynamics at low drive.

**Hard Clip (mode 1):**
```
g = 1 + d × 4    (1–5× gain)
y = clamp(g × x, −1, +1)
```
Linear gain into hard rails. Aggressive, brick-wall limiting.

**Wavefold (mode 2, Buchla-style):**
```
y = asin(sin(π/2 × (1 + d × 4) × x)) × 2/π
```
Folds signal back on itself. Even harmonics, formant-like timbres at high drive.

**Drive law (all modes):**
```
driveParam ≤ 0.20: y = x × (driveParam / 0.20)     (unity at driveParam=0.20 = 9-o'clock)
driveParam >  0.20: d = (driveParam − 0.20) / 0.80  → above mode equations
```
Input normalized to ±1 (÷5V); output scaled back to ±5V. Input: SVF BP output per group.

### BP_MIX blend

```
BP_out = (1 − mix) × LP1_output + mix × sum(distorted_groups)
```
Dry (mix=0): LP1 output passes through unmodified. Wet (mix=1): full formant/distortion. Default mix=0.5.

### 2× Oversampling

Full BP+distortion runs at 2× sample rate. Upsampler quality=8 (~90 dB stopband). Decimator applied after distortion to return to base rate. Separate decimator for BP3 output tap.

### Hardware Deviation from DSP

| DSP | Hardware |
|---|---|
| 4-pole BP (two cascaded SVF stages per group) | 2-pole BP (one OTA-C SVF per group per channel) — 4-pole doubles IC count and PCB area with marginal sonic benefit |
| Integer polarity switch (±1) | Analog polarity inversion via CD4053 analog switch or inverting op-amp switch |
| 2× oversampling in software | Hardware SVF runs at audio rate; oversampling implemented in ADC/DAC chain if needed (optional; analog SVF inherently alias-free) |

→ See aux-ota-c-svf.md for SVF topology; aux-distortion.md for distortion cells.

---

## 3. Physical Design

### OTA-C SVF instances

Three groups × two channels (L + R) = **6 OTA-C SVF instances**. Each instance requires:
- 1× LM13700 OTA cell as integrator (one IC = 2 cells = one group, one channel)
- 1× TL072 half as SUM_AMP

Grouping per IC:
- Per group: `BP_OTA_G1_L`, `BP_OTA_G1_R` etc. — one LM13700 per group per channel (dual OTA: cell A + cell B = integrator + Q VCA, OR cell A/B for two channels of same group)
- Conservative count: 3 groups × 2 channels × 1 LM13700 = **6× LM13700** for integrators + Q VCAs

**Q normalization (1/Q² at SUM_AMP):**
Standard SVF BP peak is 1× (ignores Q). To get 1/Q² normalization: add a second feedback path proportional to −v2 (LP output) at the SUM_AMP input. This effectively scales the SUM_AMP gain by 1/Q². Simpler approach: scale the BP output by 1/Q² in an external op-amp stage — preferred for hardware clarity.

**Stereo tilt implementation:**
- BP_TILT generates +V_tilt (from mod bus via attenuverter)
- +V_tilt added to L-channel expo converter offset sum
- −V_tilt generated by TL072 inverting unity buffer; added to R-channel expo converter offset sum
- One TL072 half used as tilt inverter (shared across all 3 groups, same tilt offset applied to all)

**Expo converters:**
- One THAT340 per group (BP1, BP2, BP3) — 3× THAT340 total — each shared between L and R channels
- Different f_ref per group requires separate expo trims (RV_BP1_REF, RV_BP2_REF, RV_BP3_REF)

**Distortion hardware (see aux-distortion.md):**
- Three sub-circuit chains per group: SC / HC / WF all running simultaneously
- CD4053 triple 2-channel analog mux per group selects which mode's output passes
- All 3 CD4053 select pins tied together → BP_DIST switch controls all groups simultaneously
- One 3-position slide switch (PogoSwitchH3) → 2 select lines to all 3 CD4053 ICs
- Distortion runs post-SVF at audio rate (no oversampling in analog hardware)
- BP3 output tap: taken after distortion stage on group 3, available at BP3_L/R_OUT jacks

**Oversampling:**
- Hardware runs at base rate (no analog oversampling); 2× oversampling is a software DSP artifact
- Digital oversampling reduces aliasing from nonlinear distortion in software; analog hardware inherently alias-free

**Board assignment:** BP SVF and distortion on audio board. BP control pots and jacks on control board. THAT340s on audio board near their respective SVF clusters.

### Trim Pots

| Ref | Range | Purpose |
|---|---|---|
| RV_BP1_REF | ±20% f_ref | BP1 cutoff reference (target: 200 Hz at 0V) |
| RV_BP2_REF | ±20% f_ref | BP2 cutoff reference (target: 1500 Hz at 0V) |
| RV_BP3_REF | ±20% f_ref | BP3 cutoff reference (target: 6000 Hz at 0V) |
| RV_BP1_1VOCT | ±5% tracking | BP1 expo 1V/oct calibration |
| RV_BP2_1VOCT | ±5% tracking | BP2 expo 1V/oct calibration |
| RV_BP3_1VOCT | ±5% tracking | BP3 expo 1V/oct calibration |
| RV_BP1_QMAX | V_bias | BP1 Q maximum point |
| RV_BP2_QMAX | V_bias | BP2 Q maximum point |
| RV_BP3_QMAX | V_bias | BP3 Q maximum point |

### Integrator Cap Derivation

BP1 (f_ref = 200 Hz): C = 192µS/(2π×200) = 153 nF → use 150 nF (C0G, 0805)
BP2 (f_ref = 1500 Hz): C = 192µS/(2π×1500) = 20.4 nF → use 22 nF (C0G, 0603)
BP3 (f_ref = 6000 Hz): C = 192µS/(2π×6000) = 5.1 nF → use 4.7 nF (C0G, 0603)

(Exact values adjusted via RV_BPx_REF trim; derive from nominal at I_abc = 10µA.)

### Power Draw Estimate

- 6× LM13700 (SVF integrators + Q VCAs): ~18mA
- 6× TL072 (SUM_AMPs + output buffers): ~12mA
- 3× THAT340 (expo converters): ~3mA
- 3× CD4053 (distortion mux): ~1mA
- Distortion sub-circuits (SC/HC/WF): ~6mA (TL072 op-amp stages)
- **+12V: ~25mA | −12V: ~25mA**

---

## 4. Component Requirements

| Ref | Part | Package | Value | Qty | Board | Block | Function |
|---|---|---|---|---|---|---|---|
| BP1_OTA_L, BP1_OTA_R | LM13700M | SOIC-16 | — | 2 | audio | block-6 | BP1 integrator + Q VCA (L and R, one IC each) |
| BP2_OTA_L, BP2_OTA_R | LM13700M | SOIC-16 | — | 2 | audio | block-6 | BP2 integrator + Q VCA (L and R) |
| BP3_OTA_L, BP3_OTA_R | LM13700M | SOIC-16 | — | 2 | audio | block-6 | BP3 integrator + Q VCA (L and R) |
| BP_SUM_G1_L, BP_SUM_G1_R | TL072CDT | SOIC-8 | — | 2 | audio | block-6 | BP1 SUM_AMP + output buffer (L and R) |
| BP_SUM_G2_L, BP_SUM_G2_R | TL072CDT | SOIC-8 | — | 2 | audio | block-6 | BP2 SUM_AMP + output buffer (L and R) |
| BP_SUM_G3_L, BP_SUM_G3_R | TL072CDT | SOIC-8 | — | 2 | audio | block-6 | BP3 SUM_AMP + output buffer (L and R) |
| BP_TILT_INV | TL072CDT | SOIC-8 | — | 1 | audio | block-6 | Tilt inverter (half A = −V_tilt; half B spare) |
| BP1_EXPO, BP2_EXPO, BP3_EXPO | THAT340 | SOIC-8 | — | 3 | audio | block-6 | V/oct expo converter per group (L+R shared) |
| BP_DIST_MUX_1, _2, _3 | CD4053 | SOIC-16 | — | 3 | audio | block-6 | Triple 2-ch mux: SC/HC/WF mode select per group |
| BP_DIST_OP_x | TL072CDT | SOIC-8 | — | 6 | audio | block-6 | Distortion op-amp stages (SC/HC gain, WF fold) |
| C_int_BP1 | C0G/NP0 | 0805 | 150 nF | 4 | audio | block-6 | BP1 integrator caps (2 per channel × L+R) |
| C_int_BP2 | C0G/NP0 | 0603 | 22 nF | 4 | audio | block-6 | BP2 integrator caps |
| C_int_BP3 | C0G/NP0 | 0603 | 4.7 nF | 4 | audio | block-6 | BP3 integrator caps |
| R_in_BP | — | 0603 | 100 kΩ | 6 | audio | block-6 | SUM_AMP input resistors (one per group per channel) |
| RV_BP1_REF, _2, _3 | trimpot | SMD | — | 3 | audio | block-6 | f_ref calibration per group |
| RV_BP1_1VOCT, _2, _3 | trimpot | SMD | — | 3 | audio | block-6 | 1V/oct tracking per group |
| RV_BP1_QMAX, _2, _3 | trimpot | SMD | — | 3 | audio | block-6 | Q maximum calibration per group |
| SW_DIST | "3-pos slide" | panel | — | 1 | panel | block-6 | BP_DIST_PARAM: Soft/Hard/Fold |
| SW_POL | "2-pos slide" | panel | — | 1 | panel | block-6 | BP_POL_PARAM: Positive/Negative polarity |
| RV_BP_OFFSET | xl knob | 9mm | — | 1 | control | block-6 | BP_OFFSET master freq offset (±5V/oct) |
| RV_BP_MIX | "large knob" | 9mm | — | 1 | control | block-6 | BP_MIX dry/wet blend |
| RV_BP_FREQ_ATT | trimpot | 9mm | — | 1 | control | block-6 | BP_FREQ_ATT attenuverter |
| RV_BP_TILT_ATT | trimpot | 9mm | — | 1 | control | block-6 | BP_TILT_ATT attenuverter |
| RV_BP1_FREQ, RV_BP2_FREQ, RV_BP3_FREQ | knob | 9mm | — | 3 | control | block-6 | Per-group freq offset |
| RV_BP1_FOCUS, RV_BP2_FOCUS, RV_BP3_FOCUS | knob | 9mm | — | 3 | control | block-6 | Per-group Q (Focus) |
| RV_BP1_DIST, RV_BP2_DIST, RV_BP3_DIST | knob | 9mm | — | 3 | control | block-6 | Per-group distortion drive |
| J_BP3_L, J_BP3_R | PJ301M-12 | panel | — | 2 | panel | block-6 | BP3 formant tap output jacks |
| J_BP_FREQ_IN, J_BP_TILT_IN | PJ301M-12 | panel | — | 2 | panel | block-6 | BP master freq + tilt CV override jacks |
| J_BP1_FREQ_IN through J_BP3_DIST_IN | PJ301M-12 | panel | — | 9 | panel | block-6 | Per-group CV override jacks (freq, focus, drive × 3) |
