# aux: VCA Cell (THAT 2180 Exponential VCA)

> ✅ **CORRECTED 2026-05-29** — Topology fixed to the real THAT2180 current-in/current-out
> device (was wrongly modelled as a differential voltage VCA with no output op-amp).
> Pinout from datasheet Doc 600029 Rev 02 Table 1. Verified in `kicad/nets/block-4.nets.yaml`.

Design status: [ ] draft → [ ] reviewed → [ ] validated on prototype

## Overview

Voltage-controlled amplifier using the THAT 2180 current-controlled exponential VCA IC.
Implements the pre-LP1 gain stage controlled by VCA_AMT (attenuverter), VCA_OFS (floor),
and VCA_IN (CV input). The hardware uses a dB-law (exponential gain law) device whereas
the DSP models a linear VCA — this is an intentional deviation for more musical response.

Chosen because:
- THAT 2180 is the industry-standard Eurorack/professional audio VCA IC
- Exponential (dB) response is more musical than linear for manual gain riding
- SOIC-8 footprint is compact; consumes ~2.5 mA per device
- Differential input rejects common-mode noise on the audio path
- True stereo: two separate THAT 2180 ICs (one per channel) for independent L/R gain

## Schematic


ASCII fallback (one channel; THAT2180 is current-in / current-out — datasheet pinout
Input=1, Ec+=2, Ec−=3, Sym=4, V−=5, Gnd=6, V+=7, Output=8):

```
              R_in 20k        THAT 2180 (SOIC-8)            I/V op-amp (TL072 half)
 AUDIO_IN ───[====]──► Input(1)              Output(8) ──┬──(−)──┐
                                                          │  R_f 20k │
                                              V+(7)=+12V  │  [====]  ├── AUDIO_OUT
                       Ec+(2)◄── V_ctrl       V−(5)=−12V  └─────────┘ (inverted; unity @0dB)
                       Ec−(3)── AGND               (+) = AGND
                       Sym(4)── AGND  (factory pre-trimmed)
                       Gnd(6)── AGND

 Input pin 1 is a current input (≈ virtual ground): I_in = AUDIO_IN / R_in.
 Output pin 8 is a current output → transimpedance amp: AUDIO_OUT = −I_out·R_f.
 With R_f = R_in, gain = −1 at 0 dB (single inversion; LP1's inverting SUM_AMP
 downstream restores polarity). Gain set by Ec+: G_dB = Ec+ / 6.1mV.

 Control chain (V_ctrl, shared by both channels' Ec+):
   VCA_IN jack ──[100Ω]──[BAT54S clamp]── CVP ──┬──► AMT attenuverter (RV_AMT bipolar
                                                │      pot + inverter for −CVP) → AMT·CVP
   VCA_OFS pot wiper ───────────────────────────┼──► CV summer (TL072 half) ──► V_ctrl
                                                │      (scaled toward 6.1 mV/dB)
                                          AMT·CVP┘                    │
                                                          per-channel RV_VCA_UNITY
                                                          trim → Ec+ (pin 2)
```

VCA_AMT attenuverter uses the aux-attenuverter topology (bipolar pot + inverter) to
produce AMT·CVP before the summer. Target: Ec+ = 244 mV·(control−1) where control is the
DSP gain index (1 = unity/0 dB, 0 = −40 dB); exact summer/Ec scaling is a Phase-3R trim.

## Transfer Function

### THAT 2180 Gain Law

```
G_dB = Ec+ / 6.1mV         (Ec+/Gain constant = +6.1 mV/dB; datasheet)
G_linear = 10^(G_dB / 20)

Audio scaling: AUDIO_OUT = −(R_f / R_in) · 10^(Ec+/(6.1mV·20)) · AUDIO_IN
               with R_f = R_in → −1 (unity) at Ec+ = 0
```

This is an exponential (dB-law) relationship: equal voltage steps at the **Ec+** control
port (pin 2) produce equal dB steps at the output — the expected musical behavior. The
audio path itself is current-in (R_in) / current-out (I/V op-amp), inverting at unity.

### DSP Reference (for comparison)

```
normCV = clamp(VCA_IN / 5V, 0, 1)

AMT ≥ 0: mod = 1 − normCV;    g = clamp(1 − |AMT| × mod, 0, 1)
AMT < 0: mod = normCV;         g = clamp(1 − |AMT| × mod, 0, 1)

Center detent (AMT = 0): g = 1 always (passes signal regardless of CV)
Full CW (AMT = 1), CV = 5V:  g = 1 (unity)
Full CW (AMT = 1), CV = 0V:  g = 0 (muted)
```

Note: DSP models a linear gain; hardware produces exponential gain. This produces
softer, more gradual fades and is considered more musical for a filter VCA.

### Hardware Gain Mapping (Ec+ control)

```
control (DSP index) → Ec+ = 244 mV × (control − 1):
  AMT = 0 (center):           control = 1 → Ec+ = 0      → unity (CV has no effect)
  AMT = +1, CV = 5V:          control = 1 → Ec+ = 0      → unity (accent)
  AMT = +1, CV = 0V:          control = 0 → Ec+ = −244mV → −40 dB (muted)
  AMT = −1, CV = 5V:          control = 0 → Ec+ = −244mV → −40 dB (ducked)
```

The RV_VCA_UNITY trim adjusts the per-channel Ec+ offset so Ec+ = 0 ⇒ exactly 0 dB.
Nominal small trim range → 500 Ω trimpot adequate.

## Design Choices & Rationale

### Intentional DSP-Hardware Deviation

