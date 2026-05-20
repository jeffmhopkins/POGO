# Block 6: LP Filter 2

## Status
- Phase 1 (Audio Spec): [x] complete
- Phase 2 (Analog Model): [x] complete
- Phase 3 (Circuit Design): [x] complete — mirrors LP1 SVF topology

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

### Topology: OTA-C State-Variable Filter (SVF) — identical to LP Filter 1

LP2 uses the exact same circuit as LP1: two LM13700 OTA cells as integrators, TL074 as
summing amplifier, and an LM13700 OTA cell for voltage-controlled Q. See
`specs/block-5-lp1/spec.md` Phase 3 for the full schematic description and derivations.

LP2's Q VCA uses cell B of IC_Q_AB (the same LM13700 that handles LP1 Q on cell A). LP1 and
LP2 share one LM13700 for Q VCA per audio board — no V2164 IC required.

**Key differences from LP1:**
- Separate panel controls: CUTOFF 2, RESONANCE 2
- Separate CV inputs and mod attenuverters
- Separate expo converter (THAT340 pair) — independently calibrated from LP1
- Default f_ref2 set ~2 octaves above f_ref1 (≈ 2.5 kHz at 0 V) so LP2 starts above LP1

### IC / Component Selection

Same as LP1. Per stereo pair (L+R):

| Reference | Part Number | Package | Qty | Notes |
|---|---|---|---|---|
| LP2_OTA_L, LP2_OTA_R | LM13700M | SOIC-16 | 2 | Dual OTA; both cells = 2 integrators per channel |
| LP2_SUM_L, LP2_SUM_R | TL074CDT | SOIC-14 | 2 | Summing amp + output buffers |
| IC_Q_AB_L (cell B) | LM13700M | SOIC-16 | — | LP2 L Q VCA; cell A = LP1 L Q VCA (IC shared with LP1) |
| IC_Q_AB_R (cell B) | LM13700M | SOIC-16 | — | LP2 R Q VCA; cell A = LP1 R Q VCA (IC shared with LP1) |
| LP2_EXPO | THAT340 | SOIC-8 | 1 | Separate matched pair from LP1 expo |
| C1/C2 per channel | C0G/NP0 | 0603 | 4 | 47 nF (same value as LP1) |

### Trim Pots

| Reference | Range | Purpose | Adjustment |
|---|---|---|---|
| RV_LP2_REF | f_ref2 ±20% | 1V/oct reference frequency for LP2 | Adjust until C4 (0 V CV) = ~2.5 kHz |
| RV_LP2_1VOCT | 1V/oct ±5% | Expo converter tracking | Same one-octave step test as LP1 |
| RV_LP2_QMAX | Q 10–50 | Maximum resonance / self-oscillation onset | Same procedure as LP1 |

### Power Draw Estimate
+12 V: ~15 mA | −12 V: ~15 mA (IC_Q_AB LM13700 power shared with LP1 count)

### Known Circuit Challenges
All LP1 challenges apply. Additionally:
- **Independent expo calibration**: LP1 and LP2 expo converters must be calibrated separately
  even though they use the same circuit. A CV that tracks perfectly on LP1 may be slightly
  off on LP2 if component tolerances differ — always calibrate each stage independently.
- **Ground routing**: use a single ground wire between LP1 and LP2 sections of the PCB;
  do not rely on copper pours alone between sections that carry different signal voltages.
