# Block 4: Distortion

## Status
- Phase 1 (Audio Spec): [x] complete
- Phase 2 (Analog Model): [x] complete
- Phase 3 (Circuit Design): [x] complete

---

## Phase 1: Audio / Functional Specification

### Sonic Intent
Three selectable distortion characters, each with its own DRIVE control, applied symmetrically
to L and R channels. Placed after the comb filter, the distortion interacts with the harmonic
peaks the APF section created — pushing those formants into saturation, spreading harmonics, or
folding the waveform back on itself.

- **Mode 1 — Soft Clip**: Gentle, musical saturation. Adds warmth and odd harmonics. The signal
  rounds off smoothly at the clip threshold. Sounds like a tube pre-amp at moderate drive; at
  maximum drive approaches fuzz territory. Sweet spot: DRIVE at 30–60%.
- **Mode 2 — Hard Clip**: Aggressive, transistor-style clipping. Signal hits a hard ceiling and
  flattens. Adds strong odd harmonics and a rasping, buzzy quality. At maximum drive: nearly
  square wave. Sweet spot: DRIVE at 20–50% for edge; higher for full fuzz.
- **Mode 3 — Wavefold**: Buchla-style wavefolding. The signal folds back on itself each time it
  exceeds the fold threshold. At low drive the effect is subtle (one fold); at high drive multiple
  folds produce complex, metallic, east-coast synthesis textures. Sounds unlike clipping — the
  waveform increases in harmonic complexity rather than limiting. Sweet spot: DRIVE at 40–75%.

### Parameters

| Name | Range | Default | Taper | Description |
|---|---|---|---|---|
| MODE | Switch: 1 / 2 / 3 | 1 | N/A | Selects distortion type: Soft Clip / Hard Clip / Wavefold |
| DRIVE 1 | 0–100% | 30% | Logarithmic | Drive level for Soft Clip mode |
| DRIVE 2 | 0–100% | 20% | Logarithmic | Drive level for Hard Clip mode |
| DRIVE 3 | 0–100% | 40% | Logarithmic | Drive level for Wavefold mode |

Each DRIVE knob is always accessible on the panel; only the active mode's drive is in the
signal path. This allows presetting each mode and switching between them.

### CV Modulation Targets

| Target | CV Range | Attenuverter | Notes |
|---|---|---|---|
| DRIVE (active mode) | 0–10 V | Yes | Sweeps the active mode's drive amount; modulates the one currently selected |
| MODE | 0–10 V | No | 0–3.3 V = Mode 1; 3.3–6.6 V = Mode 2; 6.6–10 V = Mode 3 |

### Signal Levels (I/O)
- Input: ±5 V audio (from Block 3; APF section is unity gain so level is preserved)
- Output: ±5 V audio at low drive; distortion stages clip internally to ±5 V range at output
  - Output buffer (Block B) follows; keep output ≤ ±10 V at all drive settings

### Stereo Behavior
True stereo: L and R processed in parallel through identical circuits.
MODE switch and each DRIVE knob apply equally to both L and R (shared panel controls).
No independent L/R distortion controls.

### Edge Cases
- At DRIVE 100% (all modes): extreme harmonic generation; output may be near-clipped sine
  (Mode 1), square wave (Mode 2), or complex folded waveform (Mode 3). Ensure downstream
  filters (LP1, LP2, HP) can handle these waveforms without instability.
- MODE switching (live, with audio): brief click possible during mechanical switching. Accept
  this as a feature characteristic of analog switching. CV mode control is click-free.
- Silence input: all modes produce silence output regardless of DRIVE setting.

---

## Phase 2: Analog Behavior Model

### Mode 1: Soft Clip Transfer Function

```
y = tanh(d × x) / tanh(d)

where x = normalized input (−1 to +1 = ±5 V full scale)
      d = drive factor; d = exp(DRIVE_knob × k)   (log taper mapping)
      y = normalized output
```

- At d → 0: y ≈ x (linear pass-through)
- At d = 1: y = tanh(x) / tanh(1) — onset of soft saturation
- At d → ∞: y = sign(x) (hard limit — approaches Mode 2 at maximum)

Symmetrical clipping → primarily odd harmonics (3rd, 5th, 7th, ...).
Even harmonics negligible unless input DC offset present.

### Mode 2: Hard Clip Transfer Function

```
y = clamp(d × x, −1, +1)

where clamp(z, lo, hi) = max(lo, min(hi, z))
```

- At d = 1: clipping only occurs at ±full scale (±5 V); subtle effect
- At d = 5: clips at ±1V (±1 V input), strong rectangular waveform content
- At d → ∞: output approaches ±1 (square wave)

Symmetrical hard clip → strong odd harmonics with no even content.
Transition from linear to flat is abrupt (unlike Mode 1).

### Mode 3: Wavefold Transfer Function

```
y = fold(d × x)

fold(z) = 4/π × arcsin(sin(π/2 × z))   [triangle-wave folding approximation]
```

Alternative (piecewise): each time the signal exceeds ±1, it reflects back:
```
fold(z): if |z| ≤ 1: y = z
         if 1 < |z| ≤ 3: y = 2 − z (for positive z)
         if 3 < |z| ≤ 5: y = −4 + z (for positive z)
         ... (repeating)
```

- At d = 1: no folding (signal stays within ±1)
- At d = 2: single fold; signal that would exceed +1 is reflected back down
- At d = 4–5: multiple folds; complex spectral content

Wavefolding is asymmetric at odd drive levels and symmetric at even drive levels, producing
a mix of even and odd harmonics depending on DRIVE setting. This is the primary timbral
interest of this mode.

