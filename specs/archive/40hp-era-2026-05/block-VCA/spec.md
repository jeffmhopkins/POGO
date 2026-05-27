# Block VCA: Pre-LP1 Voltage-Controlled Amplifier

## Status
- Phase 1R (Extract from code): [x] complete — updated for 48HP (added VCA_OFS)
- Phase 2R (Analog model): [ ] complete
- Phase 3R (Circuit design): [ ] complete

> **48HP update (2026-05-27):** Added `VCA_OFS_PARAM` floor offset. Signal chain position
> unchanged (before LP1, after Pre-Gain). Mod bus source is now LFO1 (not envelope follower).

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

| Name | Enum | Range | Default | Taper | Description |
|---|---|---|---|---|---|
| VCA Depth (AMT) | `VCA_AMT_PARAM` | −1 to +1 | 0 (center) | Linear | Bipolar attenuverter — controls how mod CV scales VCA gain |
| VCA Floor Offset | `VCA_OFS_PARAM` | 0–1 | 0.5 | Linear | Shifts the effective CV floor: 0=silent at 0V, 0.5=half floor, 1=full floor (unity regardless of CV) |

No separate LEVEL knob. When AMT = 0 (center detent), the VCA passes at unity gain — the mod
bus has no effect. Full CW: mod bus modulates gain from 0 to 1× as CV swings 0–10 V. Full CCW:
inverted — higher CV reduces gain (ducking/gating).

**VCA_OFS (floor offset):** Shifts the effective CV input before the gain law:
`eff_cv = clamp(raw_cv + VCA_OFS × 5, 0, 10)`.
- VCA_OFS=0: no shift (original behavior — signal fully muted when CV=0 and AMT>0)
- VCA_OFS=0.5: adds 2.5V floor — minimum CV of 2.5V even when VCA_IN=0
- VCA_OFS=1: adds 5V floor — equivalent to always having 5V on the CV input

### CV Modulation Targets

| Target | Enum | CV Range | Attenuverter | Notes |
|---|---|---|---|---|
| VCA Level | `VCA_INPUT` | 0–10 V | AMT (`VCA_AMT_PARAM`) | Normalizes to mod bus when unpatched |

`VCA_OFS_PARAM` is a trimpot (no CV input) — sets a fixed floor offset on the effective CV.

### Signal Levels (I/O)
- Input: stereo output from Pre-Gain (Block 1), ±5 V nominal (up to ±10.5 V at 5× gain)
- Output: same range, attenuated 0–1× by VCA CV; into LP Filter 1 (LP1) input
- At unity (AMT=0, no CV modulation): signal passes unchanged

### Stereo Behavior
True stereo: independent L and R VCA cells.
The single AMT knob and CV IN jack apply identically to L and R. No independent L/R control.

### Edge Cases
- AMT at center (0): VCA gain = 1.0 regardless of CV. The mod bus has no effect.
- AMT full CW, CV = 0 V: VCA gain = 0 — signal is fully attenuated (muted).
- AMT full CW, CV = 10 V: VCA gain = 1.0 — full pass-through.
- Inverted AMT (full CCW): 10 V input CV gives 0 gain; 0 V gives 1 gain (ducking behavior).
- Hot input (±10 V at max distortion): VCA does not clip internally; the THAT 2180 is rated for
  signal levels well within ±12 V rails. ±10 V signal is within safe operating range.

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
Flat from DC to the THAT 2180 bandwidth limit (>1 MHz). Perceptually transparent.

### Dynamic Behavior
THAT 2180 is a current-controlled exponential-law VCA. The control current (derived from the
AMT attenuverter output voltage through a gain-setting resistor) sets gain exponentially in dB.

For musical use (accent / envelope VCA), the exponential dB law matches logarithmic loudness
perception and produces natural-sounding swells and accents.

---

## Phase 3: Circuit Design

### Topology
THAT 2180 current-controlled VCA (SOIC-8). One IC per channel — no IC sharing with LP1.
The THAT 2180 accepts a differential audio input, outputs single-ended audio, and sets gain
exponentially in dB via current injected into the GAIN pin.

