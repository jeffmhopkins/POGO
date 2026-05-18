# POGO — Modulation Architecture

## Status
- Phase 1 (Audio Spec): [x] complete
- Phase 2 (Analog Behavior): [x] complete
- Phase 3 (Circuit Design): [x] complete

---

## Overview

POGO's modulation system is a centralized mod bus that routes one primary modulation source
to all CV-controllable parameters. Each destination has its own attenuverter and an override
jack that disconnects the mod bus when a cable is inserted.

```
Envelope Follower (L or R or L+R, selected via MOD SOURCE SEL switch)
  │
  ▼
PRIMARY MOD SOURCE jack  ←  tip-switching: normalizes to selected ENV OUT when unplugged
  │
  ▼
Mod Bus Processor:
  AMOUNT knob  (0.2× – 5×)  ─────┐
  OFFSET knob  (±5 V)        ─────┤──► MOD BUS SIGNAL
  │
  ▼
MOD BUS OUT jack  (buffered output for external patching)
  │
  ▼ (to each of 14 destinations)

[Per Destination]:
  MOD BUS ──[100 Ω + BAT54 clamp]──► ATTENUVERTER knob (−1× to +1×) ──► CV summing node
                                              ▲
                        OVERRIDE JACK ────────┘  (tip-switching: disconnects mod bus when patched)
```

---

## Phase 1: Functional Specification

### Primary Mod Source

- **MOD SOURCE SEL switch** (3-position, panel): selects which envelope signal normalizes into
  the PRIMARY MOD SOURCE jack
  - Position L: ENV OUT L → Mod Bus
  - Position R: ENV OUT R → Mod Bus
  - Position LR: L+R averaged → Mod Bus

- **PRIMARY MOD SOURCE jack**: tip-switching TS jack
  - Unplugged: selected ENV signal is active
  - Plugged: any external CV or audio signal overrides the envelope

### Mod Bus Processor Controls

| Name | Range | Default | Taper | Description |
|---|---|---|---|---|
| AMOUNT | 0.2× – 5× | 1× | Linear | Scales the mod source signal before adding offset |
| OFFSET | ±5 V | 0 V | Linear | DC offset added after scaling; shifts the mod signal up or down |

**Formula**: `V_modbus = AMOUNT × V_source + OFFSET`

Example: with an envelope from 0–10 V, AMOUNT=0.5, OFFSET=−2.5 V:
- Silence (V=0): mod bus = −2.5 V
- Full level (V=10): mod bus = 5 − 2.5 = 2.5 V
- Result: mod bus swings −2.5 V to +2.5 V (centered around 0)

### MOD BUS OUT jack
Buffered output of the mod bus signal. Allows routing the processed envelope/mod source
to other modules. 1 kΩ series output resistor.

### Per-Destination Circuit

For each modulation destination:
1. **OVERRIDE JACK**: tip-switching input jack. When empty, the mod bus signal feeds through.
   When a cable is inserted, the override jack signal replaces the mod bus for this destination.
2. **100 Ω + BAT54 clamp**: standard input protection on the selected signal (see shared/cv-input-protection.md)
3. **ATTENUVERTER**: bipolar pot (−1× to +1×, center detent at 0). Scales the mod signal before
   it reaches the parameter's CV summing node. Full CCW: inverts the mod signal at full scale.
   Center: cuts mod to zero. Full CW: passes mod signal at full scale.
4. **CV summing node**: attenuverter output sums with the parameter's panel knob voltage at the
   filter/distortion/APF control input.

---

## Phase 2: Analog Behavior Model

### Mod Bus Processor Transfer Function

Linear amplifier + adder:
```
V_modbus = AMOUNT × V_source + OFFSET

where AMOUNT = pot position mapped to 0.2 – 5×
      OFFSET = pot position mapped to −5 V – +5 V
```

Circuit implementation: inverting summer op-amp with two inputs:
```
V_modbus = −(R_f/R_src × V_source + R_f/R_off × V_offset)
```
Followed by inverter to restore correct polarity. (Or use non-inverting topology with gain stage.)

### Per-Destination Attenuverter Model
```
V_dest_cv = ATTENUVERTER_gain × V_selected

ATTENUVERTER_gain ∈ [−1, +1]  (bipolar pot, center detent = 0)
```

At center: `V_dest_cv = 0` — mod bus is fully cut, parameter is at its panel-knob position only.
At full CW: `V_dest_cv = V_selected` — mod bus (or override) passes at full scale.
At full CCW: `V_dest_cv = −V_selected` — mod bus is inverted.

---

## Phase 3: Circuit Design

### Mod Bus Processor Circuit

Inverting summer op-amp (TL072 half):
```
V_source ──[R_src]──┬──(−) MB_AMP ──(out)── V_modbus_inv
V_offset ──[R_off]──┘     (+) = GND
                          (out)◄──[R_f]──(−)
```

Where:
- R_f / R_src = AMOUNT gain range (0.2–5): use a pot for R_src with end resistors
- R_off sets OFFSET range: a ±5 V pot voltage into R_off with R_f sets offset range

An inverter follows to restore signal polarity:
```
V_modbus_inv ──[R_inv]──(−) MB_INV ──(out)── V_modbus
                          (+) = GND
                          (out)◄──[R_inv]──(−)
```

