# POGO — Module Overview

**48HP stereo Eurorack complex filter**  
VCV Rack 2 plugin version is the design ground truth. Hardware specs are reverse-engineered from DSP code.

---

## Signal Chain

```
Stereo Input (L + R)
  │
  ├── [block-A]  Input Buffers       100Ω series + BAT54S clamp; LM4562 unity-gain followers
  ├── [block-1]  Pre-Gain            GAIN_MAIN switch 1× / 5× (NE5532D); clip at ±10.5V
  │              ALT_BP path ─────────────────────────────────────────────────────────────────┐
  ├── [block-4]  VCA                 THAT 2180 dB-law; VCA_AMT bipolar att; VCA_OFS CV floor │
  ├── [block-5]  LP Filter 1         OTA-C SVF; LP1_FREQ, LP1_TILT (±5V/oct stereo), LP1_RES│
  │              ← ALT path joins here ←────────────────────────────────────────────────────┘
  ├── [block-6]  Triple BP + Dist    3× 4→2-pole OTA-C SVF formant filters (F1/F2/F3)
  │                                  BP_OFFSET (master), BP_MIX (dry/wet), BP_POL, BP_DIST
  │                                  Per-group: FREQ, FOCUS (Q), DRIVE; BP_TILT (stereo spread)
  │                                  Distortion: SC/HC/FOLD; CD4053 mux; 2× oversampled in DSP
  │                                  BP3_L/R output tap (post-distortion, pre-mix)
  ├── [block-7]  HP Filter           OTA-C SVF; HP_FREQ (slider, default −3V → ~80Hz), HP_RES
  ├── [block-8]  LP Filter 2         OTA-C SVF; LP2_FREQ (slider, default +2V → ~2.5kHz), LP2_RES
  └── [block-B]  Output Buffers      TL072 unity followers → 1kΩ → MAIN_L/R + BP3_L/R jacks

────────────────────────────────────────────────────────────────────────────────────────
MODULATION (parallel)
────────────────────────────────────────────────────────────────────────────────────────
  [block-2]  Dual LFO  →  LFO1 (±5V triangle, 0.05–20 Hz), LFO2 (same, independent)
  [block-3]  Mod Bus   →  LFO1 normalizes into MOD_IN; MOD_SCALE (0.2–5×), MOD_OFFSET (±5V)
                          Bus → 20 CV destinations (each: override jack + attenuverter trimpot)
                          LEDs: MOD_CLIP, MOD_POS, MOD_NEG
```

---

## Block Summary

| Block | Name | Board(s) | Phase 1R | Phase 2R | Phase 3R |
|---|---|---|---|---|---|
| A | Input Buffer | audio | ✅ | ✅ | ✅ |
| 1 | Pre-Gain | audio | ✅ | ✅ | ✅ |
| 2 | Dual LFO | utility | ✅ | ✅ | 🔲 |
| 3 | Mod Bus | utility/control | ✅ | ✅ | 🔲 |
| 4 | VCA | audio | ✅ | ✅ ⚠️ | ✅ |
| 5 | LP Filter 1 | audio | ✅ | ✅ | ✅ |
| 6 | Triple BP + Dist | audio | ✅ | ✅ | 🔲 |
| 7 | HP Filter | audio | ✅ | ✅ | ✅ |
| 8 | LP Filter 2 | audio | ✅ | ✅ | ✅ |
| B | Output Buffer | audio | ✅ | ✅ | ✅ |

⚠️ Block 4: DSP is linear VCA; hardware uses THAT 2180 (dB-law). Intentional deviation — documented in specs/block-4/spec.md.

---

## Parameters (46 total)

