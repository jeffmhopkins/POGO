# Block 2: Dual LFO
Dual independent triangle-wave LFOs (0.05–20 Hz, ±5 V) with LED indicators; both feed the MOD_SRC switch.

DSP source: `plugin/src/dsp/LFO.hpp`, `plugin/src/Pogo.cpp` (LFO process; MOD_SRC selector 363–366; output jacks + LED lights 500–505)

---

## 1. Intent

Block 2 provides two continuously running triangle-wave low-frequency oscillators. Each
has a front-panel rate pot (9mm, log taper — the same panel-pot family as the
attenuverters) spanning 0.05 Hz (a 20-second period, useful for slow filter
sweeps) to 20 Hz (at the boundary of audio, approaching ring-modulation territory). Each
LFO drives a front-panel LED that follows the LFO voltage over the **whole cycle**
(brightest at the positive peak, fully dark only at the negative peak — a "breathing"
indicator), giving a visual indication of rate and phase. Both LFOs have output jacks so
they can modulate other modules in the patch.

Internally, both LFOs feed the **MOD_SRC** selector (a 3-position panel switch: LFO 1 /
LFO 2 / External), whose output drives the mod bus processor. In the LFO 1 / LFO 2
positions the chosen LFO animates the module; in the External position the mod bus is
driven by the MOD_IN jack only (0 V if unpatched). This replaces the older "LFO1
auto-normals into MOD_IN" scheme — selection is now an explicit switch, and **both** LFO
outputs are always live at their jacks regardless of switch position. (The MOD_SRC switch
itself and the MOD_IN-as-External wiring live in block-3; block 2 only provides the two
LFO feeds to it.)

---

## 2. Theoretical Design and Topology

> ✅ **FINALIZED 2026-05-29; pot updated 2026-05-30** — Rate network uses the drive-attenuator
> topology (fixed R_INT + pot attenuator on the Schmitt output), verified against the plugin
> rate law and the components.yaml BOM. The rate control is a **9mm log-taper panel pot**
> (RD901F family, as the attenuverters) — a player control, not a screwdriver trimmer.
> Transcribed in `specs/block-2/block-2.nets.yaml`.

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

**Rate control — drive-attenuator (FINALIZED 2026-05-29; pot updated 2026-05-30):** The DSP
uses `speedHz = 0.05 × 400^param`, spanning 0.05–20 Hz (a 400:1 range). Since
f ∝ 1/(R_int·C_int), covering 400:1 by varying R_int would need a 400:1 resistance
swing (≈590 kΩ → 234 MΩ) — impractical from a single pot used as a rheostat (series R is
only additive). So the earlier "R_CW_END/R_CCW_END" rheostat scheme is **superseded**.

Instead, R_int is **fixed** and the rate is set by **attenuating the Schmitt
square-wave drive into the integrator**. The pot is wired as a voltage divider on
V_sq; its wiper feeds R_int. The integrator charge current is V_drive/R_int = k·V_sq/R_int
with k ∈ [k_min, 1] the wiper fraction, so f scales linearly with k:

```
f = k · V_sat / (4 · V_H · R_int · C_int)
```

The rate control is a **9mm log-taper panel pot** (RD901F family — the same panel-pot type as
the attenuverters and MOD_SCALE), **not** a screwdriver trimmer: it is meant to be swept by
hand. The **log taper** makes the wiper fraction k rise roughly exponentially across rotation,
so f (∝ k) approximates the plugin's `0.05 × 400^param` law over the throw — a musical sweep
rather than a linear one bunched at one end. A small floor resistor (R_FLOOR) at the divider
bottom bounds k_min so the LFO cannot stall at DC.

> **Prototype-verify (Phase 3R):** with a 1 MΩ pot the wiper source impedance (up to ~R_pot/4 ≈
> 250 kΩ near mid-rotation) adds to R_INT (590 kΩ) and perturbs the f-vs-rotation curve. Trim
> R_FLOOR / pot value on the prototype, or buffer the wiper, if the deviation from the intended
> log sweep is objectionable.

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

DSP: `brightness = (lfoRaw + 1) × 0.5` (`Pogo.cpp:504–505`)

This maps the ±1 LFO output **linearly to [0, 1] across the whole cycle**: brightness 0 at
the negative peak, 0.5 at the zero-crossing, full at the positive peak — a continuous
"breathing" indicator that is lit throughout the cycle and dark only at the trough.

