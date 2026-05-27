# Block BP: Triple Bandpass SVF (Formant Filter)

## Status
- Phase 1R (Extract from code): [ ] complete
- Phase 2R (Analog model): [ ] complete
- Phase 3R (Circuit design): [ ] complete

---

## Phase 1R: Functional Specification (extracted from plugin code)

### Sources
`plugin/src/dsp/BandpassSVF.hpp`, `plugin/src/Pogo.cpp`, `docs/plugin-topology.md`

### Overview

Three independent bandpass resonator "formant groups" (BP1, BP2, BP3), each a
4-pole (two cascaded 2-pole) Andrew Simper trapezoidal SVF in bandpass mode.
All three groups share global polarity and distortion mode controls but have
independent frequency, Q (focus), and drive controls.

The entire BP section runs at 2× oversample rate (96 kHz at 48 kHz base) to
suppress aliasing in the distortion stage.

A BP_MIX dry/wet knob blends the LP1 output (dry) with the summed BP output (wet).
BP3 formant output is also tapped (post-distortion, pre-mix) to a dedicated
output jack pair.

### Block position in signal chain

```
LP1 output ──────────────────────────────────── (dry) ──→┐
                                                          BP_MIX → HP
ALT_BP_L/R → GAIN_BP3 ──→ BP input (bypasses VCA+LP1) ──→┘
                                  ↓
               [2× upsample]
               BP1 SVF → distort → tap
               BP2 SVF → distort → tap         ─summed→ [decimate] → wet
               BP3 SVF → distort → tap ─────────────────→ [decimate] → BP3_OUT
               [-bpTiltCv for R channel]
```

### Global parameters (shared across BP1/BP2/BP3)

| Name | Enum | Range | Default | Description |
|---|---|---|---|---|
| BP Offset | `BP_OFFSET_PARAM` | −5–5 V/oct | 0 | Master frequency offset added to all 3 formant freqs |
| BP Mix | `BP_MIX_PARAM` | 0–1 | 0.5 | Dry/wet blend (0=LP1 out, 1=full BP) |
| BP Polarity | `BP_POL_PARAM` | 0/1 | 0 | 0=positive (+1), 1=negative (−1); inverts all BP output |
| BP Dist Mode | `BP_DIST_PARAM` | 0/1/2 | 0 | Distortion mode: 0=soft clip, 1=hard clip, 2=wavefold |
| BP Offset CV Depth | `BP_FREQ_ATT_PARAM` | −1–1 | 0 | Attenuverter for BP_FREQ_INPUT |
| BP Tilt CV Depth | `BP_TILT_ATT_PARAM` | −1–1 | 0 | Attenuverter for BP_TILT_INPUT |

### Per-group parameters (×3 for BP1/BP2/BP3)

| Name | Enum | Range | Default | Description |
|---|---|---|---|---|
| BPn Freq | `BP{N}_FREQ_PARAM` | −5–5 V/oct | 0 | Per-group formant frequency |
| BPn Focus | `BP{N}_FOCUS_PARAM` | 0–1 | 0 | Q (resonance sharpness); exponential taper |
| BPn Drive | `BP{N}_DIST_PARAM` | 0–1 | 0.20 | Distortion drive; 0–0.20 = unity zone, 0.20–1.0 = drive zone |
| BPn Freq CV | `BP{N}_FREQ_ATT_PARAM` | −1–1 | 0 | Attenuverter for freq CV input |
| BPn Focus CV | `BP{N}_FOCUS_ATT_PARAM` | −1–1 | 0 | Attenuverter for focus CV input |
| BPn Drive CV | `BP{N}_DIST_ATT_PARAM` | −1–1 | 0 | Attenuverter for drive CV input |

### CV Inputs (per group ×3 = 9, plus 2 global = 11 BP-related inputs)

| Name | Enum | Notes |
|---|---|---|
| BP Offset CV | `BP_FREQ_INPUT` | Added to all 3 formant freqs via attenuverter |
| BP Tilt CV | `BP_TILT_INPUT` | L freq += tilt_cv×att; R freq −= tilt_cv×att |
| BPn Freq CV | `BP{N}_FREQ_INPUT` | Per-group, via attenuverter |
| BPn Focus CV | `BP{N}_FOCUS_INPUT` | Per-group, via attenuverter |
| BPn Drive CV | `BP{N}_DIST_INPUT` | Per-group, via attenuverter |

### Alternate input path
- `ALT_BP_L_INPUT`, `ALT_BP_R_INPUT`: When patched, feed the BP section directly,
  bypassing the VCA and LP1 stages. Uses the same `GAIN_BP3` pre-gain switch (1× / 5×).
- Normalling: ALT_BP_R normalizes to ALT_BP_L when only L is patched.

### Outputs
- `BP3_L_OUTPUT`, `BP3_R_OUTPUT`: BP3 formant distorted output, tapped before the
  dry/wet blend. Decimated from 2× back to base rate.
- Main signal path continues to HP after BP_MIX blend.

### Formant reference frequencies

| Group | f_ref | Typical range |
|---|---|---|
| BP1 | 200 Hz | ~20 Hz–20 kHz (±5 V at 1V/oct) |
| BP2 | 1500 Hz | ~20 Hz–20 kHz |
| BP3 | 6000 Hz | ~20 Hz–20 kHz |

### Frequency computation (per channel, per group)
```
L_freq[n] = F_REF[n] × 2^(BP_OFFSET_cv + BP{N}_FREQ_cv + BP_TILT_cv)
R_freq[n] = F_REF[n] × 2^(BP_OFFSET_cv + BP{N}_FREQ_cv − BP_TILT_cv)
```
Clamped to [10 Hz, 0.48 × sampleRate] before filter computation.

