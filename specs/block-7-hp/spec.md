# Block 7: HP Filter

## Status
- Phase 1 (Audio Spec): [x] complete
- Phase 2 (Analog Model): [x] complete
- Phase 3 (Circuit Design): [x] complete

---

## Phase 1: Audio / Functional Specification

### Sonic Intent
A 2-pole voltage-controlled highpass filter as the final filter stage. Applied after both LP
stages, the HP filter sculpts the low-frequency content: removing sub-bass rumble, adding
tightness to the low end, or — at high resonance — creating a resonant emphasis at the HP
cutoff that produces an aggressive, formant-like peak at the bottom of the frequency spectrum.

At low resonance: clean, transparent high-pass tilt. At high resonance: pronounced resonant
peak; sweeping the cutoff with CV creates a classic "bubble" or "quack" effect. At maximum
resonance: self-oscillation at the HP cutoff frequency.

Range: 20 Hz to ~5 kHz (high cutoff frequencies are less musically useful for an HP stage
placed after two LP filters; the HP is primarily for low-end sculpting).

### Parameters

| Name | Range | Default | Taper | Description |
|---|---|---|---|---|
| CUTOFF HP | 20 Hz – 5 kHz | 80 Hz | Logarithmic (1V/oct) | HP cutoff frequency |
| RESONANCE HP | 0 – 100% (self-osc) | 0% | Linear | Q from 0.5 to ∞; self-oscillation at HP cutoff at maximum |

### CV Modulation Targets

| Target | CV Range | Attenuverter | Notes |
|---|---|---|---|
| CUTOFF HP | ±5 V (1V/oct) | Yes | Exponential mapping; sweeps 20 Hz–5 kHz |
| RESONANCE HP | 0–10 V | Yes | CV drives resonance; 10 V = self-oscillation |

### Signal Levels (I/O)
- Input: ±5 V audio (from LP2, Block 6)
- Output: ±5 V audio (HP at low resonance); resonance peak may boost level by several dB

### Stereo Behavior
True stereo: independent L and R SVF circuits.
HP CUTOFF and HP RESONANCE apply equally to L and R.

### Edge Cases
- HP CUTOFF above LP1/LP2 CUTOFF: audio is attenuated by both LP and HP; effective bandpass.
  Output level may be very low. This is a valid (if unusual) patch.
- HP CUTOFF at 20 Hz: effective bypass for most audio content; acts as a DC blocker only.
- Self-oscillation at HP: generates a sine tone at HP CUTOFF. Unlike LP self-oscillation (which
  is filtered and therefore clean), the HP self-oscillation tone is the oscillation signal
  minus all below-cutoff content — still a sine, but with some high-frequency content from the
  SVF structure.

---

## Phase 2: Analog Behavior Model

### Transfer Function (2-pole HP, SVF topology)

```
H_HP(s) = s² / (s² + (ω₀/Q) × s + ω₀²)
```

- At s → 0 (DC): H_HP → 0 (blocks DC and low frequencies)
- At s → ∞ (high frequency): H_HP → 1 (passes high frequencies)
- At s = jω₀: |H_HP| = Q (resonance peak at cutoff for Q > 1/√2)

SVF simultaneously provides:
```
H_LP(s) = ω₀² / (s² + ω₀/Q × s + ω₀²)
H_BP(s) = (ω₀/Q) × s / (s² + ω₀/Q × s + ω₀²)
H_HP(s) = s² / (s² + ω₀/Q × s + ω₀²)
```
LP and BP outputs are available as bonus jacks (if panel space permits) — document
during panel design phase.

### Frequency Response
- Below cutoff: rolls off at 12 dB/octave (−40 dB/decade)
- At cutoff: resonance peak; peak height = 20 log₁₀(Q) dB above unity for Q ≫ 1
- Above cutoff: flat passband

### SVF Signal Flow and Parameter Mapping

```
V_in ──► [summing amp] ──► [OTA integrator 1: g_m1/C1] ──► V_BP ──► [OTA integrator 2: g_m2/C2] ──► V_LP
              ▲                                                                                              │
              │ (resonance feedback)                                                                         │
              └── [−1/Q × V_BP] ──── V_LP ◄─────────────────────────────────────────────────────────────────┘
              │
          V_HP = V_in − (1/Q) × V_BP − V_LP
```

**Voltage control of ω₀** (via OTA integrators):
```
ω₀ = g_m / C,  g_m = I_abc / (2 × V_T)
I_abc = I_ref × e^(V_ctrl / V_T)    (expo converter)
```
1V/oct: V_ctrl increases by 1 V → I_abc doubles → ω₀ doubles → f_cutoff doubles (one octave up).

**Q control**:
```
Q = (summing resistor ratio at feedback input)
```
In a classic SVF: Q is set by a single resistor in the feedback path. Voltage-controlled Q
requires a VCA or OTA in the feedback path — this design uses an LM13700 OTA cell.

---

## Phase 3: Circuit Design

### Topology: Operational Transconductance Amplifier State-Variable Filter (OTA-SVF)

