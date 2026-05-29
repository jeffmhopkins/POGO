# POGO — Module Overview

**48HP stereo Eurorack complex filter**  
VCV Rack 2 plugin version is the design ground truth. Hardware specs are reverse-engineered from DSP code.

---

## Signal Chain

```
Stereo Input (L + R)
  │
  ├── [block-A]  Input Buffers       100Ω series + BAT54S clamp; OPA1612 unity-gain followers
  ├── [block-1]  Pre-Gain            GAIN switch 1× / 5× (OPA1612); clip at ±10.5V
  │              ALT_BP path ─────────────────────────────────────────────────────────────────┐
  ├── [block-4]  VCA                 THAT 2180 dB-law; VCA_AMT bipolar att; VCA_OFS CV floor │
  ├── [block-5]  LP Filter 1         OTA-C SVF; LP1_FREQ, LP1_TILT (±5V/oct stereo), LP1_RES│
  │              ← ALT path joins here ←────────────────────────────────────────────────────┘
  ├── [block-6]  Triple BP + Dist    3× 2-pole OTA-C SVF bandpass resonators (~50Hz–3.2kHz each)
  │                                  Master: BP_OFFSET, BP_TILT, BP_BYPASS (dry level), BP_WET
  │                                  Per-band: FREQ, FOCUS (Q), TILT, DIST drive, DIST_MODE switch
  │                                  Distortion per band: SC/HC/WF; CLIP LED per band
  │                                  bpOut = bandIn×bypass + wetSum×wet  (additive, not crossfade)
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

## Parameters (48 total)

| Param | Block | Type | Range | Default |
|---|---|---|---|---|
| GAIN_PARAM | 1 | toggle_dw3 | 0/1 | 0 (1×) |
| ALT_GAIN_PARAM | 1 | toggle_dw3 | 0/1 | 0 (1×) |
| LFO1_RATE_PARAM | 2 | trimpot | 0–1 | 0.3 |
| LFO2_RATE_PARAM | 2 | trimpot | 0–1 | 0.3 |
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
| BP_TILT_PARAM | 6 | medium knob | −1–1 | 0 |
| BP_OFFSET_PARAM | 6 | medium knob | −1.1–1.1 V/oct | 0 |
| BP_BYPASS_PARAM | 6 | medium knob | 0–1 | 1.0 |
| BP_WET_PARAM | 6 | medium knob | 0–1 | 1.0 |
| BP_FREQ_ATT_PARAM | 6 | trimpot | −1–1 | 0 |
| BP_TILT_ATT_PARAM | 6 | trimpot | −1–1 | 0 |
| BP1_DIST_MODE_PARAM | 6 | toggle_dw5 | 0/1/2 | 0 (SC) |
| BP1_FREQ_PARAM | 6 | xl knob | ±3.32 V/oct | 0 (→400Hz) |
| BP1_FOCUS_PARAM | 6 | large knob | 0–1 | 0 |
| BP1_TILT_PARAM | 6 | large knob | −1–1 | 0 |
| BP1_DIST_PARAM | 6 | large knob | 0–1 | 0.20 |
| BP1_FREQ_ATT_PARAM | 6 | trimpot | −1–1 | 0 |
| BP1_TILT_ATT_PARAM | 6 | trimpot | −1–1 | 0 |
| BP1_DIST_ATT_PARAM | 6 | trimpot | −1–1 | 0 |
| BP2_DIST_MODE_PARAM | 6 | toggle_dw5 | 0/1/2 | 0 (SC) |
| BP2_FREQ_PARAM | 6 | xl knob | ±3.32 V/oct | 0 (→400Hz) |
| BP2_FOCUS_PARAM | 6 | large knob | 0–1 | 0 |
| BP2_TILT_PARAM | 6 | large knob | −1–1 | 0 |
| BP2_DIST_PARAM | 6 | large knob | 0–1 | 0.20 |
| BP2_FREQ_ATT_PARAM | 6 | trimpot | −1–1 | 0 |
| BP2_TILT_ATT_PARAM | 6 | trimpot | −1–1 | 0 |
| BP2_DIST_ATT_PARAM | 6 | trimpot | −1–1 | 0 |
| BP3_DIST_MODE_PARAM | 6 | toggle_dw5 | 0/1/2 | 0 (SC) |
| BP3_FREQ_PARAM | 6 | xl knob | ±3.32 V/oct | 0 (→400Hz) |
| BP3_FOCUS_PARAM | 6 | large knob | 0–1 | 0 |
| BP3_TILT_PARAM | 6 | large knob | −1–1 | 0 |
| BP3_DIST_PARAM | 6 | large knob | 0–1 | 0.20 |
| BP3_FREQ_ATT_PARAM | 6 | trimpot | −1–1 | 0 |
| BP3_TILT_ATT_PARAM | 6 | trimpot | −1–1 | 0 |
| BP3_DIST_ATT_PARAM | 6 | trimpot | −1–1 | 0 |
| HP_FREQ_PARAM | 7 | slider | −5–5 V/oct | −3 (→~80Hz) |
| HP_RES_PARAM | 7 | trimpot | 0–1 | 0 |
| HP_FREQ_ATT_PARAM | 7 | trimpot | −1–1 | 0 |
| HP_RES_ATT_PARAM | 7 | trimpot | −1–1 | 0 |
| LP2_FREQ_PARAM | 8 | slider | −5–5 V/oct | +2 (→~2.5kHz) |
| LP2_RES_PARAM | 8 | trimpot | 0–1 | 0 |
| LP2_FREQ_ATT_PARAM | 8 | trimpot | −1–1 | 0 |
| LP2_RES_ATT_PARAM | 8 | trimpot | −1–1 | 0 |

---

## I/O (24 inputs, 6 outputs, 8 lights)

### Inputs
| Input | Block | Notes |
|---|---|---|
| L_IN_INPUT, R_IN_INPUT | A | Audio; R normalizes to L |
| ALT_BP_L_INPUT, ALT_BP_R_INPUT | 1 | Bypass VCA+LP1; feed BP directly |
| MOD_INPUT | 3 | Normalizes to LFO1 when unpatched |
| VCA_INPUT | 4 | Normalizes to mod bus |
| LP1_FREQ_INPUT, LP1_TILT_INPUT, LP1_RES_INPUT | 5 | Mod bus override jacks |
| BP_FREQ_INPUT, BP_TILT_INPUT | 6 | Master BP offset + tilt CV override jacks |
| BP1_FREQ_INPUT, BP1_TILT_INPUT, BP1_DIST_INPUT | 6 | BP1 per-band override jacks |
| BP2_FREQ_INPUT, BP2_TILT_INPUT, BP2_DIST_INPUT | 6 | BP2 per-band override jacks |
| BP3_FREQ_INPUT, BP3_TILT_INPUT, BP3_DIST_INPUT | 6 | BP3 per-band override jacks |
| HP_FREQ_INPUT, HP_RES_INPUT | 7 | HP mod override jacks |
| LP2_FREQ_INPUT, LP2_RES_INPUT | 8 | LP2 mod override jacks |

### Outputs
| Output | Block | Notes |
|---|---|---|
| LFO1_OUTPUT, LFO2_OUTPUT | 2 | ±5V triangle |
| BP3_L_OUTPUT, BP3_R_OUTPUT | B | BP3 post-distortion tap (before BP mix) |
| MAIN_L_OUTPUT, MAIN_R_OUTPUT | B | Full signal chain output (LP2 → output buffer) |

### Lights
| Light | Block | Function |
|---|---|---|
| LFO1_LIGHT, LFO2_LIGHT | 2 | Brightness tracks LFO output |
| MOD_CLIP_LIGHT | 3 | \|busV\| ≥ 9.9V |
| MOD_POS_LIGHT | 3 | busV > 0 |
| MOD_NEG_LIGHT | 3 | busV < 0 |
| BP1_CLIP_LIGHT | 6 | BP1 distortion output > ±4V |
| BP2_CLIP_LIGHT | 6 | BP2 distortion output > ±4V |
| BP3_CLIP_LIGHT | 6 | BP3 distortion output > ±4V |

---

## Modulation Destinations (19 total)

| # | Destination | Block | Param | Input | Att |
|---|---|---|---|---|---|
| 1 | VCA Level | 4 | VCA_AMT_PARAM | VCA_INPUT | (none — amt is the att) |
| 2 | LP1 Freq | 5 | LP1_FREQ_PARAM | LP1_FREQ_INPUT | LP1_FREQ_ATT_PARAM |
| 3 | LP1 Tilt | 5 | LP1_TILT_PARAM | LP1_TILT_INPUT | LP1_TILT_ATT_PARAM |
| 4 | LP1 Res | 5 | LP1_RES_PARAM | LP1_RES_INPUT | LP1_RES_ATT_PARAM |
| 5 | BP Offset | 6 | BP_OFFSET_PARAM | BP_FREQ_INPUT | BP_FREQ_ATT_PARAM |
| 6 | BP Tilt | 6 | BP_TILT_PARAM | BP_TILT_INPUT | BP_TILT_ATT_PARAM |
| 7 | BP1 Freq | 6 | BP1_FREQ_PARAM | BP1_FREQ_INPUT | BP1_FREQ_ATT_PARAM |
| 8 | BP1 Tilt | 6 | BP1_TILT_PARAM | BP1_TILT_INPUT | BP1_TILT_ATT_PARAM |
| 9 | BP1 Drive | 6 | BP1_DIST_PARAM | BP1_DIST_INPUT | BP1_DIST_ATT_PARAM |
| 10 | BP2 Freq | 6 | BP2_FREQ_PARAM | BP2_FREQ_INPUT | BP2_FREQ_ATT_PARAM |
| 11 | BP2 Tilt | 6 | BP2_TILT_PARAM | BP2_TILT_INPUT | BP2_TILT_ATT_PARAM |
| 12 | BP2 Drive | 6 | BP2_DIST_PARAM | BP2_DIST_INPUT | BP2_DIST_ATT_PARAM |
| 13 | BP3 Freq | 6 | BP3_FREQ_PARAM | BP3_FREQ_INPUT | BP3_FREQ_ATT_PARAM |
| 14 | BP3 Tilt | 6 | BP3_TILT_PARAM | BP3_TILT_INPUT | BP3_TILT_ATT_PARAM |
| 15 | BP3 Drive | 6 | BP3_DIST_PARAM | BP3_DIST_INPUT | BP3_DIST_ATT_PARAM |
| 16 | HP Freq | 7 | HP_FREQ_PARAM | HP_FREQ_INPUT | HP_FREQ_ATT_PARAM |
| 17 | HP Res | 7 | HP_RES_PARAM | HP_RES_INPUT | HP_RES_ATT_PARAM |
| 18 | LP2 Freq | 8 | LP2_FREQ_PARAM | LP2_FREQ_INPUT | LP2_FREQ_ATT_PARAM |
| 19 | LP2 Res | 8 | LP2_RES_PARAM | LP2_RES_INPUT | LP2_RES_ATT_PARAM |

VCA_OFS_PARAM is a fixed trimpot — no mod destination, no CV input.
BP_BYPASS_PARAM and BP_WET_PARAM are panel knobs only — no mod bus destination.

---

## Power Budget (Estimate)

| Block | +12V | −12V | Dominant draw |
|---|---|---|---|
| A (Input Buffer) | ~6 mA | ~6 mA | 1× OPA1612 |
| 1 (Pre-Gain) | ~11 mA | ~11 mA | 2× OPA1612 @ 5.5 mA ea |
| 2 (Dual LFO) | ~5 mA | ~5 mA | 2× TL072CDT @ 2.6 mA ea |
| 3 (Mod Bus) | ~18 mA | ~18 mA | 7× TL074CDT @ 2.6 mA ea (±12V actual) |
| 4 (VCA) | ~11 mA | ~11 mA | 2× THAT 2180 @ 4 mA ea |
| 5 (LP1) | ~27 mA | ~27 mA | 3× LM13700M + 2× OPA1612 |
| 6 (BP + Dist) | ~104 mA | ~104 mA | 17× TL072CDT (SC+HC shared) + 6× OPA1612 + 6× LM13700M |
| 7 (HP) | ~27 mA | ~27 mA | 3× LM13700M + 2× OPA1612 |
| 8 (LP2) | ~23 mA | ~23 mA | 2× LM13700M + 2× OPA1612 |
| B (Output Buffer) | ~5 mA | ~5 mA | 2× TL072CDT @ 2.6 mA ea |
| **Total** | **~237 mA** | **~237 mA** | |

Use a powered bus with **≥300 mA capacity per rail**; 350 mA preferred for headroom.
Per-block details in each block spec's Power Draw Estimate section.

Key reductions vs first-pass estimate: (1) SC+HC distortion paths share one TL072CDT per
group/channel, eliminating 6 ICs from block-6; (2) NE5532D replaced by OPA1612 in block-1
(better noise, lower power); (3) TL072/TL074 Icc corrected to ±12V operating figures (~2.6
mA/pkg) from ±15V datasheet specs.

Thermal note: all OPA1612 in SOIC-8 dissipate ~132 mW — within limits with standard copper pour.

---

## Board Architecture

Three PCBs:
- **Audio board**: all signal-path ICs (input buffer, pre-gain, VCA, LP1, BP+DIST, HP, LP2, output buffer)
- **Control board**: all pots, switches, jacks facing the panel
- **Utility board**: LFO circuits, mod bus processor, attenuverter stages

See `specs/board-layout/layout-notes.md` for detailed board layout analysis.
See `tools/panel-data.yaml` for panel positions (source of truth).
