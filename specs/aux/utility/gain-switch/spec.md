# aux: Gain Switch (Selectable 1× / 5× Input Stage)

**Type:** `utility` · **primitive** · part of the [aux circuit library](../../_LIBRARY.md)

> Authored 2026-05-31 (change 0033). The selectable-gain input stage extracted from the two POGO
> 1×/5× switches: block-1 GAIN_MAIN (pre-gain boost) and block-6 GAIN_BP3 (the ALT-path boost). A
> toggle picks between unity pass-through (1×) and a non-inverting amplifier set to ~5× (~14 dB).

Design status: [x] draft → [ ] reviewed → [ ] validated on prototype

## Overview

A **gain switch** offers the user a single-toggle choice between two gain states on an input stage:

```
1×  (switch in the BYPASS position):  V_out = V_in            (unity, op-amp out of the path)
5×  (switch in the GAIN position):    V_out = (1 + R_f/R_g)·V_in   (~14 dB; clipped at the op-amp rail)
```

The 5× state is a **non-inverting amplifier** whose gain `1 + R_f/R_g` is set by two resistors; the
1× state is a **path-select bypass** that routes the raw input around the op-amp entirely (so it
adds no noise at unity). The toggle is a DPDT used as a path selector: its common picks either the
amplifier output (5×) or the direct input (1×). At 5× the output clips at the op-amp's rail swing
(±10.5 V on ±12 V rails), giving the intentionally aggressive flat-top saturation of block-1.

`1 + R_f/R_g = 1 + 18 kΩ/4.7 kΩ = 4.83×`, which is 14 dB within 3.4 % of a nominal 5× — well inside
the ±5 % a "5× switch" implies. The library lists both the *clean nominal* 5× (R_f/R_g = 4 → 1+4 = 5)
and the *block value* 4.83× so a designer can pick either; POGO ships 4.83×.

This is the smallest reusable "boost switch" element. It appears as block-1 GAIN_MAIN (the main
signal pre-gain) and as block-6 GAIN_BP3 (the ALT-path boost feeding BP3).

## Schematic

ASCII (non-inverting amp + path-select DPDT):

```
                          R_f
                   ┌────[────────]────┐
                   │                  │
   V_in ──┬────────┼──(+)──┐          │
          │        │       │ op-amp   │
          │        └──(−)──┤ (OPA1612)├──┬──── 5× amp output  = (1 + R_f/R_g)·V_in
          │           │    └──────────┘  │      (clips at ±V_rail)
          │           │                  │
          │          R_g                 │
          │           │                  │
          │          AGND                │
          │                              │
          │          ┌───────────────────┘    ┌──────► V_out
          │          │   DPDT path-select     │
          └──────────┼────────────────────────┤  (common picks 1× raw V_in  or  5× amp out)
                   1× │ (raw input bypass)   5×│
```

Gain leg: the (+) input takes the signal; `R_g` from (−) to AGND and `R_f` from output to (−) set
`G = 1 + R_f/R_g`. The bypass leg carries the raw input directly to the switch common — no op-amp in
the 1× path.

## Transfer Function

```
Non-inverting amplifier (5× state):
   V_out = (1 + R_f/R_g) · V_in            (gain set by the resistor RATIO; polarity preserved)
   clipped:  V_out = clamp((1 + R_f/R_g)·V_in, −V_rail, +V_rail)

Bypass (1× state):
   V_out = V_in                            (path-select; op-amp removed from the path)

POGO values:
   R_f = 18 kΩ, R_g = 4.7 kΩ  →  G = 1 + 18/4.7 = 4.83×  (≈ 5×, ~14 dB)
   clean-nominal alternative:  R_f/R_g = 4 (e.g. 20k/5k) → G = 1 + 4 = 5.00× exactly
   V_rail ≈ ±10.5 V (OPA1612 output swing on ±12 V rails) — a device/rail limit, NOT resistor-set.
```

The gain is a **resistor ratio**, so it is the load-bearing, value-derived quantity (moves when R_f
or R_g moves). The clip rail is a device saturation limit (op-amp output swing), not part of the
resistor network — it is checked as a level, not a ratio.

### DSP / plugin law it realizes

```
block-1 GAIN_MAIN (PreGain.hpp:9-13):
  gainParam < 0.5 → return v                              (1× pass-through)
  else            → return clamp(5·v, −10.5, +10.5)       (5× + hard clip at the rail)

block-6 GAIN_BP3 (ALT path, same 1×/5× choice on the ALT input feeding BP3)
```