Uses two OTA cells (LM13700) as the integrators in the SVF core. The summing amplifier uses
one half of a TL072. Q is controlled by a third LM13700 OTA cell in the resonance feedback
path — OTA output current injects into the SUM_AMP virtual-ground node, giving voltage-
controlled Q independently of cutoff.

```
V_in ──[R_in]──(−) SUM_AMP ───(out)──[OTA1 as integrator]──(out)─── V_BP
                  (+)=GND               │                              │
                                        C1                             │
                                        │                              │
                                       GND                 [OTA2 as integrator]──(out)─── V_LP
                                                                        │
                                                                        C2
                                                                        │
                                                                       GND

V_HP = SUM_AMP output = V_in − V_LP − (1/Q) × V_BP

Resonance (Q control):
V_BP ──[linearizing diodes]──► HP_Q_OTA IN+
                                HP_Q_OTA IN− → GND
                                HP_Q_OTA Iabc ←── RESONANCE CV (0–10 V via R_Iabc)
                                HP_Q_OTA I_out ──► SUM_AMP (−) virtual ground node
```

Higher Iabc = higher gm = more BP feedback current = higher Q → self-oscillation.
RESONANCE knob CW = higher Iabc = higher Q.

HP_Q_OTA is cell A of IC_Q_C (one LM13700 per audio board; cell B is spare or future use).

### Integrator capacitor values (HP range: 20 Hz – 5 kHz, approximately 8 octaves)

Target ω₀_min = 2π × 20 = 125.7 rad/s at minimum V_ctrl (e.g., I_abc = 1 µA)
Target ω₀_max = 2π × 5000 = 31,416 rad/s at maximum V_ctrl (e.g., I_abc = 250 µA)

At I_abc = 10 µA nominal: g_m = 10µA / (2 × 26mV) = 192 µS
For f₀ = 1 kHz (nominal): C = g_m / ω₀ = 192µS / 6283 = 30.6 nF → use 33 nF (0603, C0G)

(Verify range in simulation — exact values set during prototyping and trim pot calibration.)

### IC / Component Selection

| Reference | Part Number | Package | Qty | Notes |
|---|---|---|---|---|
| HP_OTA_L, HP_OTA_R | LM13700M | SOIC-16 | 2 | Dual OTA; 2 integrators per channel (1 IC per channel) |
| HP_SUM_L, HP_SUM_R | TL072CDT | SOIC-8 | 2 | SVF summing amplifier + HP output buffer (1 IC per channel) |
| IC_Q_C_L | LM13700M | SOIC-16 | 1 (Left audio board) | Cell A = HP L Q VCA; cell B = spare |
| IC_Q_C_R | LM13700M | SOIC-16 | 1 (Right audio board) | Cell A = HP R Q VCA; cell B = spare |
| HP_EXPO | THAT340 | SOIC-8 | 1 | Matched NPN pair for HP expo converter (shared L+R) |
| C_int_L, C_int_R | C0G/NP0 | 0603 | 4 | 33 nF integrator caps (2 per channel: C1_L, C2_L, C1_R, C2_R) |
| R_in_L, R_in_R | — | 0603 | 2 | 100 kΩ summing amp input resistor |
| C_VCC, C_VEE | — | 0603 | 100 nF | 8 | Decoupling, 2 per IC × 4 ICs |

### Trim Pots

| Reference | Range | Purpose | Adjustment |
|---|---|---|---|
| RV_HP_REF | ±20% | HP cutoff 1V/oct reference frequency | Adjust until C2 (at 0 V CV) = target frequency |
| RV_HP_1VOCT | ±5% | HP expo converter 1V/oct tracking | One-octave step test |
| RV_HP_QMAX | Q 10–50 | Maximum Q (self-oscillation onset) | Turn RESONANCE to max; verify clean sine output |

### Power Draw Estimate
- 2× LM13700 (integrators) + 1× LM13700 (Q VCA, IC_Q_C) + 2× TL072: ~15 mA
- +12 V: ~10 mA | −12 V: ~10 mA

### Known Circuit Challenges
- SVF summing amp phase: the summing amplifier inverts. To get the correct HP output polarity,
  the V_LP and V_BP signals must be inverted before summing, OR the final HP output buffer
  inverts again. Document polarity carefully in schematic.
- OTA integrator nonlinearity at large signals: LM13700 OTA linearity degrades at high signal
  levels. Keep the signal swing at the OTA inputs below ±50 mV for low distortion. Use a
  linearizing resistor (LM13700 has built-in linearizing diodes — connect linearizing diode inputs
  to the OTA differential inputs via small series resistors, typically 1 kΩ).
- Self-oscillation level: when Q → ∞, the oscillation amplitude is limited by op-amp/OTA
  clipping. The output will be a slightly distorted sine. Acceptable behavior.
- **LM13700 Q VCA Iabc**: R_Iabc sizing follows the same derivation as LP1/LP2. With
  R_in = 100 kΩ and C = 33 nF (HP), Q ≈ 100 kΩ × Iabc / 52 mV. RV_HP_QMAX sets Iabc_max.
  Design the RESONANCE pot control circuit so Q response feels linear to the user.
