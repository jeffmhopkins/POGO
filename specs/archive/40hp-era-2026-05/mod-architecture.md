# POGO — Modulation Architecture

## Status
- Phase 1R (Extract from code): [x] complete — updated for 48HP
- Phase 2R (Analog model): [ ] complete
- Phase 3R (Circuit design): [ ] complete

> **48HP update (2026-05-27):** Mod source changed from Envelope Follower to **LFO1** (normalizes
> when MOD_IN unpatched). Destination count changed: 19 → 22 (added LP1_TILT, BP_TILT;
> VCA_OFS is a trimpot, not a mod destination). New lights: MOD_CLIP, MOD_POS, MOD_NEG.
> Mod bus scale is now exponential (0.2–5× = 0.2 × 25^param). Clamp ±10V added.

---

## Overview

POGO's modulation system is a centralized mod bus that routes one primary modulation source
to all CV-controllable parameters. Each destination has its own attenuverter and an override
jack that disconnects the mod bus when a cable is inserted.

```
LFO1 output (±5V triangle)
  │
  ▼
MOD_IN jack  ←  tip-switching: normalizes to LFO1 when unpatched; external CV overrides
  │
  ▼
Mod Bus Processor:
  MOD_SCALE trimpot  (0.2× – 5×, exp: 0.2 × 25^param)  ─────┐
  MOD_OFFSET trimpot (±5 V, offset_param × 5)           ─────┤──► MOD BUS SIGNAL (clamped ±10V)
                                                               │
  MOD_CLIP LED ← |busV| ≥ 9.9V                               │
  MOD_POS LED  ← busV > 0                                    │
  MOD_NEG LED  ← busV < 0                                    │
  │
  ▼ (to each of 22 destinations)

[Per Destination]:
  MOD BUS ──[attenuverter knob (−1× to +1×)]──► CV summing node
                  ▲
OVERRIDE JACK ────┘  (tip-switching: disconnects mod bus when patched)
```

---

## Phase 1: Functional Specification

### Primary Mod Source

- **LFO1 output** (±5 V triangle, 0.05–20 Hz) normalizes into MOD_IN when unpatched.
- **MOD_IN jack**: tip-switching TS jack
  - Unpatched: LFO1 is active
  - Patched: any external CV or audio overrides LFO1

### Mod Bus Processor Controls

| Name | Enum | Range | Default | Taper | Description |
|---|---|---|---|---|---|
| Mod Scale | `MOD_SCALE_PARAM` | 0–1 | 0.5 | Exponential | Scales: 0.2×–5× = `0.2 × 25^param` |
| Mod Offset | `MOD_OFFSET_PARAM` | −1–1 | 0 | Linear | DC offset: `offset_param × 5V` → ±5V |

**Formula**: `V_modbus = clamp(scale × V_source + offset, −10, +10)`

Example: LFO1 ±5V, scale=0.5 (= 0.2×25^0.5 ≈ 1×), offset=0:
- bus swings roughly −5 V to +5 V (passthrough at scale=~1)

MOD_CLIP LED lights when |busV| ≥ 9.9V. MOD_POS lights when busV > 0. MOD_NEG when busV < 0.

### Per-Destination Circuit

For each modulation destination:
1. **OVERRIDE JACK**: tip-switching input jack. When empty, the mod bus signal feeds through.
   When a cable is inserted, the override jack signal replaces the mod bus for this destination.
2. **100 Ω + BAT54 clamp**: standard input protection on the selected signal (see shared/cv-input-protection.md)
3. **ATTENUVERTER**: bipolar pot (−1× to +1×, center detent at 0). Scales the mod signal before
   it reaches the parameter's CV summing node. Full CCW: inverts the mod signal at full scale.
   Center: cuts mod to zero. Full CW: passes mod signal at full scale.
4. **CV summing node**: attenuverter output sums with the parameter's panel knob voltage at the
   filter/distortion/SVF control input.

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

**IC**: 1× TL072 (dual op-amp, SOIC-8) — summer + inverter. No output buffer needed.

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

**IC requirement**: 19 attenuverters × 2 op-amp halves (buffer + inverter) = 38 halves.
Use TL074 (quad, 4 halves each): **10× TL074** for all 19 attenuverter circuits (40 halves; 2 spare).

### Modulation Destinations (22 total — 48HP topology)

Each destination has an override jack (normalizes to mod bus when unpatched) and an
attenuverter trimpot (−1× to +1×). VCA_OFS is a fixed trimpot with no override jack.

