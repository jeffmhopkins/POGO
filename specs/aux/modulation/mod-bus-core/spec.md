# aux: Mod Bus Core (Processor: Scale + Offset + Clamp)

**Type:** `modulation` · part of the [aux circuit library](../../_LIBRARY.md)

> ✅ **Re-verified 2026-05-30** against the locked plugin (change 0018). Source is the MOD_SRC
> 3-way switch (LFO1 / LFO2 / External), not an LFO1 auto-normal; the 3 MOD indicator LEDs are
> removed (no plugin/panel backing); distribution feeds **18** attenuverter destinations.
> 🔧 **Change 0020 §H:** destinations must normal **low-Z directly** to the bus (jack tip-switch breaks it) — a series R_SRC_NORM into the ~few-k destination node throttled mod depth to ~3%. The single MB_INV output cannot drive all destinations; use a (paralleled) **distribution buffer**, and/or raise destination input impedance to cut the load. OFFSET scaled to ±5V (plugin). SPICE: specs/block-3/sim/modbus_depth.cir.

Design status: [x] draft → [ ] reviewed → [ ] validated on prototype

## Overview

Analog implementation of the DSP ModBusProcessor. The modulation source is chosen by the
MOD_SRC 3-way switch — LFO1 / LFO2 / External(MOD_IN) — ahead of this core (`Pogo.cpp:363–366`).
The core applies an exponential-taper gain (0.2×–5×) and a bipolar offset (±5V), then clamps
the output to ±10V, driving the mod bus distribution rail that feeds all **18** attenuverter
destinations (plus a raw VCA normal handled in block 4).

Chosen because:
- Inverting summing amplifier (MB_AMP) followed by an inverter (MB_INV) is the standard
  analog summing architecture: transparent, low-noise, DC-accurate
- Two TL074 halves handle MB_AMP and MB_INV; the remaining two halves are spare
- A single TL074 (SOIC-14) for the entire mod bus processor is IC-count efficient
- ±10V output clamp uses back-to-back zener diodes or a TL431-based precision clamp

## Schematic


ASCII fallback:

```
 LFO1 ──► SW7 A1(1) ┐
 LFO2 ──► SW7 B1(4) ├─ MOD_SRC (DW5, COMs bridged) ─► A_COM(2) ─────► V_src
 MOD_IN ─[100Ω]+[BAT54S]─► SW7 B2(6) (EXT) ┘
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
                                                         │
                                                   MOD_BUS RAIL
                                                   → 18 attenuverters
                                                     (+ raw VCA normal, block 4)
```

*(No MOD_POS/NEG/CLIP indicator LEDs: the plugin drives none and the locked panel has no
footprints for them — removed, change 0018.)*

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

