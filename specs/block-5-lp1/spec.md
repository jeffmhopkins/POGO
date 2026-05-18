# Block 5: LP Filter 1

## Status
- Phase 1 (Audio Spec): [x] complete
- Phase 2 (Analog Model): [x] complete
- Phase 3 (Circuit Design): [ ] pending topology decision

---

## Phase 1: Audio / Functional Specification

### Sonic Intent
First voltage-controlled lowpass filter stage. Post-distortion tone shaping — takes the rich
harmonic content from the wavefolder/clipper and sculpts it into the desired texture. At low
resonance and high cutoff: transparent and clean. At high resonance and swept cutoff: classic
filter sweep. At maximum resonance: self-oscillation produces a sine-wave tone at the cutoff
frequency, which can be tuned via CV (1V/oct tracking).

### Parameters

| Name | Range | Default | Taper | Description |
|---|---|---|---|---|
| CUTOFF | 20 Hz – 20 kHz | 2 kHz | Logarithmic (1V/oct) | Lowpass cutoff frequency |
| RESONANCE | 0 – 100% (self-osc) | 0% | Linear | Q from 0.5 to ∞; self-oscillation begins near 95–100% |

### CV Modulation Targets

| Target | CV Range | Attenuverter | Notes |
|---|---|---|---|
| CUTOFF | ±5 V (1V/oct) | Yes | Exponential mapping; sweeps full 20 Hz–20 kHz range |
| RESONANCE | 0–10 V | Yes | 10 V drives filter to self-oscillation |

### Signal Levels (I/O)
- Input: ±5 V audio (may be harmonically complex from Block 4 distortion)
- Output: ±5 V audio at low resonance; resonance boosts level near cutoff — may reach ±8 V
  at high resonance; stay within op-amp headroom (±10.5 V)

### Stereo Behavior
True stereo: independent L and R filter circuits.
CUTOFF and RESONANCE knobs apply equally to L and R (shared panel controls).
No independent L/R frequency or resonance control.

### Edge Cases
- Self-oscillation: at RESONANCE = 100%, filter oscillates at the cutoff frequency. This is
  a musical feature — at this point CUTOFF knob and CV become a 1V/oct pitch control.
- CUTOFF at 20 Hz: heavy bass rolloff; effectively mutes most audio content. Useful for
  envelope-follower-driven filter sweeps that open the filter with transients.
- Hot input from distortion: at maximum distortion drive, signal may approach ±10 V. Filter
  must handle this without oscillating from input overload.

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

**1V/oct cutoff control:**
```
ω₀ = ω_ref × 2^(V_cv / 1V)

where ω_ref = 2π × f_ref  (f_ref = frequency at V_cv = 0V)
```
At V_cv = 0 V: f_cutoff = f_ref (set by calibration trim pot)
At V_cv = +1 V: f_cutoff = 2 × f_ref (one octave up)
At V_cv = −1 V: f_cutoff = 0.5 × f_ref (one octave down)

With a ±5 V range: 10 octave sweep (2^10 = 1024× frequency range).
Choose f_ref ≈ 630 Hz so that ±5 V spans 20 Hz (−5 V) to ~20 kHz (+5 V).

**Resonance to Q:**
```
Q = Q_max × RESONANCE_normalized

Q_max → ∞ at self-oscillation; practical limit: Q ≈ 50 at RESONANCE = 95%
```

---

## Phase 3: Circuit Design

### Topology Decision (pending VCV prototype testing)

The 2-pole lowpass filter for this block has several viable voltage-controlled topologies.
The VCV Rack prototype will be used to confirm the target sound before committing to hardware.
Three candidate topologies are documented below.

---

#### Topology A: OTA-Based Sallen-Key (recommended starting point)

The standard Sallen-Key LP topology uses two RC stages and a gain element. Replacing the resistors
with OTA transconductors gives voltage control over ω₀ via the OTA bias current.

```
V_in ──[OTA1]──┬──[OTA2]──(+) op-amp ──(out)── V_out
               │                  │
              [C1]              ──┤─ (C2)
               │                  │
              GND                GND

OTA bias current → I_abc = I_ref × e^(V_ctrl / V_T)   (expo converter)
ω₀ = g_m / √(C1 × C2),  g_m = I_abc / (2 × V_T)
```

