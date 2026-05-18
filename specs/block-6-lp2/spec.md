# Block 6: LP Filter 2

## Status
- Phase 1 (Audio Spec): [x] complete
- Phase 2 (Analog Model): [x] complete
- Phase 3 (Circuit Design): [ ] pending topology decision (mirrors LP Filter 1)

---

## Phase 1: Audio / Functional Specification

### Sonic Intent
A second 2-pole lowpass filter stage identical in topology to LP Filter 1 (Block 5), but with
completely independent controls and modulation. Placed in series after LP1, it extends the
tone-shaping capability in several ways:

- **Stacked for steeper rolloff**: with both cutoffs at the same frequency, you get
  approximately 24 dB/octave (two 2-pole stages in series).
- **Layered for complex response**: LP1 at low cutoff + LP2 at high cutoff creates a
  bandpass-like effect with resonant peaks at both frequencies.
- **Independent modulation**: LP1 cutoff driven by the envelope follower; LP2 cutoff driven
  by an LFO or separate CV — creates independent sweeping on the two stages.

Having two identical LP stages with separate CV and modulation inputs is the primary
differentiation from LP1.

### Parameters

| Name | Range | Default | Taper | Description |
|---|---|---|---|---|
| CUTOFF 2 | 20 Hz – 20 kHz | 8 kHz | Logarithmic (1V/oct) | Lowpass cutoff frequency (independent of LP1) |
| RESONANCE 2 | 0 – 100% (self-osc) | 0% | Linear | Q from 0.5 to ∞; independent of LP1 resonance |

### CV Modulation Targets

| Target | CV Range | Attenuverter | Notes |
|---|---|---|---|
| CUTOFF 2 | ±5 V (1V/oct) | Yes | Independent expo sweep; same range as LP1 |
| RESONANCE 2 | 0–10 V | Yes | Independent of LP1 resonance |

### Signal Levels (I/O)
- Input: output of LP1 (Block 5) — ±5 V audio, with possible level boost near LP1 resonance peak
- Output: ±5 V audio, LP2 resonance peak may boost level further

### Stereo Behavior
True stereo: independent L and R filter circuits, identical to LP1 architecture.
CUTOFF 2 and RESONANCE 2 knobs apply equally to L and R.

### Edge Cases
- Both cutoffs matched and both resonances at maximum: additive resonance — very sharp resonant
  peak. Level at resonance can be very high. Monitor output headroom carefully.
- LP2 cutoff below LP1 cutoff: effectively inverted order (LP2 is the dominant filter).
  No circuit problem — the result is simply the combined frequency response.

---

## Phase 2: Analog Behavior Model

### Transfer Function

Identical to LP1 (Block 5):
```
H_LP2(s) = ω₀_2² / (s² + (ω₀_2 / Q_2) × s + ω₀_2²)
```

Combined response of LP1 + LP2 in series:
```
H_combined(s) = H_LP1(s) × H_LP2(s)
```

When ω₀_1 = ω₀_2 and Q_1 = Q_2:
- Combined slope: 24 dB/octave above cutoff
- Combined passband: flat below cutoff
- Combined resonance peak: summed (much larger than single stage)

When ω₀_1 ≠ ω₀_2:
- Two separate knee points in the frequency response
- Bandpass-like region between the two cutoffs (if LP1 < LP2: output is LP-filtered at LP2
  and the range between LP1 and LP2 is attenuated by LP1 but not LP2)
- This is musically useful for independent sweep behavior

### Parameter Mapping
Same as LP1 — see Block 5 Phase 2 for expo converter formula.

Reference frequency for LP2: f_ref2 set independently via its own trim pot.
Default f_ref2: set slightly higher than f_ref1 so LP2 starts above LP1 by default.

---

## Phase 3: Circuit Design

### Topology
Mirror of LP Filter 1. Use the same topology as chosen for LP1 after VCV prototyping.

Both LP1 and LP2 should use the same circuit topology and same PCB layout (possibly the
same PCB with dual rows). This reduces the number of unique PCB designs and simplifies
calibration (same procedure for both stages).

**Key difference from LP1**: separate panel controls, separate CV inputs, separate modulation
attenuverters — but identical underlying circuit.

If using AS3320 (Topology C from LP1 spec): each filter stage needs its own AS3320 IC pair
(one per channel). LP1 and LP2 share a PCB with 4× AS3320 total.

If using OTA-C (Topology A or B): LP1 and LP2 each need their own LM13700 pair and expo converter.

### Trim Pots

| Reference | Range | Purpose | Adjustment |
|---|---|---|---|
| RV_CUTOFF_REF2 | f_ref2 ±20% | 1V/oct reference frequency for LP2 | Set independently from LP1 |
| RV_1VOCT_LP2 | 1V/oct ±5% | Expo tracking for LP2 | Same procedure as LP1 |
| RV_RESON_MAX2 | Q 10–100 | LP2 maximum resonance | Same procedure as LP1 |

### Power Draw Estimate
Same as LP1: +12 V: ~15 mA | −12 V: ~15 mA

### Known Circuit Challenges
Same as LP1 (Block 5). Additionally:
- Ensure LP1 and LP2 expo converters are independently calibrated — they share the same
  panel CV inputs but must track independently.
- Ground routing between LP1 and LP2 PCBs: use a single ground connection between boards;
  avoid forming a ground loop through the signal cable between stages.
