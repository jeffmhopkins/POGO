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

Block B provides **six** buffered outputs across three pairs:

| Jack pair | Tap point | Musical purpose |
|---|---|---|
| LP2 AUX L / R | Block 6 (LP2) output — before HP filter | "Lowpass band" — frequency content below LP2 cutoff |
| HP AUX L / R | Block 7 (HP) output — after HP filter | "Highpass/bandpass" — frequency content above HP cutoff |
| OUT L / R | Block 7 (HP) output — same tap as HP AUX | Primary patch point for main signal |

LP2 AUX and HP AUX enable parallel routing: e.g., send the lowpass band to a reverb, the
bandpass to a delay, and the full output to the mix bus — all from a single pass through POGO.

### Parameters
None. No user controls.

### Signal Levels (I/O)
- LP2 AUX input: output of LP2 (Block 6) — ±5 V audio, up to ±8 V near LP2 resonance peak
- HP AUX / OUT input: output of HP (Block 7) — ±5 V audio, up to ±8 V near HP resonance peak
- All outputs: same levels as input, low-impedance (~1 kΩ series to jack) — drives up to 600 Ω loads

### Stereo Behavior
Independent L and R buffer circuits per pair — six independent unity-gain buffers total.

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
Non-inverting unity-gain voltage follower, identical to Block A. One buffer half per channel per output pair — six buffer halves total (3× TL072).
1 kΩ series resistor between op-amp output and jack tip (output protection).

```
V_in(LP2 L) ──(+) LP2_AUX_A ──(out)──[1 kΩ]──► LP2 AUX L Jack
                (−)◄── (out)

V_in(LP2 R) ──(+) LP2_AUX_B ──(out)──[1 kΩ]──► LP2 AUX R Jack
                (−)◄── (out)

V_in(HP L) ──(+) HP_AUX_A ──(out)──[1 kΩ]──► HP AUX L Jack  ──┬──► OUT L Jack
               (−)◄── (out)                                     │ (1 kΩ each, separate jacks)

V_in(HP R) ──(+) HP_AUX_B ──(out)──[1 kΩ]──► HP AUX R Jack  ──┴──► OUT R Jack
               (−)◄── (out)
```

Note: HP AUX and OUT tap the same Block 7 signal. Each has its own independent buffer and
1 kΩ series resistor — they are electrically isolated and can be patched to different destinations simultaneously.

### IC / Component Selection

| Reference | Part Number | Package | Value | Qty | Notes |
|---|---|---|---|---|---|
| TOB_LP2 | TL072CDT | SOIC-8 | — | 1 | LP2 AUX L + R output buffers |
| TOB_HP_AUX | TL072CDT | SOIC-8 | — | 1 | HP AUX L + R output buffers |
| TOB_OUT | TL072CDT | SOIC-8 | — | 1 | Main OUT L + R output buffers |
| R_out_x | — | 0603 | 1 kΩ | 6 | Series protection resistors (one per jack) |
| C_VCC, C_VEE | — | 0603 | 100 nF | 6 | Supply decoupling per IC (2 per TL072) |

### Trim Pots
None required.

### Power Draw Estimate
- +12 V: ~6 mA | −12 V: ~6 mA (3× TL072, ~2 mA each)

### Schematic Notes
- Place 100 nF decoupling caps within 1 mm of each TL072 supply pin
- 1 kΩ series resistors between op-amp output and jack tip — never after the jack
- No capacitors in series with audio outputs (DC-coupled)
- Use Thonkiconn PJ301M-12 (or equivalent) TS jacks for all six output jacks
- LP2 AUX taps Block 6 output node; HP AUX and OUT tap Block 7 output node
- All six jacks are on the BAND OUT / OUT top-strip subsection of the panel (see panel-notes.md)
