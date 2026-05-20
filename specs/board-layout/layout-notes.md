# POGO Board Layout Notes

## Status
- Phase 5 (Board Layout): [x] complete — strategy + connector pinout

---

## 1. Board Split Decision: 4 Boards

POGO uses four PCBs. The split is driven by three constraints:
(a) panel controls and jacks require a panel-facing board that cannot also carry dense SMD
    circuitry due to depth and assembly access;
(b) all six expo converters (THAT340) feed both L and R audio paths and belong on a central
    board, not on one channel's audio board;
(c) the left and right audio signal chains are fully independent (no cross-channel audio
    signals at the IC level) and are dense enough to warrant dedicated boards.

```
┌─────────────────────────────────────────────────────────────────┐
│  PANEL  (40 HP × 128.5 mm)                                      │
│  Control Board  (panel-mounted, 1.2 mm FR4)                     │
│    Jacks, pots, switches only — no signal processing ICs        │
└──────────────┬──────────────────────────────────────────────────┘
               │  CN_CTRL_1 + CN_CTRL_2
               │  (2× 34-pin 2.54 mm IDC ribbon cable)
               │
    ┌──────────┴──────────────────────────────────────────────┐
    │  Utility / HW-Connect Board                              │
    │  Eurorack power, mod bus, expo converters, shared CVs   │
    └─────────────────────┬─────────────────────┬────────────┘
               CN_UTIL_L  │                     │  CN_UTIL_R
          (34-pin IDC)     │                     │  (34-pin IDC)
                           │                     │
              ┌────────────┘                     └──────────────┐
              │                                                  │
    ┌─────────┴──────────┐                        ┌─────────────┴──────┐
    │  Left Audio Board  │                        │  Right Audio Board  │
    │  All L-channel ICs │                        │  All R-channel ICs  │
    │  (Block A→B, L)    │                        │  (Block A→B, R)     │
    └────────────────────┘                        └─────────────────────┘
```

---

## 2. PCB Layer Count

| Board | Layers | Rationale |
|---|---|---|
| Control board | 2-layer | No analog ICs; only jack/pot/switch routing to connector. 2-layer FR4 1.2 mm sufficient. |
| Utility board | **4-layer** | THAT340 expo converters are extremely noise-sensitive. Power + GND planes under expo area are essential. 60+ mod bus signals running in parallel benefit from reference plane between layers. Stack: Signal / GND / PWR / Signal. |
| Left audio board | **4-layer** | APF chains (9× LM13700) have long feedback traces; distortion chains have hot signals. Solid GND plane (L2) dramatically improves decoupling and shielding. Stack: Signal / GND / PWR / Signal. |
| Right audio board | **4-layer** | Same reasons as left audio board. Mirror of left. |

Standard JLCPCB 4-layer stack: 1.6 mm, 0.2 mm prepreg between L1–L2 and L3–L4.
Power plane (L3) carries +12 V and −12 V as separate copper pours; GND is full pour on L2.

---

## 3. Board Inventories

### 3.1 Control Board

**Purpose**: Panel interface only. No signal processing.

**Estimated size**: 203 mm × 80 mm (40 HP × 80 mm), 1.2 mm thick.
All components are through-hole (Thonkiconn jacks, pot hardware, switches).

| Category | Items | Count |
|---|---|---|
| Audio I/O jacks | L IN, R IN, ENV OUT L, ENV OUT R, BAND OUT L, BAND OUT R, LEFT OUT, RIGHT OUT | 8 |
| CV override jacks | BYPASS CV, OFFSET CV, FB DIST BLEND CV, VCA AMT CV, LP1 CUTOFF CV, LP1 RES CV, LP2 CUTOFF CV, LP2 RES CV, HP CUTOFF CV, HP RES CV, FREQ 1/2/3 CV, FB 1/2/3 CV, DRIVE 1/2/3 CV | 19 |
| Main panel knobs (9 mm pots) | AMOUNT, OFFSET, WIDTH, COMB BYPASS, MASTER OFFSET (XL), POLARITY, FB DIST BLEND, FREQ 1/2/3 (XL), FB 1/2/3 (large), DRIVE 1/2/3 (large), CUTOFF LP1 (large), STEREO SPREAD OFFSET, RESONANCE LP1, CUTOFF LP2 (slider), RESONANCE LP2, CUTOFF HP (slider), RESONANCE HP | ~25 |
| Attenuverter knobs (9 mm bipolar pots) | One per CV override jack (19 destinations) + AMT (VCA) | 20 |
| Switches | GAIN (horizontal 2-pos sub-mini), MODE 1/2/3 (3-pos sub-mini) | 4 |
| LEDs | (none on control board; power LED on utility board) | 0 |

