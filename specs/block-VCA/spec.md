# Block VCA: Pre-LP1 Voltage-Controlled Amplifier

## Status
- Phase 1 (Audio Spec): [x] complete
- Phase 2 (Analog Behavior): [x] complete
- Phase 3 (Circuit Design): [x] complete

---

## Phase 1: Audio / Functional Specification

### Sonic Intent
A voltage-controlled amplifier placed immediately before LP Filter 1, after the distortion
summing stage. It functions as a dynamics gate — using the mod bus (typically driven by the
envelope follower) to accent, duck, or swell the signal entering the filters. At full AMT with
the mod bus riding an envelope: the filters open with the attack of each transient. At AMT
inverted: louder input causes the filter feed to dip, creating a ducking or gating effect.

At default (AMT = center, mod bus at rest): signal passes at unity gain.

### Parameters

| Name | Range | Default | Taper | Description |
|---|---|---|---|---|
| AMT | −1× to +1× | 0 (center) | Linear | Attenuverter — controls how much the mod bus CV scales VCA gain |

No separate LEVEL knob. When AMT = 0 (center detent), the VCA passes at unity gain — the mod
bus has no effect. Full CW: mod bus modulates gain from 0 to 1× as CV swings 0–10 V. Full CCW:
inverted — higher CV reduces gain (ducking/gating).

### CV Modulation Targets

| Target | CV Range | Attenuverter | Notes |
|---|---|---|---|
| VCA Level | 0–10 V | AMT knob (attenuverter) | CV IN jack normalizes to mod bus when unplugged |

### Signal Levels (I/O)
- Input: summed stereo output from Block 4 Distortion, ±5 V nominal (up to ±10 V at high drive)
- Output: same range, attenuated 0–1× by VCA CV; into LP Filter 1 (Block 5) input
- At unity (AMT=0, no CV modulation): signal passes unchanged

### Stereo Behavior
True stereo: independent L and R VCA cells.
The single AMT knob and CV IN jack apply identically to L and R. No independent L/R control.

### Edge Cases
- AMT at center (0): VCA gain = 1.0 regardless of CV. The mod bus has no effect.
- AMT full CW, CV = 0 V: VCA gain = 0 — signal is fully attenuated (muted).
- AMT full CW, CV = 10 V: VCA gain = 1.0 — full pass-through.
- Inverted AMT (full CCW): 10 V input CV gives 0 gain; 0 V gives 1 gain (ducking behavior).
- Hot input (±10 V at max distortion): VCA does not clip internally; the V2164 is rated for
  signal levels within ±supply. With ±12 V rails, ±10 V signal is within safe operating range.

---

## Phase 2: Analog Behavior Model

### Transfer Function

Linear VCA — output is the product of input signal and control voltage:

```
V_out = V_in × G_vca

G_vca = (V_cv_att / V_ref)   where V_ref = 10 V (full-scale unipolar)
```

The AMT attenuverter scales V_cv before it reaches the VCA control input:
```
V_cv_att = AMT_gain × V_cv_in

AMT_gain ∈ [−1, +1]   (center detent = 0)
```

Combined:
```
V_out = V_in × clamp(AMT_gain × V_cv_in / 10, 0, 1)
```

Note: VCA gain is unipolar (0 to 1×). Negative AMT with positive CV produces inverted (ducking)
behavior by driving the control toward a lower gain value.

### Frequency Response
Flat from DC to the V2164 bandwidth limit (~1 MHz). Perceptually transparent.

### Dynamic Behavior
V2164 is an exponential-law VCA. The control voltage (from AMT attenuverter output) drives the
exponential gain law. A linear-law response is achieved by using a logarithmic pre-driver
(or by relying on the linear region of the V2164 at modest modulation depths).

For musical use (accent / envelope VCA), the exponential law of the V2164 is appropriate:
it matches the logarithmic nature of human loudness perception.

---

## Phase 3: Circuit Design

### Topology
V2164 quad VCA IC. This block uses 2 cells (L and R signal paths). The remaining 2 cells are
shared with LP1's resonance control (V2164 is a quad; LP1 uses 2 cells for Q modulation,
VCA uses the other 2 cells for amplitude control).

```
V_in_L ──[100 Ω]──► V2164 cell 3 (L VCA) ──► V_out_L ──► LP1 input L
V_in_R ──[100 Ω]──► V2164 cell 4 (R VCA) ──► V_out_R ──► LP1 input R

V_cv_in (CV IN jack, normalizes to mod bus)
  ──[100 Ω]──[BAT54 clamp]──► AMT attenuverter pot ──► V2164 control input
```

Both L and R cells receive the same control voltage from the AMT attenuverter — they track
together for a stereo-linked VCA response.

### CV Input Path (standard)
```
MOD BUS ──[tip switch]──[100 Ω]──[BAT54 SOT-23]──► AMT pot (−1× to +1×) ──► V2164 ctrl
                              ▲
                 CV IN jack ──┘  (tip-switching: disconnects mod bus when patched)
```

### IC / Component Selection

| Reference | Part Number | Package | Qty | Notes |
|---|---|---|---|---|
| VCA_MAIN | V2164D | SOIC-16 | 1 | Shared with LP1: cells 1+2 for LP1 Q, cells 3+4 for L/R VCA |
| RV_AMT | Bipolar pot | 9 mm | 1 | AMT attenuverter (−1× to +1×, center detent) |
| D_cv | BAT54S | SOT-23 | 1 | CV input protection clamp |
| R_cv | — | 0603 | 100 Ω | 1 | Series resistor at CV input |
| R_in_L, R_in_R | — | 0603 | 100 Ω | 2 | Series resistors at audio inputs |

### Trim Pots
None required. V2164 gain is set by control voltage; unity gain at AMT center is inherent
when V_cv_att = 0 V (center detent of attenuverter).

Optional: if unity gain offset is needed, a small trim can be added to the V2164 control
input reference, but this is typically not required with the V2164's internal reference.

### Power Draw Estimate
The V2164 IC is shared with LP1. The VCA block adds no additional ICs.
Marginal additional draw from 2 V2164 cells: < 2 mA.
- +12 V: ~2 mA | −12 V: ~2 mA (incremental, IC shared with LP1)

### Schematic Notes
- V2164 cell allocation:
  - Cell 1: LP1 L resonance Q control (Block 5)
  - Cell 2: LP1 R resonance Q control (Block 5)
  - Cell 3: VCA L signal path (this block)
  - Cell 4: VCA R signal path (this block)
- Route V2164 cells 3 and 4 control voltage from the same attenuverter node
- Place VCA on the same PCB as LP1 (they share the V2164 IC)
- Audio signal flows: Block 4 summing output → VCA inputs → LP1 summing amp input

### Known Circuit Challenges
- **V2164 cell allocation**: sharing the V2164 with LP1 saves PCB space and cost but means both
  blocks must be on the same PCB. Verify that LP1 resonance control voltage and VCA control
  voltage do not crosstalk inside the V2164 package (cells are independent — no risk at the
  circuit level, but keep control traces routed away from each other on PCB).
- **Unity-gain at center detent**: the attenuverter at center (0 V output) drives V2164 control
  to a level corresponding to G = 1. Verify this with the V2164 datasheet control law at 0 V ctrl.
  May require a small DC bias offset on the control input to set exactly G = 1 at rest.
- **Exponential vs linear perception**: for gentle accent modulation, the exponential law of the
  V2164 is helpful. For hard gating (modulation to silence), verify the V2164 reaches G ≈ 0
  within the attenuverter's output range.
