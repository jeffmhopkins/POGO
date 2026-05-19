# POGO Panel Design Notes

## Target Width: 46 HP

1 HP = 5.08 mm → total panel width = 233.68 mm

---

## Zone Layout (left to right)

```
┌──────────────┬──────────────┬───────────────────────┬────────┬────────────────────────┐
│    5 HP      │    7 HP      │        18 HP           │  5 HP  │         11 HP          │
│   STACKED    │   SHARED     │   COMB 1 / 2 / 3       │  LP 1  │   LP 2 + HP + OUT      │
│  (3 zones)   │ (Comb+Dist)  │  (6 HP per group)      │        │                        │
└──────────────┴──────────────┴───────────────────────┴────────┴────────────────────────┘
  x: 0–25.4      25.4–60.96    60.96–152.4 mm           152.4–   177.8–233.68 mm
                                                         177.8
```

### HP Coordinate Reference

| Zone | Name | HP | x start (mm) | x end (mm) |
|---|---|---|---|---|
| 0 | Stacked Left | 5 | 0 | 25.4 |
| 1 | Shared | 7 | 25.4 | 60.96 |
| 2a | Comb 1 | 6 | 60.96 | 91.44 |
| 2b | Comb 2 | 6 | 91.44 | 121.92 |
| 2c | Comb 3 | 6 | 121.92 | 152.4 |
| 3 | LP 1 | 5 | 152.4 | 177.8 |
| 4+5 | LP 2 + HP + OUT | 11 | 177.8 | 233.68 |

---

## General Layout Paradigm

### Knob sizes — 3 tiers
- **Large**: primary performance controls (CUTOFF on LP1, FREQ on each comb group, MASTER OFFSET in Shared)
- **Medium**: secondary controls (RESONANCE, FEEDBACK, DRIVE, DRY/WET, BLEND, WIDTH, ATTACK, RELEASE, AMOUNT, OFFSET)
- **Attenuverter**: narrow tall pointer-style knob (e.g. Rogan 1S or equivalent)

### Jack spacing rule
Jack center-to-center spacing must be ≥ 8 mm. When laying out the bottom CV jack row per zone,
calculate the minimum horizontal space required first, then determine the zone HP from that —
do not force jacks into a predetermined width. Attenuverter knobs directly above their CV jack.

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

### Zone 0: Stacked Left Section (5 HP, full height, 3 vertical mini-zones)

Single column, 5 HP wide (25.4 mm), 128.5 mm tall. Divided into 3 stacked mini-zones.
Mini-zone heights: 0a ≈ 34 mm (20% shorter than equal thirds), 0b ≈ 51 mm (gains the freed space), 0c ≈ 43.5 mm.
Each mini-zone labeled at its top.

#### Mini-zone 0a: INPUT / GAIN (top, ~34 mm)
| Control | Type | Size | Notes |
|---|---|---|---|
| L IN | Input jack | — | Audio input left channel — **at very top of section** |
| R IN | Input jack | — | Audio input right channel — **at very top of section** |
| GAIN | Toggle switch | — | 2-position **vertical**; top = 1×, bottom = 5× |

Layout: L IN and R IN jacks side by side at the top. GAIN vertical switch centered below them.
Switch position labels: **1×** (top), **5×** (bottom).

#### Mini-zone 0b: ENVELOPE (middle, ~51 mm — gains room from 0a shrinking)
| Control | Type | Size | Notes |
|---|---|---|---|
| ATTACK | Knob | Medium | Attack time (0.1–200 ms) |
| RELEASE | Knob | Medium | Release time (5 ms–2 s) |
| MOD SRC | Toggle switch | — | 3-position vertical; moved up into freed space; labeled L / MAX / AVG |
| ENV L | Output jack | — | Left channel envelope CV out (0–10 V) |
| ENV R | Output jack | — | Right channel envelope CV out (0–10 V) |

Layout: ATTACK and RELEASE knobs side by side, MOD SRC vertical switch between them and shifted up.
Switch position labels: **L** (top), **MAX** (middle), **AVG** (bottom).
ENV L and ENV R jacks on bottom row.