**Connects to**: Utility board via CN_CTRL_1 + CN_CTRL_2.
No BAT54 protection here — protection lives on utility board immediately after the jack signals arrive.

---

### 3.2 Utility / HW-Connect Board

**Purpose**: Power entry, power filtering, mod bus processing and distribution,
all expo converters, shared CONTROL-section processing (FB DIST BLEND, COMB BYPASS,
WIDTH, POLARITY).

**Estimated size**: 120 mm × 100 mm, 4-layer.

| Category | ICs | Notes |
|---|---|---|
| Eurorack power entry | — | 16-pin IDC header, 2× BAT85 Schottky (reverse-pol), 2× 47 µF bulk, 6× 100 nF decoupling, 2× ferrite bead (BLM18AG601, 0603) |
| Power LED | — | Red LED + 1 kΩ series on +12 V |
| Audio jack input buffers (protection) | TL074 ×2 | Buffered after BAT54+100Ω at each audio jack: L IN, R IN (+ ENV, BAND, LEFT, RIGHT jacks are outputs — protection not needed there) |
| Mod bus processor | TL072 ×1 | AMOUNT scaling summer + OFFSET adder; one op-amp per function |
| Mod destination attenuverters | TL074 ×5 | 19 destinations × attenuverter buffer (one TL072 half per destination; ~10 halves → 5 TL074); BAT54+100Ω at each override jack input |
| APF expo converters (groups 1, 2, 3) | THAT340 ×3, TL072 ×3 | One THAT340 per APF group; each drives both L and R audio boards; TL072 for Vbe reference voltage and temperature compensation per converter |
| LP1 expo converter | THAT340 ×1, TL072 ×1 | THAT340 Q1 = L channel base current; Q2 = R channel (with V_spread added at summing node before Q2 base); STEREO SPREAD OFFSET pot wiper routes here via CN_CTRL |
| LP2 expo converter | THAT340 ×1, TL072 ×1 | Both LP2 channels share one THAT340 |
| HP expo converter | THAT340 ×1, TL072 ×1 | Both HP channels share one THAT340 |
| FB DIST BLEND crossfade | TL072 ×1 | Receives post-dist taps from L+R audio boards (3 chains × 2 channels = 6 signals); crossfades with internal APF feedback; output routes back to L+R audio boards |
| COMB BYPASS VCA | TL072 ×1 | Buffer/level set for VCA_CB control voltage driving Block 3 COMB BYPASS VCA cells on each audio board |
| WIDTH + POLARITY | TL074 ×1 | Pan/polarity processing for CONTROL section; output goes to L+R audio boards |
| **Total on utility board** | **~17 ICs** | (THAT340 ×6, TL072 ×10, TL074 ×6) |

**Connects to**: Control board (CN_CTRL_1, CN_CTRL_2), Left audio board (CN_UTIL_L), Right audio board (CN_UTIL_R), Eurorack bus.

---

### 3.3 Left Audio Board

**Purpose**: Complete left-channel signal chain from Block A through Block B.

**Estimated size**: 120 mm × 110 mm, 4-layer.
Densest board in the system — Block 3 APF chains dominate the component count.

