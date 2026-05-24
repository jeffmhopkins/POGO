# POGO — KiCad Schematic Generation Process

## Overview

POGO has no EDA files — all circuit information lives in `specs/`. This document explains how
KiCad 7 `.kicad_sch` files are generated from those specs and imported into Flux.ai for PCB
layout.

The approach: write a Python generator script per board that emits valid KiCad 7 S-expression
syntax. The generator is the authoritative source; the `.kicad_sch` file is the artifact.

---

## Board Order

| Board | Why this order |
|---|---|
| 1. Control board | Purely passive (jacks, pots, switches). No ICs. Easiest to validate format. |
| 2. Utility board | Complex (mod bus, attenuverters, THAT340s). Do after format is proven. |
| 3. Left audio board | All analog signal processing ICs. Most dense. |
| 4. Right audio board | Mirror of left. Copy-paste with net-name substitution. |

---

## File Locations

```
kicad/
  pogo.kicad_pro                   KiCad 7 project file (references all schematics)
  generate_control_board.py        Generator script → produces pogo-control-board.kicad_sch
  pogo-control-board.kicad_sch     Generated artifact (control board only)
```

---

## KiCad 7 S-Expression Format

A `.kicad_sch` file is a nested S-expression (Lisp-like parenthesized text). Key sections:

```
(kicad_sch (version 20230121) (generator "eeschema") (paper "A0")
  (lib_symbols          ← inline symbol geometry (defined ONCE per type)
    (symbol "Device:R_POT" ...)
    ...
  )
  (symbol               ← component INSTANCE (one per placed component)
    (lib_id "Device:R_POT")
    (at X Y angle)
    (property "Reference" "RV1" ...)
    (property "Value" "ATTACK" ...)
    ...
  )
  (global_label         ← net label (placed at pin connection point)
    "NET_WPR_ATTACK"
    (shape input)
    (at X Y angle)
    ...
  )
)
```

### How connectivity works

Instead of drawing wires across the canvas, every component pin gets a **global label** placed
directly at its pin endpoint. Two pins with the same label string are electrically connected.
This makes the schematic readable regardless of component placement.

Pin endpoint = symbol (at X Y) + pin offset from lib_symbol definition.

---

## Symbol Library Mapping

| Component | KiCad 7 lib_id | Pins | Notes |
|---|---|---|---|
| Thonkiconn PJ301M-12 | `Device:Audio_Jack_3.5mm_SwitchT` | T=Tip, S=Sleeve, SW=Switch-lug | SW breaks when cable inserted; used for normalling |
| Alpha 9mm pot (any size) | `Device:R_POT` | 1=CCW, 2=Wiper, 3=CW | Same symbol all sizes; Value = panel label |
| ALPS RS45xx slider | `Device:R_POT` | Same 3-pin | Value="SLIDER LP2 CUTOFF" etc. |
| Sub-mini toggle 2-pos (SPDT) | `Switch:SW_SPDT` | C=Common, A=throw-A, B=throw-B | GAIN switch |
| Sub-mini toggle 3-pos (SP3T) | `Switch:SW_SP3T` | C=Common, 1/2/3=positions | MOD SRC, MODE 1/2/3, POLARITY |
| IDC 34-pin (2×17) | `Connector_IDC:IDC-Header_2x17_P2.54mm_Vertical` | Pins 1–34 | CN_CTRL_1, CN_CTRL_2 |
| IDC 24-pin placeholder (2×12) | `Connector_IDC:IDC-Header_2x12_P2.54mm_Vertical` | Pins 1–24 | CN_CTRL_3 (undocumented wipers; 23 needed + 1 spare) |
| Power rails | `power:+12V`, `power:-12V`, `power:GND` | 1 pin each | Pot supply ends |

---

## Net Naming Convention

```
NET_<SIGNAL>          Audio/CV signals on jacks (NET_L_IN, NET_ENV_OUT_L)
NET_CV_<DEST>         CV override jack tips (NET_CV_FREQ1, NET_CV_LP1_CUT)
NET_WPR_<LABEL>       Pot/slider wipers (NET_WPR_FREQ1, NET_WPR_ATT_BYPASS)
NET_SW_<LABEL>        Switch outputs (NET_SW_GAIN, NET_SW_MODE1_A)
+12V / -12V / GND     Power rails (KiCad power symbols)
```

Audio jack sleeve → `GND`. Pot CCW end:
- Bipolar attenuverter: CCW=`-12V`, CW=`+12V`
- Unipolar main pot: CCW=`GND`, CW=`+12V`

Override CV jack switch lug → same net as the attenuverter CW end on the utility board
(not on the control board connector — the switch lug is internal to the control board).
For the control board schematic, the switch lug connects to a `NET_MODBUS_NORM_<DEST>` label
(documents the normalling path; utility board resolves it).

---

## Reference Designator Scheme

| Prefix | Component |
|---|---|
| J | Audio/CV jacks (Thonkiconn) |
| RV | Pots and sliders (rotary or slider) |
| SW | Toggle switches |
| CN | IDC connectors |

Numbering is sequential within each prefix, ordered left-to-right, top-to-bottom on the panel.
J1–J8 = audio I/O jacks; J9 = MOD IN; J10–J28 = CV override jacks (19 destinations).
RV1–RV41 = pots/sliders. SW1 = GAIN; SW2 = MOD SRC; SW3 = POLARITY; SW4–SW6 = MODE 1/2/3.
CN1 = CN_CTRL_1; CN2 = CN_CTRL_2; CN3 = CN_CTRL_3 (placeholder).

---

## Known Gaps (to resolve before PCB layout)

