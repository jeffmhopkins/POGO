# Block B: Output Buffers
Unity-gain output stage that clamps and drives six output jacks: MAIN_L/R, BP3_L/R, LFO1, LFO2.

DSP source: `plugin/src/Pogo.cpp` (lines 493–499)

---

## 1. Intent

Block B is the last stage before signals leave the module. It presents six output jacks
to the outside world: the main stereo output (LP2 → MAIN_L/R), a pre-mix formant tap
from the BP3 group (BP3_L/R), and the two LFO outputs. The output buffers protect the
internal signal chain from load impedance variations introduced by downstream patch cables
and modules, hold the output voltage within the ±11 V Eurorack-safe window, and provide
a low-output-impedance drive via a 1 kΩ series resistor (the standard Eurorack output
protection value). The user hears MAIN_L/R as the fully processed signal and optionally
uses BP3_L/R as a pre-mix formant send for parallel processing. LFO outputs are available
as modulation sources for other modules.

---

## 2. Theoretical Design and Topology

### DSP-to-analog mapping

The DSP model applies a final clamp then writes to jack outputs:

```
MAIN_L/R:  V_out = clamp(LP2 output, −11 V, +11 V)
BP3_L/R:   V_out = clamp(BP3 distorted tap, −11 V, +11 V)
LFO1/2:    V_out = LFO triangle ±5 V (no additional clamp in DSP)
```

In hardware, the clamp is again the natural output swing of the buffer op-amp on ±12 V
rails. The 1 kΩ series resistor is added at the op-amp output before the jack to limit
short-circuit current and attenuate RF pickup.

### Transfer function

In the linear region:

```
H(s) = 1      (unity-gain voltage follower, for MAIN and BP3 paths)
```

The LFO outputs are already driven by a buffered op-amp stage in Block 2 (see block-2
spec). They are wired through a 1 kΩ series resistor to the jack, with no additional
buffer stage in Block B.

### Topology choice and rationale

**Non-inverting voltage follower (gain = +1)** for MAIN_L/R and BP3_L/R.

TL072 is chosen here (not LM4562 or NE5532) because:
- Block B is at the end of the chain; its noise contribution is not amplified further.
- TL072 quiescent current (~1.4 mA/channel = 2.8 mA per package) is lower, conserving power budget.
- Output swing on ±12 V rails is ±11 V typical — consistent with the DSP clamp value.
- The application is a low-gain output driver, not a noise-sensitive amplifier.

Two TL072CDT packages are used:
- U_MAIN: halves A and B serve MAIN_L and MAIN_R respectively.
- U_BP3: halves A and B serve BP3_L and BP3_R respectively.

**LFO outputs** do not receive additional buffer stages in Block B. The LFO op-amp
output from Block 2 is routed directly through a 1 kΩ series resistor to J_LFO1 and
J_LFO2. This is a valid approach because:
- The LFO stage in Block 2 already has a low-impedance op-amp output.
- The 1 kΩ series resistor provides short-circuit protection.
- LFO signals are low-frequency (0.05–20 Hz); no high-frequency loading concerns.

### Hardware deviations from DSP model

The DSP model has no output impedance — it writes a voltage directly to the rack
simulation node. In hardware, the 1 kΩ series resistor creates a voltage divider
with the input impedance of the downstream module (typically 100 kΩ), resulting in
a −0.01 dB attenuation, negligible in practice. The DSP clamp at ±11 V maps cleanly
to the TL072 output swing.

→ References `aux/unity-buffer.md`

---

## 3. Physical Design

### Component values and derivations

**Output series resistors (R_MAIN_L, R_MAIN_R, R_BP3_L, R_BP3_R): 1 kΩ each**

Standard Eurorack output protection value. Limits short-circuit current from op-amp
output:
```
I_sc = V_rail / R_series = 11 V / 1 kΩ = 11 mA
```
This is within op-amp output current ratings and prevents oscillation caused by
capacitive cable loading.

**LFO output series resistors (R_LFO1, R_LFO2): 1 kΩ each**

