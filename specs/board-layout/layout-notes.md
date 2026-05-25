# POGO Board Layout Notes

## Status
- Phase 5 (Board Layout): [x] complete — strategy + connector pinout

---

## 1. Board Split Decision: 3 Boards

POGO uses three PCBs. The split is driven by three constraints:
(a) panel controls and jacks require a panel-facing board that cannot also carry dense SMD
    circuitry due to depth and assembly access;
(b) all six expo converters (THAT340) feed both L and R audio paths and belong on a central
    board, not on one channel's audio board;
(c) the left and right audio signal chains are fully independent at the IC level and are
    combined onto a single board with strict routing discipline, saving one IDC ribbon
    interface and reducing total module depth by ~25 mm.

```
┌─────────────────────────────────────────────────────────────────┐
│  PANEL  (40 HP × 128.5 mm)                                      │
│  Control Board  (panel-mounted, 1.2 mm FR4, ~203 × 80 mm)      │
│    Jacks, pots, switches only — no signal processing ICs        │
└──────────────┬──────────────────────────────────────────────────┘
               │  CN_CTRL_1 (34-pin) + CN_CTRL_2 (40-pin) + CN_CTRL_3 (24-pin)
               │  (2.54 mm IDC ribbon cables — right-angle header on Control
               │   bottom edge; straight header on Utility top edge)
               │
    ┌──────────┴──────────────────────────────────────────────────┐
    │  Utility Board  (~200 × 80 mm, 4-layer, parallel to panel)  │
    │  Eurorack power, mod bus, expo converters, shared CVs       │
    │                                                              │
    │   STK_AUDIO_L zone (left ~100 mm)  STK_AUDIO_R zone (right ~100 mm)│
    └──────────────────────┬──────────────────────────────────────┘
                           │  STK_AUDIO_L + STK_AUDIO_R
                           │  (2× 40-pin stacking headers, face-to-face;
                           │   8 mm M3 standoffs at four corners)
    ┌──────────────────────┴──────────────────────────────────────┐
    │  Combined Audio Board  (~200 × 100 mm, 4-layer)             │
    │  ┌─────────────────────┬──┬──────────────────────────────┐  │
    │  │  L-channel (~96 mm) │4 │   R-channel (~96 mm)         │  │
    │  │  Block A→B, L side  │mm│   Block A→B, R side          │  │
    │  │                     │GN│                              │  │
    │  │                     │D │                              │  │
    │  └─────────────────────┴──┴──────────────────────────────┘  │
    │             center GND guard strip (all layers)              │
    └─────────────────────────────────────────────────────────────┘
```

**Depth from panel face:** ~30 mm total
(panel ~2 mm + Control 1.2 mm + ribbon gap ~10 mm + Utility 1.6 mm + stacking header 8 mm +
Audio 1.6 mm + Audio component bodies ~4 mm). Within Doepfer A-100 case depth for all
standard cases; no right-angle bus connector required.

---

## 2. PCB Layer Count

