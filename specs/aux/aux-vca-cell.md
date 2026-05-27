# aux: VCA Cell (THAT 2180 Exponential VCA)

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


ASCII fallback (one channel shown):

```
                        THAT 2180 (U_VCA, SOIC-8)
                   ┌────────────────────────────────┐
 AUDIO_IN+ ────────┤ IN+                  OUT+ ├──── AUDIO_OUT
 AUDIO_IN− ────────┤ IN−                  OUT− ├──── (differential; convert to SE with op-amp)
                   │                            │
 V_gain ──[R_gain]─┤ GAIN                VCC  ├──── +15V (or +12V)
                   │ GND                  VEE  ├──── −15V (or −12V)
                   └────────────────────────────┘

 V_gain control chain:
   VCA_IN jack ──[100Ω]──[BAT54S clamp]────────────────────────────┐
                                                                    │
   VCA_AMT pot wiper ──────────────────────────────────────────────►│ summing
                                                                    │  point
   VCA_OFS pot ────────────────────────────────────────────────────►│
                                                                    │
                                                               [TL072 summer]
                                                                    │
                                                               V_gain_sum
                                                                    │
                                                              [R_gain 15kΩ]
                                                                    │
                                                              THAT 2180 GAIN pin
                                                              (+) RV_VCA_UNITY trim
```

VCA_AMT attenuverter uses the aux-attenuverter topology to produce a bipolar
scaling of the VCA_IN CV before it reaches the summing point.

## Transfer Function

### THAT 2180 Gain Law

```
G_dB = K × I_gain

where I_gain = V_gain / R_gain and K is the THAT 2180 internal gain constant.
The THAT 2180 datasheet specifies unity gain at a specific current I_unity.

G_linear = 10^(G_dB / 20) = 10^(K × V_gain / (R_gain × 20))
```

This is an exponential (dB-law) relationship: equal voltage steps at the GAIN pin
produce equal dB steps at the output — the expected musical behavior.

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

### Hardware Gain Mapping

```
At AMT = 0 (center detent):
  V_gain = 0V → must correspond to unity gain → calibrate RV_VCA_UNITY so that
  I_gain = I_unity when V_gain = 0

At AMT = 1 (full CW), CV = 0V:
  V_gain → −V_max → maximum attenuation → G ≈ 0 (−∞ dB)

At AMT = 1 (full CW), CV = 5V:
  V_gain → 0V → unity gain (RV_VCA_UNITY calibration point)

At AMT = −1 (full CCW), CV = 5V:
  V_gain → −V_max → maximum attenuation
```

The RV_VCA_UNITY trim (series with R_gain) adjusts the unity-gain current offset.
Nominal ±3% factory calibration range → 500 Ω trimpot adequate.

## Design Choices & Rationale

### Intentional DSP-Hardware Deviation

The DSP uses a linear gain law because it is simpler to code and reason about. The
THAT 2180 naturally produces an exponential (dB) law. Rather than linearizing the
hardware with a predistortion circuit (adding complexity and a potential source of
error), the dB law is accepted as a desirable musical property. Users expect exponential
VCA behavior from hardware synthesizers.

### R_gain = 15 kΩ

```
From THAT 2180 datasheet: unity gain current I_unity = specified value.
R_gain = V_gain_at_unity / I_unity
Nominal 15 kΩ gives adequate headroom across the gain control range.
RV_VCA_UNITY (500 Ω SMD trimpot) provides ±3.3% trim range around nominal.
```

### Input Protection (VCA_IN jack)

```
100Ω series resistor: limits short-circuit current into BAT54S clamping diodes
BAT54S (SOT-23 dual Schottky): clamps input to ±(Vcc + 0.3V) ≈ ±12.3V
Complies with aux-cv-input-protection pattern used throughout POGO
```

### True Stereo

Two THAT 2180 ICs (one per channel) allow independent processing. Both GAIN pins
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
| U_VCA_L | THAT2180A14-U | SOIC-8 | — | Left channel VCA |
| U_VCA_R | THAT2180A14-U | SOIC-8 | — | Right channel VCA |
| R_gain | Resistor | 0603 | 15 kΩ | GAIN pin current setter; 1% tolerance |
| RV_VCA_UNITY | Bourns 3224W | SMD | 500 Ω | Unity-gain trim; series with R_gain |
| R_cv_in | Resistor | 0603 | 100 Ω | CV input protection series resistor |
| D_cv_in | BAT54S | SOT-23 | — | Dual Schottky clamp at CV input |
| C_VCC, C_VEE | Ceramic bypass | 0603 | 100 nF | Per THAT 2180 supply pin |
| R_out | Resistor | 0603 | — | Differential-to-SE conversion if needed (see notes) |

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
| Input range | ±11V | Clamped at input buffer |
| Output range | ±11V | ±12V supply |
| CV input range | 0–10V | Clamped by BAT54S |
| Supply current | ~5 mA per rail | Both channels |

## Known Gotchas / Assembly Notes

- THAT 2180 GAIN pin is high-impedance and sensitive to noise; keep R_gain trace short
  and away from audio-frequency signals on the board
- RV_VCA_UNITY calibration: apply 0V to VCA_IN, set AMT pot to center detent (0V out
  of attenuverter), trim RV_VCA_UNITY until audio output = audio input amplitude
- THAT 2180 differential output requires conversion to single-ended before the next
  block; use one TL072 half in a differential-to-SE (instrumentation amp) configuration
  or simply use the non-inverting output if the inverting output is not needed
- At maximum attenuation, the THAT 2180 produces residual feedthrough (~−80 dB);
  this is normal and typically inaudible
- BAT54S anode must connect to GND (not to signal ground return) — use analog GND star
  connection to avoid injecting clamp current into signal path
- VCA_OFS (floor offset) sets a minimum gain floor so the signal is never fully muted
  even at CV=0; this maps to the DSP `VCA_OFS` parameter. Hardware implementation is
  a bias voltage added at the summing node before R_gain.
- Two THAT 2180 supply rails must be decoupled independently; shared decoupling cap
  can allow L/R crosstalk through the supply impedance

## Used By

| Block | Instance | Board | Notes |
|---|---|---|---|
| block-4 | VCA_L, VCA_R | Control | Pre-LP1 VCA; true stereo pair |