### Q / Focus law
`Q = 0.5 × 400^focus_param`
- focus=0 → Q=0.5 (very broad, ~4 octave bandwidth)
- focus=0.5 → Q~11
- focus=1.0 → Q=200 (very sharp, ~0.07 octave bandwidth)

Output is normalized by `1/Q²` so peak gain = 1/Q (bandwidth control, not amplitude).
**Does not self-oscillate by design** (Q²-normalization prevents runaway).

### Drive / Distortion (see also Block 4 spec)
Dual-zone mapping from drive param [0,1]:
- param ≤ 0.20: gain = param/0.20 (0→unity at 9am position — mute to clean)
- param > 0.20: d = (param−0.20)/0.80 → fed to mode-specific function

Modes (shared global switch `BP_DIST_PARAM`):
- 0 = Soft clip: `tanh(drive·x)/tanh(drive)`, drive = exp(d×4)−1
- 1 = Hard clip: gain = 1+4d, clip ±1
- 2 = Wavefold: `arcsin(sin(π/2 · (1+4d)·x)) × 2/π` (Buchla-style)

### Oversampling
2× (OS=2, OS_QUALITY=8). Upsampler inserts one zero-stuffed sample; decimator applies
anti-alias FIR with 8 coefficients per polyphase arm. The SVF + distortion run at 2fs.
BP3 uses separate decimators (`decBP3L`, `decBP3R`) for the output tap.

### Output summing and mix
```cpp
// Per oversampled sample:
for i in 0..2:
    distTapL[i] = Distortion(bandpassL.prevOut[i], driveCv[i], distMode)
    dSumL += distTapL[i]    // unity weight — 3 groups sum linearly

// After decimation:
bpOutL = bandL × (1−mix) + wetL × mix   // BP_MIX dry/wet at base rate
```
Unity-weight sum means 3 groups at full amplitude can reach 3× a single group.
Users manage level with BP_MIX and per-group drive settings.

---

## Phase 2R: Analog Behavior Model

### Transfer function (per SVF group)
Andrew Simper 2-pole SVF, bandpass output (v1 in Simper notation):

```
H_BP(s) = (g·k·s) / (s² + k·s + 1)    where g = tan(π·f0/fs), k = 1/Q
```

4-pole: two cascaded 2-pole stages → bandpass becomes 4th-order with −80 dB/decade
rolloff outside the passband. Center frequency and Q are shared between the two stages
(same g and k coefficients).

**Target analog topology:** OTA-C SVF using LM13700 (same topology as LP1/LP2/HP).
The OTA's transconductance Iabc sets the cutoff frequency; two OTAs per SVF stage.
Three independent SVF groups = 6 OTA cells per channel = 12 OTA cells total (6 LM13700s
dual, or 3 quad OTA ICs).

### Frequency response
- Center frequency: 1V/oct tracking (same expo converter as LP1)
- Q normalization: hardware gain cell (VCA with 1/Q² control law) after SVF
  This is the key design challenge — see Phase 3R.

### Nonlinearity
- The DSP applies distortion after the SVF output, not in the feedback path
- Hardware: separate distortion stage (see Block 4 spec) driven by each group's output

---

## Phase 3R: Circuit Design

### Topology
OTA-C bandpass SVF, identical to LP1/LP2 topology (see `specs/block-5-lp1/spec.md`),
but using the BP output tap (v1 in the state variable topology).

Key difference from LP1: **three independent groups** each requiring:
- 2× LM13700 (dual OTA) for 4-pole: 1 per 2-pole stage → 2 stages → 4 OTAs total
  (2 LM13700 packages per group)
- 1× op-amp buffer between stage 1 and stage 2 output
- 1× VGA cell for 1/Q² normalization (could be another LM13700 cell or THAT 2180)
- 1× expo converter cell for frequency control (shared THAT340 across groups is possible)

### IC count estimate (per stereo channel)
- LM13700: 6 packages (12 OTA cells: 2 per pole stage × 2 stages × 3 groups)
- Op-amps (TL072): ~6 packages (buffers, integrators, summing)
- Expo converter (THAT340): 1 package (handles 3 groups + LP1 with appropriate buffering)
- Distortion stage: see Block 4 spec

This is the most component-dense block in POGO. PCB area per channel: ~80 × 40 mm estimated.

### 1/Q² normalization
The DSP normalizes output by `1/Q²` to keep amplitude constant as Q changes.
In hardware, this requires a VGA (voltage-controlled amplifier) with a squared-law control.
Options:
- **THAT 2180 with squared CV**: pre-square the Q control voltage using a multiplier or
  lookup table (if MCU-based control)
- **Linear VGA at 1/Q**: implement 1/Q normalization only (−20 dB/decade vs Q),
  accept small amplitude variation vs DSP model
- **Skip normalization**: accept that high-Q sounds louder — more like a hardware resonator

**Recommendation:** Evaluate in prototype. Hardware resonators typically don't
normalize — the louder peak at high Q is often desirable musically.

### Known challenges
- Thermal tracking of 3 expo converters across temperature
- 1/Q² normalization requires non-trivial analog math
- 4-pole BP has narrower bandwidth than 2-pole — matches DSP but may be harder to tune
- Distortion after bandpass increases component count significantly

### Power draw estimate (rough)
- Each SVF group: ~8 mA / −8 mA (+12V / −12V) per channel
- 3 groups, stereo: ~48 mA / −48 mA
- Distortion stages (see Block 4): separate estimate
- Total BP block: **~50 mA / −50 mA** (rough)
