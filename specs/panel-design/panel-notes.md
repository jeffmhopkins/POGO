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
┌──────┬──────────┬────────────────────┬──────┬──────┬──────┐
│  4HP │   6 HP   │      18 HP         │  4HP │  4HP │  4HP │
│STACK │  SHARED  │  COMB 1 / 2 / 3    │  LP1 │  LP2 │  HP  │
│      │          │  (6 HP per group)  │      │      │  +OUT│
└──────┴──────────┴────────────────────┴──────┴──────┴──────┘
  0–     20.32–     50.80–142.24 mm     142.24  162.56  182.88
  20.32  50.80                          –       –       –
                                        162.56  182.88  203.20
```

### HP Coordinate Reference

| Zone | Name | HP | x start (mm) | x end (mm) | Jack centers (mm from zone start) |
|---|---|---|---|---|---|
| 0 | Stacked Left | 4 | 0 | 20.32 | 5.08, 15.24 |
| 1 | Shared | 6 | 20.32 | 50.80 | 5.08, 15.24, 25.40 |
| 2a | Comb 1 | 6 | 50.80 | 81.28 | 5.08, 15.24, 25.40 |
| 2b | Comb 2 | 6 | 81.28 | 111.76 | 5.08, 15.24, 25.40 |
| 2c | Comb 3 | 6 | 111.76 | 142.24 | 5.08, 15.24, 25.40 |
| 3 | LP 1 | 4 | 142.24 | 162.56 | 5.08, 15.24 |
| 4 | LP 2 | 4 | 162.56 | 182.88 | 5.08, 15.24 |
| 5 | HP + OUT | 4 | 182.88 | 203.20 | 5.08, 15.24 |

---

## General Layout Paradigm

### Knob sizes — 3 tiers
- **Large**: primary performance controls (CUTOFF on LP1/LP2/HP, FREQ on each comb group, MASTER OFFSET in Shared)
- **Medium**: secondary controls (RESONANCE, FEEDBACK, DRIVE, DRY/WET, BLEND, WIDTH, ATTACK, RELEASE, AMOUNT, OFFSET)
- **Attenuverter**: narrow tall pointer-style knob (e.g. Rogan 1S or equivalent)

### Label placement
- Control labels: text below the knob or jack
- Zone name: labeled at the top of each zone (or mini-zone) in silk-screen
- Switch position labels: spelled out in full where panel space allows; abbreviated only where necessary

### Zone separator style
Silk-screen cyan lines between zones. Sub-group dividers within zones use dim gray lines.

### Jack row
All CV jacks in a single bottom row per zone. Attenuverter knobs directly above their respective CV jack.

---

## Zone Definitions

---

### Zone 0: Stacked Left Section (4 HP, full height, 3 vertical mini-zones)

Single column, 4 HP wide (20.32 mm), 128.5 mm tall. Divided into 3 stacked mini-zones.
Mini-zone heights: 0a ≈ 34 mm, 0b ≈ 51 mm, 0c ≈ 43.5 mm.
Each mini-zone labeled at its top.

Jack centers absolute (x): 5.08 mm (1 HP) and 15.24 mm (3 HP).

#### Mini-zone 0a: INPUT / GAIN (top, ~34 mm)
| Control | Type | Size | Notes |
|---|---|---|---|
| L IN | Input jack | — | Audio input left channel — at very top of section, x = 5.08 mm |
| R IN | Input jack | — | Audio input right channel — at very top of section, x = 15.24 mm |
| GAIN | Toggle switch | — | 2-position **vertical**; top = 1×, bottom = 5×; centered at x = 10.16 mm |

Layout: L IN and R IN jacks side by side at the top. GAIN vertical switch centered below them.
Switch position labels: **1×** (top), **5×** (bottom).

#### Mini-zone 0b: ENVELOPE (middle, ~51 mm)
| Control | Type | Size | Notes |
|---|---|---|---|
| ATTACK | Knob | Medium | Attack time (0.1–200 ms); x = 5.08 mm |
| RELEASE | Knob | Medium | Release time (5 ms–2 s); x = 15.24 mm |
| MOD SRC | Toggle switch | — | 3-position vertical; shifted up between ATTACK and RELEASE; labeled L / MAX / AVG |
| ENV L | Output jack | — | Left channel envelope CV out (0–10 V); x = 5.08 mm |
| ENV R | Output jack | — | Right channel envelope CV out (0–10 V); x = 15.24 mm |

Layout: ATTACK and RELEASE knobs side by side, MOD SRC vertical switch centered between them and shifted up.
Switch position labels: **L** (top), **MAX** (middle), **AVG** (bottom).
ENV L and ENV R jacks on bottom row.

#### Mini-zone 0c: MOD BUS (bottom, ~43.5 mm)
| Control | Type | Size | Notes |
|---|---|---|---|
| AMOUNT | Knob | Medium | Mod bus gain (0.2×–5×); x = 5.08 mm |
| OFFSET | Knob | Medium | Mod bus DC offset (±5 V); x = 15.24 mm |
| MOD IN | Input jack | — | Primary mod source (normalizes to envelope follower when unplugged); x = 10.16 mm |

Layout: AMOUNT and OFFSET knobs above, MOD IN jack centered on bottom row.

---

### Zone 1: SHARED (6 HP, full height)

6 HP wide (30.48 mm). Split into two labeled subsections: **COMB** (top) and **DIST** (bottom),
divided by a dim gray horizontal line.

**Unified bottom jack row (shared by both subsections):** all 3 CV jacks and 3 attenuverters
sit in a single row at the very bottom of the zone. This gives 3 jacks × 2 HP = 6 HP ✓.

Jack centers absolute (x): 25.40 mm (MASTER OFFSET CV), 35.56 mm (DRY/WET CV), 45.72 mm (BLEND CV).

#### Subsection: COMB (top portion)

| Control | Type | Size | Notes |
|---|---|---|---|
| DRY/WET | Knob | Medium | Wet/dry crossfade for comb filter; x = 25.40 mm (1 HP into zone) |
| WIDTH | Knob | Medium | Stereo width (R-channel frequency offset); no CV; x = 45.72 mm (5 HP into zone) |
| POLARITY | Toggle switch | — | 3-position **vertical**; centered at x = 35.56 mm (3 HP); POSITIVE / OFF / NEGATIVE |
| MASTER OFFSET | Knob | **Large** | Shifts all 3 comb group frequencies simultaneously (±5 V / 1V/oct); centered at x = 35.56 mm |
| MASTER OFFSET ATT | Attenuverter | Narrow tall | Above MASTER OFFSET CV jack; x = 25.40 mm |
| MASTER OFFSET CV | Input jack | — | CV override for MASTER OFFSET (±5 V / 1V/oct); x = 25.40 mm |

#### Subsection: DIST (bottom portion, above unified jack row)

| Control | Type | Size | Notes |
|---|---|---|---|
| BLEND | Knob | Medium | APF ↔ post-distortion crossfade; active when SOURCE = BLEND; x = 35.56 mm |
| SOURCE | Toggle switch | — | 3-position **vertical**; x = 25.40 mm; INTERNAL / BLEND / POST DIST |
| MODE | Toggle switch | — | 3-position **vertical**; x = 45.72 mm; SOFT CLIP / HARD CLIP / WAVEFOLD |
| BLEND ATT | Attenuverter | Narrow tall | Above BLEND CV jack; x = 45.72 mm |
| BLEND CV | Input jack | — | CV override for BLEND (0–10 V); x = 45.72 mm |

#### Shared bottom jack row (bottom of Zone 1)
```
  [MOFF ATT]  [DW ATT]   [BL ATT]     <- 3 attenuverters
  [MO CV]     [DW CV]    [BL CV]      <- 3 CV jacks
  MASTER OFF  DRY/WET    BLEND
  x=25.40     x=35.56    x=45.72