Same rationale as audio outputs. Placed on Block 2 board but logically part of the
output path.

**Op-amps (U_MAIN, U_BP3): TL072CDT, SOIC-8**
- One dual package per stereo pair.
- Configured as voltage followers (output tied back to inverting input).
- Supply decoupling: 100 nF X7R 0603 on each supply pin.

### Signal routing

```
LP2 outL  → U_MAIN half-A (+) → U_MAIN half-A output → R_MAIN_L (1 kΩ) → J_MAIN_L
LP2 outR  → U_MAIN half-B (+) → U_MAIN half-B output → R_MAIN_R (1 kΩ) → J_MAIN_R

BP3 tapL  → U_BP3 half-A (+)  → U_BP3 half-A output  → R_BP3_L  (1 kΩ) → J_BP3_L
BP3 tapR  → U_BP3 half-B (+)  → U_BP3 half-B output  → R_BP3_R  (1 kΩ) → J_BP3_R

LFO1 out  → R_LFO1 (1 kΩ) → J_LFO1    (no additional buffer)
LFO2 out  → R_LFO2 (1 kΩ) → J_LFO2    (no additional buffer)
```

### Calibration points

No calibration required. Unity-gain followers have no adjustable parameters. The ±11 V
output ceiling is determined by TL072 output swing — a property of the IC.

### Trim pots

None.

### Board assignment

Audio board (U_MAIN, U_BP3 and their associated resistors). Panel jacks are on the
panel board. LFO series resistors (R_LFO1, R_LFO2) are placed on the utility board
near the LFO output stage, but are logically Block B's responsibility.

### Power Draw Estimate

- 2× TL072CDT (U_MAIN, U_BP3, dual SOIC-8): ~3 mA each = ~6 mA  (TI: 1.4 mA/ch × 2 = 2.8 mA)
- **+12V: ~6 mA | −12V: ~6 mA**

→ References `aux/unity-buffer.svg` for op-amp follower schematic primitive.

---

## 4. Component Requirements

| Ref | Part | Package | Value | Qty | Board | Block | Function |
|---|---|---|---|---|---|---|---|
| U_MAIN | TL072CDT | SOIC-8 | — | 1 | audio | block-B | MAIN_L + MAIN_R output buffers |
| U_BP3 | TL072CDT | SOIC-8 | — | 1 | audio | block-B | BP3_L + BP3_R output buffers |
| R_MAIN_L | resistor | 0603 | 1 kΩ | 1 | audio | block-B | MAIN_L output series protection |
| R_MAIN_R | resistor | 0603 | 1 kΩ | 1 | audio | block-B | MAIN_R output series protection |
| R_BP3_L | resistor | 0603 | 1 kΩ | 1 | audio | block-B | BP3_L output series protection |
| R_BP3_R | resistor | 0603 | 1 kΩ | 1 | audio | block-B | BP3_R output series protection |
| R_LFO1 | resistor | 0603 | 1 kΩ | 1 | utility | block-B | LFO1 output series protection |
| R_LFO2 | resistor | 0603 | 1 kΩ | 1 | utility | block-B | LFO2 output series protection |
| C_B | cap, X7R | 0603 | 100 nF | 4 | audio | block-B | TL072 supply decoupling (2 ICs × 2 pins) |
| J_MAIN_L | PJ301M-12 | panel | — | 1 | panel | block-B | MAIN_L output jack |
| J_MAIN_R | PJ301M-12 | panel | — | 1 | panel | block-B | MAIN_R output jack |
| J_BP3_L | PJ301M-12 | panel | — | 1 | panel | block-B | BP3_L output jack (pre-mix formant tap) |
| J_BP3_R | PJ301M-12 | panel | — | 1 | panel | block-B | BP3_R output jack (pre-mix formant tap) |
| J_LFO1 | PJ301M-12 | panel | — | 1 | panel | block-B | LFO1 output jack |
| J_LFO2 | PJ301M-12 | panel | — | 1 | panel | block-B | LFO2 output jack |
