# aux: LFO Core (Triangle Oscillator)

**Type:** `modulation` · part of the [aux circuit library](../../_LIBRARY.md)

> ✅ **Re-verified 2026-05-30** against the locked plugin (change 0018). Updated for: both
> LFOs feed the MOD_SRC switch (no MOD_IN auto-normal); rate pot is a **log panel pot**
> (player control), not a linear preset; LED driver is **full-cycle breathing** (matches
> `(raw+1)×0.5`), not half-wave.

Design status: [x] draft → [ ] reviewed → [ ] validated on prototype

## Overview

Analog triangle wave oscillator using an integrator + Schmitt trigger (comparator)
feedback loop. Produces a ±5V triangle wave over the range 0.05–20 Hz. Two independent
instances (LFO1, LFO2). Each LFO output is always live at its own panel jack **and** is
tapped to the block-3 MOD_SRC selector switch (positions 0 = LFO1, 1 = LFO2; position 2 =
External MOD_IN). There is no passive MOD_IN auto-normalling — selection is the explicit
3-way switch (per the locked plugin, `Pogo.cpp:363–366`).

Rate control (FINALIZED 2026-05-29; pot type updated 2026-05-30): R_INT is **fixed** and
the rate pot attenuates the Schmitt square-wave drive into the integrator (wiper → R_INT),
so f ∝ wiper fraction k. A 1 MΩ **log-taper 9 mm panel pot** (RD901F family — a hand-swept
player control, *not* a preset) covers the full 0.05–20 Hz (400:1) range this way; a plain
rheostat cannot (a 1 MΩ pot only adds ~1 MΩ of series swing, far short of the ≈590 kΩ→234 MΩ
needed). The log taper makes k rise ~exponentially across rotation, approximating the
plugin's `0.05 × 400^param` law over the throw. The earlier "log-pot / THAT340-expo,
Phase-3R TBD" note is superseded: no expo converter is needed — the pot taper does it. See
`specs/block-2/spec.md` §2/§3.

Chosen because:
- Integrator + comparator is the minimal, most reliable triangle oscillator topology
- No startup circuitry needed: positive feedback in the Schmitt trigger ensures the
  oscillator always starts (no stuck-at-zero states)
- Triangle output from the integrator is inherently available; square wave from the
  comparator output is a bonus (could be exposed as a gate/sync output if desired)
- TL072CDT is adequate for the LFO frequency range (20 Hz max); no HF op-amp needed

## Schematic


ASCII fallback (one LFO, component labels for LFO1):

```
 ┌─────────────────────────────────────────────────────────────────────┐
 │                      Triangle Oscillator Core                       │
 │                                                                     │
 │   ┌──── INTEGRATOR (TL072 half A) ────┐                            │
 │   │                                    │                            │
 │   │  [R_INT]    C_INT                  │                            │
 │   │  V_sq ──[──]──┬──(−)──[TL072]──┬──┴── V_tri                   │
 │   │               │   (+)= AGND    │                               │
 │   │               │                │ C_INT = 47nF (or per design)  │
 │   │               │                │                               │
 │   │               └────────────────┘                               │
 │   │                                                                 │
 │   └─────────────────────────────────────────────────────────────────┤
 │                                                                     │
 │   ┌──── SCHMITT TRIGGER (TL072 half B) ────┐                       │
 │   │                                         │                       │
 │   │         R_HYS                           │                       │
 │   │  V_sq ──[──]──┬──(+)──[TL072]──┬── V_sq (comparator output)   │
 │   │               │   (−) = V_tri  │                               │
 │   │               └────────────────┘ (positive feedback → Schmitt) │
 │   │                                                                 │
 │   │  V_sq swings between +Vsat ≈ +11V and −Vsat ≈ −11V           │
 │   │  Hysteresis thresholds: V_H = ±Vsat × R_HYS/(R_HYS + R_out)  │
 │   │  Set R_HYS so thresholds = ±5V for ±5V triangle swing         │
 │   │                                                                 │
 │   └─────────────────────────────────────────────────────────────────┤
 │                                                                     │
 │   Rate control:                                                     │
 │   RATE pot wiper ──────────────────────────────────► R_INT input   │
 │   (sets charge current into C_INT via R_INT)                       │
 │   → slower pot CW rotation → smaller R_INT → faster rate           │
 │                                                                     │
 │   LED:                                                              │
 │   "breathing" LED: MMBT3904 current source driven by ½(V_tri+1)   │
 │                                                                     │
 └─────────────────────────────────────────────────────────────────────┘

 V_tri ──[R_out 1kΩ]──► LFO1_OUTPUT jack (±5V triangle)
```