```

DRY/WET ATT sits at x = 35.56 mm above DRY/WET CV.

Layout sketch (top to bottom within 6 HP):
```
SHARED
==============================
  COMB
  --------------------------
  [DRY/WET]        [WIDTH]
  [POLARITY sw -- centered]
  [MASTER OFFSET -- centered, large knob]
  --------------------------
  DIST
  --------------------------
  [SOURCE sw]  [BLEND]  [MODE sw]
==========================================
  [MOFF ATT]   [DW ATT]   [BL ATT]
  [MO CV]      [DW CV]    [BL CV]
```

---

### Zone 2: COMB 1 / 2 / 3 (18 HP total — 6 HP per group)

Three groups (1, 2, 3), each 6 HP wide. Knob stacks are **vertically aligned** within each column.
Sub-group dividers (dim gray) between groups.

Jack pitch = 3 jacks × 2 HP = 6 HP (already compliant — no change from prior design).

| Control | Type | Size | Notes |
|---|---|---|---|
| FREQ 1 / 2 / 3 | Knob | Large | Center frequency per group; centered in zone |
| FEED 1 / 2 / 3 | Knob | Medium | Feedback amount per group (0–95%); centered |
| DRIVE 1 / 2 / 3 | Knob | Medium | Distortion drive per group; centered |
| FREQ ATT 1/2/3 | Attenuverter | Narrow tall | Above FREQ CV jack (1 HP into zone) |
| FEED ATT 1/2/3 | Attenuverter | Narrow tall | Above FEED CV jack (3 HP into zone) |
| DRIVE ATT 1/2/3 | Attenuverter | Narrow tall | Above DRIVE CV jack (5 HP into zone) |
| FREQ CV 1/2/3 | Input jack | — | CV override for FREQ (±5 V / 1V/oct); 1 HP into zone |
| FEED CV 1/2/3 | Input jack | — | CV override for FEED (0–10 V); 3 HP into zone |
| DRIVE CV 1/2/3 | Input jack | — | CV override for DRIVE (0–10 V); 5 HP into zone |

Layout per group (vertically stacked, centered in 6 HP column):
```
  COMB N
  --------------------------
  [FREQ N]         <- large knob, centered
  [FEED N]         <- medium knob, centered
  [DRIVE N]        <- medium knob, centered
  [ATT] [ATT] [ATT]
  [FC]  [Fb]  [Dr]
  FREQ  FEED  DRIVE
