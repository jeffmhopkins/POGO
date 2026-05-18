# Block B: Output Buffers

## Status
- Phase 1 (Audio Spec): [x] complete
- Phase 2 (Analog Model): [x] complete
- Phase 3 (Circuit Design): [x] complete

---

## Phase 1: Audio / Functional Specification

### Sonic Intent
Transparent, low-impedance output buffers. Drive the output jacks and any downstream module
without coloration, without frequency-dependent loading, and without the last filter stage's
output impedance interacting with cable capacitance. Identical to Block A in philosophy —
the signal should not change passing through this block.

### Parameters
None. No user controls.

### Signal Levels (I/O)
- Input: output of HP Filter (Block 7) — ±5 V audio (up to ±8 V with resonance boost)
- Output: same levels, low-impedance (~1 kΩ series to jack) — drives up to 600 Ω loads

### Stereo Behavior
Independent L and R output buffer circuits. Each jack has its own buffer.

### Edge Cases
- Short circuit on output jack: 1 kΩ series resistor limits current to ≤12 mA — TL072 output
  can source/sink ~25 mA → survives short circuit without damage
- Capacitive cable load: 1 kΩ series resistor + cable capacitance (~100 pF for 1m cable) forms
  an RC lowpass at 1.6 MHz — negligible in the audio band

---

## Phase 2: Analog Behavior Model

### Transfer Function
`H(s) = 1`  — same as Block A input buffers.

### Frequency Response
Flat from DC to ~3 MHz (TL072 GBW at unity gain). Audio band: essentially perfect.

---

## Phase 3: Circuit Design

### Topology
Non-inverting unity-gain voltage follower, identical to Block A. One TL072 half per channel.
1 kΩ series resistor between op-amp output and jack tip (output protection).

```
V_in(L from HP) ──(+) TOB_A ──(out)──[1 kΩ]──► L Output Jack
                    (−)◄── (out)

V_in(R from HP) ──(+) TOB_B ──(out)──[1 kΩ]──► R Output Jack
                    (−)◄── (out)
```

### IC / Component Selection

| Reference | Part Number | Package | Value | Qty | Notes |
|---|---|---|---|---|---|
| TOB | TL072CDT | SOIC-8 | — | 1 | Dual op-amp; TOB_A = L channel, TOB_B = R channel |
| R_out_L, R_out_R | — | 0603 | 1 kΩ | 2 | Series output protection resistors |
| C_VCC, C_VEE | — | 0603 | 100 nF | 2 | Supply decoupling at TOB supply pins |

### Trim Pots
None required.

### Power Draw Estimate
- +12 V: ~2 mA | −12 V: ~2 mA

### Schematic Notes
- Place 100 nF decoupling caps within 1 mm of TOB supply pins
- 1 kΩ series resistors go between op-amp output pin and jack tip — do not place after the jack
- No capacitors in series with audio outputs (DC-coupled per Eurorack convention)
- Use Thonkiconn PJ301M-12 (or equivalent) TS jacks for L OUT and R OUT
