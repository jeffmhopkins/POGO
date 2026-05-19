# POGO Panel Design Notes

## Target Width: 50 HP

1 HP = 5.08 mm → total panel width = 254 mm

---

## Zone Layout (left to right)

```
┌──────────────┬─────────────┬───────┬───────┬───────┬──────────────┬───────┬───────┬──────────────┐
│   5 HP       │    5 HP     │  5 HP │  5 HP │  5 HP │    9 HP      │  5 HP │  5 HP │    6 HP      │
│   STACKED    │  B3 SHARED  │ COMB1 │ COMB2 │ COMB3 │  DISTORTION  │  LP1  │  LP2  │  HP + OUT    │
│  (3 zones)   │             │       │       │       │              │       │       │              │
└──────────────┴─────────────┴───────┴───────┴───────┴──────────────┴───────┴───────┴──────────────┘
```

---

## Zone Definitions

### Zone 0: Stacked Left Section (5 HP, full height, 3 vertical mini-zones)

Single column, 5 HP wide (25.4 mm), 128.5 mm tall, divided into 3 equal stacked mini-zones
each approximately 42 mm tall.

| Stack position | Block | Contents |
|---|---|---|
| Top | Block A + Block 1 | L/R audio input jacks, pre-gain switch |
| Middle | Block 2 | Attack, Release, ENV OUT L/R jacks, MOD SOURCE SEL switch |
| Bottom | Mod Bus | Primary mod source jack, AMOUNT, OFFSET |

---

### Zone 1: Block 3 Shared (5 HP)

Shared controls for the triple comb filter — applies to all three comb groups.

Controls: DRY/WET, BLEND, STEREO WIDTH, SOURCE switch, POLARITY switch
Mod: DRY/WET attenuverter + CV jack, BLEND attenuverter + CV jack

---

### Zone 2: Comb 1 (5 HP)

Low formant group (~100 Hz – 1 kHz).

Controls: FREQ 1 knob, FEEDBACK 1 knob
Mod: FREQ 1 attenuverter + CV jack, FEEDBACK 1 attenuverter + CV jack

---

### Zone 3: Comb 2 (5 HP)

Mid formant group (~500 Hz – 5 kHz).

Controls: FREQ 2 knob, FEEDBACK 2 knob
Mod: FREQ 2 attenuverter + CV jack, FEEDBACK 2 attenuverter + CV jack

---

### Zone 4: Comb 3 (5 HP)

High formant group (~2 kHz – 20 kHz).

Controls: FREQ 3 knob, FEEDBACK 3 knob
Mod: FREQ 3 attenuverter + CV jack, FEEDBACK 3 attenuverter + CV jack

---

### Zone 5: Distortion (9 HP)

Three independent drive stages (one per comb group output), plus global mode selection.
3-column internal layout — one column per comb group.

| Column | Contents |
|---|---|
| Left (Comb 1 drive) | DRIVE 1 knob, DRIVE 1 attenuverter, DRIVE 1 CV jack |
| Center (Comb 2 drive) | DRIVE 2 knob, DRIVE 2 attenuverter, DRIVE 2 CV jack |
| Right (Comb 3 drive) | DRIVE 3 knob, DRIVE 3 attenuverter, DRIVE 3 CV jack |
| Shared (top area) | MODE switch |

---

### Zone 6: LP Filter 1 (5 HP)

Resonant low-pass filter, first stage.

Controls: CUTOFF knob, RESONANCE knob
Mod: CUTOFF attenuverter + CV jack, RESONANCE attenuverter + CV jack

---

### Zone 7: LP Filter 2 (5 HP)

Resonant low-pass filter, second stage (different topology).

Controls: CUTOFF knob, RESONANCE knob
Mod: CUTOFF attenuverter + CV jack, RESONANCE attenuverter + CV jack

---

### Zone 8: HP Filter + Output (6 HP)

High-pass filter plus stereo audio outputs.

Controls: CUTOFF knob, RESONANCE knob
Mod: CUTOFF attenuverter + CV jack, RESONANCE attenuverter + CV jack
Output: L OUT jack, R OUT jack (audio output, bottom row)

---

## General Layout Paradigm

### Knob sizes — 3 tiers
- **Attenuverter**: narrow tall style (e.g. Rogan 1S or equivalent pointer knob)
- **Medium**: secondary parameters (feedback, resonance, blend, offset, amount)
- **Large**: primary parameters (cutoff, freq, drive, dry/wet, attack, release)

### Jack color coding
None — all jacks uniform hardware finish.

### Attenuverter center detent
Panel marking only — no physical detent in the pot.

### Label placement
- Control labels: text below the knob or jack
- Zone name: labeled at the top of the zone in silk-screen

### Zone separator style
Silk-screen lines between zones, similar to Pittsburgh Modular SV-1b treatment.

### LED indicators
TBD — zone by zone.

---

## Open Questions

- Exact control coordinates (HP column + mm from top) — to be determined zone by zone
- Panel material and finish — TBD
- Silk-screen font and size — TBD
- VCV Rack panel SVG — to be derived from this document
