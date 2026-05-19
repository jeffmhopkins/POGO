# Block 1: Pre-Gain Boost

## Status
- Phase 1 (Audio Spec): [x] complete
- Phase 2 (Analog Model): [x] complete
- Phase 3 (Circuit Design): [x] complete

---

## Phase 1: Audio / Functional Specification

### Sonic Intent
A switchable gain boost placed right at the input, before any filtering or distortion. At unity
the signal passes through clean and transparent. At 5× (~14 dB) the input gain is high enough
to push quieter sources harder into the comb filter and distortion stages — adding apparent
saturation and density to the signal chain downstream without changing the filter parameters.

The toggle switch should feel intentional and definitive, like toggling between "signal" and
"driven." No soft ramping. The gain change is instantaneous.

### Parameters

| Name | Range | Default | Taper | Description |
|---|---|---|---|---|
| BOOST | Toggle: OFF / ON | OFF | N/A | OFF = unity (1×); ON = 5× boost (~14 dB) |

No CV modulation for this block — mechanical toggle only.

### Signal Levels (I/O)
- Input: ±5 V audio (from Block A buffers)
- Unity output: ±5 V
- Boost (5×) output: up to ±25 V pre-clamp — must be clamped before the next stage
  - In practice: the op-amp will hard-clip at ~±10.5 V on ±12 V rails
  - Intentional soft saturation from op-amp limiting at high-amplitude inputs in boost mode
  - Output fed to Block 2 (Envelope Follower), which sees ±5 V to ±10.5 V depending on input

### Stereo Behavior
Single toggle switch applies equally to both L and R channels simultaneously. Both channels
share the same gain state at all times. True stereo signal path (independent op-amps for L and R).

### Edge Cases
- At 5× gain with a full-scale ±5 V input: theoretical output ±25 V, clamped to ~±10.5 V by
  op-amp output swing limits. This soft saturation is a feature, not a bug — it adds harmonic
  content before the comb filter.
- Signal near silence: 5× of near-zero is still near-zero. No noise floor amplification concern
  given TL072's input noise floor.

---

## Phase 2: Analog Behavior Model

### Transfer Function
Linear amplifier with switchable gain:

```
V_out = G × V_in

where G = 1.0  (unity, toggle OFF)
      G = 5.0  (boost, toggle ON)
```

Non-inverting op-amp configuration:
`G = 1 + R_f / R_in`

- Unity (G=1): R_f = 0 (short), R_in = ∞ (open) — or: direct feedback, no input resistor
  (standard voltage follower)
- Boost (G=5): `5 = 1 + R_f / R_in` → `R_f / R_in = 4` → e.g. R_f = 40 kΩ, R_in = 10 kΩ

The toggle switch selects between these two feedback networks.

### Frequency Response
Flat from DC to:
- Unity: ~3 MHz (TL072 GBW at gain=1)
- Boost (×5): GBW/5 = ~600 kHz (still well beyond audio band)

Both settings are flat across 20 Hz – 20 kHz.

### Saturation Model
At boost (×5), op-amp output is limited by the supply rails (~±10.5 V on ±12 V supply):

```
V_out = clamp(5 × V_in, −10.5, +10.5)
```

For a ±5 V input signal this means clipping onset at V_in ≥ ±2.1 V.
Typical Eurorack audio peaks at ±5 V, so clipping is hard at boost — intentionally aggressive.
The TL072 soft-clips slightly before the hard rail limit, adding gentle odd harmonics at onset.

### Parameter-to-Behavior Mapping
Toggle OFF: pass-through (unity follower)
Toggle ON: gain = 5× via switched resistor feedback network

---

## Phase 3: Circuit Design

### Topology
Non-inverting op-amp with toggle-switched feedback resistors. Single-pole double-throw (SPDT)
toggle switch on the front panel selects between two feedback ratios.

```
                 ┌────[R_f]────┐
                 │             │
V_in(L) ─(+)─[TG1A]─(out)──┬──┘  BOOST_out(L) → Block 2
               (−)◄──────────┤
                             │     Toggle position:
                             │     OFF: R_f = 0Ω wire (follower)  → G = 1×
                             │     ON:  R_f = 40kΩ, R_in = 10kΩ  → G = 5×
                             │
                   GND──[R_in]─────(−) for gain mode
                                   (switched in by toggle)
```

Both L and R channels use identical circuits. A dual SPDT toggle switch (2PDT) selects both
channels simultaneously with a single panel control.

**Switch wiring note:** The toggle physically switches the feedback path between a wire (G=1)
and the R_f/R_in network (G=5). Use a 2PDT toggle: one pole for L, one pole for R.

### IC / Component Selection

| Reference | Part Number | Package | Value | Qty | Notes |
|---|---|---|---|---|---|
| TG1 | TL072CDT | SOIC-8 | — | 1 | Dual op-amp: TG1A = L channel, TG1B = R channel |
| R_f | — | 0603 | 40.2 kΩ | 2 | Feedback resistor (E96 value closest to 40 kΩ) |
| R_in | — | 0603 | 10.0 kΩ | 2 | Input resistor (1% tolerance) |
| SW1 | 2PDT toggle | Panel mount | — | 1 | Panel toggle, 2-pole: L and R switched simultaneously |
| C_VCC, C_VEE | — | 0603 | 100 nF | 2 | Supply decoupling at TG1 pins |

### Component Value Derivations
- Target G = 5: `R_f/R_in = G−1 = 4`
- Choose R_in = 10 kΩ → R_f = 40 kΩ → use 40.2 kΩ (E96 series, ≤0.5% error)
- Use 1% tolerance resistors for both to keep gain error <2%

### Trim Pots
None required. The gain values are set by resistor ratios; 1% resistors give <2% gain error.
If L/R gain matching better than 1 dB is needed, replace one R_in per channel with a 10 kΩ
series combination of 9.1 kΩ fixed + 2 kΩ trim pot (Bourns 3224W).

### Power Draw Estimate
- TL072: ~1.4 mA quiescent per rail per IC
- +12 V: ~3 mA | −12 V: ~3 mA

### Schematic Notes (see schematic.svg)
- Route toggle switch wires as short as possible to avoid RF pickup on the feedback node
- Place 100 nF decoupling caps within 1 mm of TG1 supply pins
- Label SW1 positions on the schematic: position A = UNITY, position B = BOOST

### Known Circuit Challenges
- At BOOST mode with hot input (>±2.1 V), the op-amp hard-clips. This is intentional, but
  ensure the downstream stage (Block 2 Envelope Follower) handles the clipped waveform correctly —
  a clipped waveform has a very accurate envelope (nearly constant amplitude), which is useful
  for the envelope follower tracking drums or sustained notes.
- 2PDT toggle must switch cleanly with no intermediate floating state between positions;
  use a break-before-make or make-before-break toggle (either acceptable here since the gain
  stages are not sensitive to momentary float during switching)