---

## Phase 3: Circuit Design

### Topology
Three parallel signal paths, switched by the MODE control:
- Each mode's circuit is always powered and idle when not selected
- The MODE switch (mechanical or CV-controlled) routes the signal through the active path
- CV mode control: comparator circuit with 3.3 V thresholds routes to one of three paths

#### Mode 1: Soft Clip — Diode Feedback Op-amp

```
V_in ──[R_in]──(−) TL072A ──── V_out
                 (+) = GND
                 (out)◄──[D1+D2 anti-parallel]──(−)
                 (out)◄──[R_f]──────────────────(−)
```

- D1, D2: matched 1N4148 diodes in anti-parallel across feedback resistor R_f
- At small signals: diodes do not conduct; gain = −R_f / R_in (linear amplifier)
- At large signals: diodes conduct, reducing effective feedback impedance → gain decreases
  → smooth saturation characteristic approximating tanh
- Drive (DRIVE 1 knob): varies R_in (input resistor), changing the gain and onset level

#### Mode 2: Hard Clip — Zener Clipping

```
V_in ──[R_drive]──(−) TL072B ──── V_out
                   (+) = GND
                   (out)◄──[R_f]──(−)
                   (out)──[Z1+Z2 anti-parallel zeners]──GND
```

- Z1, Z2: matched Zener diodes (BZX84-C5V1, 5.1 V, SOT-23) to set clip threshold at ~±5.1 V
- Op-amp provides gain, zeners hard-clip the output
- DRIVE 2 knob: varies input gain (R_drive), setting how much gain before the clip threshold
- Threshold is fixed at ±5.1 V; increasing DRIVE pushes more signal into the clip region

#### Mode 3: Wavefold — Cascaded Op-amp Folder

Classic Buchla/Serge-inspired wavefolder. Each fold stage inverts the portion of the signal
beyond the threshold:

```
Stage 1:
V_in ──[R1]──(+) TL072 ──── V_fold1
              (−)◄─────────────┘
              compare to V_thresh via diodes D3, D4

Stage 2: same topology, cascaded from V_fold1
...
```

Practical implementation: use a triangle-wave shaper with cascaded reflection stages.
Reference: MFOS Wavefolder / Buchla 259 wavefolder topology.
Two fold stages (requiring ~4 op-amp halves) produce musically useful fold depths.

DRIVE 3 knob: input gain before folding stages; higher drive = more folds active.

#### MODE Switch and CV Mode Control

**Mechanical switch**: 3-position rotary or sub-mini toggle (3-pos) routes V_in to one of
the three mode inputs via analog switch IC (CD4053 triple 2:1 mux, SOIC-16) or 3-position switch.

**CV Mode Control**: Voltage comparator chain:
- Comparator A (threshold 3.3 V): V_cv > 3.3 V → Mode 2 or 3
- Comparator B (threshold 6.6 V): V_cv > 6.6 V → Mode 3
- Logic drives CD4053 select inputs
- Use LM393 (dual comparator, SOIC-8) + basic logic

### IC / Component Selection

| Reference | Part Number | Package | Qty | Notes |
|---|---|---|---|---|
| DST1_L, DST1_R | TL072CDT | SOIC-8 | 2 | Soft clip op-amp (1 half per channel) |
| DST2_L, DST2_R | TL072CDT | SOIC-8 | 2 | Hard clip op-amp (1 half per channel) |
| DST3 | TL074CDT | SOIC-14 | 2 | Wavefold stages (2 halves per channel × 2 channels) |
| SW_MODE | CD4053 | SOIC-16 | 1 | Triple SPDT analog mux; routes signal to active mode |
| CMP_MODE | LM393D | SOIC-8 | 1 | Dual comparator for CV mode control |
| D1–D4 (Mode 1) | 1N4148WS | SOD-323 | 4 | Soft clip diodes (2 per channel: anti-parallel pair) |
| Z1–Z4 (Mode 2) | BZX84-C5V1 | SOT-23 | 4 | 5.1 V zeners (2 per channel: anti-parallel) |
| RV_DRV1_L/R | Log pot | 9mm | 1 | DRIVE 1 (shared L+R) |
| RV_DRV2_L/R | Log pot | 9mm | 1 | DRIVE 2 (shared L+R) |
| RV_DRV3_L/R | Log pot | 9mm | 1 | DRIVE 3 (shared L+R) |
| SW1_MODE | 3-pos switch | Panel | 1 | Manual mode select |

### Trim Pots

| Reference | Range | Purpose | Adjustment |
|---|---|---|---|
| RV_THRESH_HC | ±1 V | Hard clip threshold fine-tune | Adjust until symmetrical clip at ±5 V |
| RV_FOLD_GAIN | ×0.8–×1.2 | Wavefold input gain calibration | Adjust until fold onset is at DRIVE=50% |

### Power Draw Estimate
- 6× TL072 + 1× TL074 + support ICs: ~15 mA
- +12 V: ~15 mA | −12 V: ~15 mA

### Known Circuit Challenges
- CD4053 signal routing: the analog switch introduces a small series resistance (~100 Ω on ±5 V supply) and some charge injection at mode switch. Feed a unity-gain buffer after the switch to isolate downstream.
- Diode matching (Mode 1): 1N4148 diodes on the same tape reel are reasonably matched; use diodes from the same batch for L and R to minimize L/R asymmetry.
- Wavefold op-amps must slew fast enough for high-frequency audio — TL072 slew rate (13 V/µs) is adequate for 20 kHz audio at ±10 V.