| Block | Key ICs | Count |
|---|---|---|
| Block A L: Input buffer | TL072 (half A + BAT54 clamp) | TL072 ×1 |
| Block 1 L: Pre-gain | TL072 (half B), gain switch resistors | (shared with Block A IC) |
| Block 2 L: Envelope follower | TL074 ×1 (full-wave rectifier + peak detector), TL072 ×1 (buffer + MOD SEL diode-OR) | TL074 ×1, TL072 ×1 |
| Block 3 L: APF chains 1+2+3 | LM13700M ×9 (6 stages × 3 chains; 2 LM13700 cells per stage, 1 stage = half a LM13700 dual; 6 stages ÷ 2 per IC × 3 chains = 9 ICs), TL072 ×9 (stage buffers + comb tap) | LM13700 ×9, TL072 ×9 |
| Block 4 L: Distortion | TL072 ×3 (soft clip, 1 per chain), TL072 ×3 (hard clip, 1 per chain), TL074 ×3 (wavefold, 2-stage per chain), TL074 ×1 (sum amp) | TL072 ×6, TL074 ×4 |
| Block VCA L: Pre-LP1 VCA signal path | V2164-A cell 3 (VCA L) — shares IC with LP1 L | (shared with LP1 below) |
| Block 5 L: LP Filter 1 | LM13700M ×1 (2 OTA integrators), TL074 ×1 (SVF sum amp + buffers), **V2164-A** ×1 (cell 1 = LP1 L Q; cell 3 = VCA L signal path) | LM13700 ×1, TL074 ×1, V2164 ×1 |
| Block 6 L: LP Filter 2 | LM13700M ×1, TL074 ×1, **V2164-C** cell 1 (LP2 L Q) | LM13700 ×1, TL074 ×1, V2164 ×1 |
| Block 7 L: HP Filter | LM13700M ×1 (or equivalent OTA), TL072 ×1, **V2164-C** cell 2 (HP L Q) | LM13700 ×1, TL072 ×1, (shared V2164-C) |
| Block B L: Output buffers | TL072 ×1 (BAND OUT L + LEFT OUT, two halves) | TL072 ×1 |
| **Left board total** | | **LM13700 ×12, TL072 ×22, TL074 ×7, V2164 ×2** |

V2164 allocation on Left audio board:
- **V2164-A**: Cell 1 = LP1 L Q feedback; Cell 3 = Block VCA L signal; Cells 2+4 = spare
- **V2164-C**: Cell 1 = LP2 L Q feedback; Cell 2 = HP L Q feedback; Cells 3+4 = spare

---

### 3.4 Right Audio Board

**Purpose**: Mirror of left audio board for right channel.

Identical IC inventory to left audio board. Component placement is a near-mirror of the left
board layout (not electrically identical due to STEREO SPREAD OFFSET, which adds V_spread
to R channel only at the expo converter — this is handled on the utility board before the
expo output arrives, so the R audio board receives a pre-offset I_abc signal and its LP1
circuit is structurally identical to L).

V2164 allocation on Right audio board:
- **V2164-B**: Cell 1 = LP1 R Q feedback; Cell 3 = Block VCA R signal; Cells 2+4 = spare
- **V2164-D**: Cell 1 = LP2 R Q feedback; Cell 2 = HP R Q feedback; Cells 3+4 = spare

---

## 4. V2164 Full Allocation Table

Total V2164 ICs: **4** (2 per audio board).

| IC | Board | Cell 1 | Cell 2 | Cell 3 | Cell 4 |
|---|---|---|---|---|---|
| V2164-A | Left audio | LP1 L Q (resonance feedback) | spare | Block VCA L signal path | spare |
| V2164-B | Right audio | LP1 R Q (resonance feedback) | spare | Block VCA R signal path | spare |
| V2164-C | Left audio | LP2 L Q (resonance feedback) | HP L Q (resonance feedback) | spare | spare |
| V2164-D | Right audio | LP2 R Q (resonance feedback) | HP R Q (resonance feedback) | spare | spare |

**Design note**: The previous spec had 2× V2164 total with L+R channels sharing one IC
(cells 1+2 = LP1 L+R Q; cells 3+4 = VCA L+R). That allocation mixes channels across one IC,
which is incompatible with the L/R audio board split. The 4× V2164 allocation here keeps all
audio signal paths on their respective channel board. Control voltages (Q drive, VCA level CV)
arrive from the utility board via CN_UTIL_L / CN_UTIL_R — no audio signal crosses the
board boundary.