**Pros:** Widely used in Eurorack; well-understood; integrates naturally with the APCF block
(same LM13700 family); self-oscillation behavior is controllable.

**Cons:** Requires expo converter (adds complexity and calibration); THD increases at high
frequencies due to OTA linearity limits; needs matched OTA cells.

**ICs:** 2× LM13700 halves (from shared IC with APCF), 1× TL072 op-amp, 1× expo transistor pair.
**Component values (starting point):** C1 = C2 = 10 nF, g_m_nom = ω₀_nom × C = 2π×1kHz × 10nF = 63 µS,
I_abc_nom = 63 µS × 2 × 26 mV = 3.3 µA.

---

#### Topology B: State-Variable Filter (SVF) — LP output tapped

The SVF uses two OTA-C integrators and a summing amplifier. Simultaneously produces LP, BP, and HP
outputs. Tapping the LP output gives the desired 2-pole lowpass response.

```
V_in ──[sum amp]──(out)── V_BP via [OTA-integrator 1]── V_LP
    ↑                         │
    └── (resonance feedback) ◄┘
              │
              ▼
           V_HP = V_in − V_BP × (1/Q) − V_LP
```

Transfer functions:
```
H_LP(s) = ω₀² / (s² + ω₀/Q × s + ω₀²)
H_BP(s) = ω₀ × s / (s² + ω₀/Q × s + ω₀²)
H_HP(s) = s² / (s² + ω₀/Q × s + ω₀²)
```

**Pros:** Inherently stable at high Q; self-oscillation is clean and controllable; BP and HP
outputs available as bonus jacks; Resonance (Q) is controlled by one resistor — easy panel control.
**Cons:** Requires two OTA integrators (same IC count as Topology A); output amplitude at self-
oscillation requires limiting; more complex summing network.

**ICs:** 1× LM13700 (both OTA cells as integrators), 1× TL074 (summing amp + output buffers),
expo converter.

---

#### Topology C: AS3320 / CEM3320 Dedicated Filter IC

The AS3320 (Alpha Semiconductor clone of the CEM3320) is a dedicated 4-pole LP filter with
built-in resonance control and expo converter. Can be configured for 2-pole response.

**Pros:** Extremely clean, very low noise; built-in expo converter; resonance is a single pin;
calibration is much simpler; classic Moog/Jupiter filter sound.
**Cons:** Proprietary part; higher cost; 4-pole primary mode (2-pole requires tapping the midpoint);
harder to source reliably.

**ICs:** 1× AS3320 per channel (2 total), standard biasing resistors.

---

### Topology to be confirmed during VCV Rack prototyping

Implement all three in the VCV plugin with a test switch. Compare:
- Frequency response accuracy
- Resonance behavior and self-oscillation quality
- Noise floor
- Component count vs. performance trade-off

Document the chosen topology here before starting PCB layout.

---

### Trim Pots (common to all topology candidates)

| Reference | Range | Purpose | Adjustment |
|---|---|---|---|
| RV_CUTOFF_REF | f_ref ±20% | 1V/oct reference frequency calibration | Adjust until C4 (0 V) = target reference frequency |
| RV_1VOCT | 1V/oct ±5% | Expo converter tracking | Play two notes 1 octave apart; adjust for exact octave |
| RV_RESON_MAX | Q 10–100 | Maximum resonance / self-oscillation onset | Turn RESONANCE to max; verify clean self-oscillation |

### Power Draw Estimate
- +12 V: ~15 mA | −12 V: ~15 mA (varies by topology; AS3320 is most efficient)

### Known Circuit Challenges
- 1V/oct expo converter temperature drift: must use matched transistor pair (THAT340) for stable tracking. Validate across temperature range (10°C – 40°C) during prototype bring-up.
- Self-oscillation amplitude: at Q → ∞, filter output grows unbounded in theory. Real circuit limits this by op-amp rail clipping. Add a soft-limiting circuit on the feedback path to prevent hard rail-to-rail clipping during self-oscillation.
- L/R gain matching at high resonance: L and R filters need closely matched RESONANCE control (common pot). If L/R resonance differs by >2%, noticeable stereo imbalance at self-oscillation. Use 1% resistors in resonance feedback path.