MOD BUS OUT: unity-gain output buffer (third TL072 half) + 1 kΩ series to jack.

**IC**: 1× TL074 (quad op-amp, SOIC-14) — summer + inverter + output buffer + 1 spare half.

### Per-Destination Attenuverter Circuit (×14 destinations)

```
V_mod ──[100 Ω]──[BAT54]──────────────────────────────────────────────────── V_att_in
                                                                              │
Override jack tip ──[100 Ω]──[BAT54]──[tip switch logic]──────────────────────┘
  (normalizes to V_att_in when unplugged; disconnects V_att_in when patched)

V_att_in ──(CW end of ATTENUVERTER pot)──(wiper)──(CCW end = GND)

Wiper ──► CV summing node at parameter input
```

Bipolar pot wiring:
- CW end: V_att_in
- CCW end: −V_att_in (inverted via resistor divider and op-amp, or: CW end is tied to positive,
  CCW end to negative of a virtual ±V_att supply via a unity-gain inverter)
- Wiper sweeps from −V_att_in to +V_att_in

Simpler approach: use a center-tapped pot connected between +V and −V rails:
```
+V_att ──(CW) ── pot ── (CCW) ── −V_att
              └── (wiper) ──► CV input
```
Where +V_att and −V_att come from the override jack or mod bus attenuated via a virtual ground.

**IC requirement**: 19 attenuverters × (1 buffer + 1 inverter) = 38 op-amp halves for full
isolation. Use TL074 (quad, 4 halves each): 10× TL074 for all 19 attenuverter circuits.
(Note: APF SOURCE/POLARITY and Distortion MODE have no attenuverter — switches only.)

### Modulation Destinations

| Destination | Block | CV Type | Override Jack |
|---|---|---|---|
| APF Freq 1 | 3 | ±5 V, 1V/oct | Yes |
| APF Freq 2 | 3 | ±5 V, 1V/oct | Yes |
| APF Freq 3 | 3 | ±5 V, 1V/oct | Yes |
| APF Feedback 1 | 3 | 0–10 V | Yes |
| APF Feedback 2 | 3 | 0–10 V | Yes |
| APF Feedback 3 | 3 | 0–10 V | Yes |
| APF Blend | 3 | 0–10 V | Yes |
| APF Dry/Wet | 3 | 0–10 V | Yes |
| Distortion Drive 1 (Group 1) | 4 | 0–10 V | Yes |
| Distortion Drive 2 (Group 2) | 4 | 0–10 V | Yes |
| Distortion Drive 3 (Group 3) | 4 | 0–10 V | Yes |
| LP1 Cutoff | 5 | ±5 V, 1V/oct | Yes |
| LP1 Resonance | 5 | 0–10 V | Yes |
| LP2 Cutoff | 6 | ±5 V, 1V/oct | Yes |
| LP2 Resonance | 6 | 0–10 V | Yes |
| HP Cutoff | 7 | ±5 V, 1V/oct | Yes |
| HP Resonance | 7 | 0–10 V | Yes |
| Pre-Gain Level | 1 | 0–10 V | Yes (future: CV-selectable gain stage) |

### IC / Component Selection (Mod Bus Processor)

| Reference | Part Number | Package | Qty | Notes |
|---|---|---|---|---|
| MB_PROC | TL074CDT | SOIC-14 | 1 | Summer + inverter + output buffer + spare |
| MB_ATT_x | TL074CDT | SOIC-14 | 7 | Attenuverter inverter stages (14 destinations × 2 halves / 4 per IC) |
| D_clamp_x | BAT54S | SOT-23 | 16 | Input clamp at each attenuverter input (14 destinations + 2 spares) |
| R_clamp_x | — | 0603 | 100 Ω | 14 | Series resistors at each attenuverter input |
| RV_AMOUNT | Lin pot | 9mm | 1 | Mod bus AMOUNT (0.2× – 5×) |
| RV_OFFSET | Lin pot | 9mm | 1 | Mod bus OFFSET (±5 V) |
| RV_ATT_x | Bipolar pot | 9mm | 13 | Attenuverters (13 destinations with attenuverter; MODE has none) |

### Trim Pots

| Reference | Purpose | Adjustment |
|---|---|---|
| RV_MB_ZERO | Mod bus zero offset null: output = 0 V when source = 0 V and offset knob centered | Trim until V_modbus = 0 V with V_source = 0 V and OFFSET at center |
| RV_MB_AMOUNT_MAX | AMOUNT maximum gain calibration (target: 5.0×) | Set AMOUNT to max; input 1 V; trim until output = 5 V |

### Power Draw Estimate
- 8× TL074 (mod bus + 7 attenuverter ICs): ~30 mA
- +12 V: ~15 mA | −12 V: ~15 mA

### Known Circuit Challenges
- 14 attenuverter pots is a very large number for a single module. Evaluate during panel
  layout whether all 14 can fit. If space is constrained, group modulation targets (e.g., a
  single APF attenuverter for all three APF freq destinations) and add sub-routing switches.
- Tip-switch normalling for 14 jacks: all jacks must be TS type with sleeve-switching lug
  connected to the mod bus. Verify jack footprint (Thonkiconn) has switching lug accessible
  in PCB layout.
- Op-amp count in mod architecture alone: ~8 TL074 ICs. Total op-amp count for the full module
  is significant — plan power budget carefully.