The hardware matches this with a **full-cycle NPN current-source driver** (change 0018,
G5/G6a approved): the bipolar triangle is level-shifted onto a transistor base so the LED
current rises with `(V_tri + 5)`, breathing across the whole cycle rather than the old
half-wave "pulsing" lamp (which was OFF for the entire negative half — not a match for the
plugin law). See §3 for the circuit. *(A small exponential toe near the dark end from the
V_be knee, and ~2 mV/°C dark-point drift, are accepted as cosmetically invisible.)*

### MOD_SRC feed (both LFOs → block-3 switch)

Per the locked plugin (`Pogo.cpp:363–366`), the mod-bus source is an explicit 3-way
switch — `modSrcV = (pos 0) lfo1V : (pos 1) lfo2V : (pos 2) MOD_IN (0 V if unpatched)`.
There is **no** passive jack-normalling. Each LFO's triangle output therefore needs a tap
that drives **both** its own output jack (always live, `Pogo.cpp:500–501`) and the MOD_SRC
switch input. Since the jack (1 kΩ series) and the switch input (into the SCALE pot, light
load) are both light loads on the TL072 integrator output, a **passive mult off V_tri is
adequate** — no dedicated buffer is required (re-verify on the prototype if both paths
interact). The MOD_SRC switch (DW5, block-3) selects between the two LFO taps and the
MOD_IN jack (External). Block 2 exposes `LFO1_OUT` and `LFO2_OUT` as boundary nets to
block-3's switch (positions 0 and 1 respectively).

### Hardware behavior notes

Items 1 and 3 below are intentional DSP advantages kept by design. Item 2 is now modeled in DSP.

1. **Phase reset:** The DSP `reset()` method zeroes the phase accumulator. There is no
   hardware phase reset circuit; LFOs free-run from power-on. This is acceptable for a
   modulation source.

2. **Waveform peak rounding:** The hardware triangle has slight rounding near the peaks
   due to integrator slew rate and Schmitt comparator switching delay. The DSP models
   this with a one-pole LP filter at 10× the LFO rate, producing the same characteristic
   soft peak rounding. This is sonically desirable (softer modulation edges).

3. **Rate law:** The DSP uses a precise exponential: `0.05 × 400^param`. The hardware uses a
   log-taper panel pot whose rotation tracks that exponential approximately (it IS a swept
   performance control). Exact exponential tracking is not required — the log taper just keeps
   the sweep musical across the throw.

4. **Frequency accuracy:** Component tolerances on R_int and C_int affect absolute
   frequency. A 10% tolerance capacitor produces ±10% frequency error at any given
   pot position. No calibration trimmer is specified in Phase 3R for LFO rate — this is
   to be confirmed in Phase 3R design review.

→ References `aux/aux-lfo-core.md`

---

## 3. Physical Design

> ✅ **FINALIZED 2026-05-29; pot updated 2026-05-30** — Rate network uses the drive-attenuator
> topology (fixed R_INT + pot attenuator on the Schmitt output), verified against the plugin
> rate law and the components.yaml BOM. The rate control is a **9mm log-taper panel pot**
> (RD901F family, as the attenuverters) — a player control, not a screwdriver trimmer.
> Transcribed in `specs/block-2/block-2.nets.yaml`.

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

**Rate attenuator (RV_RATE = 1 MΩ log-taper panel pot + R_FLOOR):** the pot is a divider
on V_sq — top (pin 3) to V_sq, bottom (pin 1) to GND via R_FLOOR, wiper (pin 2) to R_INT.
The wiper fraction k sets the charge current and thus f = k · f_max. The end points are set
by the divider exactly as for a linear pot (the log taper only reshapes the middle of the
throw into the exponential sweep):
```
k_max ≈ 1                         → f_max ≈ 19.8 Hz   (full CW)
k_min = R_FLOOR / (RV + R_FLOOR)  → f_min ≈ k_min · f_max
R_FLOOR = 2.4 kΩ → k_min = 2.4k / (1M + 2.4k) ≈ 0.0024 → f_min ≈ 0.047 Hz ✓
```
R_INT (590 kΩ) loads the wiper; with a 1 MΩ pot the wiper source impedance (up to ~R_pot/4)
is not negligible against R_INT, so the f-vs-rotation curve is to be trimmed/verified on the
prototype (see §2 note — re-trim R_FLOOR/pot value or buffer the wiper if needed). Achievable
range ≈0.05–20 Hz. C_INT must be C0G (timing stability).

**Schmitt trigger thresholds (±5 V):** Positive feedback divider from comparator output
to (+) input, with a lower resistor to GND:
```
V_H = V_sat × R_HYS / (R_fb_sq + R_HYS)    [R_fb_sq = top (output→(+)), R_HYS = bottom ((+)→GND)]
5 V  = 11 × 82 kΩ / (100 kΩ + 82 kΩ)
V_H  = 11 × 0.451 = 4.96 V ≈ 5 V  ✓
```
Use R_fb_sq = 100 kΩ, R_HYS = 82 kΩ.