### CN_CTRL_3: Missing main parameter wipers

CN_CTRL_1 and CN_CTRL_2 (documented in `specs/board-layout/layout-notes.md`) cover:
- Audio I/O jacks (8 signals)
- 19 override CV jack tips
- 19 attenuverter wipers (one per mod destination; pins 9–27 of CN_CTRL_2)
- GAIN switch, MODE switch position outputs, MOD SRC switch, POLARITY switch
- AMOUNT wiper, OFFSET wiper, STEREO SPREAD OFFSET wiper

**Note on layout-notes.md "19 + VCA AMT = 20"**: VCA Level IS one of the 19 mod destinations
and its attenuverter wiper appears once (CN_CTRL_2 pin 12 = `NET_WPR_ATT_VCA_AMT`). The
layout-notes phrasing is misleading. CN_CTRL_2 pin 28 is SPARE.

**Not covered** by CN_CTRL_1/2 (21 signals requiring 24-pin CN_CTRL_3):
- ATTACK wiper, RELEASE wiper
- COMB BYPASS wiper, WIDTH wiper, MASTER OFFSET wiper, FB DIST BLEND wiper
- FREQ 1/2/3 wipers, FB 1/2/3 wipers, DRIVE 1/2/3 wipers
- LP1 CUTOFF wiper, LP1 RESONANCE wiper
- LP2 CUTOFF (slider) wiper, LP2 RESONANCE wiper
- HP CUTOFF (slider) wiper, HP RESONANCE wiper

These are assigned to **CN_CTRL_3** (24-pin IDC, 2×12 = 23 signals + 1 spare) in the
generated schematic. The actual pinout must be added to `layout-notes.md` before PCB layout.

### MODE switch encoding and count

**Switch count ambiguity**: panel-notes.md shows ONE shared MODE switch (SW4, in Zone 1
DIST section) for all 3 comb groups. layout-notes.md CN_CTRL_2 pins 6–8 says "3-pos switch
per distortion chain" (implying 3 switches, one per comb group). The generator follows
panel-notes (1 shared switch). Decision must be confirmed before PCB layout.

**How position signals reach utility board**: CN_CTRL_2 pins 6–8 carry the 3 position output
nets of SW4: `NET_SW_MODE_SFT`, `NET_SW_MODE_HRD`, `NET_SW_MODE_WFD`. The switch common
ties to +12V on the control board; the active position pulls its net to +12V while the other
two float (or are pulled low on the utility board). The utility board decodes which of the 3
is high to select the CD4053 A/B state. If 3 separate switches are used, expand CN_CTRL_2
pins 6–8 to carry one position signal per switch group (possibly 9 pins for 3 switches × 3
positions), requiring a pinout revision in layout-notes.md.

---

## Generator Script Approach

`kicad/generate_control_board.py` produces the `.kicad_sch` by:

1. Defining all lib_symbol geometries (once per type) — correct pin count, type, position
2. Building a component list (ref, lib_id, value, net assignments per pin)
3. Placing components in a zone-based grid matching the panel layout zones
4. Emitting a global_label for every pin (net label placed at the pin's canvas coordinate)
5. Emitting power symbols (+12V, −12V, GND) for pot supply ends
6. Writing the complete S-expression to `pogo-control-board.kicad_sch`

Run from the `kicad/` directory:
```bash
cd kicad
python3 generate_control_board.py
```

---

## Validation Steps

1. Open `pogo-control-board.kicad_sch` in KiCad 7 (free download from kicad.org)
2. Run ERC (Tools → Electrical Rules Checker):
   - Expected: "pin unconnected" warnings for CN_CTRL_3 placeholder pins — these are intentional
   - Not expected: short circuits, missing power pins, duplicate reference designators
3. Check component count: 28 jacks + 41 pots/sliders + 6 switches + 3 connectors = 78 components
4. Verify connector pin assignments match `layout-notes.md` CN_CTRL_1 and CN_CTRL_2 tables
5. Export netlist: File → Export → Netlist → KiCad format → `pogo-control-board.net`

---

## Flux.ai Import

1. In Flux.ai: **File → Import → KiCad 7 Schematic**
2. Select `pogo-control-board.kicad_sch`
3. Flux auto-matches standard library parts (R_POT, AudioJack, SW_SPDT, SW_SP3T)
4. IDC connectors may need manual part assignment — search Nexar/Octopart within Flux for
   "2.54mm IDC header 34 pin" and "2.54mm IDC header 20 pin"
5. Net names are preserved exactly as generated — verify them in Flux's net list view
6. PCB layout can begin once all four schematics are imported and part numbers are assigned

---

## Template for Subsequent Boards

Each board's generator script follows the same structure:

| Section | Content |
|---|---|
| lib_symbols | Only types used on that board |
| Power symbols | +12V, -12V, GND at every IC supply pin |
| Component instances | One per IC, resistor, capacitor, etc. |
| Global labels | Net name at every pin |
| Connector block | IDC connector with CN_UTIL_L / CN_UTIL_R / CN_CTRL pinout |

For the utility board: add `Device:R` (resistors), `Device:C` (caps), `Amplifier_Operational:TL074`
(quad op-amp SOIC-14), `Amplifier_Operational:TL072` (dual op-amp), and the THAT340 (custom
symbol needed — 16-pin SOIC with 4 NPN transistors).

For audio boards: additionally `Amplifier_Operational:LM13700` (18-pin DIP/SOIC OTA),
`Amplifier_Operational:LM4562` (SOIC-8), `Amplifier_Operational:NE5532` (SOIC-8),
and the CD4053 analog switch (SOIC-16).
