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
┌──────────────── R_fb ────────────────────┐
│                                          │
─── [Rate pot → V-to-I] → R_int ─── [C_int] ─── [TL072 integrator] ─── Triangle out (±5 V)
                                                         │
                                                    [TL072 Schmitt trigger comparator]
                                                    │                    │
                                                  −V_th                +V_th (set by R_pos_fb)
                                                    └──────────────── comparator output (square)
                                                    feeds back to integrator input via sign switch
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

### Hardware deviations from DSP model

1. **Phase reset:** The DSP `reset()` method zeroes the phase accumulator. There is no
   hardware phase reset circuit; LFOs free-run from power-on. This is acceptable for a
   modulation source.

2. **Waveform linearity:** The DSP triangle is perfectly linear. The hardware triangle
   has slight rounding near the peaks due to integrator slew rate and comparator switching
   delay. This is inaudible and sonically desirable (softer modulation edges).

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

**Integrator time constant:** Choose a nominal mid-range frequency of ~1 Hz at
pot center (50% rotation, consistent with DSP: `0.05 × 400^0.5 ≈ 1 Hz`).

At f = 1 Hz, V_th = 5 V, V_sat = 11 V:
```
R_int × C_int = 5 / (2 × 1 × 11) = 0.227 s
```

Choose C_int = 100 nF; then R_int_nominal = 2.27 MΩ at mid-rate.

The rate pot varies R_int over the range required to span 0.05–20 Hz:
```
At f_min = 0.05 Hz:  R_int = 5 / (2 × 0.05 × 11) = 4.55 MΩ
At f_max = 20 Hz:    R_int = 5 / (2 × 20 × 11)   = 11.4 kΩ
```

A 500 kΩ log-taper pot (RV_LFO) in series with a minimum resistance R_min = 10 kΩ
(floor resistor to prevent zero impedance) achieves this range approximately. The
log-taper mimics the exponential law; exact calibration is Phase 3R work.

**Schmitt trigger thresholds (±5 V):** Set by positive feedback resistor divider:
```
V_th = V_sat × R_lower / (R_upper + R_lower)
5 V  = 11 V × R_lower / (R_upper + R_lower)
```
Using R_upper = 120 kΩ, R_lower = 100 kΩ:
```
V_th = 11 × 100 / 220 = 5.0 V  ✓
```

**LED current-limiting resistor (R_LED):**
```
I_LED_target = 2 mA (visible but not blinding)
V_source = 5 V (peak positive triangle), V_f_LED ≈ 2.0 V (green)
R_LED = (5 − 2.0) / 0.002 = 1.5 kΩ  → use 1.5 kΩ standard
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

None specified at this phase. Revisit in Phase 3R.

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
| RV_LFO1 | log-taper pot | 9 mm | 500 kΩ | 1 | control | block-2 | LFO1 rate (0.05–20 Hz) |
| RV_LFO2 | log-taper pot | 9 mm | 500 kΩ | 1 | control | block-2 | LFO2 rate (0.05–20 Hz) |
| C_INT1 | cap, C0G | 0603 | 100 nF | 1 | utility | block-2 | LFO1 integrator timing capacitor |
| C_INT2 | cap, C0G | 0603 | 100 nF | 1 | utility | block-2 | LFO2 integrator timing capacitor |
| R_MIN1 | resistor | 0603 | 10 kΩ | 1 | utility | block-2 | LFO1 minimum rate resistor (floor) |
| R_MIN2 | resistor | 0603 | 10 kΩ | 1 | utility | block-2 | LFO2 minimum rate resistor (floor) |
| R_TH1_U | resistor | 0603 | 120 kΩ | 1 | utility | block-2 | LFO1 Schmitt upper threshold resistor |
| R_TH1_L | resistor | 0603 | 100 kΩ | 1 | utility | block-2 | LFO1 Schmitt lower threshold resistor |
| R_TH2_U | resistor | 0603 | 120 kΩ | 1 | utility | block-2 | LFO2 Schmitt upper threshold resistor |
| R_TH2_L | resistor | 0603 | 100 kΩ | 1 | utility | block-2 | LFO2 Schmitt lower threshold resistor |
| R_LED1 | resistor | 0603 | 1.5 kΩ | 1 | utility | block-2 | LFO1 LED current limit |
| R_LED2 | resistor | 0603 | 1.5 kΩ | 1 | utility | block-2 | LFO2 LED current limit |
| LED_LFO1 | green LED | 3 mm | — | 1 | panel | block-2 | LFO1 rate/phase indicator |
| LED_LFO2 | green LED | 3 mm | — | 1 | panel | block-2 | LFO2 rate/phase indicator |
| C_LFO1 | cap, X7R | 0603 | 100 nF | 2 | utility | block-2 | U_LFO1 supply decoupling (+12 V and −12 V) |
| C_LFO2 | cap, X7R | 0603 | 100 nF | 2 | utility | block-2 | U_LFO2 supply decoupling (+12 V and −12 V) |
| J_LFO1 | PJ301M-12 | panel | — | 1 | panel | block-2 | LFO1 output jack |
| J_LFO2 | PJ301M-12 | panel | — | 1 | panel | block-2 | LFO2 output jack |
| J_MOD_IN | PJ301M-12 | panel | — | 1 | panel | block-2 | MOD_IN jack (LFO1 normalled via tip-switch) |
