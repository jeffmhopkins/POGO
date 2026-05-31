# aux: Inverting Summer (Virtual-Ground Op-Amp Adder)

**Type:** `modulation` · **primitive** · part of the [aux circuit library](../../_LIBRARY.md)

> Authored 2026-05-31 (change 0032). Atomic op-amp summing-amplifier primitive extracted from the
> composed `mod-bus-core` (SCALE/OFFSET summer) and `attenuverter` (−V_src inverter) cells, and used
> directly by the audio-path summers (block-7 SUM_AMP, the OTA-C SVF summing node).

Design status: [x] draft → [ ] reviewed → [ ] validated on prototype

## Overview

The **inverting summer** is the canonical virtual-ground op-amp adder: each input drives the
inverting (−) node through its own input resistor, a single feedback resistor closes the loop, and
the (+) input is tied to the analog ground (AGND) reference. Because the (−) node is held at virtual
ground, every input current `V_in,i / R_in,i` sums into the feedback resistor independently — no
input interacts with another (each sees a virtual-ground sink, not the other inputs).

This is the smallest reusable POGO summing element. It appears:
- as the **scale + offset summer** inside `mod-bus-core` (V_src through R_src, V_off through R_off,
  one R_f feedback) — see that cell's `**Composes:**`;
- as the **−V_src / −V_att inverter** inside `attenuverter` (a single-input summer with R_in = R_f → G = −1);
- as a **standalone audio summer** in block-7 (HP SUM_AMP) and the OTA-C SVF summing node.

The 2nd-stage **unity polarity inverter** (G = −1) found in `mod-bus-core` (MB_INV) and the
attenuverter's −V_att generator are both this primitive specialized to a single input with
R_in = R_f.

## Schematic

ASCII (N-input inverting summer, N = 1…k):

```
                 R_in,1
  V_in,1 ──────[───────]──┐
                          │
                 R_in,2   │      R_f
  V_in,2 ──────[───────]──┼────[───────]──┐
                          │                │
       …                  ├──(−) ─────────┤  ← virtual ground (V_sum_node ≈ 0)
                 R_in,k   │                │
  V_in,k ──────[───────]──┘   ┌────────┐   │
                              │ op-amp ├───┴── V_out = −Σ (R_f/R_in,i)·V_in,i
                       (+)────┤        │
                        │     └────────┘
                       AGND

  Single-input specialization (R_in = R_f): V_out = −V_in  (unity inverter, G = −1)
```

## Transfer Function

```
Virtual ground at (−):  Σ_i (V_in,i / R_in,i)  +  (V_out / R_f) = 0

→  V_out = −Σ_i (R_f / R_in,i) · V_in,i

Per-input gain magnitude:  |G_i| = R_f / R_in,i   (always inverting)

Special cases:
  Unity sum  (all R_in,i = R_f):  V_out = −Σ_i V_in,i
  Unity inv  (single input, R_in = R_f):  V_out = −V_in   (G = −1)
  Gain stage (single input, R_f ≠ R_in):  V_out = −(R_f/R_in)·V_in
```

Inputs are **independent**: the virtual ground decouples them, so the source impedance of one
input does not affect another input's gain. Each input gain depends only on its own R_in and the
shared R_f.

### DSP / plugin law it realizes

```
mod-bus-core (ModBus.hpp:22-25):
  V_bus_pre = sourceV·gain + offset
  → analog summer: V_sum = −(V_src·R_f/R_src + V_off·R_f/R_off)   (sign restored by MB_INV)
  gain  = amountGain(amountParam) = 0.2·25^p   → realized by R_f/R_src
  offset= offsetParam·5            (±5 V)       → realized by R_f/R_off with a ±5 V reference

attenuverter −V_att inverter (ModBus.hpp:29-33, applyDestination = source·att):
  needs a clean −1 inverter to make the bipolar pot rail symmetric (center → 0)
  → single-input summer with R_in = R_f → G = −1
```

