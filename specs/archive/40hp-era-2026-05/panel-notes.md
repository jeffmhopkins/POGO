# POGO Panel Design Notes

## Target Width: 40 HP

1 HP = 5.08 mm → total panel width = 203.20 mm

### Jack Spacing Standard: 1 Jack per 2 HP

Jack center-to-center pitch = 2 HP = 10.16 mm (minimum spec is ≥ 8 mm ✓).
Every zone's width is derived from: **(max jacks in one horizontal row) × 2 HP**.
In a 4 HP zone, 2 jack centers fall at x_zone + 5.08 mm and x_zone + 15.24 mm (1 HP and 3 HP).
In a 6 HP zone, 3 jack centers fall at x_zone + 5.08, +15.24, +25.40 mm (1, 3, 5 HP).

---

## Zone Layout (left to right)

```
┌──────┬──────────┬────────────────────┬──────────┬──────┬──────┐
│  4HP │   6 HP   │      18 HP         │   4 HP   │  4HP │  4HP │
│STACK │ CONTROL  │  COMB 1 / 2 / 3    │  VCA+LP1 │  LP2 │  HP  │
│      │          │  (6 HP per group)  │          │      │  +OUT│
└──────┴──────────┴────────────────────┴──────────┴──────┴──────┘
  0–     20.32–     50.80–142.24 mm     142.24–    162.56  182.88
  20.32  50.80                          162.56     –       –
                                                   182.88  203.20
```

### HP Coordinate Reference

| Zone | Name | HP | x start (mm) | x end (mm) | Zone center x (mm) | Jack centers (mm absolute) |
|---|---|---|---|---|---|---|
| 0 | Stacked Left | 4 | 0 | 20.32 | 10.16 | 5.08, 15.24 |
| 1 | CONTROL | 6 | 20.32 | 50.80 | 35.56 | 25.40, 35.56, 45.72 |
| 2a | Comb 1 | 6 | 50.80 | 81.28 | 66.04 | 55.88, 66.04, 76.20 |
| 2b | Comb 2 | 6 | 81.28 | 111.76 | 96.52 | 86.36, 96.52, 106.68 |
| 2c | Comb 3 | 6 | 111.76 | 142.24 | 127.00 | 116.84, 127.00, 137.16 |
| 3 | VCA + LP 1 | 4 | 142.24 | 162.56 | 152.40 | 147.32, 157.48 |
| 4 | BAND OUT + LP 2 | 4 | 162.56 | 182.88 | 172.72 | 167.64, 177.80 |
| 5 | OUT + HP | 4 | 182.88 | 203.20 | 193.04 | 187.96, 198.12 |

### Horizontal Divider

A cyan horizontal line at y = 28 mm spans x = 142.24–203.20 mm (Zones 3–5), separating the
top-strip output/VCA section from the filter controls below.

---

## General Layout Paradigm

### Knob sizes — 4 tiers

| Tier | SVG radius | Diameter | Used for |
|---|---|---|---|
| XL | r = 9 | 18 mm | FREQ 1/2/3 (per-comb center freq), MASTER OFFSET |
| Large | r = 7 | 14 mm | CUTOFF LP1, FB 1/2/3, DRIVE 1/2/3 |
| Medium | r = 4.5 | 9 mm | RESONANCE LP1/LP2/HP, COMB BYPASS, WIDTH, ATTACK, RELEASE, AMOUNT, OFFSET, STEREO SPREAD OFFSET, FB DIST BLEND |
| Attenuverter | r = 2.5 | 5 mm | All per-destination CV depth knobs; AMT (VCA); all bottom-row attenuverters |

