# POGO Panel Design Notes

## Target Width: 50 HP

1 HP = 5.08 mm → total panel width = 254 mm

---

## Zone Layout (left to right)

```
┌──────────────┬──────────┬────────────────────────────────────────────┬────────┬────────┬──────────────┐
│    5 HP      │   5 HP   │                  24 HP                     │  5 HP  │  5 HP  │    6 HP      │
│   STACKED    │  SHARED  │           COMB / DISTORTION                │  LP 1  │  LP 2  │  HP + OUT    │
│  (3 zones)   │          │                                            │        │        │              │
└──────────────┴──────────┴────────────────────────────────────────────┴────────┴────────┴──────────────┘
```

---

## General Layout Paradigm

### Knob sizes — 3 tiers
- **Large**: primary performance controls (CUTOFF on LP1, FREQ on each comb group)
- **Medium**: secondary controls (RESONANCE, FEEDBACK, DRIVE, DRY/WET, BLEND, WIDTH, ATTACK, RELEASE, AMOUNT, OFFSET, LP2 CUTOFF, HP CUTOFF/RESONANCE)
- **Attenuverter**: narrow tall pointer-style knob (e.g. Rogan 1S or equivalent)

### Jack color coding
None — all jacks uniform hardware finish.

### Attenuverter center detent
Panel marking only — no physical detent in the pot.

### Label placement
- Control labels: text below the knob or jack
- Zone name: labeled at the top of each zone (or mini-zone) in silk-screen

### Zone separator style
Silk-screen lines between zones, similar to Pittsburgh Modular SV-1b treatment.

### Jack row
All CV jacks in a single bottom row per zone. Attenuverter knobs directly above their respective CV jack.

---

## Zone Definitions

---

### Zone 0: Stacked Left Section (5 HP, full height, 3 vertical mini-zones)

Single column, 5 HP wide (25.4 mm), 128.5 mm tall, divided into 3 equal stacked mini-zones
each approximately 42 mm tall. Each mini-zone labeled at its top.

#### Mini-zone 0a: INPUT / GAIN (top)
| Control | Type | Size | Notes |
|---|---|---|---|
| L IN | Input jack | — | Audio input left channel |
| R IN | Input jack | — | Audio input right channel |
| GAIN | Toggle switch | — | 2-position; labeled 1× and 5× at each position |

Layout: GAIN switch above, L IN and R IN jacks side by side on bottom row.

#### Mini-zone 0b: ENVELOPE (middle)
| Control | Type | Size | Notes |
|---|---|---|---|
| ATK | Knob | Medium | Attack time |
| REL | Knob | Medium | Release time |
| MOD SRC | Toggle switch | — | 3-position vertical; labeled l / max / avg; sits between ATK and REL |
| ENV L | Output jack | — | Left channel envelope CV out |
| ENV R | Output jack | — | Right channel envelope CV out |

Layout: ATK and REL knobs with MOD SRC switch vertically oriented between them; ENV L and ENV R jacks on bottom row.

#### Mini-zone 0c: MOD BUS (bottom)
| Control | Type | Size | Notes |
|---|---|---|---|
| AMOUNT | Knob | Medium | Mod bus gain (0.2× – 5×) |
| OFFSET | Knob | Medium | Mod bus DC offset (±5 V) |
| MOD IN | Input jack | — | Primary mod source (normalizes to envelope follower) |

Layout: AMOUNT and OFFSET knobs above, MOD IN jack on bottom row.

---

### Zone 1: SHARED (5 HP, full height)

Shared controls for the COMB / DISTORTION section.

| Control | Type | Size | Notes |
|---|---|---|---|
| DRY/WET | Knob | Medium | Wet/dry crossfade for comb filter |
| BLEND | Knob | Medium | Feedback source blend ratio; active when SOURCE = Blend |
| SOURCE | Toggle switch | — | 3-position: I (internal) · Bl (blend) · PD (post-dist) |
| POLARITY | Toggle switch | — | 3-position: + · 0 · − |
| MODE | Toggle switch | — | 3-position: soft clip · hard clip · wavefold |
| WIDTH | Knob | Medium | Stereo width (R channel frequency offset); no CV |
| DRY/WET ATT | Attenuverter | Narrow tall | Above DRY/WET CV jack |
| BLEND ATT | Attenuverter | Narrow tall | Above BLEND CV jack |
| DRY/WET CV | Input jack | — | CV override for DRY/WET |
| BLEND CV | Input jack | — | CV override for BLEND |