---

## 5. Connector Strategy

All connectors are 2.54 mm pitch shrouded IDC headers on the utility board side and matching
IDC ribbon cable assemblies. Right-angle header on the audio boards (they hang perpendicular
to the panel). Straight header on the utility board (faces outward to the L/R audio boards).

### CN_CTRL_1 and CN_CTRL_2 (Control board ↔ Utility board)

Two 34-pin IDC connectors (2×17, shrouded) = 68 total pins.
Ribbon cables run from control board (back of panel) down to utility board (hanging behind).

**CN_CTRL_1 — Power + Audio I/O + Override CV jacks (34 pins)**

| Pins | Signal | Direction | Notes |
|---|---|---|---|
| 1–2 | +12 V | → ctrl | For pot reference rails (bipolar attenuverter ends) |
| 3–4 | −12 V | → ctrl | |
| 5–6 | GND ×2 | — | Signal ground |
| 7 | L IN tip | ← ctrl | Audio input L (from jack to utility buffer) |
| 8 | R IN tip | ← ctrl | Audio input R |
| 9 | ENV OUT L | → ctrl | Envelope follower L output (to panel jack) |
| 10 | ENV OUT R | → ctrl | Envelope follower R output |
| 11 | BAND OUT L | → ctrl | LP1 L output (to panel BAND OUT L jack) |
| 12 | BAND OUT R | → ctrl | LP1 R output |
| 13 | LEFT OUT | → ctrl | Main stereo L output (to panel LEFT jack) |
| 14 | RIGHT OUT | → ctrl | Main stereo R output |
| 15–27 | Override CV jacks 1–13 (tips) | ← ctrl | Mod destination override jack tips (BYPASS, OFFSET, FB DIST BLEND, VCA AMT, LP1 CUTOFF, LP1 RES, LP2 CUTOFF, LP2 RES, HP CUTOFF, HP RES, FREQ 1, FREQ 2, FREQ 3) |
| 28–34 | Override CV jacks 14–19 + spare (tips) | ← ctrl | FB 1, FB 2, FB 3, DRIVE 1, DRIVE 2, DRIVE 3 override jacks + 1 spare |

**CN_CTRL_2 — Panel pot wipers + switch positions (34 pins)**

| Pins | Signal | Direction | Notes |
|---|---|---|---|
| 1–2 | GND ×2 | — | Wiper return ground |
| 3–4 | +12 V, −12 V | → ctrl | Bipolar pot reference rails |
| 5 | GAIN switch pos | ← ctrl | 1× or 5× switch position (logic level) |
| 6–8 | MODE 1/2/3 switch pos | ← ctrl | 3-pos switch per distortion chain |
| 9–28 | Attenuverter wipers ×19 + AMT wiper | ← ctrl | One wiper per mod destination attenuverter knob (19) + VCA AMT (1) = 20 wipers |
| 29 | AMOUNT wiper | ← ctrl | Mod bus AMOUNT knob |
| 30 | OFFSET wiper | ← ctrl | Mod bus OFFSET knob |
| 31 | STEREO SPREAD OFFSET wiper | ← ctrl | LP1 R spread; routes to utility board LP1 expo summing node |
| 32–34 | spare | — | |

---

### CN_UTIL_L (Utility board ↔ Left audio board)

One 34-pin IDC connector (2×17).