## Transfer Function

### Oscillation Frequency

The integrator ramps V_tri at rate:

```
dV_tri/dt = −V_sq / (R_INT × C_INT)

The Schmitt trigger flips when V_tri reaches ±V_H (hysteresis threshold):
  V_H = V_sat × R_HYS / (R_HYS + R_fb_sq)   [voltage divider with positive feedback]

Time for one half-cycle (ramp from −V_H to +V_H):
  T/2 = (2 × V_H × R_INT × C_INT) / V_sat

Oscillation frequency:
  f = 1/T = V_sat / (4 × V_H × R_INT × C_INT)
  
  Since V_H = V_sat × R_HYS / (R_HYS + R_fb_sq):
  f = (R_HYS + R_fb_sq) / (4 × R_HYS × R_INT × C_INT)
  f ≈ 1 / (4 × R_INT × C_INT)   when R_fb_sq >> R_HYS
```

Setting V_H = ±5V for ±5V triangle output:
```
V_H = V_sat × R_HYS / (R_HYS + R_fb_sq) = 5V
With V_sat ≈ 11V:
  R_HYS / (R_HYS + R_fb_sq) = 5/11 = 0.455
  → R_HYS = R_fb_sq × 0.455/0.545 = 0.83 × R_fb_sq
  e.g. R_HYS = 82 kΩ, R_fb_sq = 100 kΩ
```

### DSP Reference (LFO)

```
speedHz = 0.05 × 400^speedParam    speedParam ∈ [0, 1]
f range: 0.05 Hz (min) → 20 Hz (max)   [ratio = 400]

Triangle output:
  V_LFO = ±5V triangle, −5V at phase=0, +5V at phase=0.5
```

### Frequency Range Derivation

```
Required: f_min = 0.05 Hz, f_max = 20 Hz (ratio = 400:1)

f = 1 / (4 × R_INT × C_INT)

At f_max (R_INT = R_min):
  R_min = 1 / (4 × f_max × C_INT) = 1 / (4 × 20 × 47nF) = 266 kΩ

At f_min (R_INT = R_max):
  R_max = 1 / (4 × f_min × C_INT) = 1 / (4 × 0.05 × 47nF) = 106 MΩ

The ratio R_max/R_min = 400 matches the DSP ratio. A single 1 MΩ pot cannot
cover this range linearly. Two approaches:

Option A — Log-taper pot (preferred for simplicity):
  A 1 MΩ log-taper pot provides a 10:1 or 100:1 taper depending on the pot curve.
  End resistors on CW and CCW ends trim the effective range to 266 kΩ – 106 MΩ.
  True 400:1 range may require custom end-resistor tuning.

Option B — THAT340 expo converter:
  Same architecture as aux/filter/expo-converter; V/Hz tracking.
  More accurate exponential taper; harder to calibrate.
  Enables V/oct or V/Hz LFO sync if a SYNC input is added later.
  Phase 3R decision: prefer Option A unless sync is required.
```

## Design Choices & Rationale

### Integrator + Schmitt Trigger (Astable)

This is the minimal triangle oscillator: two op-amp halves (one TL072CDT), plus
R_INT, C_INT, R_HYS, R_fb_sq. The integrator produces the triangle; the Schmitt
trigger produces the control square wave that drives the integrator. The feedback
loop is inherently stable and always starts oscillating.

Alternatives considered:
- XR2206 function generator IC: single IC, but requires PLCC/CDIP package, difficult
  to source reliably in 2026
- Wien bridge oscillator: produces sine, not triangle; requires AGC for amplitude
  stability; more complex
- CMOS timer (555): produces sawtooth, not triangle; extra conversion stage needed

