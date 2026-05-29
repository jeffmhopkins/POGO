# Block 2: Dual LFO
Dual independent triangle-wave LFOs (0.05–20 Hz, ±5 V) with LED indicators; LFO1 normalizes into the mod bus.

DSP source: `plugin/src/dsp/LFO.hpp`, `plugin/src/Pogo.cpp` (lines 364–368)

---

## 1. Intent

Block 2 provides two continuously running triangle-wave low-frequency oscillators. Each
has a front-panel rate trimpot (screwdriver-set preset) spanning 0.05 Hz (a 20-second period, useful for slow filter
sweeps) to 20 Hz (at the boundary of audio, approaching ring-modulation territory). Each
LFO drives a front-panel LED that brightens on positive half-cycles and dims on negative
half-cycles, giving a visual indication of rate and phase. Both LFOs have output jacks
so they can modulate other modules in the patch. LFO1 is the primary internal modulation
source: when the MOD_IN jack is unpatched, LFO1 automatically feeds the mod bus
processor, making the module self-animating out of the box. LFO2 is standalone — output
jack only, no automatic normalling.

---

## 2. Theoretical Design and Topology

> ✅ **FINALIZED 2026-05-29** — Rate network reworked to the drive-attenuator topology
> (fixed R_INT + trimpot attenuator on the Schmitt output) and verified against the
> plugin rate law and the components.yaml BOM. Transcribed in `kicad/nets/block-2.nets.yaml`.

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
f = V_sat / (4 × V_H × R_int × C_int)
```

where R_int and C_int are the integrator resistor and capacitor, V_sat is the
comparator's output saturation voltage (≈ 11 V for TL072 on ±12 V), and V_H is the
Schmitt trigger threshold (= 5 V). The factor of 4 arises from two half-periods each of
duration 2×V_H×R_int×C_int/V_sat. Rearranging for the integrator resistor:

```
R_int = V_sat / (4 × V_H × f × C_int)
```

**Rate control — drive-attenuator (FINALIZED 2026-05-29):** The DSP uses
`speedHz = 0.05 × 400^param`, spanning 0.05–20 Hz (a 400:1 range). Since
f ∝ 1/(R_int·C_int), covering 400:1 by varying R_int would need a 400:1 resistance
swing (≈590 kΩ → 234 MΩ) — impossible from a single 1 MΩ linear trimpot used as a
rheostat (series R is only additive). The 3296W is a cermet preset (linear taper only;
no log option), so the earlier "R_CW_END/R_CCW_END" rheostat scheme could not deliver
the range and is **superseded**.

Instead, R_int is **fixed** and the rate is set by **attenuating the Schmitt
square-wave drive into the integrator**. The trimpot is wired as a voltage divider on
V_sq; its wiper feeds R_int. The integrator charge current is V_drive/R_int = k·V_sq/R_int
with k ∈ [k_min, 1] the wiper fraction, so f scales linearly with k:

```
f = k · V_sat / (4 · V_H · R_int · C_int)
```

This covers the full 400:1 range from one linear trimpot. Because the trimpot is a
set-once preset, the (now linear-in-rotation) rate law is irrelevant — the user simply
turns to the desired rate during setup. A small floor resistor (R_FLOOR) at the divider
bottom bounds k_min so the LFO cannot stall at DC.

### Topology: integrator + Schmitt trigger

```
Triangle oscillator — two op-amp halves per LFO (one TL072CDT):

Rate attenuator (sets charge current):
  V_sq ──[RV_RATE top]──┐
                        ├── wiper = V_drive = k·V_sq  ──[R_INT]──►(−) TL072-A
  GND ──[R_FLOOR]──[RV_RATE bottom]┘   (k ∈ [k_min,1] set by trimpot position)

Half A — Integrator:
  V_drive (attenuated square) ──[R_INT fixed]──►(−) TL072-A
                                                     │
                                                   C_INT  (feedback; (−) is virtual ground)
                                                     │
                                                V_tri (op-amp output)
  (+) input tied to AGND (signal ground)
  Capacitor integrates: V_tri = −∫(V_drive / R_INT·C_INT) dt → linear ramp; rate ∝ k

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

3. **Rate law:** The DSP uses a precise exponential: `0.05 × 400^param`. The hardware
   trimpot is linear-taper; the rate set corresponds to a specific wiper position during
   setup, not a swept performance control. Exact exponential tracking is not required.

4. **Frequency accuracy:** Component tolerances on R_int and C_int affect absolute
   frequency. A 10% tolerance capacitor produces ±10% frequency error at any given
   pot position. No calibration trimmer is specified in Phase 3R for LFO rate — this is
   to be confirmed in Phase 3R design review.

→ References `aux/lfo-core.md`

---

## 3. Physical Design

> ✅ **FINALIZED 2026-05-29** — Rate network reworked to the drive-attenuator topology
> (fixed R_INT + trimpot attenuator on the Schmitt output) and verified against the
> plugin rate law and the components.yaml BOM. Transcribed in `kicad/nets/block-2.nets.yaml`.

### Component values and derivations

**Target frequency range:** 0.05 Hz to 20 Hz.

**Integrator capacitor:** C_INT = 47 nF C0G ceramic (0603). C0G mandatory —
X7R will cause LFO rate drift with temperature (audible as wandering sweep rate).

