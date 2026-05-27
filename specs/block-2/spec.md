# Block 2: Dual LFO
Dual independent triangle-wave LFOs (0.05–20 Hz, ±5 V) with LED indicators; LFO1 normalizes into the mod bus.

DSP source: `plugin/src/dsp/LFO.hpp`, `plugin/src/Pogo.cpp` (lines 364–368)

---

## 1. Intent

Block 2 provides two continuously running triangle-wave low-frequency oscillators. Each
has a front-panel rate knob spanning 0.05 Hz (a 20-second period, useful for slow filter
sweeps) to 20 Hz (at the boundary of audio, approaching ring-modulation territory). Each
LFO drives a front-panel LED that brightens on positive half-cycles and dims on negative
half-cycles, giving a visual indication of rate and phase. Both LFOs have output jacks
so they can modulate other modules in the patch. LFO1 is the primary internal modulation
source: when the MOD_IN jack is unpatched, LFO1 automatically feeds the mod bus
processor, making the module self-animating out of the box. LFO2 is standalone — output
jack only, no automatic normalling.

---

## 2. Theoretical Design and Topology

### DSP-to-analog mapping

The DSP model is a phase-accumulator triangle oscillator:

```
speedHz = 0.05 × 400^param         (exponential, param ∈ [0, 1])
phase  += speedHz × dt             (phase ∈ [0, 1))
output  = (phase < 0.5) ? (4×phase − 1) : (3 − 4×phase)   ∈ [−1, +1]
V_out   = output × 5 V             (±5 V)
```

The hardware analog equivalent is a classic op-amp triangle oscillator: an integrator
whose output ramps linearly, feeding a Schmitt trigger comparator that flips its output
when the triangle reaches either threshold, which in turn changes the integrator's input
sign and reverses the ramp direction. This naturally generates a triangle wave at the
integrator output and a square wave at the comparator output.

### Transfer function

This is a nonlinear oscillator, not a linear time-invariant system, so an H(s) transfer
function does not fully describe it. The key relationships are:

**Triangle amplitude:** Set by the comparator threshold voltages. The Schmitt trigger
flips at ±V_th (set by positive feedback resistor ratio). The integrator ramps between
−V_th and +V_th. Target: V_th = 5 V to produce a ±5 V triangle.

**Oscillation frequency:**

```
f = V_th / (2 × R_int × C_int × V_sat)
```

where R_int and C_int are the integrator resistor and capacitor, and V_sat is the
comparator's output saturation voltage (approximately V_rail − 1 V ≈ 11 V for a
TL072 on ±12 V). Rearranging for the integrator time constant:

```
R_int × C_int = V_th / (2 × f × V_sat)
```

**Rate control — exponential law:** The DSP uses `speedHz = 0.05 × 400^param`, which
spans 0.05 to 20 Hz over the [0, 1] knob range — a ratio of 400, equivalent to ~8.6
octaves. In hardware, an exponential (antilog) response over this range is achieved by
combining a linear pot with an exponential converter (resistor-diode network biased for
~10 mV/decade) or simply by selecting a logarithmic-taper potentiometer (which provides
an approximate exponential response). A log-taper pot is the simpler implementation
and is sufficient for a rate control where precise pitch tracking is not required.

The rate control pot varies R_int by changing the current into the integrator, or
alternatively varies the control current in a V-to-I stage ahead of the integrator
capacitor.

### Topology: integrator + Schmitt trigger