The summer **inverts**; POGO restores polarity with a *second* inverting summer (a unity inverter,
this same primitive with G = −1), so the net bus follows the non-inverted plugin sum.

## Design Choices & Rationale

### Virtual-Ground Adder vs Passive Mixer

A passive resistor mixer (inputs summed onto a node, no op-amp) makes each input's gain depend on
the *other* inputs' source impedances (they all share the summing node). The virtual-ground
inverting summer holds the summing node at 0 V so inputs are decoupled and gains are exact
ratios — required for the calibrated SCALE/OFFSET math. The cost is one op-amp and a polarity
inversion (corrected downstream).

### Feedback Resistor Sets the Common Scale

R_f scales *all* inputs equally; each R_in,i sets that input's relative weight. POGO picks
R_f = 100 kΩ as the family value (mod bus) or R_f = R_in (unity inverters), keeping noise and bias
current modest while staying well above op-amp output drive limits.

### Matching for Unity Inverters

When the primitive is used as a G = −1 inverter (MB_INV, attenuverter −V_att), R_in and R_f must
**match** (1 % or better) or the center-null / polarity symmetry degrades. A 1 % mismatch gives
~1 % gain error → only ~40 dB center null; use 0.1 % or trim where deep null matters
(attenuverter center detent).

## Component Values (POGO-specific)

Representative values (the live per-instance values are in each using block's netlist; this is the
generic primitive form):

| Ref (generic) | Part | Package | Value | Notes |
|---|---|---|---|---|
| U_SUM | TL074CDT / TL072CDT | SOIC-14 / SOIC-8 | — | One op-amp section per summer |
| R_f | Resistor | 0603 | 100 kΩ | Feedback; sets the common scale (mod bus family value) |
| R_in,i | Resistor | 0603 | per input | Input weight resistor; R_f/R_in,i = that input's gain |
| (unity inverter) R_in = R_f | Resistor | 0603 | matched | G = −1; 1 % (0.1 % for deep center null) |

## Performance Characteristics

| Parameter | Value | Condition |
|---|---|---|
| Per-input gain | −R_f/R_in,i | Exact ratio (virtual ground) |
| Input independence | inputs decoupled | Virtual ground at (−) |
| Polarity | inverting | Restored by a 2nd inverter where needed |
| Bandwidth | >100 kHz (TL07x) | Not audio-critical at mod rates |
| Unity-inverter null | >60 dB | With 0.1 % matched R_in = R_f |

## Known Gotchas / Assembly Notes

- The (−) node is a high-impedance virtual ground: keep R_in/R_f traces short to avoid noise
  injection and stray-capacitance peaking.
- The summer inverts — always account for the sign downstream (mod-bus-core adds MB_INV to restore
  polarity; the attenuverter *wants* the −1 to generate its negative pot rail).
- For unity inverters, match R_in = R_f (1 %/0.1 %); a mismatch skews both the −1 gain and any
  center-null that depends on it.
- TL07x input common-mode range excludes the negative rail; all POGO summer signals stay within
  ±10 V on ±12 V rails, so this is satisfied.

## Used By

| Composed cell / Block | Instance | Board | Notes |
|---|---|---|---|
| aux/modulation/mod-bus-core | MB_AMP (scale+offset summer) | control | 2-input summer: V_src·R_f/R_src + V_off·R_f/R_off |
| aux/modulation/mod-bus-core | MB_INV (polarity restore) | control | single-input, R_in=R_f → G=−1 |
| aux/modulation/attenuverter | −V_att inverter | control | single-input, R_in=R_f → G=−1 (negative pot rail) |
| block-3 | U3-A MB_AMP, U3-B MB_INV | control | the live mod-bus instance |
| block-3 | MB_INV_1..5 (−V_att) | control | per-destination attenuverter inverters |
| block-7 | HP SUM_AMP | audio | SVF summing node (x − k·v1 − v2) |
