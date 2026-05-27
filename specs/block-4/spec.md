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

### Hardware Analog Model — THAT 2180

The THAT 2180 is an SSM2164-compatible dB-law VCA in SOIC-8. Its gain is controlled by a
current into the GAIN pin:

```
Gain (dB) = –6 dB × I_gain / I_ref    (approximately, from THAT 2180 datasheet)
```

The VCA_AMT pot and VCA_OFS resistor network are connected to the GAIN pin to implement a
hardware equivalent of the DSP gain law. The DSP dB-law matches the THAT 2180 exponential characteristic: equal control-voltage steps produce equal dB steps, tracking human loudness perception.

**Unity gain calibration:** A Bourns 3224W SMD trimmer (500 Ω) in series with R_gain sets the
exact bias current for 0 dB gain. One trimmer per channel allows the two channels to be
matched. Nominal R_gain = 15 kΩ (verify from THAT 2180 application note for ±12 V supply).

**CV conditioning:**

1. Raw CV enters through a 100 Ω series resistor and BAT54S clamp (same protection topology
   as all other CV inputs in the module).
2. VCA_OFS trimpot (0–1) provides a DC voltage 0–5 V that is summed with raw CV at a TL072
   input summing node, implementing `eff_CV = raw_CV + VCA_OFS × 5`.
3. VCA_AMT trimpot (–1 to +1, centre detent) is wired as a bipolar voltage divider (same
   topology as mod bus attenuverters) to scale and optionally invert eff_CV before it reaches
   the GAIN pin of each THAT 2180.
4. For negative AMT (duck mode), the inverted CV drives the GAIN pin so that rising CV
   reduces gain. The inversion is implemented by a TL072 half configured as a unity-gain
   inverter, whose output is selected by AMT pot wiper direction (CCW = inverted path).

In practice, the AMT pot wiper voltage drives the GAIN pin through R_gain. A TL072 single op-
amp (one per channel) handles the OFS summing and inversion buffer. Two TL072s total (one per
channel) are required; they can be combined as one TL072 dual op-amp (SOIC-8) package.

**AMT pot loading note:** The AMT pot (10 kΩ) wiper has a source impedance of up to
R_pot / 4 = 2.5 kΩ at mid-travel. In series with R_GAIN (15 kΩ), this creates a
position-dependent gain error of up to 2.5 / (2.5 + 15) = 14 %. This shifts the
THAT 2180 gain law and must be absorbed by the RV_VCA_UNITY trim — but the error
varies with pot position, creating a non-uniform gain law.

Recommended fix: reduce the AMT pot value to **1 kΩ** (max wiper impedance = 250 Ω;
error < 1.6 %). The 1 kΩ pot must be driven from the TL072 output (low impedance);
connect the pot CW lug to eff_CV and CCW lug to −eff_CV (from the inverter), then
route the wiper through a 47 Ω series resistor directly to R_GAIN. Alternatively,
add a TL072 unity-gain follower between the wiper and R_GAIN, but this requires a
third IC half; lowering the pot value is simpler.

---

## 3. Physical Design

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

Two THAT 2180 ICs process L and R channels independently. The CV path is shared (same eff_CV
applied to both GAIN pins), maintaining the stereo image. Unity-gain trimmers RV_VCA_UNITY_L
and RV_VCA_UNITY_R allow the two channels to be matched for DC offset and gain accuracy.

**Signal levels:**

- Input to THAT 2180 IN+ pin: audio from pre-gain block, ±10.5 V max (clipped by Block 1).
- THAT 2180 output: same range, attenuated.
- eff_CV: 0–10 V (clamped).
- GAIN pin drive: 0–500 µA (set by R_gain and supply rails, per THAT 2180 datasheet).

**Power estimate:**

- 2× THAT 2180: ~2.5 mA each = ~5 mA per rail.
- 1× TL072 (dual): ~1.8 mA per rail.
- Total: +12 V ~7 mA, –12 V ~7 mA.

---

## 4. Component Requirements

| Ref | Part | Package | Value | Qty | Board | Block | Function |
|---|---|---|---|---|---|---|---|
| VCA_L | THAT 2180 | SOIC-8 | — | 1 | audio | 4 | L-channel dB-law VCA |
| VCA_R | THAT 2180 | SOIC-8 | — | 1 | audio | 4 | R-channel dB-law VCA |
| U_VCA_CV | TL072CDT | SOIC-8 | — | 1 | audio | 4 | CV summing (OFS) and inversion buffer, both channels |
| RV_VCA_AMT | Bipolar pot, 9 mm, centre detent | panel | 1 kΩ | 1 | control | 4 | VCA_AMT attenuverter –1× to +1×; 1 kΩ limits wiper impedance to 250 Ω max → < 1.6 % THAT 2180 gain error |
| RV_VCA_OFS | Linear pot, 9 mm | panel | 50 kΩ | 1 | control | 4 | VCA_OFS CV floor 0–5 V |
| RV_VCA_UNITY_L | Bourns 3224W | SMD | 500 Ω | 1 | audio | 4 | L unity-gain trim (GAIN pin bias adjust) |
| RV_VCA_UNITY_R | Bourns 3224W | SMD | 500 Ω | 1 | audio | 4 | R unity-gain trim |
| R_GAIN_L | Resistor | 0603 | 15 kΩ | 1 | audio | 4 | L V-to-I at THAT 2180 GAIN pin (nominal; verify from datasheet) |
| R_GAIN_R | Resistor | 0603 | 15 kΩ | 1 | audio | 4 | R V-to-I at THAT 2180 GAIN pin |
| R_VCA_CV | Resistor | 0603 | 100 Ω | 1 | audio | 4 | Series protection on VCA_INPUT |
| D_VCA | BAT54S | SOT-23 | — | 1 | audio | 4 | Dual Schottky clamp on VCA CV input |
| R_OFS_IN | Resistor | 0603 | 100 kΩ | 1 | audio | 4 | Input resistor for VCA_OFS summing node |
| R_OFS_CV | Resistor | 0603 | 100 kΩ | 1 | audio | 4 | Input resistor for raw CV at summing node |
| R_OFS_F | Resistor | 0603 | 100 kΩ | 1 | audio | 4 | Feedback resistor for OFS summing op-amp stage |
| C_VCA_L | Capacitor | 0603 | 100 nF | 2 | audio | 4 | THAT 2180 L supply decoupling (V+ and V–) |
| C_VCA_R | Capacitor | 0603 | 100 nF | 2 | audio | 4 | THAT 2180 R supply decoupling (V+ and V–) |
| C_U_VCA | Capacitor | 0603 | 100 nF | 2 | audio | 4 | TL072 supply decoupling (V+ and V–) |
| J_VCA_IN | PJ301M-12 | panel | — | 1 | panel | 4 | VCA_INPUT jack (normalles to mod bus) |