```

Zone x boundaries: Comb 1 = 50.80–81.28 mm · Comb 2 = 81.28–111.76 mm · Comb 3 = 111.76–142.24 mm.

---

### Zone 3: LP 1 (4 HP, full height)

4 HP wide (20.32 mm), x = 142.24–162.56 mm. Single column; CUTOFF large knob (~14 mm dia)
centered at x = 152.40 mm (zone center). ~3 mm clearance to zone edges.

Jack centers absolute (x): 147.32 mm (CUTOFF CV), 157.48 mm (RESONANCE CV).

| Control | Type | Size | Notes |
|---|---|---|---|
| CUTOFF | Knob | Large | Filter cutoff frequency (20 Hz – 20 kHz, 1V/oct); centered |
| RESONANCE | Knob | Medium | Filter resonance / Q (0–100%); centered below CUTOFF |
| CUTOFF ATT | Attenuverter | Narrow tall | Above CUTOFF CV jack (1 HP into zone) |
| RESONANCE ATT | Attenuverter | Narrow tall | Above RESONANCE CV jack (3 HP into zone) |
| CUTOFF CV | Input jack | — | CV override for cutoff (±5 V / 1V/oct) |
| RESONANCE CV | Input jack | — | CV override for resonance (0–10 V) |

Layout:
```
LP 1
-------------
[CUTOFF]      <- large, centered
[RESONANCE]   <- medium, centered
[ATT]  [ATT]
[CV]   [CV]
CUT    RES
```

---

### Zone 4: LP 2 (4 HP, full height)

4 HP wide (20.32 mm), x = 162.56–182.88 mm. This zone serves double duty:
- **Top strip** (y ~ 4.5–28 mm): BAND OUT jacks — LP2 and HP auxiliary outputs
- **Filter section** (y ~ 28–128.85 mm): LP2 vertical cutoff slider and controls

Jack centers absolute (x): 167.64 mm (1 HP into zone) and 177.80 mm (3 HP into zone).

#### Top Strip: BAND OUT (y ~ 4.5–28 mm)
Individual auxiliary tap outputs for parallel routing.

| Control | Type | Notes |
|---|---|---|
| LP2 L | Output jack | LP2 stage left output (±5 V, tapped before HP); x = 167.64 mm, y ~ 15 mm |
| LP2 R | Output jack | LP2 stage right output; x = 177.80 mm, y ~ 15 mm |
| HP L | Output jack | HP stage left output (±5 V, tapped after HP); x = 167.64 mm, y ~ 23 mm |
| HP R | Output jack | HP stage right output; x = 177.80 mm, y ~ 23 mm |

#### Filter Controls: LP 2 (below top strip)
| Control | Type | Size | Notes |
|---|---|---|---|
| CUTOFF | **Vertical slider** | — | LP2 cutoff frequency (20 Hz – 20 kHz, 1V/oct); centered in 4 HP |
| RESONANCE | Knob | Medium | LP2 resonance / Q (0–100%) — below the slider; centered |
| CUTOFF ATT | Attenuverter | Narrow tall | Above CUTOFF CV jack (1 HP into zone) |
| RESONANCE ATT | Attenuverter | Narrow tall | Above RESONANCE CV jack (3 HP into zone) |
| CUTOFF CV | Input jack | — | CV override for cutoff (±5 V / 1V/oct) |
| RESONANCE CV | Input jack | — | CV override for resonance (0–10 V) |

Layout:
```
BAND OUT          (y ~ 4.5–28)
-----------------
[LP2 L] [LP2 R]   y ~ 15
[HP L]  [HP R]    y ~ 23
-----------------
LP 2              (y ~ 28–128.85)
-----------------
[CUTOFF slider]   <- vertical slider, full height below strip
[RESONANCE]       <- medium knob below slider
[ATT]  [ATT]
[CV]   [CV]
CUT    RES
```

---

### Zone 5: HP + OUT (4 HP, full height)

4 HP wide (20.32 mm), x = 182.88–203.20 mm. This zone also serves double duty:
- **Top strip** (y ~ 4.5–28 mm): main stereo OUT jacks
- **Filter section** (y ~ 28–128.85 mm): HP vertical cutoff slider and controls

Jack centers absolute (x): 187.96 mm (1 HP into zone) and 198.12 mm (3 HP into zone).

#### Top Strip: OUT (y ~ 4.5–28 mm)
Main stereo output — signal after the HP filter stage, primary patch point.

| Control | Type | Notes |
|---|---|---|
| L OUT | Output jack | Main stereo output left (±5 V); x = 187.96 mm, y ~ 15 mm |
| R OUT | Output jack | Main stereo output right (±5 V); x = 198.12 mm, y ~ 15 mm |

#### Filter Controls: HP (below top strip)
| Control | Type | Size | Notes |
|---|---|---|---|
| CUTOFF | **Vertical slider** | — | HP cutoff frequency (20 Hz – 20 kHz, 1V/oct); centered |
| RESONANCE | Knob | Medium | HP resonance / Q (0–100%) — below the slider; centered |
| CUTOFF ATT | Attenuverter | Narrow tall | Above CUTOFF CV jack (1 HP into zone) |
| RESONANCE ATT | Attenuverter | Narrow tall | Above RESONANCE CV jack (3 HP into zone) |
| CUTOFF CV | Input jack | — | CV override for cutoff (±5 V / 1V/oct) |
| RESONANCE CV | Input jack | — | CV override for resonance (0–10 V) |

Layout:
```
OUT               (y ~ 4.5–28)
-----------------
[L OUT] [R OUT]   y ~ 15
-----------------
HP                (y ~ 28–128.85)
-----------------
[CUTOFF slider]   <- vertical slider, full height below strip
[RESONANCE]       <- medium knob below slider
[ATT]  [ATT]
[CV]   [CV]
CUT    RES
```

---

## Zone Separator Positions

Cyan separators at zone boundaries (at jack midpoints between adjacent zones):

| Separator | Position (mm) |
|---|---|
| Zone 0 \| Zone 1 | 20.32 mm (exact HP boundary) |
| Zone 1 \| Comb 1 | 50.80 mm (exact HP boundary) |
| Comb 3 \| LP 1 | 142.24 mm (exact HP boundary) |
| LP 1 \| LP 2 | 162.56 mm (exact HP boundary) |
| LP 2 \| HP+OUT | 182.88 mm (exact HP boundary) |

Gray sub-dividers (comb group internal boundaries):
- Comb 1 \| Comb 2: 81.28 mm
- Comb 2 \| Comb 3: 111.76 mm

---

## Open Questions

- Exact slider travel height (mm) for LP2 and HP CUTOFF sliders — set during SVG build
- Silk-screen font and size — TBD
- Panel material and finish — TBD
- VCV Rack panel SVG — to be derived from this document (SVG built from scratch, not edited)
