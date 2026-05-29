# Block 4: VCA
Pre-LP1 voltage-controlled amplifier; accents or ducks the signal entering the filter stack via mod bus or external CV.

DSP source: `plugin/src/dsp/VcaBlock.hpp`, `plugin/src/Pogo.cpp` (lines 389–397)

---

## 1. Intent

Block 4 is a stereo VCA inserted between the pre-gain stage (Block 1) and the LP1 filter
(Block 5). Its purpose is dynamic amplitude control of the signal before it enters the filter
stack — accent, ducking, or gating driven by the mod bus or an external envelope.

Two trimpots govern behaviour:

- **VCA_AMT** (bipolar, –1 to +1): determines how much and in which direction the CV affects
  gain. At noon (0), the VCA is transparent — gain is unity regardless of CV. Turned CW
  (positive), the CV accents the signal: CV=0 → muted, CV=5 V → unity. Turned CCW (negative),
  the CV ducks the signal: CV=0 → unity, CV=5 V → muted.

- **VCA_OFS** (unipolar, 0–1): adds a fixed floor to the effective CV before the gain
  calculation. At noon (0.5), a 2.5 V floor is added, so the signal never fully disappears
  even with a zero-volt CV at positive AMT settings. This is a "minimum volume" or
  "always-on" control.

The VCA_INPUT jack normalles to V_modbus, so without any patch cable the mod bus drives the
VCA directly. Plugging into VCA_INPUT overrides this.

Both channels (L, R) are processed identically — the same CV and parameter values are applied
to both, maintaining stereo balance.

---

## 2. Theoretical Design and Topology

> ✅ **CORRECTED 2026-05-29** — THAT2180 reworked to its real current-in/current-out
> topology (datasheet pinout) with R_in + I/V op-amp per channel and Ec+ control; the
> prior differential-voltage model (IN+/IN−/OUT+/OUT−, R_OUT_N) was wrong and is removed.
> Verified in `kicad/nets/block-4.nets.yaml`. CV-conditioning scaling is Phase-3R bring-up.

### Gain Law (DSP and hardware)

```cpp
float normCV = clamp(cvV / 5.f, 0.f, 1.f);
float control;
if (amtParam >= 0.f)
    control = 1.f - amtParam * (1.f - normCV);   // 1 − AMT×(1−CV)
else
    control = 1.f + amtParam * normCV;            // 1 − |AMT|×CV
control = clamp(control, 0.f, 1.f);
// dB-law: G = 10^(2*(control-1))  →  0 dB at control=1, −40 dB at control=0
float G = (control <= 0.001f) ? 0.f : std::pow(10.f, 2.f * (control - 1.f));
// output = input × G
```

Key operating points:

| AMT  | CV    | control | G (dB-law) | Description |
|------|-------|---------|------------|-------------|
| 0    | any   | 1.0     | 1.00 (0 dB)   | Unity always (AMT at noon) |
| +1   | 0 V   | 0.0     | 0.00 (−∞ dB)  | Muted |
| +1   | 5 V   | 1.0     | 1.00 (0 dB)   | Accent: unity at 5 V |
| +1   | 2.5 V | 0.5     | 0.10 (−20 dB) | Mid-CV accent; perceptually ~half loudness |
| –1   | 0 V   | 1.0     | 1.00 (0 dB)   | Through (duck mode, no CV) |
| –1   | 5 V   | 0.0     | 0.00 (−∞ dB)  | Ducked fully at 5 V |
| –1   | 2.5 V | 0.5     | 0.10 (−20 dB) | Mid-CV duck; perceptually ~half loudness |

The OFS floor is applied before this calculation:

```
eff_CV = clamp(raw_CV + VCA_OFS × 5, 0, 10)
```

At default OFS = 0.5: eff_CV = raw_CV + 2.5 V (floor 2.5 V; signal never fully silenced
at positive AMT unless raw_CV goes negative, which is clamped away).

### Hardware Analog Model — THAT 2180 (current-in / current-out)

Per the datasheet (Doc 600029 Rev 02, Table 1), the THAT 2180 is a **current-in / current-out**
Blackmer VCA. Pinout: **Input=1, Ec+=2, Ec−=3, Sym=4, V−=5, Gnd=6, V+=7, Output=8**. Gain is
set by a voltage at the **Ec+** control port:

```
G_dB = Ec+ / (6.1 mV/dB)      (Ec+/Gain constant = +6.1 mV/dB; Ec−/Gain = −6.1 mV/dB)
```

Matching the DSP law `G = 10^(2·(control−1))` ⇒ `G_dB = 40·(control−1)` gives the control target:

```
Ec+ = 6.1 mV/dB × 40 × (control−1) = 244 mV × (control−1)
       control = 1 → Ec+ = 0   (0 dB, unity)
       control = 0 → Ec+ = −244 mV   (−40 dB)
```

**Audio path (per channel, single inversion):**
- `AUDIO_IN → R_in (20 kΩ) → Input (pin 1)`. Pin 1 is a current input (≈ virtual ground);
  `I_in = AUDIO_IN / R_in`.
- `Output (pin 8) → transimpedance op-amp (TL072 half, (+)=AGND, R_f feedback) → AUDIO_OUT`.
  `AUDIO_OUT = −I_out·R_f`; with `R_f = R_in (20 kΩ)`, gain = −1 at 0 dB. The single inversion
  is compensated by LP1's inverting SUM_AMP downstream.
- `Ec− (pin 3)`, `Sym (pin 4, factory pre-trimmed)` and `Gnd (pin 6)` → AGND. `V+ (7)=+12 V`,
  `V− (5)=−12 V`.

This requires **one I/V op-amp half per channel** (U6 = dual TL072) — there is no voltage
output pin and no IN−/OUT−/OUT-termination (the earlier differential-VCA model was wrong).

**Unity-gain calibration:** a Bourns 3224W (500 Ω) per channel trims the Ec+ offset so
`Ec+ = 0` ⇒ exactly 0 dB, matching L and R.

**CV conditioning (U63 = dual TL072):**

1. Raw CV enters through a 100 Ω series resistor + BAT54S clamp (standard CV protection); call
   the protected node CVP.
2. **AMT attenuverter:** a TL072 half (U63-A) inverts CVP to −CVP; the bipolar VCA_AMT pot
   (RV24, CW=CVP, CCW=−CVP, wiper = AMT·CVP) produces the bipolar-scaled CV. Center detent = 0.
3. **OFS floor:** the VCA_OFS pot (RV25) adds a DC floor.
4. **Summer/scaler:** a TL072 half (U63-B) sums AMT·CVP + OFS and scales toward the
   6.1 mV/dB Ec range → `V_ctrl`, which drives both channels' Ec+ via the per-channel unity
   trims (RV1/RV2).

The exact summer/Ec scaling (to hit `Ec+ = 244 mV·(control−1)`) and the precise piecewise AMT
law are nominal here and set at **Phase-3R bring-up** — consistent with the project's
intentional DSP↔hardware deviation (linear DSP gain index vs. true dB-law hardware).

**Stage boundaries:** Block 1 (OPA1612 output, <50 Ω) drives R_in (20 kΩ) — negligible loss;
VCA I/V output (op-amp, <100 Ω) drives LP1's input resistor — negligible loss.

---

## 3. Physical Design

> ✅ **CORRECTED 2026-05-29** — THAT2180 reworked to its real current-in/current-out
> topology (datasheet pinout) with R_in + I/V op-amp per channel and Ec+ control; the
> prior differential-voltage model (IN+/IN−/OUT+/OUT−, R_OUT_N) was wrong and is removed.
> Verified in `kicad/nets/block-4.nets.yaml`. CV-conditioning scaling is Phase-3R bring-up.

**Board assignment:** Audio board (carries audio-frequency signal; THAT 2180 and CV
conditioning are co-located with the signal path).

**Panel controls / jacks:**

| Item | Qty | Type | Notes |
|---|---|---|---|
| VCA_INPUT jack | 1 | PJ301M-12 | Tip-switching; normalles to mod bus V_modbus |
| VCA_AMT trimpot | 1 | 9 mm, centre detent | Bipolar –1× to +1× |
| VCA_OFS trimpot | 1 | 9 mm | Unipolar 0–1 (CV floor) |