| # | Destination | Block | Param Enum | Input Enum | Att Enum | CV Type |
|---|---|---|---|---|---|---|
| 1 | VCA Level | VCA | `VCA_AMT_PARAM` | `VCA_INPUT` | — | 0–10 V |
| 2 | LP1 Freq | LP1 | `LP1_FREQ_PARAM` | `LP1_FREQ_INPUT` | `LP1_FREQ_ATT_PARAM` | ±5 V, 1V/oct |
| 3 | LP1 Tilt | LP1 | `LP1_TILT_PARAM` | `LP1_TILT_INPUT` | `LP1_TILT_ATT_PARAM` | ±5 V |
| 4 | LP1 Res | LP1 | `LP1_RES_PARAM` | `LP1_RES_INPUT` | `LP1_RES_ATT_PARAM` | 0–10 V |
| 5 | BP Offset | BP | `BP_OFFSET_PARAM` | `BP_FREQ_INPUT` | `BP_FREQ_ATT_PARAM` | ±5 V, 1V/oct |
| 6 | BP Tilt | BP | — | `BP_TILT_INPUT` | `BP_TILT_ATT_PARAM` | ±5 V |
| 7 | BP1 Freq | BP1 | `BP1_FREQ_PARAM` | `BP1_FREQ_INPUT` | `BP1_FREQ_ATT_PARAM` | ±5 V, 1V/oct |
| 8 | BP1 Focus | BP1 | `BP1_FOCUS_PARAM` | `BP1_FOCUS_INPUT` | `BP1_FOCUS_ATT_PARAM` | 0–10 V |
| 9 | BP1 Drive | BP1 | `BP1_DIST_PARAM` | `BP1_DIST_INPUT` | `BP1_DIST_ATT_PARAM` | 0–10 V |
| 10 | BP2 Freq | BP2 | `BP2_FREQ_PARAM` | `BP2_FREQ_INPUT` | `BP2_FREQ_ATT_PARAM` | ±5 V, 1V/oct |
| 11 | BP2 Focus | BP2 | `BP2_FOCUS_PARAM` | `BP2_FOCUS_INPUT` | `BP2_FOCUS_ATT_PARAM` | 0–10 V |
| 12 | BP2 Drive | BP2 | `BP2_DIST_PARAM` | `BP2_DIST_INPUT` | `BP2_DIST_ATT_PARAM` | 0–10 V |
| 13 | BP3 Freq | BP3 | `BP3_FREQ_PARAM` | `BP3_FREQ_INPUT` | `BP3_FREQ_ATT_PARAM` | ±5 V, 1V/oct |
| 14 | BP3 Focus | BP3 | `BP3_FOCUS_PARAM` | `BP3_FOCUS_INPUT` | `BP3_FOCUS_ATT_PARAM` | 0–10 V |
| 15 | BP3 Drive | BP3 | `BP3_DIST_PARAM` | `BP3_DIST_INPUT` | `BP3_DIST_ATT_PARAM` | 0–10 V |
| 16 | HP Freq | HP | `HP_FREQ_PARAM` | `HP_FREQ_INPUT` | `HP_FREQ_ATT_PARAM` | ±5 V, 1V/oct |
| 17 | HP Res | HP | `HP_RES_PARAM` | `HP_RES_INPUT` | `HP_RES_ATT_PARAM` | 0–10 V |
| 18 | LP2 Freq | LP2 | `LP2_FREQ_PARAM` | `LP2_FREQ_INPUT` | `LP2_FREQ_ATT_PARAM` | ±5 V, 1V/oct |
| 19 | LP2 Res | LP2 | `LP2_RES_PARAM` | `LP2_RES_INPUT` | `LP2_RES_ATT_PARAM` | 0–10 V |

**Removed from 40HP:** FB_DIST_BLEND, COMB_BYPASS, per-group SVF resonance as mod target
(FOCUS param handles this but is modulated by its own group jack, not a shared destination).

**VCA_OFS** (`VCA_OFS_PARAM`): fixed trimpot, no mod destination, no CV input.

### IC / Component Selection (Mod Bus Processor)

| Reference | Part Number | Package | Qty | Notes |
|---|---|---|---|---|
| MB_PROC | TL074CDT | SOIC-14 | 1 | Summer + inverter + output buffer + spare |
| MB_ATT_x | TL074CDT | SOIC-14 | 10 | Attenuverter inverter stages (19 destinations × 2 halves / 4 per IC = 10 ICs) |
| D_clamp_x | BAT54S | SOT-23 | 16 | Input clamp at each attenuverter input (14 destinations + 2 spares) |
| R_clamp_x | — | 0603 | 100 Ω | 14 | Series resistors at each attenuverter input |
| RV_AMOUNT | Lin pot | 9mm | 1 | Mod bus AMOUNT (0.2× – 5×) |
| RV_OFFSET | Lin pot | 9mm | 1 | Mod bus OFFSET (±5 V) |
| RV_ATT_x | Bipolar pot | 9mm | 19 | Attenuverters (one per destination; all 19 destinations have attenuverters) |

### Trim Pots

| Reference | Purpose | Adjustment |
|---|---|---|
| RV_MB_ZERO | Mod bus zero offset null: output = 0 V when source = 0 V and offset knob centered | Trim until V_modbus = 0 V with V_source = 0 V and OFFSET at center |
| RV_MB_AMOUNT_MAX | AMOUNT maximum gain calibration (target: 5.0×) | Set AMOUNT to max; input 1 V; trim until output = 5 V |

### Power Draw Estimate
- 1× TL074 (MB_PROC) + 10× TL074 (attenuverter stages) = 11× TL074 total: ~38 mA
- +12 V: ~40 mA | −12 V: ~40 mA

### Known Circuit Challenges
- 19 attenuverter pots is a very large number for a single module. Panel layout (Phase 4) has
  confirmed all 19 fit at 40 HP — see specs/panel-design/panel-notes.md for placement.
- Tip-switch normalling for 19 jacks: all jacks must be TS type with sleeve-switching lug
  connected to the mod bus. Verify jack footprint (Thonkiconn) has switching lug accessible
  in PCB layout.
- Op-amp count in mod architecture alone: ~8 TL074 ICs. Total op-amp count for the full module
  is significant — plan power budget carefully.