| Param | Block | Type | Range | Default |
|---|---|---|---|---|
| GAIN_MAIN_PARAM | 1 | switch | 0/1 | 0 (1×) |
| GAIN_BP3_PARAM | 1 | switch | 0/1 | 0 (1×) |
| LFO1_RATE_PARAM | 2 | knob | 0–1 | 0.3 |
| LFO2_RATE_PARAM | 2 | knob | 0–1 | 0.3 |
| MOD_SCALE_PARAM | 3 | trimpot | 0–1 | 0.5 (≈1×) |
| MOD_OFFSET_PARAM | 3 | trimpot | −1–1 | 0 |
| VCA_AMT_PARAM | 4 | trimpot | −1–1 | 0 |
| VCA_OFS_PARAM | 4 | trimpot | 0–1 | 0.5 |
| LP1_FREQ_PARAM | 5 | xl knob | −5–5 V/oct | 0 |
| LP1_TILT_PARAM | 5 | large knob | −1–1 | 0 |
| LP1_RES_PARAM | 5 | large knob | 0–1 | 0 |
| LP1_FREQ_ATT_PARAM | 5 | trimpot | −1–1 | 0 |
| LP1_TILT_ATT_PARAM | 5 | trimpot | −1–1 | 0 |
| LP1_RES_ATT_PARAM | 5 | trimpot | −1–1 | 0 |
| BP_POL_PARAM | 6 | switch | 0/1 | 0 (+) |
| BP_DIST_PARAM | 6 | switch | 0/1/2 | 0 (Soft) |
| BP_OFFSET_PARAM | 6 | xl knob | −5–5 V/oct | 0 |
| BP_MIX_PARAM | 6 | large knob | 0–1 | 0.5 |
| BP_FREQ_ATT_PARAM | 6 | trimpot | −1–1 | 0 |
| BP_TILT_ATT_PARAM | 6 | trimpot | −1–1 | 0 |
| BP1_FREQ_PARAM | 6 | knob | −5–5 V/oct | 0 (→200Hz) |
| BP1_FOCUS_PARAM | 6 | knob | 0–1 | 0 |
| BP1_DIST_PARAM | 6 | knob | 0–1 | 0.20 |
| BP1_FREQ_ATT_PARAM | 6 | trimpot | −1–1 | 0 |
| BP1_FOCUS_ATT_PARAM | 6 | trimpot | −1–1 | 0 |
| BP1_DIST_ATT_PARAM | 6 | trimpot | −1–1 | 0 |
| BP2_FREQ_PARAM | 6 | knob | −5–5 V/oct | 0 (→1500Hz) |
| BP2_FOCUS_PARAM | 6 | knob | 0–1 | 0 |
| BP2_DIST_PARAM | 6 | knob | 0–1 | 0.20 |
| BP2_FREQ_ATT_PARAM | 6 | trimpot | −1–1 | 0 |
| BP2_FOCUS_ATT_PARAM | 6 | trimpot | −1–1 | 0 |
| BP2_DIST_ATT_PARAM | 6 | trimpot | −1–1 | 0 |
| BP3_FREQ_PARAM | 6 | knob | −5–5 V/oct | 0 (→6000Hz) |
| BP3_FOCUS_PARAM | 6 | knob | 0–1 | 0 |
| BP3_DIST_PARAM | 6 | knob | 0–1 | 0.20 |
| BP3_FREQ_ATT_PARAM | 6 | trimpot | −1–1 | 0 |
| BP3_FOCUS_ATT_PARAM | 6 | trimpot | −1–1 | 0 |
| BP3_DIST_ATT_PARAM | 6 | trimpot | −1–1 | 0 |
| HP_FREQ_PARAM | 7 | slider | −5–5 V/oct | −3 (→~80Hz) |
| HP_RES_PARAM | 7 | slider | 0–1 | 0 |
| HP_FREQ_ATT_PARAM | 7 | trimpot | −1–1 | 0 |
| HP_RES_ATT_PARAM | 7 | trimpot | −1–1 | 0 |
| LP2_FREQ_PARAM | 8 | slider | −5–5 V/oct | +2 (→~2.5kHz) |
| LP2_RES_PARAM | 8 | slider | 0–1 | 0 |
| LP2_FREQ_ATT_PARAM | 8 | trimpot | −1–1 | 0 |
| LP2_RES_ATT_PARAM | 8 | trimpot | −1–1 | 0 |

---

## I/O (24 inputs, 6 outputs, 5 lights)

### Inputs
| Input | Block | Notes |
|---|---|---|
| L_IN_INPUT, R_IN_INPUT | A | Audio; R normalizes to L |
| ALT_BP_L_INPUT, ALT_BP_R_INPUT | 1 | Bypass VCA+LP1; feed BP directly |
| MOD_INPUT | 3 | Normalizes to LFO1 when unpatched |
| VCA_INPUT | 4 | Normalizes to mod bus |
| LP1_FREQ_INPUT, LP1_TILT_INPUT, LP1_RES_INPUT | 5 | Mod bus override jacks |
| BP_FREQ_INPUT, BP_TILT_INPUT | 6 | Master BP mod override jacks |
| BP1_FREQ_INPUT, BP1_FOCUS_INPUT, BP1_DIST_INPUT | 6 | BP1 group override jacks |
| BP2_FREQ_INPUT, BP2_FOCUS_INPUT, BP2_DIST_INPUT | 6 | BP2 group override jacks |
| BP3_FREQ_INPUT, BP3_FOCUS_INPUT, BP3_DIST_INPUT | 6 | BP3 group override jacks |
| HP_FREQ_INPUT, HP_RES_INPUT | 7 | HP mod override jacks |
| LP2_FREQ_INPUT, LP2_RES_INPUT | 8 | LP2 mod override jacks |

### Outputs
| Output | Block | Notes |
|---|---|---|
| LFO1_OUTPUT, LFO2_OUTPUT | 2 | ±5V triangle |
| BP3_L_OUTPUT, BP3_R_OUTPUT | B | BP3 post-distortion tap (before BP_MIX) |
| MAIN_L_OUTPUT, MAIN_R_OUTPUT | B | Full signal chain output (LP2 → output buffer) |

