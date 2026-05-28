# aux: Mod Bus Core (Processor: Scale + Offset + Clamp)

> ⚠️ **STALE** — Circuit library entry pending re-verification against current panel design (2026-05-28).

Design status: [ ] draft → [ ] reviewed → [ ] validated on prototype

## Overview

Analog implementation of the DSP ModBusProcessor. Takes the module's primary modulation
source (LFO1 when unpatched; external CV when MOD_INPUT is patched), applies an
exponential-taper gain (0.2×–5×) and a bipolar offset (±5V), then clamps the output
to ±10V. Drives the mod bus distribution rail that feeds all 19 attenuverter destinations.

Also drives three indicator LEDs: MOD_CLIP (|V_bus| ≥ 9.9V), MOD_POS (V_bus > 0),
MOD_NEG (V_bus < 0).

Chosen because:
- Inverting summing amplifier (MB_AMP) followed by an inverter (MB_INV) is the standard
  analog summing architecture: transparent, low-noise, DC-accurate
- Two TL074 halves handle MB_AMP and MB_INV; remaining two halves are available for
  LED drivers or utility functions
- A single TL074 (SOIC-14) for the entire mod bus processor is IC-count efficient
- ±10V output clamp uses back-to-back zener diodes or a TL431-based precision clamp

## Schematic


ASCII fallback:

```
 LFO1_OUT ──(normally closed via J_MOD_IN tip switch)─────────────────┐
                                                                        │
 MOD_IN jack ────────────────────────────────────────────────────────► │
                                                                        │
 [100Ω] + [BAT54S] protection ─────────────────────────────────────► V_src
                                                                        │
                         R_src (AMOUNT pot + end resistors)             │
 V_src ──────────────────[─────────────────────]───┐
                                                    │
                                               (−) ─┤
 V_off ──[R_off]────────────────────────────────────┤ MB_AMP (TL074 half)
                                                (+)─┴─ AGND
                         R_f ──────────────────────┘    │
                                                         ▼
                                                   V_modbus_inv = −(V_src × Rf/Rsrc + V_off × Rf/Roff)
                                                         │
                                                    [±10V clamp]
                                                    (back-to-back 10V zeners)
                                                         │
                                               V_modbus_inv (clamped)
                                                         │
                                        MB_INV (TL074 half, G=−1):
                                        [R_inv_in] → (−), (+ )=AGND, R_inv_f feedback
                                                         │
                                                    V_modbus (correct polarity)
                                                         │
                                              ┌──────────┴──────────┐
                                              │                      │
                                         [LED drivers]         MOD_BUS RAIL
                                         (MOD_POS, MOD_NEG,    → all attenuverters
                                          MOD_CLIP)
```

LED driver detail:

```
 V_modbus ──[R_LED_P]──► LED_POS (green)  + comparator ref = 0V → lights when V > 0
 V_modbus ──[R_LED_N]──► LED_NEG (red)    + comparator ref = 0V → lights when V < 0
 |V_modbus| ──[comparator at 9.9V ref]──► LED_CLIP (yellow/amber) → lights when |V| ≥ 9.9V
```

## Transfer Function

### DSP Reference

```
gain = 0.2 × 25^amountParam        amountParam ∈ [0, 1]
  → gain range: 0.2 × 25^0 = 0.2× to 0.2 × 25^1 = 5×

offset = offsetParam × 5V          offsetParam ∈ [−1, +1]
  → offset range: −5V to +5V

V_bus = clamp(V_src × gain + offset, −10, +10)
```

### Hardware Summing Amplifier (MB_AMP)

```
V_modbus_inv = −(V_src × R_f/R_src + V_off_scaled × R_f/R_off)

With R_f = 100 kΩ:
  Gain control: R_src varies from 20 kΩ (5× gain, R_f/R_src = 5) to
                                  500 kΩ (0.2× gain, R_f/R_src = 0.2)
  Offset control: R_off = 100 kΩ; V_off from pot between +5V and −5V references
                  → offset contribution = −(V_off × 1) → ±5V offset range at output
```