### Label placement
- Control labels: text centered below the knob or jack
- Zone name: labeled at the top of each zone (or mini-zone) in cyan (#00d4ff)
- Switch position labels: abbreviated (space constraints); full names in this document
- Output jack labels: monospace text with a thin rounded-rectangle border stroke

### Zone separator style
Cyan lines between zones. Gray sub-dividers within zones (comb group internal boundaries).

### Jack row
All CV jacks in a single bottom row per zone. Attenuverter knobs directly above their CV jack.
CV jack label color: #777. Audio jack label color: #888. Knob/switch label color: #999.

---

## Zone Definitions

---

### Zone 0: Stacked Left (4 HP, full height, 3 vertical mini-zones)

Single column, 4 HP wide (20.32 mm). Jack centers absolute: x = 5.08 mm and x = 15.24 mm.

#### Mini-zone 0a: INPUT / GAIN (top)

| Control | Type | Notes |
|---|---|---|
| L IN | Input jack, cx = 5.08, cy = 16 | Audio input left |
| R IN | Input jack, cx = 15.24, cy = 16 | Audio input right |
| GAIN | 2-pos **horizontal** toggle switch | Body 9×2.4 mm centered at x = 10.16; slug at left = 1×, right = 5× |

Switch position labels below body: **1×** (left position), **5×** (right position).

#### Mini-zone 0b: ENVELOPE (middle)

| Control | Type | Notes |
|---|---|---|
| MOD SRC | 3-pos vertical toggle | 3-position: L / MAX / AVG; centered at x = 10.16, shifted up |
| ATTACK | Knob — small (attenuverter size, r = 2.5) | x = 5.08 |
| RELEASE | Knob — small (attenuverter size, r = 2.5) | x = 15.24 |
| ENV L | Output jack, cx = 5.08 | Envelope CV out left (0–10 V); bordered label |
| ENV R | Output jack, cx = 15.24 | Envelope CV out right (0–10 V); bordered label |

Switch position labels right of body: **L** (top), **MAX** (middle), **AVG** (bottom).

#### Mini-zone 0c: MOD BUS (bottom)

| Control | Type | Notes |
|---|---|---|
| AMOUNT | Knob — small (r = 2.5) | Mod bus gain (0.2×–5×); x = 5.08 |
| OFFSET | Knob — small (r = 2.5) | Mod bus DC offset (±5 V); x = 15.24 |
| MOD IN | Input jack, cx = 10.16 | Primary mod source (normalizes to envelope when unplugged) |

---

### Zone 1: CONTROL (6 HP, full height)

6 HP wide (30.48 mm). Split into two labeled subsections: **COMB** (top, y = 4.5–74) and
**DIST** (bottom, y = 74–128.85), divided by a dim gray horizontal line.

**Unified bottom CV row** (shared by COMB and DIST subsections):
```
  [BYPASS ATT]  [OFFSET ATT]  [BLEND ATT]   ← attenuverters, cy = 109
  [BYPASS CV]   [OFFSET CV]   [BLEND CV]    ← CV jacks, cy = 118
   x = 25.40     x = 35.56     x = 45.72
   label: BYPASS  OFFSET        BLEND         y = 124.5
```

#### Subsection: COMB (top portion, y = 4.5–74)

| Control | Type | Notes |
|---|---|---|
| COMB BYPASS | Knob — medium (r = 4.5) | Pre-comb VCA level; 0% = comb bypassed; cx = 29.0, cy = 21 |
| WIDTH | Knob — medium (r = 4.5) | Stereo width (R-channel frequency offset); cx = 42.14, cy = 21 |
| POLARITY | 3-pos vertical toggle | Centered at cx = 35.56; positions: POS / OFF / NEG |
| MASTER OFFSET | Knob — XL (r = 9) | Shifts all 3 comb groups simultaneously (±5 V, 1V/oct); cx = 35.56, cy = 57 |

Switch position labels right of POLARITY body: **POS** (top), **OFF** (middle), **NEG** (bottom).

#### Subsection: DIST (bottom portion, y = 74–128.85, above CV row)

SOURCE switch removed. The continuous FB DIST BLEND knob now handles the full range from
clean signal (0%) through blend to post-distortion signal additively mixed into each SVF group input (100%).

| Control | Type | Notes |
|---|---|---|
| MODE | 3-pos vertical toggle | Distortion mode; cx = 28, body y = 81–93; SFT / HRD / WFD |
| FB DIST BLEND | Knob — medium (r = 4.5) | Post-dist additive blend into SVF input; cx = 40, cy = 87 |

Switch position labels right of MODE body: **SFT** (top), **HRD** (middle), **WFD** (bottom).
Full names: Soft Clip / Hard Clip / Wavefold.

Layout sketch:
```
CONTROL
==============================
  COMB
  --------------------------
  [COMB BYPASS]    [WIDTH]
  [POLARITY sw -- centered]
  [MASTER OFFSET -- centered, XL knob]
  --------------------------
  DIST
  --------------------------
  [MODE sw]   [FB DIST BLEND]
==========================================
  [BYPASS ATT]  [OFFSET ATT]  [BLEND ATT]
  [BYPASS CV]   [OFFSET CV]   [BLEND CV]
```

---

### Zone 2: COMB 1 / 2 / 3 (18 HP total — 6 HP per group)

Three groups (1, 2, 3), each 6 HP wide. Knob stacks vertically aligned within each column.
Gray sub-dividers between groups.

Each group has a frequency range label in dim color below the section title:
- Comb 1: 20 Hz – 2 kHz
- Comb 2: 200 Hz – 8 kHz
- Comb 3: 1 kHz – 20 kHz

| Control | Type | Size | Notes |
|---|---|---|---|
| FREQ 1 / 2 / 3 | Knob | **XL (r = 9)** | Center frequency per group; centered in zone, cy = 32 |
| FB 1 / 2 / 3 | Knob | **Large (r = 7)** | Feedback amount per group (0–95%); centered, cy = 61 |
| DRIVE 1 / 2 / 3 | Knob | **Large (r = 7)** | Distortion drive per group; centered, cy = 87; dual-zone: CCW=mute, 9am=unity/clean, CW=full distortion drive |
| FREQ ATT 1/2/3 | Attenuverter | r = 2.5 | Above FREQ CV jack (left jack position) |
| FB ATT 1/2/3 | Attenuverter | r = 2.5 | Above FB CV jack (center jack position) |
| DRIVE ATT 1/2/3 | Attenuverter | r = 2.5 | Above DRIVE CV jack (right jack position) |
| FREQ CV 1/2/3 | Input jack | — | CV override for FREQ (±5 V / 1V/oct); left position |
| FB CV 1/2/3 | Input jack | — | CV override for FB (0–10 V); center position |
| DRIVE CV 1/2/3 | Input jack | — | CV override for DRIVE (0–10 V); right position |

Common bottom row: ATT cy = 109, CV cy = 118, label y = 124.5.

Layout per group:
```
  COMB N  (freq range)
  --------------------------
  [FREQ N]         ← XL knob, centered, cy = 32
  [FB N]           ← large knob, centered, cy = 61
  [DRIVE N]        ← large knob, centered, cy = 87
  [F.ATT] [FB.ATT] [DR.ATT]  cy = 109
  [F.CV]  [FB.CV]  [DR.CV]   cy = 118
   FREQ    FB       DRIVE     y = 124.5
```

Zone x boundaries: Comb 1 = 50.80–81.28 · Comb 2 = 81.28–111.76 · Comb 3 = 111.76–142.24 mm.

---

### Zone 3: VCA + LP 1 (4 HP, full height)

4 HP wide (20.32 mm), x = 142.24–162.56 mm. Zone center x = 152.40 mm.
Jack centers absolute: x = 147.32 mm (left) and x = 157.48 mm (right).

**Horizontal divider at y = 28 mm** divides this zone into:
- **Top strip (y = 4.5–28): VCA section**
- **Filter section (y = 28–128.85): LP 1**

#### Top Strip: VCA (y = 4.5–28)

| Control | Type | Notes |
|---|---|---|
| AMT | Attenuverter (r = 2.5) | VCA CV depth; cx = 147.32, cy = 16 |
| CV IN | Input jack | VCA CV input; normalizes to mod bus when unplugged; cx = 157.48, cy = 16 |

Label "AMT" at y = 24.5 below attenuverter. Label "CV IN" at y = 24.5 below jack.

#### Filter Controls: LP 1 (y = 28–128.85)

"LP 1" section label at y = 33 (cyan, below divider).

| Control | Type | Notes |
|---|---|---|
| CUTOFF | Knob — Large (r = 7) | Filter cutoff (20 Hz – 20 kHz, 1V/oct); cx = 152.40, cy = 47 (top edge at y = 40, aligned with LP2 slider top) |
| STEREO SPREAD OFFSET | Knob — Medium (r = 4.5) | Bipolar; skews L vs R cutoff; cx = 152.40, cy = 70 (centered between CUTOFF and RESONANCE) |
| RESONANCE | Knob — Medium (r = 4.5) | Filter resonance / Q; cx = 152.40, cy = 93 (aligned with LP2/HP RESONANCE row) |
| CUTOFF ATT | Attenuverter (r = 2.5) | cx = 147.32, cy = 109 |
| RESONANCE ATT | Attenuverter (r = 2.5) | cx = 157.48, cy = 109 |
| CUTOFF CV | Input jack | cx = 147.32, cy = 118; label "CUT" at y = 124.5 |
| RESONANCE CV | Input jack | cx = 157.48, cy = 118; label "RES" at y = 124.5 |

Layout:
```
VCA           (y = 4.5–28)
--------------
[AMT]  [CV IN]     cy = 16
AMT    CV IN        y = 24.5
--------------
LP 1          (y = 28–128.85)
--------------
[CUTOFF]            large, cy = 47
[STEREO SPREAD]     medium, cy = 70
[OFFSET]
[RESONANCE]         medium, cy = 93 (aligned with LP2/HP)
[ATT]  [ATT]        cy = 109
[CV]   [CV]         cy = 118
CUT    RES           y = 124.5
```

---

### Zone 4: BAND OUT + LP 2 (4 HP, full height)

4 HP wide (20.32 mm), x = 162.56–182.88 mm. Zone center x = 172.72 mm.
Jack centers absolute: x = 167.64 mm and x = 177.80 mm.

**Horizontal divider at y = 28 mm** divides this zone into:
- **Top strip (y = 4.5–28): BAND OUT jacks**
- **Filter section (y = 28–128.85): LP 2**

#### Top Strip: BAND OUT (y = 4.5–28)

LP1 output taps — stereo signal after LP1, before LP2.

| Control | Type | Notes |
|---|---|---|
| LP1 L | Output jack | LP1 output left; cx = 167.64, cy = 16; bordered label |
| LP1 R | Output jack | LP1 output right; cx = 177.80, cy = 16; bordered label |

Labels with thin rounded-rectangle border: "LP1 L" and "LP1 R" centered at y = 24.5.

#### Filter Controls: LP 2 (y = 28–128.85)

"LP 2" section label at y = 33.

| Control | Type | Notes |
|---|---|---|
| CUTOFF | Vertical slider (45 mm travel) | Track y = 40–85, width 4 mm; centered at cx = 172.72 |
| RESONANCE | Knob — Medium (r = 4.5) | cx = 172.72, cy = 93 |
| CUTOFF ATT | Attenuverter (r = 2.5) | cx = 167.64, cy = 109 |
| RESONANCE ATT | Attenuverter (r = 2.5) | cx = 177.80, cy = 109 |
| CUTOFF CV | Input jack | cx = 167.64, cy = 118; label "CUT" |
| RESONANCE CV | Input jack | cx = 177.80, cy = 118; label "RES" |

---

### Zone 5: OUT + HP (4 HP, full height)

4 HP wide (20.32 mm), x = 182.88–203.20 mm. Zone center x = 193.04 mm.
Jack centers absolute: x = 187.96 mm and x = 198.12 mm.

**Horizontal divider at y = 28 mm** divides this zone into:
- **Top strip (y = 4.5–28): main stereo OUT jacks**
- **Filter section (y = 28–128.85): HP**

#### Top Strip: OUT (y = 4.5–28)

Main stereo output — signal after the HP filter stage, primary patch point.

| Control | Type | Notes |
|---|---|---|
| LEFT | Output jack | Main stereo output left; cx = 187.96, cy = 16; bordered label |
| RIGHT | Output jack | Main stereo output right; cx = 198.12, cy = 16; bordered label |

Labels with bordered text: "LEFT" and "RIGHT" centered at y = 24.5.

#### Filter Controls: HP (y = 28–128.85)

"HP" section label at y = 33.

| Control | Type | Notes |
|---|---|---|
| CUTOFF | Vertical slider (45 mm travel) | Track y = 40–85; centered at cx = 193.04 |
| RESONANCE | Knob — Medium (r = 4.5) | cx = 193.04, cy = 93 |
| CUTOFF ATT | Attenuverter (r = 2.5) | cx = 187.96, cy = 109 |
| RESONANCE ATT | Attenuverter (r = 2.5) | cx = 198.12, cy = 109 |
| CUTOFF CV | Input jack | cx = 187.96, cy = 118; label "CUT" |
| RESONANCE CV | Input jack | cx = 198.12, cy = 118; label "RES" |

---

## Zone Separator Positions

Cyan vertical separators at zone boundaries:

| Separator | x position (mm) |
|---|---|
| Zone 0 \| Zone 1 | 20.32 |
| Zone 1 \| Comb 1 | 50.80 |
| Comb 1 \| Comb 2 | 81.28 |
| Comb 2 \| Comb 3 | 111.76 |
| Comb 3 \| VCA+LP1 | 142.24 |
| VCA+LP1 \| LP2 | 162.56 |
| LP2 \| HP+OUT | 182.88 |

Gray sub-dividers (comb group internal, full height): 81.28 mm and 111.76 mm.
Cyan horizontal divider (top strip / filter boundary): y = 28 mm, x = 142.24–203.20 mm.
Gray horizontal divider (COMB/DIST boundary in CONTROL zone): y ≈ 74 mm, x = 20.32–50.80 mm.

---

## Panel Module Labeling

- **Top strip** (y = 0–4.5, fill #141414): "POGO  ·  STEREO TRIPLE COMB FILTER" — centered,
  font-size = 3.5, bold, cyan (#00d4ff); dot separator in orange (#ff8800).
- **Bottom strip** (y = 128.85–133.35, fill #141414): "SPACE COAST SYNTHESIZERS  ·  SCS" —
  centered, font-size = 2.4, muted (#4a6070).

---

## Deferred to Manufacturing Phase

These do not block Phase 6 (VCV Rack DSP validation precedes hardware manufacturing decisions).

- Exact slider part selection (ALPS RS4515N or equivalent) — confirm travel and PCB footprint
- Silk-screen font for manufacturing files
- Panel material and finish (FR4 with white silk-screen vs. anodized aluminum)
