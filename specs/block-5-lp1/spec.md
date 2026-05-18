# Block 5: LP Filter 1

## Status
- Phase 1 (Audio Spec): [x] complete
- Phase 2 (Analog Model): [x] complete
- Phase 3 (Circuit Design): [x] complete — SVF (OTA-C, LP output tapped)

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

### Topology: State-Variable Filter (OTA-C), LP output tapped

Two LM13700 OTA cells act as the integrators in the SVF core. The summing amplifier uses a
TL074. Q (resonance) is controlled by a V2164 VCA cell in the BP feedback path, giving
voltage-controlled resonance independently of cutoff. Tapping V_LP gives the 2-pole lowpass
output. V_BP and V_HP are available as auxiliary output jacks.

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
V_BP ──[V2164 VCA cell, gain = 1/Q]──► (−) input of SUM_AMP
```

Higher V2164 gain = less feedback = lower Q (wider, flatter).
RESONANCE knob wired so CW = more feedback = higher Q → self-oscillation.

### Signal Flow and Transfer Functions

```
H_LP(s) = ω₀² / (s² + ω₀/Q × s + ω₀²)    ← primary output
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

At maximum I_abc (≈10 mA for f = 20 kHz):
```
g_m_max = 10 mA / 52 mV = 192 mS
ω₀_max = g_m_max / C = 192 mS / 47 nF = 4.09 Mrad/s → f ≈ 650 kHz
```
The OTA is capable well beyond 20 kHz; expo converter scaling limits the useful range.

### IC / Component Selection

| Reference | Part Number | Package | Qty | Notes |
|---|---|---|---|---|
| LP1_OTA_L, LP1_OTA_R | LM13700M | SOIC-16 | 2 | Dual OTA; both cells = 2 integrators per channel |
| LP1_SUM_L, LP1_SUM_R | TL074CDT | SOIC-14 | 2 | Summing amp + HP/BP/LP output buffers (1 per channel) |
| LP1_VCA | V2164D | SOIC-16 | 1 | Quad VCA; 2 cells for L resonance + 2 cells for R resonance |
| LP1_EXPO | THAT340 or LM394 | SOIC-8 | 1 | Matched NPN pair for expo converter (L+R share one expo) |
| C1_L, C2_L, C1_R, C2_R | C0G/NP0 | 0603 | 4 | 47 nF integrator capacitors |
| R_in_L, R_in_R | — | 0603 | 2 | 100 kΩ summing amp input resistor |
| C_VCC, C_VEE | — | 0603 | 100 nF | 8 | Decoupling, 2 per IC × 4 ICs |

### Trim Pots

| Reference | Range | Purpose | Adjustment |
|---|---|---|---|
| RV_LP1_REF | f_ref ±20% | 1V/oct reference frequency | Adjust until C4 (0 V CV) = 630 Hz at LP1 output |
| RV_LP1_1VOCT | 1V/oct ±5% | Expo converter tracking calibration | One-octave step: +1 V CV should double cutoff frequency |
| RV_LP1_QMAX | Q 10–50 | Maximum resonance / self-oscillation onset | Turn RESONANCE to max; verify clean, stable sine output |

### Power Draw Estimate
- 2× LM13700 + 2× TL074 + 1× V2164 (shared with LP2): ~15 mA
- +12 V: ~15 mA | −12 V: ~15 mA

### Known Circuit Challenges
- **Expo converter temperature drift**: THAT340 matched pair required for stable 1V/oct tracking. Calibrate at room temperature; verify at 10°C and 40°C extremes during bring-up.
- **Self-oscillation amplitude**: at Q → ∞, output amplitude is limited by OTA/op-amp rail clipping. Add a soft limiter (BAT54 anti-parallel diodes across feedback R in the SUM_AMP) to prevent hard clipping during self-oscillation.
- **V2164 Q control law**: V2164 gain is exponential in its control voltage. The RESONANCE pot wiring should shape the control voltage so Q response feels approximately linear to the user.
- **L/R resonance matching**: L and R use separate V2164 cells but the same control voltage from the RESONANCE pot. If cells are mismatched, stereo imbalance at high Q is audible. V2164 cells on the same die are well-matched; use adjacent cells (cells 1+2 for L, cells 3+4 for R).
- **V2164 shared with LP2**: the one V2164 (quad) serves both LP1 and LP2 Q control (2 cells per filter pair). Verify this sharing does not create crosstalk between LP1 and LP2 resonance control.