```
Triangle oscillator — two op-amp halves per LFO (one TL072CDT):

Half A — Integrator:
  V_sq (comparator output) ──[R_INT]──►(−) TL072-A
                                              │
                                            C_INT  (to GND; op-amp (−) is virtual ground)
                                              │
                                         V_tri (op-amp output)
  (+) input tied to AGND (signal ground)
  Capacitor integrates: V_tri = −∫(V_sq / R_INT·C_INT) dt → linear ramp

Half B — Schmitt trigger (non-inverting comparator with hysteresis):
  V_tri ──────────────────────────────────►(−) TL072-B  ← inverting input follows triangle
                 R_fb_sq                          │
  V_sq ──[R_fb_sq]──►(+)──[R_HYS to GND]    V_sq (comparator output)
                                           (positive feedback via R_fb_sq sets ±V_th)

Feedback loop:
  V_sq = +V_sat: integrator ramps UP until V_tri > +V_th → Schmitt flips → V_sq = −V_sat
  V_sq = −V_sat: integrator ramps DOWN until V_tri < −V_th → Schmitt flips → V_sq = +V_sat
  Steady-state: triangle at integrator output; square wave at comparator output.
```

Two op-amp halves per LFO:
- Half A: integrator (produces the triangle)
- Half B: Schmitt trigger comparator (produces the square; drives integrator direction)

One TL072CDT (dual, SOIC-8) per LFO. Two packages total: U_LFO1, U_LFO2.

### LED brightness law

DSP: `brightness = (lfoRaw + 1) × 0.5`

This maps the ±1 LFO output linearly to [0, 1], meaning the LED is off at the negative
peak and full brightness at the positive peak. In hardware, the LED is driven directly
from the triangle output via a current-limiting resistor. The LED forward voltage drop
(~2 V for green) and resistor value determine the drive current. The LED naturally dims
at negative half-cycles (reverse-biased) and brightens at positive half-cycles —
matching the DSP model without any additional driver circuit.

### LFO1 normalling into MOD_IN

The LFO1 output connects to the tip-switching normalling ring of the MOD_IN jack.
When MOD_IN is unpatched, the tip-switch routes LFO1's output to the mod bus processor
input. When a cable is inserted into MOD_IN, the tip-switch disconnects LFO1 and the
external signal takes over. This is a passive mechanical normalling, requiring only a
physical PCB/panel trace connection.

### Hardware behavior notes

Items 1 and 3 below are intentional DSP advantages kept by design. Item 2 is now modeled in DSP.

1. **Phase reset:** The DSP `reset()` method zeroes the phase accumulator. There is no
   hardware phase reset circuit; LFOs free-run from power-on. This is acceptable for a
   modulation source.

2. **Waveform peak rounding:** The hardware triangle has slight rounding near the peaks
   due to integrator slew rate and Schmitt comparator switching delay. The DSP models
   this with a one-pole LP filter at 10× the LFO rate, producing the same characteristic
   soft peak rounding. This is sonically desirable (softer modulation edges).

3. **Rate law:** The DSP uses a precise exponential: `0.05 × 400^param`. A log-taper
   pot approximates this but does not match it exactly. For a modulation rate control
   (not a pitch-tracking application), this deviation is acceptable.

4. **Frequency accuracy:** Component tolerances on R_int and C_int affect absolute
   frequency. A 10% tolerance capacitor produces ±10% frequency error at any given
   pot position. No calibration trimmer is specified in Phase 3R for LFO rate — this is
   to be confirmed in Phase 3R design review.

→ References `aux/lfo-core.md`

---

## 3. Physical Design

### Component values and derivations

**Target frequency range:** 0.05 Hz to 20 Hz.

**Integrator capacitor:** C_INT = 47 nF C0G ceramic (0603). C0G mandatory —
X7R will cause LFO rate drift with temperature (audible as wandering sweep rate).

**Required R_INT range** (from frequency equation f = V_sat / (4 × V_H × R_INT × C_INT)):
```
V_sat ≈ 11 V, V_H = 5 V, C_INT = 47 nF

At f_max = 20 Hz:   R_INT = 11 / (4 × 5 × 20 × 47n) = 293 kΩ
At f_min = 0.05 Hz: R_INT = 11 / (4 × 5 × 0.05 × 47n) = 117 MΩ
```