At clamp onset (|V| ≥ 9.9V due to zener tolerance), the zeners conduct and hold the output.
```

### MOD_CLIP / clamp behavior

DSP: `|busV| ≥ 10V` hard clamp. Hardware: back-to-back BZX84C10 zeners in the MB_INV
feedback path; zener knee typically 9.9–10.1V (±5% tolerance → 9.5–10.5V onset). There is
no MOD_CLIP indicator LED (the plugin drives none; the locked panel has no footprint).

## Design Choices & Rationale

### TL074 for Entire Processor

MB_AMP (half A) + MB_INV (half B); halves C and D spare. The whole mod bus processor is one
TL074CDT (SOIC-14) plus passives on a small board section.

### Mod Bus Distribution

V_modbus drives 18 per-destination R_SRC_NORM resistors (100 kΩ each) — the bus normals into
each override jack through its 100 kΩ. Total load on V_modbus:
  18 × 100 kΩ in parallel ≈ 5.6 kΩ

At V_modbus = ±10 V and 5.6 kΩ load: I ≈ ±1.8 mA — easily driven by the MB_INV output (U3.7)
directly; **no distribution buffer is needed** (halves C+D stay spare). The attenuverter pot
for each destination sits on the destination's V_src node (bus-via-R_SRC_NORM when unpatched,
or the override jack when patched), not directly across the bus rail.

### Offset Reference

V_off is derived from a voltage divider between the module's +5V and −5V precision
references (if available) or from the ±12V rails through resistive division. Using
the same ±5V references as the CV scaling circuitry ensures offset calibration
is consistent with the mod bus gain calibration.

## Component Values (POGO-specific)

| Ref (generic) | Part | Package | Value | Notes |
|---|---|---|---|---|
| MB_PROC_A | TL074CDT | SOIC-14 | — | Half A = MB_AMP, Half B = MB_INV; halves C+D spare |
| R_f | Resistor | 0603 | 100 kΩ | MB_AMP feedback; sets gain denominator |
| R_src | Pot + end R | Panel | 492 kΩ total | AMOUNT pot: 470 kΩ log taper + 22 kΩ floor resistor; sets 0.2×–4.55× (≈0.2×–5×) range |
| R_src_floor | Resistor | 0603 | 22 kΩ | Floor input resistor in series with pot; limits max gain to 100/22 = 4.55× |
| R_off | Resistor | 0603 | 100 kΩ | Offset input resistor; R_f/R_off = 1 → ±5V offset |
| R_inv_in | Resistor | 0603 | 100 kΩ | MB_INV input resistor |
| R_inv_f | Resistor | 0603 | 100 kΩ | MB_INV feedback; 1% tolerance |
| D_CLAMP_P, D_CLAMP_N | BZX84-C10 | SOT-23 | 10V zener | Back-to-back in MB_INV feedback; ±10V clamp |
| RV_MB_ZERO | Bourns 3224W | SMD | 10 kΩ | Zero-offset null trim at MB_AMP |
| RV_MB_AMOUNT_MAX | Bourns 3224W | SMD | 10 kΩ | 5× gain calibration trim in R_src leg |
| R_cv_in | Resistor | 0603 | 100 Ω | MOD_IN jack series protection |
| D_cv_in | BAT54S | SOT-23 | — | MOD_IN input clamp |
| SW_MOD_SRC | Dailywell DW5 | sub-mini toggle | — | 3-way source select LFO1/LFO2/EXT (COMs bridged) |
| C_VCC, C_VEE | Ceramic bypass | 0603 | 100 nF | Per IC supply pin |

## Performance Characteristics

| Parameter | Value | Condition |
|---|---|---|
| Gain range | 0.2× – 5× | AMOUNT pot full sweep |
| Gain taper | ~log (perceptual) | Log-taper pot |
| Offset range | ±5V | OFFSET pot full sweep |
| Output clamp | ±10V | BZX84-C10 zeners |
| Clamp onset | ±9.9V (±10V nominal) | Zener knee |
| Bandwidth | >100 kHz | TL074; not audio-critical |
| Offset null | <10 mV | After RV_MB_ZERO trim |
| Output drive | ~1.8 mA | 18 × 100 kΩ R_SRC_NORM loads (direct, no buffer) |

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
- No distribution buffer needed: the bus drives 18 × 100 kΩ R_SRC_NORM resistors (~5.6 kΩ,
  ~1.8 mA), well within the MB_INV output (U3.7). Halves C+D of MB_PROC_A stay spare.
- MOD_SRC select: the bus source is the DW5 3-way switch (LFO1 / LFO2 / External), with the
  DPDT commons bridged (see Schematic). MOD_IN feeds only the EXT throw — no auto-normal.
  Both LFO outputs remain live at their own jacks regardless of switch position.

## Used By

| Block | Instance | Board | Notes |
|---|---|---|---|
| block-3 | MB_PROC | utility | Single instance; feeds 18 attenuverters + raw VCA normal |
| block-3 | MOD_SRC (SW7, DW5) | control | 3-way select LFO1/LFO2/EXT → V_src (COMs bridged) |