The DSP uses a linear gain law because it is simpler to code and reason about. The
THAT 2180 naturally produces an exponential (dB) law. Rather than linearizing the
hardware with a predistortion circuit (adding complexity and a potential source of
error), the dB law is accepted as a desirable musical property. Users expect exponential
VCA behavior from hardware synthesizers.

### R_in = R_f = 20 kΩ (audio path)

```
THAT2180 Input (pin 1) is a current input; R_in sets V→I (I_in = AUDIO_IN / R_in).
Output (pin 8) is a current output into an I/V op-amp; AUDIO_OUT = −I_out · R_f.
R_f = R_in = 20 kΩ → unity (−1) at 0 dB; ~20 kΩ input impedance.
RV_VCA_UNITY (500 Ω SMD trimpot) provides ±3.3% trim range around nominal.
```

### Input Protection (VCA_IN jack)

```
100Ω series resistor: limits short-circuit current into BAT54S clamping diodes
BAT54S (SOT-23 dual Schottky): clamps input to ±(Vcc + 0.3V) ≈ ±12.3V
Complies with aux-cv-input-protection pattern used throughout POGO
```

### True Stereo

Two THAT 2180 ICs (one per channel) allow independent processing. Both Ec+ pins
are driven by the same control voltage (summed from VCA_AMT + VCA_OFS + VCA_IN),
so L and R track together unless a tilt CV is added in Phase 3R.

### Power Supply

THAT 2180 operates on ±15V in professional audio applications. POGO uses ±12V Eurorack
rails. The THAT 2180 is specified to operate on supplies down to ±5V; ±12V operation
is confirmed in the datasheet, with slightly reduced headroom. Audio headroom will be
±11V at ±12V supply (consistent with the ±11V clamp used elsewhere in POGO).

## Component Values (POGO-specific)

| Ref (generic) | Part | Package | Value | Notes |
|---|---|---|---|---|
| U_VCA_L/R | THAT2180LD | SOIC-8 | — | Per-channel VCA (current-in/out) |
| U_IV | TL072CDT | SOIC-8 | — | I/V transimpedance converters (one half per channel) |
| U_CV | TL072CDT | SOIC-8 | — | CV conditioning: AMT inverter + CV/OFS summer |
| R_in | Resistor | 0603 | 20 kΩ | Audio V→I into Input (pin 1); 1% |
| R_f | Resistor | 0603 | 20 kΩ | I/V transimpedance feedback (unity @0 dB); 1% |
| RV_VCA_UNITY | Bourns 3224W | SMD | 500 Ω | Per-channel unity-gain trim at Ec+ |
| R_cv_in | Resistor | 0603 | 100 Ω | CV input protection series resistor |
| D_cv_in | BAT54S | SOT-23 | — | Dual Schottky clamp at CV input |
| C_VCC, C_VEE | Ceramic bypass | 0603 | 100 nF | Per supply pin (THAT2180 ×2 + each TL072) |

### Power Budget

| Item | +12V | −12V |
|---|---|---|
| THAT 2180 L | ~2.5 mA | ~2.5 mA |
| THAT 2180 R | ~2.5 mA | ~2.5 mA |
| TL072 summers | ~1.5 mA | ~1.5 mA |
| **Total (VCA block)** | **~6.5 mA** | **~6.5 mA** |

## Performance Characteristics

| Parameter | Value | Condition |
|---|---|---|
| Gain law | Exponential (dB) | THAT 2180 characteristic |
| Unity gain accuracy | ±1 dB | After RV_VCA_UNITY trim |
| Audio bandwidth | >100 kHz | THAT 2180 specification |
| THD+N | <0.01% | Unity gain, 1 kHz, ±5V input |
| Dynamic range | >100 dB | THAT 2180 specification |
| Audio input impedance (IN+) | ~20 kΩ | Small-signal; THAT 2180A14-U translinear cell |
| Audio output impedance (OUT+) | <100 Ω | Low-Z transimpedance output stage |
| Input range | ±11V | Clamped at input buffer |
| Output range | ±11V | ±12V supply |
| CV input range | 0–10V | Clamped by BAT54S |
| Supply current | ~5 mA per rail | Both channels |

## Known Gotchas / Assembly Notes

- THAT 2180 Ec+ control pin (pin 2) is sensitive to noise (6.1 mV/dB); keep the control
  trace short and away from audio-frequency signals on the board
- RV_VCA_UNITY calibration: apply 0V to VCA_IN, set AMT pot to center detent (0V out
  of attenuverter), trim RV_VCA_UNITY until audio output = audio input amplitude
- THAT 2180 is current-in / current-out (single Input pin 1, single Output pin 8). It
  REQUIRES an R_in (V→I) at the input and a transimpedance op-amp (I→V) at the output —
  there is no voltage output pin and no IN−/OUT−. (An earlier revision wrongly modelled it
  as a differential voltage VCA with an OUT− termination resistor; that was incorrect and
  has been removed.)
- At maximum attenuation, the THAT 2180 produces residual feedthrough (~−80 dB);
  this is normal and typically inaudible
- BAT54S anode must connect to GND (not to signal ground return) — use analog GND star
  connection to avoid injecting clamp current into signal path
- VCA_OFS (floor offset) sets a minimum gain floor so the signal is never fully muted
  even at CV=0; this maps to the DSP `VCA_OFS` parameter. Hardware implementation is
  a bias voltage added at the CV summer (U63-B) before the Ec+ scaling.
- Two THAT 2180 supply rails must be decoupled independently; shared decoupling cap
  can allow L/R crosstalk through the supply impedance

## Used By

| Block | Instance | Board | Notes |
|---|---|---|---|
| block-4 | VCA_L, VCA_R | Control | Pre-LP1 VCA; true stereo pair |