Full range (293 kΩ to 117 MΩ) requires an effective resistance ratio of 400:1. Achieved
with a 1 MΩ log-taper pot (RV_LFO) plus two end resistors:
- **R_CW_END = 270 kΩ** in parallel with the pot at the CW end — limits R_INT_min:
  R_INT_min ≈ 270k || 0 = 270kΩ → f_max ≈ 11/(4×5×270k×47n) = 43 Hz  
  (fast side is intentionally wider; the log pot's CW end compresses, trimmed by assembly)
- **R_CCW_END = 10 MΩ** in series at the CCW end — limits R_INT_max ≈ 11 MΩ →  
  f_min ≈ 11/(4×5×11M×47n) ≈ 0.053 Hz ≈ 0.05 Hz ✓

Actual achievable range with these end resistors: ~0.05 Hz to ~25 Hz. The extra headroom
at the fast end is acceptable for a modulation source.

**Schmitt trigger thresholds (±5 V):** Positive feedback divider from comparator output
to (+) input, with a lower resistor to GND:
```
V_H = V_sat × R_HYS / (R_fb_sq + R_HYS)    [R_fb_sq = top (output→(+)), R_HYS = bottom ((+)→GND)]
5 V  = 11 × 82 kΩ / (100 kΩ + 82 kΩ)
V_H  = 11 × 0.451 = 4.96 V ≈ 5 V  ✓
```
Use R_fb_sq = 100 kΩ, R_HYS = 82 kΩ.

**LED brightness and half-wave rectification:**

A 1N4148W diode (SOD-123) in series with the LED anode ensures the LED only
illuminates on positive half-cycles (pulsing lamp effect, easier to read rate by eye):
```
V_tri_pos (>0) → D_LED (1N4148W, V_f ≈ 0.7V) → R_LED → LED → GND
LED only drives when V_tri > V_f_LED + V_f_diode ≈ 2.7 V
```

LED current-limiting resistor:
```
I_LED_target = 2 mA
V_source = 5 V (peak), V_f_LED ≈ 2.0 V (green), V_f_diode ≈ 0.7 V
R_LED = (5 − 2.0 − 0.7) / 0.002 = 1.15 kΩ  → use 1.2 kΩ standard
```

### Signal routing

```
RV_LFO1 (rate pot) → R_min → integrator input
Schmitt output → integrator input (sign reversal via comparator polarity)
Integrator output (triangle) → U_LFO1-A output → R_LED1 → LED_LFO1
                             → R_LFO1 (1 kΩ) → J_LFO1 output jack
                             → (normalling ring of J_MOD_IN) ← tip-switch controlled

RV_LFO2 (rate pot) → R_min → integrator input (U_LFO2-A)
Integrator output → R_LED2 → LED_LFO2
                 → R_LFO2 (1 kΩ) → J_LFO2 output jack
```

### Calibration points

No rate calibration trimmer is specified in the current design. The log-taper pot
produces an approximate exponential law adequate for a modulation rate control. If
tighter frequency accuracy is required in Phase 3R, a trimmer in series with R_min
can adjust the maximum frequency endpoint.

### Trim pots

None required. The 1 MΩ log-taper pot with end resistors provides adequate
rate-law approximation (±1 half-octave accuracy is sufficient for a modulation
source). If tighter maximum-rate calibration is needed during assembly, a 10 kΩ–
50 kΩ trimmer can be added in series with R_CW_END; this is not required for
functionality and is omitted from the bill of materials.

### Board assignment

Utility board. LFOs are non-audio signals (0.05–20 Hz); they do not require the
low-noise audio board ground plane. Rate pots and LEDs are on the control/panel board.
LFO output series resistors (R_LFO1, R_LFO2, 1 kΩ) logically belong to Block B's
output protection but are physically placed on the utility board near the LFO outputs.

→ References `aux/lfo-core.md` for detailed integrator + Schmitt trigger schematic.

---

## 4. Component Requirements

| Ref | Part | Package | Value | Qty | Board | Block | Function |
|---|---|---|---|---|---|---|---|
| U_LFO1 | TL072CDT | SOIC-8 | — | 1 | utility | block-2 | LFO1 integrator (half A) + Schmitt trigger (half B) |
| U_LFO2 | TL072CDT | SOIC-8 | — | 1 | utility | block-2 | LFO2 integrator (half A) + Schmitt trigger (half B) |
| RV_LFO1 | log-taper pot | 9 mm | 1 MΩ | 1 | control | block-2 | LFO1 rate (0.05–20 Hz); wiper → R_INT input |
| RV_LFO2 | log-taper pot | 9 mm | 1 MΩ | 1 | control | block-2 | LFO2 rate (0.05–20 Hz) |
| C_INT1 | cap, C0G | 0603 | 47 nF | 1 | utility | block-2 | LFO1 integrator timing cap; C0G mandatory |
| C_INT2 | cap, C0G | 0603 | 47 nF | 1 | utility | block-2 | LFO2 integrator timing cap; C0G mandatory |
| R_CW_END1 | resistor | 0603 | 270 kΩ | 1 | utility | block-2 | LFO1 CW end resistor; limits f_max ≈ 25 Hz |
| R_CW_END2 | resistor | 0603 | 270 kΩ | 1 | utility | block-2 | LFO2 CW end resistor |
| R_CCW_END1 | resistor | 0603 | 10 MΩ | 1 | utility | block-2 | LFO1 CCW end resistor; limits f_min ≈ 0.05 Hz |
| R_CCW_END2 | resistor | 0603 | 10 MΩ | 1 | utility | block-2 | LFO2 CCW end resistor |
| R_FB_SQ1 | resistor | 0603 | 100 kΩ | 1 | utility | block-2 | LFO1 Schmitt feedback (output → (+) input) |
| R_HYS1 | resistor | 0603 | 82 kΩ | 1 | utility | block-2 | LFO1 Schmitt hysteresis ((+) input → GND); sets V_H = 5V |
| R_FB_SQ2 | resistor | 0603 | 100 kΩ | 1 | utility | block-2 | LFO2 Schmitt feedback |
| R_HYS2 | resistor | 0603 | 82 kΩ | 1 | utility | block-2 | LFO2 Schmitt hysteresis |
| R_LED1 | resistor | 0603 | 1.2 kΩ | 1 | utility | block-2 | LFO1 LED current limit (≈2 mA at V_tri=+5V) |
| R_LED2 | resistor | 0603 | 1.2 kΩ | 1 | utility | block-2 | LFO2 LED current limit |
| D_LED1 | 1N4148W | SOD-123 | — | 1 | utility | block-2 | LFO1 LED half-wave rectifier (pulsing effect) |
| D_LED2 | 1N4148W | SOD-123 | — | 1 | utility | block-2 | LFO2 LED half-wave rectifier |
| LED_LFO1 | warm-white LED | 3 mm | — | 1 | panel | block-2 | LFO1 rate/phase indicator |
| LED_LFO2 | warm-white LED | 3 mm | — | 1 | panel | block-2 | LFO2 rate/phase indicator |
| R_OUT1 | resistor | 0603 | 1 kΩ | 1 | utility | block-2 | LFO1 output series protection to jack |
| R_OUT2 | resistor | 0603 | 1 kΩ | 1 | utility | block-2 | LFO2 output series protection to jack |
| C_BYPASS_LFO1 | cap, X7R | 0603 | 100 nF | 2 | utility | block-2 | U_LFO1 supply bypass (+12 V and −12 V pins) |
| C_BYPASS_LFO2 | cap, X7R | 0603 | 100 nF | 2 | utility | block-2 | U_LFO2 supply bypass (+12 V and −12 V pins) |
| J_LFO1 | PJ301M-12 | panel | — | 1 | panel | block-2 | LFO1 output jack |
| J_LFO2 | PJ301M-12 | panel | — | 1 | panel | block-2 | LFO2 output jack |
| J_MOD_IN | PJ301M-12 | panel | — | 1 | panel | block-2 | MOD_IN jack (LFO1 normalled via NC tip-switch) |