Note: MB_AMP inverts polarity; MB_INV restores it. The double inversion means
V_modbus has the same polarity as the expected DSP output.

### MB_INV (TL074 half, G=−1)

```
V_modbus = −V_modbus_inv = V_src × R_f/R_src + V_off_scaled

This equals the DSP formula V_bus = V_src × gain + offset (before clamping).
```

### Gain Taper

The DSP gain taper is 0.2 × 25^x — an exponential curve. Hardware approximation:
- Linear pot with end resistors creates a pseudo-exponential taper by padding the
  wiper extremes (a standard technique for audio log/anti-log pots)
- OR: use a genuine log-taper pot (−A curve) for gain control
- The 0.2× to 5× range spans 28 dB, which a 270° log-taper pot covers comfortably
- Exact taper law matching is not critical; the user is adjusting modulation depth
  by ear, so a perceptually smooth taper is more important than DSP accuracy

### Clamp Implementation

```
Target: clamp V_modbus to ±10V

Option A: back-to-back 10V zeners in feedback path of MB_INV
  → clamp is applied at the MB_INV output; clean limiting behavior
  → zener noise is injected into the feedback node — low impedance source minimizes this

Option B: external BAT54 diode clamp to ±10V reference (TL431-based)
  → more precise; requires TL431 reference

Recommended: Option A (simpler) with BZX84-C10 10V zeners (SOT-23) in the MB_INV
feedback loop, back-to-back.

At clamp onset (|V| ≥ 9.9V due to zener tolerance), MOD_CLIP LED activates.
```

### MOD_CLIP Threshold

DSP: `|busV| ≥ 9.9V`. Hardware: zener knee typically 9.9–10.1V. The LED is driven
by a comparator with a 9.9V reference (two equal resistors from 10V zener node to GND,
midpoint = 5V; then voltage divider from V_modbus compared against 9.9V reference).
Alternatively: the MOD_CLIP LED turns on when the zener clamps (zener current ≥ LED
threshold current) — simple and self-indicating.

## Design Choices & Rationale

### TL074 for Entire Processor

MB_AMP (half A) + MB_INV (half B) + LED comparator (half C) + spare (half D):
All four functions fit in one TL074CDT (SOIC-14). This is compact and keeps the
mod bus processor as a single IC plus passives on a small board section.

### Mod Bus Distribution

V_modbus drives 19 attenuverter inputs in parallel. Each attenuverter pot is 10 kΩ
wired across V_modbus and −V_modbus (bipolar). Total load on V_modbus:
  19 × 10 kΩ in parallel = 10 kΩ / 19 ≈ 526 Ω

At V_modbus = ±10 V and 526 Ω load: I = ±19 mA — marginal for a single TL074 output.
To achieve reliable ±10 V swing, MB_PROC_A uses both spare sections (halves C and D)
paralleled as the distribution buffer (each carries ~9.5 mA). A 47 Ω series resistor
on each output before the join prevents oscillation. This is entirely within the four
sections of MB_PROC_A; no additional IC is needed. See block-3/spec.md for details.

### Offset Reference

V_off is derived from a voltage divider between the module's +5V and −5V precision
references (if available) or from the ±12V rails through resistive division. Using
the same ±5V references as the CV scaling circuitry ensures offset calibration
is consistent with the mod bus gain calibration.

## Component Values (POGO-specific)