| Pins | Signal | Direction | Notes |
|---|---|---|---|
| 1–2 | +12 V | → L audio | |
| 3–4 | −12 V | → L audio | |
| 5–6 | GND ×2 | — | |
| 7 | L IN buffered | → L audio | L audio input (post utility-board buffer) |
| 8 | ENV OUT L | ← L audio | Envelope follower L output → to utility board → CN_CTRL_1 |
| 9 | BAND OUT L | ← L audio | LP1 L output → to utility board → CN_CTRL_1 |
| 10 | LEFT OUT | ← L audio | HP L output → to utility board → CN_CTRL_1 |
| 11 | APF FREQ 1 expo out | → L audio | I_abc for APF group 1 L (expo current from THAT340-1) |
| 12 | APF FREQ 2 expo out | → L audio | APF group 2 L |
| 13 | APF FREQ 3 expo out | → L audio | APF group 3 L |
| 14 | LP1 L expo out | → L audio | I_abc for LP1 L integrators (from THAT340-LP1 Q1) |
| 15 | LP2 L expo out | → L audio | I_abc for LP2 L |
| 16 | HP L expo out | → L audio | I_abc for HP L |
| 17 | LP1 CUTOFF CV | → L audio | Scaled CV after attenuverter (summing node input) |
| 18 | LP1 RES Q CV | → L audio | V2164-A cell 1 control voltage |
| 19 | LP2 CUTOFF CV | → L audio | |
| 20 | LP2 RES Q CV | → L audio | V2164-C cell 1 control voltage |
| 21 | HP CUTOFF CV | → L audio | |
| 22 | HP RES Q CV | → L audio | V2164-C cell 2 control voltage |
| 23 | VCA Level CV | → L audio | V2164-A cell 3 control voltage |
| 24 | COMB BYPASS CV | → L audio | Block 3 COMB BYPASS VCA control (each APF chain) |
| 25 | APF FB 1 CV | → L audio | Feedback depth CV for APF chain 1 |
| 26 | APF FB 2 CV | → L audio | |
| 27 | APF FB 3 CV | → L audio | |
| 28 | DRIVE 1 CV | → L audio | Distortion chain 1 drive CV |
| 29 | DRIVE 2 CV | → L audio | |
| 30 | DRIVE 3 CV | → L audio | |
| 31 | Post-dist tap L chain 1 | ← L audio | Post-dist signal → utility board FB DIST BLEND crossfade |
| 32 | Post-dist tap L chain 2 | ← L audio | |
| 33 | Post-dist tap L chain 3 | ← L audio | |
| 34 | FB DIST BLEND out (to L APF) | → L audio | Crossfaded feedback signal back to Block 3 L |

---

### CN_UTIL_R (Utility board ↔ Right audio board)

Mirror of CN_UTIL_L with R-channel signals.

Key difference: LP1 R expo out (pin 14 equivalent) carries the I_abc from THAT340-LP1 Q2,
which has V_spread already summed into its base voltage on the utility board. The R audio
board LP1 circuit is structurally identical to the L board; the STEREO SPREAD OFFSET
is transparent to the R audio board.

Pin mapping: identical structure to CN_UTIL_L with all "L" signal names replaced by "R"
and V2164-A/C references replaced by V2164-B/D.

---

## 6. Ground Plane Strategy

- **Single analog GND** on each board: full copper pour on L2 (inner layer 1) of 4-layer
  audio and utility boards. GND on bottom copper of 2-layer control board.
- **Star ground point**: all board GNDs converge at a single solder star on the utility board,
  located within 10 mm of the Eurorack power header GND pins. GND returns from CN_UTIL_L,
  CN_UTIL_R, and CN_CTRL connector shells tie here, not daisy-chained.
- **Chassis ground**: Thonkiconn jack sleeve grounds on the control board connect to a chassis
  ground point (single solder jumper JP_CHASSIS). JP_CHASSIS ties to signal GND at one point
  on the utility board via CN_CTRL. This chassis ↔ signal ground connection is made in only
  one place; opening JP_CHASSIS allows floating chassis ground for noise troubleshooting.
- **No split ground plane**: POGO is fully analog. No digital signals are present; no split
  plane is needed or beneficial.
- **APF expo converters**: place THAT340 group at least 15 mm from power entry ferrite beads
  and at least 10 mm from power header. The expo area on the utility board should have an
  uninterrupted GND pour on L2 directly beneath all THAT340 footprints.

---

## 7. Placement Rules

### All boards
1. Decoupling caps (100 nF ceramic, 0603) within 1 mm of each IC supply pin — place before
   routing power traces.
2. Ferrite beads and 47 µF bulk caps at Eurorack power header (utility board only); route
   power from there outward.