```
V_in_L ──[100 Ω]──► THAT_VCA_L IN+
                     THAT_VCA_L IN− → GND
                     THAT_VCA_L OUT ──► V_out_L ──► LP1 input L
                     THAT_VCA_L GAIN ──[R_gain]── V_cv_att

V_in_R ──[100 Ω]──► THAT_VCA_R IN+
                     THAT_VCA_R IN− → GND
                     THAT_VCA_R OUT ──► V_out_R ──► LP1 input R
                     THAT_VCA_R GAIN ──[R_gain]── V_cv_att
```

V_cv_att (stereo-linked — both GAIN pins driven identically):
  AMT wiper → utility board → VCA Level CV on STK_AUDIO_L / STK_AUDIO_R → R_gain → GAIN pin

R_gain converts the attenuverter voltage to the GAIN pin control current. Value from THAT 2180
datasheet gain law; typically 10–22 kΩ to achieve unity gain at V_cv_att = 0 V (AMT center).

### CV Input Path (standard)
```
MOD BUS ──[tip switch]──[100 Ω]──[BAT54 SOT-23]──► AMT pot (−1× to +1×) ──► V_cv_att
                              ▲
                 CV IN jack ──┘  (tip-switching: disconnects mod bus when patched)
```

### IC / Component Selection

| Reference | Part Number | Package | Qty | Notes |
|---|---|---|---|---|
| THAT_VCA_L | THAT 2180 | SOIC-8 | 1 (combined audio, L-channel) | L channel signal path VCA |
| THAT_VCA_R | THAT 2180 | SOIC-8 | 1 (combined audio, R-channel) | R channel signal path VCA |
| RV_AMT | Bipolar pot | 9 mm | 1 | AMT attenuverter (−1× to +1×, center detent) |
| D_cv | BAT54S | SOT-23 | 1 | CV input protection clamp |
| R_cv | — | 0603 | 100 Ω | 1 | Series resistor at CV input |
| R_in_L, R_in_R | — | 0603 | 100 Ω | 2 | Series resistors at audio inputs |
| R_gain_L, R_gain_R | — | 0603 | 15 kΩ | 2 | V-to-I resistors at GAIN pins; nominal starting value — verify unity-gain current from THAT 2180 datasheet |
| RV_VCA_UNITY_L, RV_VCA_UNITY_R | Bourns 3224W | SMD | 500 Ω | 2 | Unity-gain trim; in series with R_gain at each GAIN pin; one per channel |

### Trim Pots

| Reference | Range | Purpose | Adjustment |
|---|---|---|---|
| RV_VCA_UNITY_L | ±3% of R_gain | Unity gain at AMT center (L board) | Set AMT to center detent, CV IN unplugged; adjust until V_out_L = V_in_L (0 dB) |
| RV_VCA_UNITY_R | ±3% of R_gain | Unity gain at AMT center (R board) | Same procedure on R channel |

### Power Draw Estimate
Two THAT 2180 ICs (one per channel on combined audio board). No IC sharing.
- +12 V: ~5 mA | −12 V: ~5 mA (2× THAT 2180, ~2.5 mA each)

### Schematic Notes
- THAT 2180 placement: each IC in its channel half of the combined audio board, immediately before the LP1 summing amp.
- Control voltage routing: AMT wiper → utility board → VCA Level CV pin on STK_AUDIO_L /
  STK_AUDIO_R → R_gain → THAT 2180 GAIN pin. No cross-channel audio signal routing.
- Audio signal: Block 4 summing output → THAT 2180 IN+ → OUT → LP1 summing amp input.
- Supply decoupling: 100 nF ceramic at each THAT 2180 supply pin.

### Known Circuit Challenges
- **Unity gain at AMT center**: THAT 2180 GAIN pin requires a specific bias current for unity gain.
  R_gain = 15 kΩ is a nominal starting value; verify the exact unity-gain control current from the
  THAT 2180 datasheet and adjust R_gain accordingly. RV_VCA_UNITY_L/R (Bourns 3224W, 500 Ω) in
  series with R_gain provides ±3% trim range for factory calibration after bring-up.
- **Hot input headroom**: THAT 2180 handles signals within ±12 V rails. Block 4 output up to
  ±10 V is safe.
- **Hard gating at full negative AMT**: verify the attenuverter output swing drives the GAIN
  pin to THAT 2180's minimum gain point (typically −80 dB or better) within the CV range.
