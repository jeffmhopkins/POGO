# aux: Schmitt Trigger (Non-Inverting Hysteretic Comparator)

**Type:** `modulation` · **primitive** · part of the [aux circuit library](../../_LIBRARY.md)

> Authored 2026-05-31 (change 0032). Atomic non-inverting comparator-with-hysteresis primitive
> extracted from the composed `lfo-core` triangle oscillator (its square-wave comparator half).

Design status: [x] draft → [ ] reviewed → [ ] validated on prototype

## Overview

The **Schmitt trigger** is a comparator wrapped in positive feedback: the output `V_sq` slams to
one supply rail (±`V_sat`), and a resistor divider `R_a / R_b` feeds a fraction of that output back
to the non-inverting (+) input, so the comparator does not flip until the input crosses a
*displaced* threshold. The two thresholds (rising vs falling) are offset by the hysteresis window,
which makes the trigger immune to noise around the switch point and — critically for the LFO — lets
it **hold state** until the integrator ramp has traversed the full window.

It is the atomic stateful element under [`lfo-core`](../lfo-core/spec.md): the integrator produces
the triangle and this Schmitt produces the ±`V_sat` square that reverses the integrator's ramp at
each threshold crossing. The triangle's peak-to-peak amplitude is exactly the Schmitt's threshold
window, so this primitive sets the LFO output level (±5 V).

In the **non-inverting** topology the input is applied to the bottom of the feedback divider (or,
equivalently in the LFO, the (−) input tracks the integrator triangle while the (+) input sees the
divided output); the trip points are symmetric about 0 V at `±V_sat · R_b/(R_a+R_b)`.

## Schematic

ASCII (non-inverting Schmitt; LFO convention — (−) tracks the ramp, (+) sees the divider):

```
                                        ┌──────────── V_sq  (output, ±V_sat)
                                        │
                              R_a       │
            V_sq ───────────[───────]───┤
                                        ├──(+) ───┐
                              R_b       │         │
            AGND ───────────[───────]───┘    ┌────────┐
                                        ▲     │ comp.  ├──── V_sq
              V_+ = V_sq · R_b/(R_a+R_b)│     │ (op-amp│
                                        │     │  open  │
            V_ramp ────────────────────(−)────┤  loop) │
              (integrator triangle)           └────────┘

  Trip when  V_ramp = V_+ = ± V_sat · R_b/(R_a+R_b)
  Output HOLDS (positive feedback) until the ramp crosses the (divided) threshold, then flips.
```

In `lfo-core` the divider resistors are named `R_FB_SQ` (= `R_a`, output → (+)) and `R_HYS`
(= `R_b`, (+) → AGND).

## Transfer Function

```
Feedback divider:   V_+ = V_sq · R_b / (R_a + R_b)

Output is bistable:  V_sq = +V_sat  while V_ramp < V_+   (then holds)
                     V_sq = −V_sat  while V_ramp > V_+

Trip thresholds (the input level at which V_sq flips):
    V_trip = ± V_sat · R_b / (R_a + R_b)

Trip-threshold ratio (V_sat-independent — the load-bearing law):
    V_trip / V_sat = R_b / (R_a + R_b)

Hysteresis window (full):
    ΔV_H = V_trip,+ − V_trip,− = 2 · V_sat · R_b / (R_a + R_b)
```

The ratio `R_b/(R_a+R_b)` is the entire design parameter: it is set purely by the divider and is
independent of the (unmeasured) supply saturation `V_sat`. Choosing `R_a = 100 kΩ`, `R_b = 82 kΩ`
gives `82/182 = 0.4505`, so with `V_sat ≈ 11 V` the thresholds land at `±4.96 V ≈ ±5 V`.

### Plugin reference