**LED driver — full-cycle "breathing" NPN current source (change 0018, G5/G6a approved):**

A single NPN (MMBT3904, SOT-23) per LED acts as a voltage-controlled current source. The
bipolar triangle `V_tri` (±5 V) is level-shifted onto the transistor base by a 3-resistor
network so the base sits below the conduction threshold at −5 V and rises through the active
region toward +5 V; the LED is fed from +12 V through the transistor, with the emitter
resistor `R_E` setting the full-scale current. The result is `I_LED ≈ (V_base − V_be)/R_E`
with `V_base ≈ 0.14·V_tri + 1.3 V`, i.e. ~0 at −5 V (Q cut off → LED dark) rising to ~3 mA
at +5 V — a full-cycle breathing indicator matching the plugin law.

```
   +12V ──► LED_anode ──► LED_cathode ──► Q collector
                                          Q emitter ──[R_E 470 Ω]──► GND
   base level-shift:
     V_tri ──[R_BTRI 51 kΩ]──┐
     +12V  ──[R_BBIAS 68 kΩ]─┼──► Q base
     GND   ──[R_BGND 10 kΩ]──┘

   V_tri  −5 V / 0 V / +5 V  →  V_base 0.585 / 1.31 / 2.04 V  →  I_LED ≈ 0 / 1.4 / 3.0 mA
```

Component values (per LED): R_BTRI 51 kΩ, R_BBIAS 68 kΩ, R_BGND 10 kΩ, R_E 470 Ω, Q =
MMBT3904. The +12 V bias leg sets the dark-point (LED off near `V_tri = −5 V`); a few-percent
rail tolerance only nudges that point and is cosmetically invisible. Transistor dissipation
≈ 26 mW (well within SOT-23). This **replaces** the former D1/D2 (1N4148) + R9/R10 half-wave
limiter; R9/R10 are repurposed as the emitter resistors `R_E1/R_E2`.

### Signal routing

```
LFO1 (U1 = TL072): integrator (A) + Schmitt (B)
  Schmitt out V_sq → RV1 top; RV1 bottom → R3 (R_FLOOR) → GND; RV1 wiper → R1 (R_INT) → U1A(−)
  U1A: (+) = GND, (−) = R1/C1 summing node, out = V_tri; C1 (C_INT) feedback (−)↔out
  Schmitt U1B: (−) = V_tri, (+) = R5(R_FB_SQ to V_sq)/R7(R_HYS to GND) node, out = V_sq
  V_tri → R19 (R_BTRI) → Q1 base (level-shift w/ R20 from +12V, R21 to GND); LED1 ← +12V → Q1 collector; Q1 emitter → R9 (R_E) → GND
  V_tri → R11 (R_OUT 1 kΩ) → J5 (LFO1 jack)  and  → LFO1_OUT boundary → block-3 MOD_SRC switch pos 0

LFO2 (U2): identical — V_tri → R12 → J6 (LFO2 jack) and → LFO2_OUT boundary → block-3 MOD_SRC switch pos 1.
```

### Calibration points

No factory rate trimmer is needed: the panel rate pot (RV1/RV2) is the user's control.
R_INT (590 kΩ) sets the fast endpoint; R_FLOOR (2.4 kΩ) sets the slow floor; C_INT
tolerance shifts absolute frequency but the wide throw easily covers 0.05–20 Hz, so the
player just dials the rate they want.

### Pots

RV1/RV2 (1 MΩ **log taper**, RD901F 9mm panel pot — the same family as the attenuverters)
are the rate controls, wired as drive attenuators on the Schmitt output (not as rheostats).
The log taper gives the roughly exponential rate-vs-rotation sweep (see §2 prototype-verify
note on wiper loading).

### Board assignment

Utility board. LFOs are non-audio signals (0.05–20 Hz); they do not require the
low-noise audio board ground plane. Rate pots and LEDs are on the control/panel board.
LFO output series resistors (R_LFO1, R_LFO2, 1 kΩ) logically belong to Block B's
output protection but are physically placed on the utility board near the LFO outputs.

→ References `aux/aux-lfo-core.md` for detailed integrator + Schmitt trigger schematic.

---

## 4. Component Requirements

Component set: see the generated BOM `kicad/pogo-bom.csv` (rows with `Block = block-2`),
sourced from `specs/components.yaml` (the per-ref design manifest) and enriched by the
`components/` registry (MPN, footprint, datasheet). Verification status: `specs/STATUS.md`.