#### Mini-zone 0c: MOD BUS (bottom, ~43.5 mm)
| Control | Type | Size | Notes |
|---|---|---|---|
| AMOUNT | Knob | Medium | Mod bus gain (0.2×–5×) |
| OFFSET | Knob | Medium | Mod bus DC offset (±5 V) |
| MOD IN | Input jack | — | Primary mod source (normalizes to envelope follower when unplugged) |

Layout: AMOUNT and OFFSET knobs above, MOD IN jack on bottom row.

---

### Zone 1: SHARED (7 HP, full height — +2 HP from previous 5 HP)

Split into two labeled subsections: **COMB** (top) and **DIST** (bottom), divided by a dim gray line.

#### Subsection: COMB

| Control | Type | Size | Notes |
|---|---|---|---|
| DRY/WET | Knob | Medium | Wet/dry crossfade for comb filter |
| POLARITY | Toggle switch | — | 3-position **vertical**; POSITIVE / OFF / NEGATIVE |
| WIDTH | Knob | Medium | Stereo width (R-channel frequency offset); no CV |
| MASTER OFFSET | Knob | **Large** | New — shifts all 3 comb group frequencies simultaneously (±5 V / 1V/oct) |
| MASTER OFFSET ATT | Attenuverter | Narrow tall | CV attenuator for MASTER OFFSET |
| MASTER OFFSET CV | Input jack | — | CV override for MASTER OFFSET (±5 V / 1V/oct) |
| DRY/WET ATT | Attenuverter | Narrow tall | CV attenuator for DRY/WET |
| DRY/WET CV | Input jack | — | CV override for DRY/WET (0–10 V) |

#### Subsection: DIST

| Control | Type | Size | Notes |
|---|---|---|---|
| BLEND | Knob | Medium | APF ↔ post-distortion crossfade; active when SOURCE = BLEND |
| SOURCE | Toggle switch | — | 3-position **vertical**; INTERNAL / BLEND / POST DIST |
| MODE | Toggle switch | — | 3-position **vertical**; SOFT CLIP / HARD CLIP / WAVEFOLD |
| BLEND ATT | Attenuverter | Narrow tall | CV attenuator for BLEND |
| BLEND CV | Input jack | — | CV override for BLEND (0–10 V) |

Layout (top to bottom within 7 HP):
```
SHARED
══════════════════════
  COMB
  ──────────────────
  [DRY/WET]
  [POLARITY sw]   (vertical: POSITIVE / OFF / NEGATIVE)
  [WIDTH]
  [MASTER OFFSET]  ← large knob
  [ATT]  [ATT]
  [CV]   [CV]
  (MASTER OFFSET CV left, DRY/WET CV right)

  DIST
  ──────────────────
  [BLEND]
  [SOURCE sw]     (vertical: INTERNAL / BLEND / POST DIST)
  [MODE sw]       (vertical: SOFT CLIP / HARD CLIP / WAVEFOLD)
  [ATT]
  [CV]
  (BLEND CV)
```

---

### Zone 2: COMB 1 / 2 / 3 (18 HP total — 6 HP per group)

Three groups (1, 2, 3), each 6 HP wide. Knob stacks are **vertically aligned** within each column.
Sub-group dividers (dim gray) at x = 91.44 mm and x = 121.92 mm.

| Control | Type | Size | Notes |
|---|---|---|---|
| FREQ 1 / 2 / 3 | Knob | Large | Center frequency per group |
| FEED 1 / 2 / 3 | Knob | Medium | Feedback amount per group (0–95%) |
| DRIVE 1 / 2 / 3 | Knob | Medium | Distortion drive per group |
| FREQ ATT 1/2/3 | Attenuverter | Narrow tall | Above FREQ CV jacks |
| FEED ATT 1/2/3 | Attenuverter | Narrow tall | Above FEED CV jacks |
| DRIVE ATT 1/2/3 | Attenuverter | Narrow tall | Above DRIVE CV jacks |
| FREQ CV 1/2/3 | Input jack | — | CV override for FREQ (±5 V / 1V/oct) |
| FEED CV 1/2/3 | Input jack | — | CV override for FEED (0–10 V) |
| DRIVE CV 1/2/3 | Input jack | — | CV override for DRIVE (0–10 V) |