Layout (top to bottom):
```
SHARED
─────────────────
[DRY/WET] [BLEND]
[SRC sw]  [POL sw]
     [MODE sw]
[WIDTH]
[ATT]      [ATT]
[CV]       [CV]
```

SOURCE and POLARITY switches side by side. MODE switch centered below them. WIDTH knob below MODE. Attenuverters above their CV jacks at the bottom.

---

### Zone 2: COMB / DISTORTION (24 HP, full height)

Three groups (1, 2, 3) across the full width — no sub-zone labels. Knob labels identify which group each control belongs to. All CV jacks in a single bottom row.

| Control | Type | Size | Notes |
|---|---|---|---|
| FREQ 1 / 2 / 3 | Knob | Large | Center frequency per group |
| FEED 1 / 2 / 3 | Knob | Medium | Feedback amount per group |
| DRIVE 1 / 2 / 3 | Knob | Medium | Distortion drive per group |
| FREQ ATT 1/2/3 | Attenuverter | Narrow tall | Above FREQ CV jacks |
| FEED ATT 1/2/3 | Attenuverter | Narrow tall | Above FEED CV jacks |
| DRIVE ATT 1/2/3 | Attenuverter | Narrow tall | Above DRIVE CV jacks |
| FREQ CV 1/2/3 | Input jack | — | CV override for FREQ per group |
| FEED CV 1/2/3 | Input jack | — | CV override for FEED per group |
| DRIVE CV 1/2/3 | Input jack | — | CV override for DRIVE per group |

Layout (top to bottom):
```
COMB / DISTORTION
──────────────────────────────────────────────────────────
[FREQ 1]  [FEED 1]  [DRIVE 1] | [FREQ 2]  [FEED 2]  [DRIVE 2] | [FREQ 3]  [FEED 3]  [DRIVE 3]


[ATT]  [ATT]  [ATT]  [ATT]  [ATT]  [ATT]  [ATT]  [ATT]  [ATT]
[CV]   [CV]   [CV]   [CV]   [CV]   [CV]   [CV]   [CV]   [CV]
 F1    Fb1    Dr1    F2     Fb2    Dr2    F3     Fb3    Dr3
```

---

### Zone 3: LP 1 (5 HP, full height)

| Control | Type | Size | Notes |
|---|---|---|---|
| CUTOFF | Knob | Large | Filter cutoff frequency |
| RESONANCE | Knob | Medium | Filter resonance / Q |
| CUTOFF ATT | Attenuverter | Narrow tall | Above CUTOFF CV jack |
| RESONANCE ATT | Attenuverter | Narrow tall | Above RESONANCE CV jack |
| CUTOFF CV | Input jack | — | CV override for cutoff |
| RESONANCE CV | Input jack | — | CV override for resonance |

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

### Zone 4: LP 2 (5 HP, full height)

Same layout as LP 1 but both knobs are medium size (LP2 is the secondary filter stage).

| Control | Type | Size | Notes |
|---|---|---|---|
| CUTOFF | Knob | Medium | Filter cutoff frequency |
| RESONANCE | Knob | Medium | Filter resonance / Q |
| CUTOFF ATT | Attenuverter | Narrow tall | Above CUTOFF CV jack |
| RESONANCE ATT | Attenuverter | Narrow tall | Above RESONANCE CV jack |
| CUTOFF CV | Input jack | — | CV override for cutoff |
| RESONANCE CV | Input jack | — | CV override for resonance |

---

### Zone 5: HP + OUT (6 HP, full height)

| Control | Type | Size | Notes |
|---|---|---|---|
| CUTOFF | Knob | Medium | HP filter cutoff frequency |
| RESONANCE | Knob | Medium | HP filter resonance / Q |
| CUTOFF ATT | Attenuverter | Narrow tall | Above CUTOFF CV jack |
| RESONANCE ATT | Attenuverter | Narrow tall | Above RESONANCE CV jack |
| CUTOFF CV | Input jack | — | CV override for cutoff |
| RESONANCE CV | Input jack | — | CV override for resonance |
| L OUT | Output jack | — | Stereo audio output left |
| R OUT | Output jack | — | Stereo audio output right |

Layout:
```
HP + OUT
──────────────────
[CUTOFF]

[RESONANCE]

[ATT]   [ATT]
[CV]  [CV]  [L]  [R]
```

All four jacks in a single bottom row across 6HP.

---

## Open Questions

- Exact control coordinates (HP column + mm from top) — pending panel.svg
- Panel material and finish — TBD
- Silk-screen font and size — TBD
- VCV Rack panel SVG — to be derived from this document