### Lights
| Light | Block | Function |
|---|---|---|
| LFO1_LIGHT, LFO2_LIGHT | 2 | Brightness tracks LFO output |
| MOD_CLIP_LIGHT | 3 | |busV| ≥ 9.9V |
| MOD_POS_LIGHT | 3 | busV > 0 |
| MOD_NEG_LIGHT | 3 | busV < 0 |

---

## Modulation Destinations (20 total)

| # | Destination | Block | Param | Input | Att |
|---|---|---|---|---|---|
| 1 | VCA Level | 4 | VCA_AMT_PARAM | VCA_INPUT | (none — amt is the att) |
| 2 | LP1 Freq | 5 | LP1_FREQ_PARAM | LP1_FREQ_INPUT | LP1_FREQ_ATT_PARAM |
| 3 | LP1 Tilt | 5 | LP1_TILT_PARAM | LP1_TILT_INPUT | LP1_TILT_ATT_PARAM |
| 4 | LP1 Res | 5 | LP1_RES_PARAM | LP1_RES_INPUT | LP1_RES_ATT_PARAM |
| 5 | BP Offset | 6 | BP_OFFSET_PARAM | BP_FREQ_INPUT | BP_FREQ_ATT_PARAM |
| 6 | BP Tilt | 6 | — | BP_TILT_INPUT | BP_TILT_ATT_PARAM |
| 7 | BP1 Freq | 6 | BP1_FREQ_PARAM | BP1_FREQ_INPUT | BP1_FREQ_ATT_PARAM |
| 8 | BP1 Focus | 6 | BP1_FOCUS_PARAM | BP1_FOCUS_INPUT | BP1_FOCUS_ATT_PARAM |
| 9 | BP1 Drive | 6 | BP1_DIST_PARAM | BP1_DIST_INPUT | BP1_DIST_ATT_PARAM |
| 10 | BP2 Freq | 6 | BP2_FREQ_PARAM | BP2_FREQ_INPUT | BP2_FREQ_ATT_PARAM |
| 11 | BP2 Focus | 6 | BP2_FOCUS_PARAM | BP2_FOCUS_INPUT | BP2_FOCUS_ATT_PARAM |
| 12 | BP2 Drive | 6 | BP2_DIST_PARAM | BP2_DIST_INPUT | BP2_DIST_ATT_PARAM |
| 13 | BP3 Freq | 6 | BP3_FREQ_PARAM | BP3_FREQ_INPUT | BP3_FREQ_ATT_PARAM |
| 14 | BP3 Focus | 6 | BP3_FOCUS_PARAM | BP3_FOCUS_INPUT | BP3_FOCUS_ATT_PARAM |
| 15 | BP3 Drive | 6 | BP3_DIST_PARAM | BP3_DIST_INPUT | BP3_DIST_ATT_PARAM |
| 16 | HP Freq | 7 | HP_FREQ_PARAM | HP_FREQ_INPUT | HP_FREQ_ATT_PARAM |
| 17 | HP Res | 7 | HP_RES_PARAM | HP_RES_INPUT | HP_RES_ATT_PARAM |
| 18 | LP2 Freq | 8 | LP2_FREQ_PARAM | LP2_FREQ_INPUT | LP2_FREQ_ATT_PARAM |
| 19 | LP2 Res | 8 | LP2_RES_PARAM | LP2_RES_INPUT | LP2_RES_ATT_PARAM |

VCA_OFS_PARAM is a fixed trimpot — no mod destination, no CV input.

---

## Power Budget (Estimate)

| Block | +12V | −12V |
|---|---|---|
| A (Input Buffer) | ~2 mA | ~2 mA |
| 1 (Pre-Gain) | ~20 mA | ~20 mA |
| 2 (Dual LFO) | ~4 mA | ~4 mA |
| 3 (Mod Bus) | ~42 mA | ~42 mA |
| 4 (VCA) | ~5 mA | ~5 mA |
| 5 (LP1) | ~12 mA | ~12 mA |
| 6 (BP + Dist) | ~25 mA | ~25 mA |
| 7 (HP) | ~10 mA | ~10 mA |
| 8 (LP2) | ~12 mA | ~12 mA |
| B (Output Buffer) | ~4 mA | ~4 mA |
| **Total** | **~136 mA** | **~136 mA** |

This is a high-current module. Use a powered bus with ≥250 mA capacity per rail.

---

## Board Architecture

Three PCBs:
- **Audio board**: all signal-path ICs (input buffer, pre-gain, VCA, LP1, BP+DIST, HP, LP2, output buffer)
- **Control board**: all pots, switches, jacks facing the panel
- **Utility board**: LFO circuits, mod bus processor, attenuverter stages

See `specs/board-layout/layout-notes.md` for detailed board layout analysis.
See `tools/panel-data.yaml` for panel positions (source of truth).