`5·v` is realized by `1 + R_f/R_g = 4.83×` (within tolerance of 5×); `clamp(…, ±10.5)` is the
op-amp rail swing. The 1× branch returning `v` unchanged is the bypass path-select.

## Design Choices & Rationale

### Non-Inverting (Not Inverting) Gain

The plugin multiplies by **+5** (polarity preserved). A non-inverting amplifier `1 + R_f/R_g` keeps
polarity in a single stage (an inverting `−R_f/R_g` would need a second stage to restore sign) and
presents a high input impedance suitable for driving from an op-amp output or an external jack.

### Path-Select Bypass (Not Op-Amp Gain-of-1)

At 1× the DPDT routes the raw input *around* the op-amp, so the unity path adds no op-amp noise.
This faithfully matches the plugin's true bypass (`return v` unchanged) rather than a gain-of-1
buffer that would still contribute a noise floor.

### Resistor Choice (Noise vs Gain)

R_f = 18 kΩ / R_g = 4.7 kΩ (gain 4.83×) is chosen over higher-impedance 47k/12k to lower the
op-amp current-noise contribution through R_g (lower R → lower `i_n·R` noise) while landing within
3.4 % of 5×. At 5× the output-referred noise rises 14 dB, so a low-noise op-amp (OPA1612, 1.1 nV/√Hz)
is specified for the gain leg.

### Clip Is the Rail, Not a Resistor

The ±10.5 V flat-top is the OPA1612 output saturation on ±12 V rails — intentional aggressive
clipping, not a resistor-set threshold. It is a device limit ([NV]-style), checked as a level.

## Component Values (POGO-specific)

Representative values (live per-instance values are in each using block's netlist; this is the
generic primitive form):

| Ref (generic) | Part | Package | Value | Notes |
|---|---|---|---|---|
| U_GAIN | OPA1612 (block-1) / TL072 (block-6 ALT) | SOIC-8 | — | Non-inverting gain section |
| R_f | Resistor | 0603 | 18 kΩ | Feedback; G = 1 + R_f/R_g |
| R_g | Resistor | 0603 | 4.7 kΩ | (−)-to-AGND leg; 18k/4.7k → 4.83× (≈5×) |
| (clean alt) R_f / R_g | Resistor | 0603 | 20 kΩ / 5 kΩ | → G = 5.00× exactly, if exact 5× wanted |
| SW_GAIN | Dailywell DW3 (2M DPDT ON-ON) | toggle | — | Path-select: 5× amp out vs 1× raw bypass |

## Performance Characteristics

| Parameter | Value | Condition |
|---|---|---|
| Gain (5×) | 1 + R_f/R_g = 4.83× | 18k/4.7k; ≈ +13.7 dB (~14 dB) |
| Gain (1×) | 1.00× | Bypass path-select |
| Clip level | ±10.5 V | OPA1612 rail swing on ±12 V (device limit) |
| Polarity | non-inverting | +5 (matches plugin) |
| 1× path noise | input noise only | op-amp out of the path |

## Known Gotchas / Assembly Notes

- **Gain = 1 + R_f/R_g, NOT R_f/R_g** — the +1 is the non-inverting through-term; 18k/4.7k gives
  4.83× (not 3.83×). Easy off-by-one if copied from an inverting summer.
- The 1× bypass must be a true path-select (op-amp removed), else the "unity" path carries op-amp
  noise. Use a DPDT path selector, not a software-style gain set to 1.
- 4.83× vs an exact 5×: inaudible (3.4 %), within the ±5 % a "5×" switch implies. Use 20k/5k (or
  0.1 % parts) only if exact 5× is required.
- The clip rail is the op-amp swing — pick an op-amp whose rail gives the intended ±10.5 V flat-top
  on ±12 V supplies; it is not set by R_f/R_g.

## Used By

| Block | Instance | Board | Notes |
|---|---|---|---|
| block-1 | GAIN_MAIN (SW1) — main pre-gain 1×/5× | audio | OPA1612 non-inverting; R3=R_g(4.7k), R4=R_f(18k); clip ±10.5 V |
| block-6 | GAIN_BP3 (SW2) — ALT-path 1×/5× into BP3 | audio | Same 1×/5× choice on the ALT input feeding BP3 |
