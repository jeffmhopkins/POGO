# Block A: Input Buffers + Protection

## Status
- Phase 1 (Audio Spec): [x] complete
- Phase 2 (Analog Model): [x] complete
- Phase 3 (Circuit Design): [x] complete

---

## Phase 1: Audio / Functional Specification

### Sonic Intent
Transparent, unity-gain buffering. This block is invisible to the audio signal — its sole job
is to isolate POGO's internal circuitry from whatever is plugged into the jacks, and to protect
ICs from out-of-range voltages. No coloration. No filtering.

### Parameters
None. No user controls — purely passive protection + active buffer.

### Signal Levels (I/O)
- Input: ±5 V audio (10 Vpp), 0–10 V or ±5 V CV — whatever arrives from the patch
- Output (to Block 1): same levels, buffered — ≤0.01 dB insertion loss, no measurable distortion

### Stereo Behavior
True stereo: independent L and R buffer circuits.

### Edge Cases
- Hot signal from a distorted source: up to ±12 V possible in the wild → clamped to ±12 V by BAT54 before the buffer
- CV from a buggy module: same clamp protection
- Short circuit at the jack: 100 Ω series resistor limits current to ≤120 mA before clamp engages

---

## Phase 2: Analog Behavior Model

### Transfer Function
`H(s) = 1`  — unity gain, all frequencies, flat phase response.

Op-amp configured as a voltage follower (non-inverting, gain = 1):
`V_out = V_in` over the full audio range (DC to 100 kHz with TL072, GBW = 3 MHz)

### Frequency Response
Flat from DC to ~100 kHz (−3 dB at GBW/1 ≈ 3 MHz for TL072 at unity gain). Audio band
(20 Hz – 20 kHz) is essentially perfect.

### Nonlinearity
None intended. Input is clamped to ±12 V before the op-amp; op-amp output swings to within ~1.5 V
of the ±12 V rails (TL072 output: ±10.5 V typical on ±12 V supply). Signals above ~±10.5 V
will be clipped by the op-amp — acceptable, as Eurorack signals should not exceed ±5 V.

### Known Analog Imperfections
- TL072 input offset voltage: ~3 mV typical → negligible DC offset at output
- TL072 noise: 18 nV/√Hz — acceptable for a signal that will be heavily processed downstream

---

## Phase 3: Circuit Design

### Topology
Non-inverting op-amp voltage follower. One half of a TL072 (SOIC-8) per input channel.
Two inputs (L + R) fit on a single TL072. See `specs/shared/cv-input-protection.md` for the
input protection network preceding each buffer.

```
Jack (L) tip
  │──[100 Ω]──+─(+in) TU1A ─(out)──── L_buffered → Block 1
               │        └──(−in)◄────────────────── (feedback, unity gain)
             BAT54
           +12V/−12V

Jack (R) tip
  │──[100 Ω]──+─(+in) TU1B ─(out)──── R_buffered → Block 1
               │        └──(−in)◄────────────────── (feedback, unity gain)
             BAT54
           +12V/−12V
```

### IC / Component Selection

| Reference | Part Number | Package | Value | Qty | Notes |
|---|---|---|---|---|---|
| TU1 | TL072CDT | SOIC-8 | — | 1 | Dual op-amp; one half per channel |
| R_L_in, R_R_in | — | 0603 | 100 Ω | 2 | Series protection |
| D_L, D_R | BAT54S | SOT-23 | — | 2 | Dual Schottky clamp; 1 per jack |
| C_VCC, C_VEE | — | 0603 | 100 nF | 2 | Decoupling at TU1 supply pins |

### Trim Pots
None required for input buffers — unity gain is set by direct feedback topology.

### Power Draw Estimate
- TL072 quiescent: ~1.4 mA per supply rail per IC
- +12 V: ~2 mA | −12 V: ~2 mA (for L+R input buffer pair)

### Schematic Notes (see schematic.svg)
- Place 100 nF decoupling caps within 1 mm of TU1 supply pins (pins 4 and 8)
- Route BAT54 clamp diodes close to the jack footprint, before the series resistor traces reach TU1
- L and R inputs share one TL072 package; label TU1A (L) and TU1B (R)

### Known Circuit Challenges
- TL072 is not rail-to-rail output; keep internal signal levels ≤ ±10 V to avoid clipping
- BAT54S SOT-23 package is polarity-sensitive — double-check cathode/anode orientation in layout