No LEDs for this block; status is not indicated on panel.

**Stereo implementation:**

Two THAT 2180 ICs process L and R channels independently. The CV path is shared (same V_ctrl
applied to both Ec+ pins via the per-channel unity trims), maintaining the stereo image.
Unity-gain trimmers RV1/RV2 match the two channels for gain accuracy.

**Signal levels:**

- Audio into R_in → Input (pin 1): from pre-gain block, ±10.5 V max (clipped by Block 1).
- I/V op-amp output: same range, attenuated by the dB-law gain.
- eff_CV: 0–10 V (clamped).
- Ec+ control: 0 V (unity) down to ≈ −244 mV (−40 dB), per the 6.1 mV/dB constant.

**Power estimate:**

- 2× THAT 2180: ~4 mA each = ~8 mA per rail.  (THAT Corp datasheet: Icc = 4 mA typ)
- 1× TL072CDT (dual): ~3 mA per rail.  (TI: 1.4 mA/ch × 2 = 2.8 mA)
- Total: +12 V ~11 mA, −12 V ~11 mA.

---

## 4. Component Requirements

> ✅ **CORRECTED 2026-05-29** — THAT2180 reworked to its real current-in/current-out
> topology (datasheet pinout) with R_in + I/V op-amp per channel and Ec+ control; the
> prior differential-voltage model (IN+/IN−/OUT+/OUT−, R_OUT_N) was wrong and is removed.
> Verified in `kicad/nets/block-4.nets.yaml`. CV-conditioning scaling is Phase-3R bring-up.

Mirrors `specs/components.yaml` block-4 (authoritative). Refs as in components.yaml.

| Ref | Part | Package | Value | Qty | Board | Block | Function |
|---|---|---|---|---|---|---|---|
| U4 | THAT2180 | SOIC-8 | — | 1 | audio | 4 | L-channel dB-law VCA (current-in/out) |
| U5 | THAT2180 | SOIC-8 | — | 1 | audio | 4 | R-channel dB-law VCA (current-in/out) |
| U6 | TL072CDT | SOIC-8 | — | 1 | audio | 4 | I/V transimpedance converters (L=A, R=B) |
| U63 | TL072CDT | SOIC-8 | — | 1 | audio | 4 | CV conditioning: AMT inverter (A) + CV/OFS summer (B) |
| R7, R8 | Resistor 1% | 0603 | 20 kΩ | 2 | audio | 4 | R_in L/R: audio V→I into Input (pin 1) |
| R40, R41 | Resistor 1% | 0603 | 20 kΩ | 2 | audio | 4 | R_f L/R: I/V feedback (unity @0 dB; inverting) |
| R42, R43 | Resistor | 0603 | 10 kΩ | 2 | audio | 4 | AMT attenuverter inverter in/fb |
| R44, R45 | Resistor | 0603 | 100 kΩ | 2 | audio | 4 | CV summer inputs (AMT-scaled CV, OFS) |
| R46 | Resistor | 0603 | 2.4 kΩ | 1 | audio | 4 | CV summer feedback (Ec scaling; Phase-3R trim) |
| R9 | Resistor | 0603 | 100 Ω | 1 | audio | 4 | VCA_INPUT series protection |
| D3 | BAT54S | SOT-23 | — | 1 | audio | 4 | VCA CV input clamp ±12 V |
| RV1, RV2 | Bourns 3224W | SMD | 500 Ω | 2 | audio | 4 | L/R unity-gain trim (Ec+ offset) |
| RV24 | Bipolar pot, 9 mm | panel | 1 kΩ | 1 | control | 4 | VCA_AMT attenuverter −1×…+1× |
| RV25 | Linear pot, 9 mm | panel | — | 1 | control | 4 | VCA_OFS CV floor |
| C7–C10 | Capacitor | 0603 | 100 nF | 4 | audio | 4 | THAT2180 L/R supply decoupling (V+ and V−) |
| C41–C44 | Capacitor | 0603 | 100 nF | 4 | audio | 4 | U6, U63 supply decoupling |
| J26 | PJ301M-12 | panel | — | 1 | panel | 4 | VCA_INPUT jack (normalles to mod bus) |