Integrator + comparator is well-understood, reproducible, and easily tunable.

### Two Independent LFOs

LFO1 and LFO2 are separate oscillator circuits on the same board, sharing only the
power supply. This allows:
- Independent RATE pots (no LFO rate CV input in the current design)
- Phase independence (they free-run at separate rates)
- Either LFO selectable as the mod-bus source via the block-3 MOD_SRC switch, independently

Two TL072CDT ICs (one per LFO) plus passive networks. Total area budget: two
standard LFO footprints ~10 × 15 mm each on the control board.

### LED Brightness Tracking — full-cycle "breathing" (matches plugin)

The plugin LED law is `brightness = (V_tri/5 + 1) × 0.5 = (V_tri + 5)/10` over the **whole
cycle** (`Pogo.cpp:504`): dark only at −5 V, half at the zero-crossing, full at +5 V. The
hardware therefore uses a **full-cycle transconductance driver** whose LED current is
proportional to `(V_tri + 5)`:
```
I_LED ∝ (V_tri + 5V)      (0 at −5 V, max at +5 V — breathing, lit across the whole cycle)
```
This is realized as a per-LED op-amp current sink with an input level-shift (sum V_tri with a
+5 V reference) so the LED conducts proportionally from zero — **not** a passive
diode+resistor off V_tri. The concrete component set is specced in `block-2/spec.md` §3 as a
G5/G6a proposal under change 0018.

> **Superseded:** an earlier half-wave scheme (1N4148 between V_tri and the LED, lit only on
> the positive half-cycle) produced a *pulsing* lamp that does **not** match the plugin's
> full-cycle law. It is dropped in favor of the breathing driver above. The "breathing vs
> pulsing — Phase 3R open item" is therefore **closed: breathing.**

### Rate taper — RESOLVED (drive-attenuator + 9mm log panel pot)

The DSP rate taper is 0.05 × 400^x — a genuine exponential spanning 400:1. This is
**RESOLVED** in block-2/spec.md §2/§3: it is **not** reproduced by varying R_int with a
pot (that needs a 400:1 resistance swing). Instead block-2 uses a **drive-attenuator** —
R_int is fixed and a pot divides the Schmitt square-wave drive into the integrator
(f ∝ wiper fraction). The rate control is a **9mm log-taper panel pot** (RD901F family, as
the attenuverters); the log taper gives the roughly exponential rate-vs-rotation sweep. The
THAT340-expo option is **not** used (the log panel pot is adequate and far cheaper);
CV-over-rate is deferred to a future revision.

## Component Values (POGO-specific)

| Ref (generic) | Part | Package | Value | Notes |
|---|---|---|---|---|
| U_LFO1 | TL072CDT | SOIC-8 | — | Half A = integrator; half B = Schmitt trigger |
| U_LFO2 | TL072CDT | SOIC-8 | — | Half A = integrator; half B = Schmitt trigger (LFO2) |
| C_INT | C0G ceramic | 0603 | 47 nF | Integrator cap; C0G for frequency stability |
| R_INT | Resistor | 0603 | 590 kΩ | **Fixed** integrator input R; sets f_max ≈ 20 Hz at full drive |
| RV_RATE | Log-taper pot | 9mm T18 | 1 MΩ | RATE panel pot (drive attenuator on V_sq; RD901F family, as the attenuverters) |
| R_FLOOR | Resistor | 0603 | 2.4 kΩ | Divider floor (pot bottom → GND); sets f_min ≈ 0.05 Hz |
| R_HYS | Resistor | 0603 | 82 kΩ | Schmitt trigger hysteresis; sets ±5V threshold |
| R_fb_sq | Resistor | 0603 | 100 kΩ | Schmitt trigger feedback resistor |
| R_LED_LFO | Resistor | 0603 | — | LFO LED current-set R in the breathing driver (value per block-2 §3 G6a) |
| LED_LFO | LED | 0603 | warm white | LFO indicator; brightness tracks triangle |
| LED driver | (op-amp current sink) | — | — | Full-cycle breathing driver; per-LED. See block-2 §3 (G6a) — replaces the old 1N4148 half-wave |
| R_out_LFO | Resistor | 0603 | 1 kΩ | Output series protection to LFO jack |
| C_VCC, C_VEE | Ceramic bypass | 0603 | 100 nF | Per TL072 supply pin |

