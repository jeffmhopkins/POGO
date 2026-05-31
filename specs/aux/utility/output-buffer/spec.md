# aux: Output Buffer (Unity Follower + Series-R + ±11 V Clamp)

**Type:** `utility` · part of the [aux circuit library](../../_LIBRARY.md)

Design status: [ ] draft → [ ] reviewed → [ ] validated on prototype

## Overview

The standard POGO **output stage**: a non-inverting unity voltage follower (G = +1)
followed by a 1 kΩ series protection resistor into the output jack. The op-amp's natural
output swing on ±12 V rails provides a ±11 V clamp with no extra parts — this is the analog
realization of the plugin's `clamp(…, −11 V, +11 V)` on the MAIN/BP3 jacks.

This cell isolates the upstream high-impedance filter node from the patch cable, limits
short-circuit current (≤ 11 mA), and presents a low output impedance to the next module.
It is the I/O dual of `aux/utility/cv-protection` (which guards *inputs*).

Chosen because:
- A voltage follower adds no gain → no extra noise; TL072 is adequate at signal levels (±5 V).
- The 1 kΩ series R is the standard Eurorack output-protection value; its only audible effect
  is a negligible divider into the next module's input impedance (≈ −0.087 dB into 100 kΩ).
- The ±11 V ceiling is free (the op-amp rail-limited swing), matching the DSP clamp exactly.

## Schematic

ASCII (one channel; the upstream node is already a low-Z op-amp output or a filter output buffer):

```
                  ┌───────────────────┐
  V_node ─────────┤ (+)  TL072 half    ├───┬──[ R_ser 1 kΩ ]──► J_OUT ──► downstream module
                  │ (−)◄───────────────┤   │                              (≈100 kΩ input Z)
                  └───────────────────┘   └─ follower output (low-Z, ±11 V rail-limited)

  Clamp:  V_OUT = clamp(V_node, −11 V, +11 V)   — the TL072 output swing on ±12 V rails
  Divider into a 100 kΩ load:  V_jack = V_OUT · R_load/(R_load + R_ser)
```

## Transfer Function

```
In-band (|V_node| ≤ 11 V):
  V_buf  = V_node                                  (unity follower, G = +1)
  V_jack = V_buf · R_load / (R_load + R_ser)        (series-R / load divider)
         = V_buf · 100k / (100k + 1k) = 0.99010 · V_buf   (−0.087 dB into 100 kΩ)

Over-rail (|V_node| > 11 V):
  V_buf  = sign(V_node) · 11 V                      (op-amp rail-limited swing) [NV]
```

The unity gain is topological (no gain-setting resistors). The divider ratio is set purely
by `R_ser` against the downstream load; with the standard 1 kΩ series R into a nominal 100 kΩ
module input it is 0.990×. The ±11 V ceiling is **[NV]** — it depends on the op-amp's output
swing on ±12 V rails (a device constant), not on any bindable resistor, so the sim checks only
that the clamp reaches +11 V (no more), it does not pin 11 V to a part value.

## Design Choices & Rationale

- **TL072CDT (not LM4562/NE5532):** the followers add no gain, so low-noise audio op-amps buy
  nothing here; TL072 has lower Iq (~1.4 mA/ch) and its ±11 V swing on ±12 V rails is exactly
  the DSP clamp value. (See `aux/utility/unity-buffer` for the IC-selection rationale.)
- **1 kΩ series R at the jack only:** short-circuit current `I_sc = 11 V / 1 kΩ = 11 mA`; the
  R is omitted on internal nodes to avoid needless HF roll-off into cable capacitance.
- **Clamp = rail swing, not diodes:** the MAIN/BP3 outputs are already inside ±11 V from the
  upstream clamps; the buffer rail merely enforces the ceiling. No output clamp diodes needed.

## Component Values (POGO-specific)

| Ref (generic) | Part | Package | Value | Notes |
|---|---|---|---|---|
| U_OUT | TL072CDT | SOIC-8 | — | One half per channel; non-inverting follower |
| R_ser | Resistor | 0603 | 1 kΩ | Series output protection at the jack; sets the load divider |
| C_VCC, C_VEE | Ceramic bypass | 0603 | 100 nF | Per supply pin |

## Performance Characteristics

| Parameter | Value | Condition |
|---|---|---|
| Gain (follower) | +1.000 (0 dB) | G = 1, unity |
| Insertion loss into 100 kΩ | −0.087 dB (0.990×) | 1 kΩ series R |
| Output ceiling | ±11 V | TL072 swing on ±12 V rails [NV] |
| Output impedance | ~50 Ω + 1 kΩ series | At the jack |
| Short-circuit current | ≤ 11 mA | Via 1 kΩ R_ser |

## Known Gotchas / Assembly Notes

- The −0.087 dB divider only appears when a load is attached; an unloaded (open-jack) output
  reads the full follower voltage. Calibration against the plugin should account for the load.
- TL072 input common-mode range excludes the negative rail; fine for audio (stays |V| ≤ 11 V).
- 100 nF decoupling within 1 mm of each supply pin or the TL072 can oscillate with cable load.

## Used By

| Block | Instance | Board | Notes |
|---|---|---|---|
| block-B | MAIN_L/R buffers (U_MAIN) | audio | TL072; unity follower + 1 kΩ; ±11 V = plugin `clamp(±11)` |
| block-B | BP3_L/R buffers (U_BP3) | audio | TL072; unity follower + 1 kΩ; R normals to L (block-6 owns the jacks) |