The LFO DSP (`plugin/src/dsp/LFO.hpp:19–20`) maps the unit phase ramp to a `±1` triangle and the
caller scales it to a `±5 V` output. The analog amplitude is set by the Schmitt threshold window:
the triangle ramps between `+V_trip` and `−V_trip`, so `V_trip = ±5 V` is what realizes the
plugin's `±5 V` triangle. The Schmitt's *hold* behavior (positive feedback) is what makes the
relaxation oscillator a real bistable loop — a memoryless comparator cannot oscillate
(see [`lfo-core`](../lfo-core/spec.md) §"Transfer Function").

## Design Choices & Rationale

### Positive Feedback Holds State

A bare comparator (no hysteresis) chatters around the switch point and, in the LFO loop, cannot
sustain oscillation deterministically. Feeding a fraction of the output back to (+) creates two
displaced thresholds: once the output flips, the threshold jumps to the *other* side, so the input
must traverse the whole window before the next flip. This both rejects noise and sets the
oscillator's amplitude/period.

### Divider Sets Amplitude, Not Rail

Because the trip points scale with `V_sat`, the *ratio* `R_b/(R_a+R_b)` — not the absolute rail —
is the calibration target. This is deliberate: the LFO frequency formula
`f = (R_a+R_b)/(4·R_b·R_INT·C_INT)` is likewise `V_sat`-free (the threshold scales with the rail,
which cancels), so trimming the divider sets amplitude and the rate stays put.

### Threshold Pair Choice

`R_a = 100 kΩ`, `R_b = 82 kΩ` → ratio 0.4505 → `±4.96 V` at `V_sat ≈ 11 V` (`±12 V` supply, ~1 V
op-amp headroom each rail). E12 values; 1 % tolerance keeps the ±5 V target within a few percent.

## Component Values (POGO-specific)

Representative library values; the live per-instance values are in `lfo-core` / block-2.

| Ref (generic) | Part | Package | Value | Notes |
|---|---|---|---|---|
| U_CMP | TL072CDT | SOIC-8 | — | One op-amp section, run open-loop as comparator |
| R_a (= R_FB_SQ) | Resistor | 0603 | 100 kΩ | Divider top: output → (+) |
| R_b (= R_HYS) | Resistor | 0603 | 82 kΩ | Divider bottom: (+) → AGND; sets ratio 0.4505 |

## Performance Characteristics

| Parameter | Value | Condition |
|---|---|---|
| Trip ratio | R_b/(R_a+R_b) = 0.4505 | Set by divider only |
| Trip thresholds | ±4.96 V | V_sat ≈ 11 V |
| Hysteresis window | ~9.9 V p-p | 2·V_trip |
| Output levels | ±V_sat (≈ ±11 V) | Op-amp rails on ±12 V supply |
| State hold | bistable | Positive feedback |

## Known Gotchas / Assembly Notes

- The threshold is set by the *ratio* `R_b/(R_a+R_b)`; a single-resistor drift moves the LFO
  amplitude (and, via the divider in `f`, slightly the period) — match/tolerance both resistors.
- An op-amp run open-loop as a comparator is acceptable at LFO speeds (no fast-edge requirement);
  for the triangle LFO the slow slew is harmless and even slightly rounds the peaks.
- Output swing is `±V_sat`, not `±V_supply`: the TL072 saturates ~1 V short of each rail, so
  `V_sat ≈ 11 V` on a ±12 V supply — this is the value that lands the `±5 V` triangle.
- Get the divider polarity right: the feedback must be *positive* (output → (+), not (−)) or the
  stage degenerates to a linear inverting amp and the loop will not latch/oscillate.

## Used By

| Composed cell / Block | Instance | Board | Notes |
|---|---|---|---|
| [lfo-core](../lfo-core/spec.md) | Square-wave comparator (TL072 half B) | utility | Sets the ±5 V triangle window; reverses the integrator ramp |
| block-2 | LFO1 / LFO2 Schmitt (R5 = R_FB_SQ, R7 = R_HYS) | utility | The live triangle-oscillator comparator halves |