### Utility board
3. THAT340 group: cluster all 6 THAT340 ICs in the same thermal zone, center of board, away
   from the power entry corner. Matching across expo converters is improved by common thermal.
4. Mod bus attenuverter ICs (TL074 ×5): place in a row adjacent to the CN_CTRL connectors
   (short traces from override jack pins to attenuverter inputs).
5. FB DIST BLEND crossfade op-amp: place adjacent to CN_UTIL_L and CN_UTIL_R connectors
   (post-dist tap signals arrive here; crossfaded result routes back on same connectors).

### Left and Right audio boards
6. Block 3 APF chains: arrange in 3 columns (one column per chain, left-to-right = chains 1–3).
   Within each column: LM13700 stages in series order top-to-bottom (stage 1 nearest input,
   stage 6 nearest output). This minimizes feedback trace length (critical for APF stability).
7. Post-distortion tap traces (Block 4 output to board edge CN_UTIL connector): route on L4
   (bottom signal layer) with adjacent GND pour to shield from APF feedback traces.
8. V2164 ICs: place adjacent to their primary filter block (V2164-A near LP1 OTAs; V2164-C
   near LP2/HP OTA cluster). Keep control voltage traces short.
9. Trim pots: place on the top edge of each audio board (pins 1 and 3 accessible by
   screwdriver without removing the board).

---

## 8. Physical Stack and Assembly

```
Panel (aluminum or FR4, 40 HP)
  │  (jack nuts + pot hardware secure control board to panel)
  ▼
Control board (1.2 mm, 2-layer, ~203 mm × 80 mm)
  │  2× ribbon cables (CN_CTRL_1, CN_CTRL_2)
  ▼
Utility board (1.6 mm, 4-layer, ~120 mm × 100 mm)
  Mounted on M3 standoffs from control board PCB edge (or panel rail)
  │                         │
  │ CN_UTIL_L               │ CN_UTIL_R
  ▼                         ▼
Left audio board        Right audio board
(1.6 mm, 4-layer,       (1.6 mm, 4-layer,
 ~120 mm × 110 mm)       ~120 mm × 110 mm)
  Mounted perpendicular to utility board on right-angle headers
  (left board on left side; right board on right side)
```

Maximum depth from panel face to back of deepest board: estimate ~55 mm.
This fits within Doepfer A-100 case depth (35 mm busboard + component overhang) for
most cases; verify in a deep case (55+ mm) or use a right-angle Eurorack bus connector.

---

## 9. Reverse Polarity Protection

Placed on utility board, immediately after power header:
- +12 V rail: 1× BAT85 (SOD-80) Schottky in series, ~0.3 V forward drop
- −12 V rail: 1× BAT85 in series (reversed orientation)
- After protection: 47 µF electrolytic + 100 nF ceramic on each rail before ferrite bead
- Red power-indicator LED (2 mA) with 4.7 kΩ series resistor across post-protection +12 V

---

## 10. Inter-Board Signal Counts (Summary)

| Connector | Pins | Type |
|---|---|---|
| CN_CTRL_1 | 34 | 2.54 mm IDC, ribbon cable |
| CN_CTRL_2 | 34 | 2.54 mm IDC, ribbon cable |
| CN_UTIL_L | 34 | 2.54 mm IDC, ribbon cable |
| CN_UTIL_R | 34 | 2.54 mm IDC, ribbon cable |
| Eurorack bus | 16 | Shrouded IDC, standard Eurorack |

Total inter-board connections: **152 pins** across 5 connectors.

---

## 11. Power Budget Revision

With 4× V2164 (was 2×), and the board split now confirmed, the estimated power draw is:

| Board | +12 V est. | −12 V est. |
|---|---|---|
| Control board (passive) | 0 mA | 0 mA |
| Utility board (mod bus + expo + shared) | ~55 mA | ~55 mA |
| Left audio board (full L chain) | ~70 mA | ~70 mA |
| Right audio board (full R chain) | ~70 mA | ~70 mA |
| **Total** | **~195 mA** | **~195 mA** |

Measure actual draw during bring-up. 200 mA / rail is the target ceiling for a standard
Eurorack busboard slot.

Last updated: 2026-05-20