**Fixed integrator resistor R_INT** (sets f_max at full drive, k=1):
```
V_sat ≈ 11 V, V_H = 5 V, C_INT = 47 nF
R_INT = V_sat / (4 × V_H × f_max × C_INT) = 11 / (4 × 5 × 20 × 47n) = 585 kΩ
→ R_INT = 590 kΩ (E96, 1%)  → f_max ≈ 19.8 Hz at k = 1
```

**Rate attenuator (RV_RATE = 1 MΩ linear trimpot + R_FLOOR):** the trimpot is a divider
on V_sq — top (pin 3) to V_sq, bottom (pin 1) to GND via R_FLOOR, wiper (pin 2) to R_INT.
The wiper fraction k sets the charge current and thus f = k · f_max:
```
k_max ≈ 1                         → f_max ≈ 19.8 Hz   (wiper at top)
k_min = R_FLOOR / (RV + R_FLOOR)  → f_min ≈ k_min · f_max
R_FLOOR = 2.4 kΩ → k_min = 2.4k / (1M + 2.4k) ≈ 0.0024 → f_min ≈ 0.047 Hz ✓
```
R_INT (590 kΩ) loads the wiper in parallel with R_FLOOR (≈2.39 kΩ effective); the small
shift is absorbed when the preset is dialled in at assembly. Achievable range ≈0.05–20 Hz
from a single linear trimpot. C_INT must be C0G (timing stability).

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
LFO1 (U1 = TL072): integrator (A) + Schmitt (B)
  Schmitt out V_sq → RV1 top; RV1 bottom → R3 (R_FLOOR) → GND; RV1 wiper → R1 (R_INT) → U1A(−)
  U1A: (+) = GND, (−) = R1/C1 summing node, out = V_tri; C1 (C_INT) feedback (−)↔out
  Schmitt U1B: (−) = V_tri, (+) = R5(R_FB_SQ to V_sq)/R7(R_HYS to GND) node, out = V_sq
  V_tri → D1 (1N4148W) → R9 (R_LED 1.2 kΩ) → LED1 → GND   (half-wave pulsing indicator)
  V_tri → R11 (R_OUT 1 kΩ) → J5 (LFO1 jack)  and  → MOD_IN normalling ring (block-3)

LFO2 (U2): identical, standalone — V_tri → R12 → J6 (LFO2 jack); no normalling.
```

### Calibration points

The rate trimpot (RV1/RV2) IS the calibration: dial each LFO to the desired rate at
assembly. R_INT (590 kΩ) sets the fast endpoint; R_FLOOR (2.4 kΩ) sets the slow floor.
C_INT tolerance shifts absolute frequency but the preset absorbs it. No additional rate
trimmer is needed.

### Trim pots

RV1/RV2 (1 MΩ linear, Bourns 3296W) are the rate presets, wired as drive attenuators on
the Schmitt output (not as rheostats). Linear taper is correct — the rate law across
rotation is irrelevant for a set-once preset.

### Board assignment

Utility board. LFOs are non-audio signals (0.05–20 Hz); they do not require the
low-noise audio board ground plane. Rate pots and LEDs are on the control/panel board.
LFO output series resistors (R_LFO1, R_LFO2, 1 kΩ) logically belong to Block B's
output protection but are physically placed on the utility board near the LFO outputs.

→ References `aux/lfo-core.md` for detailed integrator + Schmitt trigger schematic.

---

## 4. Component Requirements

> ✅ **FINALIZED 2026-05-29** — Rate network reworked to the drive-attenuator topology
> (fixed R_INT + trimpot attenuator on the Schmitt output) and verified against the
> plugin rate law and the components.yaml BOM. Transcribed in `kicad/nets/block-2.nets.yaml`.

| Ref | Part | Package | Value | Qty | Board | Block | Function |
|---|---|---|---|---|---|---|---|
| U_LFO1 | TL072CDT | SOIC-8 | — | 1 | utility | block-2 | LFO1 integrator (half A) + Schmitt trigger (half B) |
| U_LFO2 | TL072CDT | SOIC-8 | — | 1 | utility | block-2 | LFO2 integrator (half A) + Schmitt trigger (half B) |
| RV_LFO1 | Bourns 3296W trimpot | through-hole | 1 MΩ | 1 | control | block-2 | LFO1 rate preset (0.05–20 Hz); wiper → R_INT input |
| RV_LFO2 | Bourns 3296W trimpot | through-hole | 1 MΩ | 1 | control | block-2 | LFO2 rate preset (0.05–20 Hz) |
| C_INT1 | cap, C0G | 0603 | 47 nF | 1 | utility | block-2 | LFO1 integrator timing cap; C0G mandatory |
| C_INT2 | cap, C0G | 0603 | 47 nF | 1 | utility | block-2 | LFO2 integrator timing cap; C0G mandatory |
| R_INT1 (R1) | resistor 1% | 0603 | 590 kΩ | 1 | utility | block-2 | LFO1 integrator input R (fixed); f_max ≈ 20 Hz at full drive |
| R_INT2 (R2) | resistor 1% | 0603 | 590 kΩ | 1 | utility | block-2 | LFO2 integrator input R (fixed) |
| R_FLOOR1 (R3) | resistor | 0603 | 2.4 kΩ | 1 | utility | block-2 | LFO1 rate-attenuator floor; sets f_min ≈ 0.05 Hz |
| R_FLOOR2 (R4) | resistor | 0603 | 2.4 kΩ | 1 | utility | block-2 | LFO2 rate-attenuator floor |
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