| Board | Layers | Rationale |
|---|---|---|
| Control board | 2-layer | No analog ICs; only jack/pot/switch routing to connector. 2-layer FR4 1.2 mm sufficient. |
| Utility board | **4-layer** | THAT340 expo converters are extremely noise-sensitive. Power + GND planes under expo area are essential. 60+ mod bus signals running in parallel benefit from reference plane between layers. Stack: Signal / GND / PWR / Signal. |
| Combined audio board | **4-layer** | APF chains (9× LM13700 per channel) have long feedback traces; distortion chains have hot signals. Solid GND plane (L2) dramatically improves decoupling and shielding. Also provides the ground reference for the 4 mm center GND guard strip separating L and R signal areas. Stack: Signal / GND / PWR / Signal. |

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
| Attenuverter knobs (9 mm bipolar pots) | One per mod destination (19 total; VCA AMT is destination #4, not a separate knob) | 19 |
| Switches | GAIN (2-pos horizontal sub-mini, SW1), MOD SRC (3-pos horizontal sub-mini, SW2), POLARITY (3-pos horizontal sub-mini, SW3), MODE (3-pos vertical sub-mini, SW4 — 1 shared switch for all 3 comb groups, per panel.svg) | 4 |
| LEDs | (none on control board; power LED on utility board) | 0 |

**Connects to**: Utility board via CN_CTRL_1 + CN_CTRL_2 + CN_CTRL_3.
No BAT54 protection here — protection lives on utility board immediately after the jack signals arrive.

---

### 3.2 Utility / HW-Connect Board

**Purpose**: Power entry, power filtering, mod bus processing and distribution,
all expo converters, shared CONTROL-section processing (FB DIST BLEND, COMB BYPASS,
WIDTH, POLARITY).

**Estimated size**: ~200 mm × 80 mm, 4-layer (full-width, matching Control board).

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

**Connects to**: Control board (CN_CTRL_1, CN_CTRL_2, CN_CTRL_3 via IDC ribbon), Combined audio board (STK_AUDIO_L + STK_AUDIO_R stacking headers), Eurorack bus.

---

### 3.3 Combined Audio Board

**Purpose**: Complete signal chain (Block A through Block B) for both L and R channels on a
single PCB. L-channel occupies the left half (~96 mm), R-channel occupies the right half
(~96 mm), separated by a 4 mm center GND guard strip (full copper pour on all layers, zero
signal traces).

**Estimated size**: ~200 mm × 100 mm, 4-layer.
Densest board in the system — Block 3 APF chains dominate component count per channel.

#### L-channel (left half)

| Block | Key ICs | Count |
|---|---|---|
| Block A L: Input buffer | LM4562 (half A + BAT54 clamp) | LM4562 ×1 |
| Block 1 L: Pre-gain | NE5532 (half B), gain switch resistors | NE5532 ×1 |
| Block 2 L: Envelope follower | TL074 ×1 (full-wave rectifier + peak detector), TL072 ×1 (buffer + MOD SEL diode-OR) | TL074 ×1, TL072 ×1 |
| Block 3 L: APF chains 1+2+3 | LM13700M ×9 (6 stages × 3 chains; 2 LM13700 cells per stage = 9 ICs), LM13700M ×1 (**LM13700_CB1** = COMB BYPASS VCA), TL072 ×9 (stage buffers + comb tap) | LM13700 ×10, TL072 ×9 |
| Block 4 L: Distortion | TL072 ×3 (soft clip), TL072 ×3 (hard clip), TL074 ×3 (wavefold), TL074 ×1 (sum amp) | TL072 ×6, TL074 ×4 |
| Block VCA L: Pre-LP1 VCA | **THAT_VCA_L** (THAT 2180, SOIC-8) — 1 per channel; no IC sharing | THAT 2180 ×1 |
| Block 5 L: LP Filter 1 | LM13700M ×1 (2 OTA integrators), TL074 ×1 (SVF sum amp + buffers), **IC_Q_AB_L** cell A (LP1 L Q; cell B = LP2 L Q) | LM13700 ×1, TL074 ×1 |
| Block 6 L: LP Filter 2 | LM13700M ×1, TL074 ×1, **IC_Q_AB_L** cell B (LP2 L Q — same IC as LP1 Q) | LM13700 ×1, TL074 ×1, (IC_Q_AB_L shared) |
| Block 7 L: HP Filter | LM13700M ×1 (2 OTA integrators), TL072 ×1, **IC_Q_C_L** cell A (HP L Q; cell B = spare) | LM13700 ×2, TL072 ×1 |
| Block B L: Output buffers | TL072 ×1 (BAND OUT L + LEFT OUT) | TL072 ×1 |
| **L-channel total** | | **LM13700 ×15, TL072 ×22, TL074 ×7, THAT 2180 ×1, LM4562 ×1, NE5532 ×1** |

LM13700 allocation, L-channel:
- **Block 3 APF ×9** + **LM13700_CB1 ×1** (COMB BYPASS VCA) = 10 for Block 3
- **LP1 integrators ×1** + **IC_Q_AB_L ×1** (LP1+LP2 Q shared) + **LP2 integrators ×1** = 3 for Blocks 5+6
- **HP integrators ×1** + **IC_Q_C_L ×1** (HP Q) = 2 for Block 7

LM13700 Q VCA allocation, L-channel:
- **IC_Q_AB_L**: Cell A = LP1 L Q feedback; Cell B = LP2 L Q feedback
- **IC_Q_C_L**: Cell A = HP L Q feedback; Cell B = spare

#### R-channel (right half)

Identical IC inventory to L-channel (**LM13700 ×15, TL072 ×22, TL074 ×7, THAT 2180 ×1,
LM4562 ×1, NE5532 ×1** — includes LM13700_CB2 COMB BYPASS VCA). Component placement mirrors
the L-channel layout. Not electrically identical: STEREO SPREAD OFFSET adds V_spread to the
R-channel LP1 expo converter on the utility board before the Iabc signal arrives, so the
R-channel LP1 circuit on the audio board is structurally identical to L.

LM13700 Q VCA allocation, R-channel:
- **IC_Q_AB_R**: Cell A = LP1 R Q feedback; Cell B = LP2 R Q feedback
- **IC_Q_C_R**: Cell A = HP R Q feedback; Cell B = spare

#### Center GND guard strip

A 4 mm wide strip runs the full 100 mm height of the board between the L and R signal areas.
All four copper layers carry a solid GND pour in this strip; no signal traces cross it.
This provides electromagnetic isolation between the two independent signal chains equivalent
to a 4 mm air gap shielded on all layers.

---

## 4. VCA / Q IC Allocation Table

V2164D has been **removed from the design** (specialty Eurorack-only sourcing). Replaced with:
- **THAT 2180** (SOIC-8): signal-path VCA in Block VCA — 1 per channel (Mouser stock)
- **LM13700** (SOIC-16): Q feedback OTA cells — already used throughout Block 3 APF

LM13700 Q VCA allocation: **4× LM13700** for Q control (2 per channel).

| IC | Board | Cell A | Cell B |
|---|---|---|---|
| IC_Q_AB_L | Combined audio (L-channel) | LP1 L Q (resonance BP feedback) | LP2 L Q (resonance BP feedback) |
| IC_Q_AB_R | Combined audio (R-channel) | LP1 R Q (resonance BP feedback) | LP2 R Q (resonance BP feedback) |
| IC_Q_C_L | Combined audio (L-channel) | HP L Q (resonance BP feedback) | spare |
| IC_Q_C_R | Combined audio (R-channel) | HP R Q (resonance BP feedback) | spare |

THAT 2180 allocation: **2× THAT 2180**, one per channel.

| IC | Location | Function |
|---|---|---|
| THAT_VCA_L | Combined audio (L-channel) | Block VCA L signal-path VCA (GAIN pin current-controlled) |
| THAT_VCA_R | Combined audio (R-channel) | Block VCA R signal-path VCA (GAIN pin current-controlled) |

All audio signal paths remain within their respective channel half of the combined audio board.
No audio signal crosses the center GND guard strip. Q control Iabc and VCA level CV arrive
from the utility board via STK_AUDIO_L / STK_AUDIO_R stacking headers.

---

## 5. Connector Strategy

Two connection technologies are used, chosen to match the physical constraints of each interface:

**Control → Utility (IDC ribbon cables):** The back face of the Control board is crowded with
Thonkiconn jack bodies (~10 mm protrusion) and pot hardware — face-to-face stacking is not
feasible. Right-angle IDC headers on the Control board bottom edge + straight IDC headers on
the Utility board top edge + short ribbon cable (~100 mm) provide the flexible interface.
Three cables: CN_CTRL_1 (34-pin), CN_CTRL_2 (40-pin), CN_CTRL_3 (24-pin).

**Utility → Audio (stacking headers, face-to-face):** The Utility board's back face and the
Combined audio board's front face are both SMD populations with maximum component height ~4 mm
(SOIC ICs). 8 mm M3 standoffs at the four corners give adequate clearance. Straight 2×20
2.54 mm pin headers on the Utility back face; matching socket headers on the Audio top face.
Two zones: STK_AUDIO_L (left ~100 mm, L-channel signals) and STK_AUDIO_R (right ~100 mm,
R-channel signals).

### CN_CTRL_1 and CN_CTRL_2 (Control board ↔ Utility board)

CN_CTRL_1 is 34-pin (2×17); CN_CTRL_2 is 40-pin (2×20) — 74 total pins across these two connectors.
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
| 28–33 | Override CV jacks 14–19 (tips) | ← ctrl | FB 1, FB 2, FB 3, DRIVE 1, DRIVE 2, DRIVE 3 override jacks |
| 34 | MOD IN tip | ← ctrl | Primary mod source jack tip → utility board mod bus processor input |

**CN_CTRL_2 — Panel pot wipers + switch position outputs (40 pins, 2×20)**

| Pins | Signal | Direction | Notes |
|---|---|---|---|
| 1–2 | GND ×2 | — | Wiper return ground |
| 3–4 | +12 V, −12 V | → ctrl | Bipolar pot reference rails |
| 5 | GAIN switch pos | ← ctrl | SW1 common output; 1× position → GND on ctrl board, 5× position → pulled high |
| 6 | MODE SFT pos | ← ctrl | SW4 pos-1 output (Soft Clip); high when MODE = SFT; utility board decodes which of pins 6–8 is high |
| 7 | MODE HRD pos | ← ctrl | SW4 pos-2 output (Hard Clip) |
| 8 | MODE WFD pos | ← ctrl | SW4 pos-3 output (Wavefold) |
| 9–27 | Attenuverter wipers ×19 | ← ctrl | One wiper per mod destination (19 total). Order: BYPASS, MASTER OFFSET, FB DIST BLEND, VCA AMT, LP1 CUT, LP1 RES, LP2 CUT, LP2 RES, HP CUT, HP RES, FREQ1, FREQ2, FREQ3, FB1, FB2, FB3, DRIVE1, DRIVE2, DRIVE3 |
| 28 | spare | — | Previously described as "VCA AMT wiper" — VCA AMT IS destination #4, already on pin 12 above |
| 29 | AMOUNT wiper | ← ctrl | Mod bus AMOUNT knob |
| 30 | OFFSET wiper | ← ctrl | Mod bus OFFSET knob |
| 31 | STEREO SPREAD OFFSET wiper | ← ctrl | LP1 R spread; routes to utility board LP1 expo summing node |
| 32 | MOD SRC pos-1 (L) | ← ctrl | SW2 pos-1 output; high when MOD SRC = L ENV |
| 33 | MOD SRC pos-2 (MAX) | ← ctrl | SW2 pos-2 output; high when MOD SRC = MAX(L,R) |
| 34 | MOD SRC pos-3 (AVG) | ← ctrl | SW2 pos-3 output; high when MOD SRC = AVG(L,R) |
| 35 | POLARITY pos-1 (POS) | ← ctrl | SW3 pos-1 output; high when POLARITY = Positive |
| 36 | POLARITY pos-2 (OFF) | ← ctrl | SW3 pos-2 output; high when POLARITY = Off |
| 37 | POLARITY pos-3 (NEG) | ← ctrl | SW3 pos-3 output; high when POLARITY = Negative |
| 38 | ENV NORM return | → ctrl | Selected ENV output from utility board → MOD IN jack SW lug (J9 normalling). When no cable in J9, tip = SW = this ENV signal, normalizing MOD IN to ENV. |
| 39 | MOD BUS NORM | → ctrl | Processed Mod Bus output (post AMOUNT/OFFSET) from utility board → all 19 CV override jack SW lugs (wired together on control board PCB). When no cable in any CV jack, its tip = SW = the Mod Bus, normalizing that attenuverter input to the Mod Bus. |
| 40 | spare | — | |

**Switch commons on control board**: All four switch commons tie directly to +12V on the
control board (no connector pin needed). Each position pin is high (+12V) when selected,
while the other positions of the same switch are open (float or are pulled low on the
utility board). The utility board decodes which of the three position pins is high.

**MODE switch**: panel.svg (authoritative) shows **one** shared 3-pos MODE switch (SW4) for
all three distortion chains simultaneously. All three comb groups always use the same
distortion mode. CN_CTRL_2 pins 6–8 carry the single switch's position outputs (SFT / HRD / WFD).

**MOD IN normalling (J9)**: Tip → CN_CTRL_1 pin 34 → utility board mod bus processor input.
SW lug → CN_CTRL_2 pin 38 (ENV NORM return). When no cable: tip = SW = selected ENV, so
the ENV signal drives the mod bus input. When cable plugged: tip = cable, SW disconnects.

**CV override jack normalling (J10–J28)**: All 19 SW lugs are wired together on the control
board PCB as one net (NET_MODBUS_NORM). That net connects to CN_CTRL_2 pin 39, driven by the
utility board's processed Mod Bus output (buffered op-amp output, low impedance). When no cable
is plugged into any CV override jack, its tip = SW = Mod Bus, normalizing the attenuverter
input to the Mod Bus. The utility board buffer comfortably drives all 19 high-impedance
attenuverter inputs simultaneously (~5 kΩ total load at 19 × 100 kΩ pots in parallel).

---

### CN_CTRL_3 (Control board ↔ Utility board — main parameter wipers)

**24-pin IDC connector (2×12).** Carries the 21 main parameter pot/slider wipers that do not
fit in CN_CTRL_1 or CN_CTRL_2. These are the "raw" panel position signals for the signal-
processing parameters; the utility board and audio boards use them to set filter cutoff,
feedback depth, etc.

**Status: finalized — implemented in `kicad/pogo-control-board.kicad_sch` and verified by `kicad/validate_schematic.py` checks 9–11 (CN3 pinout, 24 pin assignments).**

| Pins | Signal | Direction | Notes |
|---|---|---|---|
| 1–2 | GND ×2 | — | Wiper return ground |
| 3 | ATTACK wiper | ← ctrl | RV1; 0–+12 V → utility board envelope follower τ_attack |
| 4 | RELEASE wiper | ← ctrl | RV2; 0–+12 V → utility board envelope follower τ_release |
| 5 | COMB BYPASS wiper | ← ctrl | RV5; 0–+12 V → utility board COMB BYPASS VCA level |
| 6 | WIDTH wiper | ← ctrl | RV6; bipolar → utility board APF R-channel freq offset |
| 7 | MASTER OFFSET wiper | ← ctrl | RV7; bipolar → utility board APF global freq offset |
| 8 | FB DIST BLEND wiper | ← ctrl | RV8; 0–+12 V → utility board FB DIST BLEND crossfade |
| 9 | FREQ 1 wiper | ← ctrl | RV12; bipolar → utility board APF group 1 expo converter |
| 10 | FREQ 2 wiper | ← ctrl | RV18; bipolar → APF group 2 expo converter |
| 11 | FREQ 3 wiper | ← ctrl | RV24; bipolar → APF group 3 expo converter |
| 12 | FB 1 wiper | ← ctrl | RV13; 0–+12 V → utility board APF FB1 CV |
| 13 | FB 2 wiper | ← ctrl | RV19 |
| 14 | FB 3 wiper | ← ctrl | RV25 |
| 15 | DRIVE 1 wiper | ← ctrl | RV14; 0–+12 V → audio board Block 4 chain 1 |
| 16 | DRIVE 2 wiper | ← ctrl | RV20 |
| 17 | DRIVE 3 wiper | ← ctrl | RV26 |
| 18 | LP1 CUTOFF wiper | ← ctrl | RV31; bipolar → utility board LP1 expo converter |
| 19 | LP1 RESONANCE wiper | ← ctrl | RV33; 0–+12 V → utility board LP1 Q CV |
| 20 | LP2 CUTOFF wiper | ← ctrl | RV36 (ALPS slider); bipolar → utility board LP2 expo converter |
| 21 | LP2 RESONANCE wiper | ← ctrl | RV37; 0–+12 V → utility board LP2 Q CV |
| 22 | HP CUTOFF wiper | ← ctrl | RV40 (ALPS slider); bipolar → utility board HP expo converter |
| 23 | HP RESONANCE wiper | ← ctrl | RV41; 0–+12 V → utility board HP Q CV |
| 24 | spare | — | |

**Connector spec**: 2.54 mm pitch shrouded IDC header (2×12), same series as CN_CTRL_1/2.
Standard parts: Amphenol T813, TE 1-103976-4, or equivalent.

---

### STK_AUDIO_L (Utility board ↔ Combined audio board, L-channel zone)

**40-pin stacking header (2×20).** Straight 2.54 mm pin header on Utility board back face
(left zone, ~100 mm from left edge); matching socket header on Combined audio board top face.
GND guard pins retained from original design for I_abc signal integrity (noise-audit.md H2).

| Pins | Signal | Direction | Notes |
|---|---|---|---|
| 1–2 | +12 V | → L audio | Power |
| 3–4 | −12 V | → L audio | Power |
| 5–6 | GND ×2 | — | Star-ground return for power |
| 7 | L IN buffered | → L audio | L audio input (post utility-board buffer) |
| 8 | ENV OUT L | ← L audio | Envelope follower L output → utility board → CN_CTRL_1 |
| 9 | BAND OUT L | ← L audio | LP1 L output → utility board → CN_CTRL_1 |
| 10 | LEFT OUT | ← L audio | HP L output → utility board → CN_CTRL_1 |
| 11 | **GND guard** | — | Ground return adjacent to I_abc group; reduces capacitive coupling onto expo current lines |
| 12 | APF FREQ 1 expo out | → L audio | I_abc for APF group 1 L (from THAT340-1) |
| 13 | APF FREQ 2 expo out | → L audio | I_abc for APF group 2 L |
| 14 | **GND guard** | — | |
| 15 | APF FREQ 3 expo out | → L audio | I_abc for APF group 3 L |
| 16 | LP1 L expo out | → L audio | I_abc for LP1 L integrators (from THAT340-LP1 Q1) |
| 17 | **GND guard** | — | |
| 18 | LP2 L expo out | → L audio | I_abc for LP2 L |
| 19 | HP L expo out | → L audio | I_abc for HP L |
| 20 | LP1 CUTOFF CV | → L audio | Scaled CV after attenuverter (summing node input) |
| 21 | LP1 RES Q CV | → L audio | IC_Q_AB_L cell A Iabc drive |
| 22 | LP2 CUTOFF CV | → L audio | |
| 23 | LP2 RES Q CV | → L audio | IC_Q_AB_L cell B Iabc drive |
| 24 | HP CUTOFF CV | → L audio | |
| 25 | HP RES Q CV | → L audio | IC_Q_C_L cell A Iabc drive |
| 26 | VCA Level CV | → L audio | THAT_VCA_L GAIN pin drive (via R_gain) |
| 27 | COMB BYPASS CV | → L audio | Block 3 COMB BYPASS VCA control |
| 28 | APF FB 1 CV | → L audio | Feedback depth CV for APF chain 1 |
| 29 | APF FB 2 CV | → L audio | |
| 30 | APF FB 3 CV | → L audio | |
| 31 | DRIVE 1 CV | → L audio | Distortion chain 1 drive CV |
| 32 | DRIVE 2 CV | → L audio | |
| 33 | DRIVE 3 CV | → L audio | |
| 34 | **GND** | — | Ground return adjacent to post-dist tap group |
| 35 | Post-dist tap L chain 1 | ← L audio | Post-dist audio → utility board FB DIST BLEND. Add 100 pF C0G to GND at utility board entry (EMI only; do NOT use 100 nF — audio signal) |
| 36 | Post-dist tap L chain 2 | ← L audio | Same |
| 37 | Post-dist tap L chain 3 | ← L audio | Same |
| 38 | FB DIST BLEND out (to L APF) | → L audio | Crossfaded feedback → Block 3 L. Add 100 pF C0G to GND at audio board entry |
| 39–40 | spare | — | |

**I_abc group routing note:** Add 10 nF C0G 0402 bypass cap from each I_abc trace to GND
on the combined audio board immediately after the stacking header footprint (within 2 mm of pin).
See noise-audit.md H3. Combined with GND guard pins, these provide ~60 dB noise rejection
on expo current lines. Stacking headers have significantly lower inter-pin coupling than IDC
ribbon (no adjacent conductors running parallel over long lengths), further improving I_abc
signal integrity beyond the original IDC ribbon design.

**Post-dist tap note:** Pins 35–37 carry full-bandwidth audio (up to 20 kHz). The 100 pF
bypass caps at the utility board entry suppress EMI above ~1 GHz without affecting audio.
Do NOT substitute 100 nF — that would roll off at 16 kHz at 100 Ω source impedance. See
noise-audit.md H6.

---

### STK_AUDIO_R (Utility board ↔ Combined audio board, R-channel zone)

**40-pin stacking header (2×20).** Mirror of STK_AUDIO_L with R-channel signals.
Straight 2.54 mm pin header on Utility board back face (right zone); matching socket header
on Combined audio board top face (right half).

Key difference: LP1 R expo out (pin 16) carries the I_abc from THAT340-LP1 Q2, which has
V_spread already summed into its base voltage on the utility board. The R-channel LP1 circuit
on the combined audio board is structurally identical to L; STEREO SPREAD OFFSET is
transparent to the R-channel circuitry.

Pin mapping: identical structure to STK_AUDIO_L with all "L" signal names replaced by "R"
and IC_Q_AB_L/IC_Q_C_L references replaced by IC_Q_AB_R/IC_Q_C_R.

---

## 6. Ground Plane Strategy

- **Single analog GND** on each board: full copper pour on L2 (inner layer 1) of 4-layer
  audio and utility boards. GND on bottom copper of 2-layer control board.
- **Star ground point**: all board GNDs converge at a single solder star on the utility board,
  located within 10 mm of the Eurorack power header GND pins. GND returns from STK_AUDIO_L,
  STK_AUDIO_R stacking header GND pins, and CN_CTRL connector shells tie here, not daisy-chained.
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
5. FB DIST BLEND crossfade op-amp: place adjacent to STK_AUDIO_L and STK_AUDIO_R stacking
   header zones (post-dist tap signals arrive here; crossfaded result routes back on same headers).

### Combined audio board
6. Block 3 APF chains: within each channel half, arrange in 3 columns (chains 1–3).
   Within each column: LM13700 stages in series order top-to-bottom (stage 1 nearest input,
   stage 6 nearest output). This minimizes feedback trace length (critical for APF stability).
   Mirror the column layout symmetrically between L and R halves across the center GND strip.
7. Post-distortion tap traces (Block 4 output to top-edge STK_AUDIO connector): route on L4
   (bottom signal layer) with adjacent GND pour to shield from APF feedback traces.
8. LM13700 Q VCA ICs (IC_Q_AB, IC_Q_C): place adjacent to their respective filter OTAs
   (IC_Q_AB near LP1+LP2 OTA cluster; IC_Q_C near HP OTAs). Keep Iabc drive traces short.
   THAT 2180 VCA: place between Block 4 distortion output and LP1 OTA input.
9. Trim pots: place on the top edge of each audio board (pins 1 and 3 accessible by
   screwdriver without removing the board).
10. **L/R signal isolation rule (M1):** The center GND guard strip provides primary L/R
    isolation. Within each channel half, APF chain signal traces must maintain ≥3 mm separation
    from the nearest traces in the other channel's half. No signal trace crosses the center strip.
    Prefer routing L-channel signals on L1 (top) and R-channel signals on L4 (bottom) where
    traces from both halves approach the center — the L2 GND plane then acts as an additional
    inter-channel shield. Applies to all 36 LM13700 signal nodes (18 per channel) and TL072
    APF amp outputs. See noise-audit.md M1.
11. **OTA HF suppression cap placement rule (M4):** The 22 pF C0G HF-suppression cap at each
    LM13700 OTA output pin (pin 4 per cell) must be placed within 1 mm of the pin, with the
    GND via on the cap's second pad. Do not route through any shared trace before the cap.
    Series inductance (~5 nH/cm) on a 5 mm trace resonates with 22 pF at ~680 MHz, worsening
    HF behavior. Total trace length OTA pin → cap pad: ≤1 mm. See noise-audit.md M4.
12. **THAT340 Kelvin ground for emitter bias resistors (M3):** Each THAT340 emitter bias
    resistor (R_e) ground return must connect via a **dedicated trace** (≥0.5 mm wide, ≤5 mm
    length) directly to the L2 GND plane via, not through any shared audio signal return trace.
    Audio return currents in a shared trace create I×R voltage across R_e, modulating the expo
    output (pitch modulation at audio frequency). See noise-audit.md M3.

### Utility board (additional to rules 3–5 above)
13. **THAT340 power island (H5):** Add a dedicated local pi-filter for the THAT340 cluster
    supply rails, separate from the main board power pour:
    - +12 V: [main plane] → [100 Ω 0603] → [10 µF electrolytic] → [100 nF ceramic] → THAT340 +VCC
    - −12 V: same structure
    The 100 Ω series resistance + 10 µF capacitor creates a lowpass at 159 Hz, attenuating
    100 Hz busboard ripple and HF switching noise before it reaches expo converters. Power drop:
    100 Ω × (6 THAT340 × 1 mA) = 0.6 V → THAT340 operates at 11.4 V (within spec, operates
    to 5 V minimum). Route THAT340 power island as an isolated copper island on L3 (power layer)
    connected to the main power pour only at the pi-filter input side. See noise-audit.md H5.
14. **I_abc bypass caps at audio board stacking header (H3):** On the combined audio board,
    place 10 nF C0G 0402 caps from each I_abc trace to GND immediately after the STK_AUDIO_L/R
    stacking header footprint (within 2 mm of each I_abc pin). Applies to pins 12, 13, 15, 16,
    18, 19 of STK_AUDIO_L and STK_AUDIO_R. Combined with GND guard pins (H2), these caps
    provide ~60 dB rejection of any noise on expo current lines. The stacking header design
    further reduces coupling vs. the original IDC ribbon cable. See noise-audit.md H3.

---

## 8. Physical Stack and Assembly

All three boards are **parallel to the panel face** — the stack grows in the depth direction.

```
Panel (aluminum or FR4, 40 HP)
  │  (jack nuts + pot hardware secure control board)
  ▼
Control board (1.2 mm, 2-layer, ~203 × 80 mm)
  Component bodies on back face: Thonkiconn jacks ~10 mm, pot hardware ~5 mm
  │
  │  3× IDC ribbon cables (~100 mm length)
  │  CN_CTRL_1 (34-pin) + CN_CTRL_2 (40-pin) + CN_CTRL_3 (24-pin)
  │  Right-angle IDC headers on Control board bottom-edge clear strip
  │  → Straight IDC headers on Utility board top edge
  │
  ▼ (~2 mm clearance after Thonkiconn bodies)
Utility board (1.6 mm, 4-layer, ~200 × 80 mm)
  Mounted on M3 standoffs from panel rail — independent of control board.
  SMD components on back face: max height ~4 mm (SOIC-16).
  STK_AUDIO_L (left zone) + STK_AUDIO_R (right zone) pin headers on back face.
  │
  │  2× 40-pin stacking headers (2×20, 2.54 mm, 8 mm standoff height)
  │  Face-to-face: Utility back face → Audio board top face
  │  M3 standoffs at four corners of combined audio board
  │
  ▼
Combined audio board (1.6 mm, 4-layer, ~200 × 100 mm)
  L-channel left half | 4 mm GND strip | R-channel right half
  SMD components on back face: max height ~4 mm.
```

**Depth calculation from panel face:**

| Layer | Thickness / Offset | Cumulative depth |
|---|---|---|
| Panel face | — | 0 mm |
| Control board back | 1.2 mm board + ~2 mm mounting offset | ~3 mm |
| Thonkiconn body tip (deepest Control component) | 10 mm protrusion | ~13 mm |
| Utility board front face (2 mm clearance gap) | — | ~15 mm |
| Utility board back face | 1.6 mm | ~17 mm |
| Stacking header standoff (clears 4 mm SOIC bodies) | 8 mm | ~25 mm |
| Audio board back face | 1.6 mm | ~27 mm |
| Audio board component bodies | ~4 mm | ~31 mm |

**Maximum depth from panel face: ~31 mm.** Fits within the Doepfer A-100 standard case
(35 mm from panel to busboard face). No right-angle Eurorack bus connector required.
This is a ~24 mm improvement over the previous 4-board design (~55 mm) achieved by
eliminating the perpendicular audio board orientation and switching to parallel stacking.

---

## 9. Reverse Polarity Protection

Placed on utility board, immediately after power header:
- +12 V rail: 1× BAT85 (SOD-80) Schottky in series, ~0.3 V forward drop
- −12 V rail: 1× BAT85 in series (reversed orientation)
- After protection: 47 µF electrolytic + 100 nF ceramic on each rail before ferrite bead
- Red power-indicator LED (2 mA) with 4.7 kΩ series resistor across post-protection +12 V

---

## 10. Inter-Board Signal Counts (Summary)

| Connector | Pins | Type | Notes |
|---|---|---|---|
| CN_CTRL_1 | 34 | 2.54 mm IDC, ribbon cable | Power + audio I/O + 19 CV tips + MOD IN tip |
| CN_CTRL_2 | **40** | 2.54 mm IDC, ribbon cable | Wipers + switch position outputs + ENV NORM return; expanded from 34 to carry all SP3T position nets individually |
| CN_CTRL_3 | **24** | 2.54 mm IDC, ribbon cable | 21 main parameter wipers (FREQ/FB/DRIVE/LP/HP/ATTACK/RELEASE etc.) + 2 GND + 1 spare |
| STK_AUDIO_L | **40** | 2.54 mm stacking header (face-to-face) | L-channel; GND guard pins retained for I_abc group |
| STK_AUDIO_R | **40** | 2.54 mm stacking header (face-to-face) | R-channel; mirror of STK_AUDIO_L |
| Eurorack bus | 16 | Shrouded IDC, standard Eurorack | Unchanged |

Total inter-board connections: **194 pins** across 6 connectors (CN_CTRL_2 expanded from 34→40 to accommodate individual SP3T position outputs).

---

## 11. Power Budget Revision

With V2164 removed and replaced by THAT 2180 + additional LM13700s, power draw is similar (LM13700 and THAT 2180 have comparable supply currents to V2164). The board split is confirmed:

| Board | +12 V est. | −12 V est. |
|---|---|---|
| Control board (passive) | 0 mA | 0 mA |
| Utility board (mod bus + expo + shared) | ~55 mA | ~55 mA |
| Combined audio board (full L + R chain) | ~140 mA | ~140 mA |
| **Total** | **~195 mA** | **~195 mA** |

Measure actual draw during bring-up. 200 mA / rail is the target ceiling for a standard
Eurorack busboard slot.

---

## 12. Bring-Up Checklist

Complete these checks **before** applying audio signals to any assembled board.

### All boards
- [ ] **BAT54S polarity (M2):** For every BAT54S clamp IC on the board, verify with diode-test
  DMM: pin 2 (center, signal node) reads ~300 mV forward drop to pin 3 (toward +12 V) and
  ~300 mV to pin 1 (toward −12 V). Reversed orientation creates a silent ESD protection failure
  with no obvious symptom. ~50+ BAT54S ICs across all boards. See noise-audit.md M2.
- [ ] **Power rail voltages:** Measure +12 V and −12 V at the power header pins before
  inserting the module in a case. Verify BAT85 reverse polarity protection diodes pass correct
  polarity and block reversed supply.

### Utility board
- [ ] **THAT340 power island:** Verify +12 V at THAT340 cluster VCC pins is 11.4 ± 0.3 V
  (100 Ω drop at ~6 mA → 0.6 V from 12 V rail). If outside range, check pi-filter resistor.
- [ ] **Mod bus zero offset:** Adjust RV_MB_ZERO with AMOUNT at center and input = 0 V;
  trim until mod bus output = 0 V.

### Combined audio board
- [ ] **CD4053 V_EE supply (D4):** Before applying audio, verify V_EE = −12 V on all three
  CD4053 ICs (Block 4) with a DMM. If V_EE = GND, the mode mux will silently distort all
  negative-going audio — no other symptom. See noise-audit.md D4.
- [ ] **LM4562 Block A output:** Feed a 1 kHz sine at ±1 V into L IN and R IN jacks; verify
  unity-gain output at Block A output nodes with oscilloscope.
- [ ] **LP1/LP2/HP expo converters:** Calibrate 1V/oct tracking per block (RV_REF, RV_1VOCT
  trim pots). Verify at 25°C; recheck at operating temperature after 10 min warm-up.
- [ ] **BAND OUT phase (D3):** With a 1 kHz sine at L IN, compare BAND OUT L and LEFT OUT
  phase on an oscilloscope. Confirm both are in-phase with the input (or document the offset
  if they are not). See noise-audit.md D3.

---

Last updated: 2026-05-25 (3-board redesign — combined audio board replaces separate L/R audio boards)
