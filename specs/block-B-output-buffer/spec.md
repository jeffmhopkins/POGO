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

Block B provides **four** buffered outputs across two pairs:

| Jack pair | Tap point | Musical purpose |
|---|---|---|
| LP1 L / LP1 R | Block 5 (LP1) output — before LP2 | BAND OUT: LP-filtered content before the second LP stage; useful for parallel routing |
| LEFT / RIGHT | Block 7 (HP) output | Primary patch point: main stereo output after full signal chain |

BAND OUT taps at the LP1 output. This enables parallel routing — e.g., LP1 output to one
destination (reverb, delay, aux mix) while the full output (LP2 + HP) goes to the main bus.

### Parameters
None. No user controls.

### Signal Levels (I/O)
- BAND OUT input: LP1 output (Block 5) — ±5 V audio, up to ±8 V near LP1 resonance peak
- LEFT/RIGHT input: HP filter output (Block 7) — ±5 V audio, up to ±8 V near HP resonance peak
- All outputs: same levels as input, low-impedance (~1 kΩ series to jack) — drives up to 600 Ω loads

### Stereo Behavior
Independent L and R buffer circuits per pair — four independent unity-gain buffers total.

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
Non-inverting unity-gain voltage follower, identical to Block A. One buffer half per channel per
output pair — four buffer halves total (2× TL072).
1 kΩ series resistor between op-amp output and jack tip (output protection).

```
V_in(LP1 L) ──(+) BAND_BUF_A ──(out)──[1 kΩ]──► BAND OUT L Jack  (LP1 L)
                 (−)◄── (out)

V_in(LP1 R) ──(+) BAND_BUF_B ──(out)──[1 kΩ]──► BAND OUT R Jack  (LP1 R)
                 (−)◄── (out)

V_in(HP L) ──(+) OUT_BUF_A ──(out)──[1 kΩ]──► LEFT Output Jack
               (−)◄── (out)

V_in(HP R) ──(+) OUT_BUF_B ──(out)──[1 kΩ]──► RIGHT Output Jack
               (−)◄── (out)
```

Each pair uses one TL072 (dual op-amp): half A for L, half B for R.

### IC / Component Selection

| Reference | Part Number | Package | Value | Qty | Notes |
|---|---|---|---|---|---|
| TOB_BAND | TL072CDT | SOIC-8 | — | 1 | BAND OUT L + R buffers (LP1 tap) |
| TOB_OUT | TL072CDT | SOIC-8 | — | 1 | Main LEFT + RIGHT output buffers (HP tap) |
| R_out_x | — | 0603 | 1 kΩ | 4 | Series protection resistors (one per jack) |
| C_VCC, C_VEE | — | 0603 | 100 nF | 4 | Supply decoupling per IC (2 per TL072) |

### Trim Pots
None required.

### Power Draw Estimate
- +12 V: ~4 mA | −12 V: ~4 mA (2× TL072, ~2 mA each)

### Schematic Notes
- Place 100 nF decoupling caps within 1 mm of each TL072 supply pin
- 1 kΩ series resistors between op-amp output and jack tip — never after the jack
- No capacitors in series with audio outputs (DC-coupled)
- Use Thonkiconn PJ301M-12 (or equivalent) TS jacks for all four output jacks
- BAND OUT taps Block 5 (LP1) output node; LEFT/RIGHT tap Block 7 (HP) output node
- All four jacks are on the top-strip subsections of the panel (see panel-notes.md)