### Component Values Derivation Summary

```
C_INT = 47 nF (C0G); R_INT = 590 kΩ (fixed)
Drive-attenuator: f = k · f_max, k = wiper fraction of RV_RATE (1 MΩ log) divider on V_sq
    f_max ≈ 1/(4 × 590k × 47n) ≈ 19.8 Hz   (k ≈ 1, full CW)
    k_min = R_FLOOR/(RV_RATE + R_FLOOR) = 2.4k/(1M + 2.4k) ≈ 0.0024 → f_min ≈ 0.047 Hz ✓
  (Log taper reshapes the middle of the throw into the exponential sweep; end points set by
   the divider. Wiper source impedance into R_INT is a prototype-trim item — see block-2 §2.)

Schmitt trigger thresholds:
  V_H = 5V (target)
  R_HYS = 82 kΩ, R_fb_sq = 100 kΩ
  V_H = 11V × 82/(82+100) = 11 × 0.451 = 4.96V ≈ 5V ✓
```

## Performance Characteristics

| Parameter | Value | Condition |
|---|---|---|
| Frequency range | 0.05 – 20 Hz | Full RATE pot sweep |
| Frequency taper | ~exponential | Log-taper pot in drive-attenuator divider |
| Output amplitude | ±5V triangle | ±12V supply, V_H calibrated |
| Output waveform | Triangle | Integrator output |
| Frequency stability | ±1% / °C | C0G cap; TL072 offset drift |
| Startup | Always oscillates | Schmitt trigger positive feedback |
| Supply current | ~3 mA per LFO | TL072 × 2 + passives |

## Known Gotchas / Assembly Notes

- C_INT must be C0G (NP0): X7R capacitor frequency coefficient will cause audible
  pitch drift in the LFO rate as the module warms up
- TL072 integrator output can clip if V_H is set incorrectly (if the comparator
  doesn't flip before the integrator rail): verify V_H < V_sat (≈11V) in simulation
  before committing component values
- The integrator (−) input is a virtual ground node; keep R_INT trace short and
  away from digital control lines to avoid noise injection into LFO rate
- Power-on: the Schmitt trigger may power up in either state; the integrator will
  immediately start ramping in whichever direction. This is normal — no startup
  circuit is needed
- MOD_SRC taps (both LFOs): each LFO's V_tri drives its own panel jack (1 kΩ series) and
  is also tapped to the block-3 MOD_SRC 3-way switch (pos 0 = LFO1, 1 = LFO2). Both loads
  are light, so a passive mult off V_tri is adequate; add a unity-gain buffer only if the
  prototype shows the two paths interacting. (There is no MOD_IN auto-normalling — selection
  is the explicit switch; MOD_IN is the External position only.)
- At minimum rate (0.05 Hz), the period is 20 seconds. Any TL072 input bias current
  will cause DC drift on C_INT over this timescale:
  TL072 I_bias ≈ 50 pA; drift = I_bias / C_INT × T = 50pA / 47nF × 20s = 21 mV
  → acceptable (triangle swings ±5V = 10V total; 21 mV < 0.2% error)
- Minimum rate accuracy is set by R_FLOOR (2.4 kΩ) in the drive-attenuator divider, not by
  any series rheostat. (The old "R_CCW_END 10 MΩ" rheostat note is obsolete — that scheme was
  superseded by the drive-attenuator; minimum rate need not be calibrated precisely.)
- Two LFO oscillators on the same board: layout them far from each other and from
  the LP filter frequency CV inputs to prevent LFO rate injection via stray coupling

## Used By

| Block | Instance | Board | Notes |
|---|---|---|---|
| block-2 | LFO1_OSC | utility | LFO1; output jack + tap to MOD_SRC switch pos 0 |
| block-2 | LFO2_OSC | utility | LFO2; output jack + tap to MOD_SRC switch pos 1 |
| block-3 | MOD_SRC select | control | 3-way switch picks LFO1 / LFO2 / External(MOD_IN) as mod-bus source |