| Ref (generic) | Part | Package | Value | Notes |
|---|---|---|---|---|
| MB_PROC_A | TL074CDT | SOIC-14 | — | Half A = MB_AMP, Half B = MB_INV, Halves C+D = distribution buffer (paralleled) |
| MB_PROC_B | TL074CDT | SOIC-14 | — | Halves A/B/C = LED comparators (POS, NEG, CLIP); half D spare |
| R_f | Resistor | 0603 | 100 kΩ | MB_AMP feedback; sets gain denominator |
| R_src | Pot + end R | Panel | 492 kΩ total | AMOUNT pot: 470 kΩ log taper + 22 kΩ floor resistor; sets 0.2×–4.55× (≈0.2×–5×) range |
| R_src_floor | Resistor | 0603 | 22 kΩ | Floor input resistor in series with pot; limits max gain to 100/22 = 4.55× |
| R_47k | Resistor | 0603 | 47 Ω | Series resistor on each paralleled buffer output (×2) before joining; prevents oscillation |
| R_off | Resistor | 0603 | 100 kΩ | Offset input resistor; R_f/R_off = 1 → ±5V offset |
| R_inv_in | Resistor | 0603 | 100 kΩ | MB_INV input resistor |
| R_inv_f | Resistor | 0603 | 100 kΩ | MB_INV feedback; 1% tolerance |
| D_CLAMP_P, D_CLAMP_N | BZX84-C10 | SOT-23 | 10V zener | Back-to-back in MB_INV feedback; ±10V clamp |
| RV_MB_ZERO | Bourns 3224W | SMD | 10 kΩ | Zero-offset null trim at MB_AMP |
| RV_MB_AMOUNT_MAX | Bourns 3224W | SMD | 10 kΩ | 5× gain calibration trim in R_src leg |
| R_cv_in | Resistor | 0603 | 100 Ω | MOD_IN jack series protection |
| D_cv_in | BAT54S | SOT-23 | — | MOD_IN input clamp |
| R_LED_P, R_LED_N | Resistor | 0603 | 10 kΩ | MOD_POS/NEG LED current limiting |
| LED_POS | LED | 0603 | green | MOD_POS indicator |
| LED_NEG | LED | 0603 | red | MOD_NEG indicator |
| LED_CLIP | LED | 0603 | amber/yellow | MOD_CLIP indicator |
| C_VCC, C_VEE | Ceramic bypass | 0603 | 100 nF | Per IC supply pin |

## Performance Characteristics

| Parameter | Value | Condition |
|---|---|---|
| Gain range | 0.2× – 5× | AMOUNT pot full sweep |
| Gain taper | ~log (perceptual) | Log-taper pot |
| Offset range | ±5V | OFFSET pot full sweep |
| Output clamp | ±10V | BZX84-C10 zeners |
| MOD_CLIP threshold | ±9.9V (±10V nominal) | Zener knee |
| Bandwidth | >100 kHz | TL074; not audio-critical |
| Offset null | <10 mV | After RV_MB_ZERO trim |
| Output drive | 22 mA (buffered) | 22 attenuverter loads |

## Known Gotchas / Assembly Notes

- MB_INV feedback zeners (±10V clamp): orient carefully — one zener anode to
  output, cathode to feedback node; the other reversed (cathode to output, anode
  to feedback node); back-to-back allows both polarities to clamp
- Zener clamp in MB_INV feedback: when clamping, the TL074 virtual ground is
  violated (the op-amp is no longer linear); this is expected and harmless as
  long as the op-amp output current is within spec (25 mA max for TL074)
- RV_MB_ZERO trim: with V_src = 0V and OFFSET pot at center, trim until
  V_modbus = 0V (null the op-amp input offset voltage)
- RV_MB_AMOUNT_MAX trim: apply a reference signal (e.g. 1V DC), set AMOUNT
  to max CW, trim until V_modbus = 5× input (5V DC)
- Mod bus distribution buffer: essential given the 455 Ω combined load from
  22 attenuverters; without it, TL074 half B is dissipating up to 220 mW (!!!)
  at maximum V_modbus — add the buffer, it is not optional
- MOD_IN jack normalling: LFO1_OUT connects to the NC contact of J_MOD_IN;
  when unpatched, LFO1 feeds the mod bus; when patched, external CV takes over.
  LFO1_OUT still outputs its signal independently (LFO1 jack is a separate output)
- LED polarity indicators (MOD_POS green, MOD_NEG red): use a simple diode bridge
  or zero-crossing comparator (TL074 half C) to drive each LED only when V > 0
  or V < 0 respectively; current limit 1-2 mA for 0603 LEDs

## Used By

| Block | Instance | Board | Notes |
|---|---|---|---|
| block-3 | MB_PROC | Control | Single instance; feeds all 22 attenuverters |
| block-2 | LFO1 normalized in | Control | LFO1_OUT → NC contact of J_MOD_IN |