Layout per group (vertically stacked, centered in 6 HP column):
```
  COMB N
  ──────────
  [FREQ N]     ← large knob
  [FEED N]     ← medium knob
  [DRIVE N]    ← medium knob
  [ATT][ATT][ATT]
  [CV] [CV] [CV]
  FREQ FEED DRIVE
```

---

### Zone 3: LP 1 (5 HP, full height — unchanged)

| Control | Type | Size | Notes |
|---|---|---|---|
| CUTOFF | Knob | Large | Filter cutoff frequency (20 Hz – 20 kHz, 1V/oct) |
| RESONANCE | Knob | Medium | Filter resonance / Q (0–100%) |
| CUTOFF ATT | Attenuverter | Narrow tall | Above CUTOFF CV jack |
| RESONANCE ATT | Attenuverter | Narrow tall | Above RESONANCE CV jack |
| CUTOFF CV | Input jack | — | CV override for cutoff (±5 V / 1V/oct) |
| RESONANCE CV | Input jack | — | CV override for resonance (0–10 V) |

Layout:
```
LP 1
─────────────────
[CUTOFF]

[RESONANCE]

[ATT]      [ATT]
[CV]       [CV]
```

---

### Zone 4+5: LP 2 + HP + OUT (11 HP combined)

LP 2 and HP are combined into a single zone with vertical cutoff sliders. Output jacks live in a
small labeled sub-box at the top right.

#### OUT subsection (top-right corner, ~2 HP)
| Control | Type | Notes |
|---|---|---|
| L OUT | Output jack | Stereo audio output left (±5 V) |
| R OUT | Output jack | Stereo audio output right (±5 V) |

Two jacks side by side, labeled **L** and **R**, in a small box at the top-right corner of the zone.

#### LP 2 (left ~5.5 HP of zone)
| Control | Type | Size | Notes |
|---|---|---|---|
| CUTOFF | **Vertical slider** | — | LP2 cutoff frequency (20 Hz – 20 kHz, 1V/oct) |
| RESONANCE | Knob | Medium | LP2 resonance / Q (0–100%) — below the slider |
| CUTOFF ATT | Attenuverter | Narrow tall | CV attenuator for cutoff |
| CUTOFF CV | Input jack | — | CV override for cutoff (±5 V / 1V/oct) |
| RESONANCE ATT | Attenuverter | Narrow tall | CV attenuator for resonance |
| RESONANCE CV | Input jack | — | CV override for resonance (0–10 V) |

#### HP (right ~3.5 HP of zone, below OUT box)
| Control | Type | Size | Notes |
|---|---|---|---|
| CUTOFF | **Vertical slider** | — | HP cutoff frequency (20 Hz – 20 kHz, 1V/oct) |
| RESONANCE | Knob | Medium | HP resonance / Q (0–100%) — below the slider |
| CUTOFF ATT | Attenuverter | Narrow tall | CV attenuator for cutoff |
| CUTOFF CV | Input jack | — | CV override for cutoff (±5 V / 1V/oct) |
| RESONANCE ATT | Attenuverter | Narrow tall | CV attenuator for resonance |
| RESONANCE CV | Input jack | — | CV override for resonance (0–10 V) |

Layout sketch:
```
LP 2 + HP                                      ┌─ OUT ─┐
─────────────────────────────────────────────  │  [L]  │
                                               │  [R]  │
  [LP2 CUTOFF   ]    [HP CUTOFF    ]           └───────┘
  [   slider    ]    [  slider     ]
                                  ← below OUT box
  [RESONANCE LP2]    [RESONANCE HP ]
  [ATT] [ATT]        [ATT] [ATT]
  [CV]  [CV]         [CV]  [CV]
  CUT   RES          CUT   RES
```

---

## Open Questions

- Exact slider travel height (mm) for LP2 and HP CUTOFF sliders — set during SVG build
- Silk-screen font and size — TBD
- Panel material and finish — TBD
- VCV Rack panel SVG — to be derived from this document (SVG built from scratch, not edited)
