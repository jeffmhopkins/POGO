# POGO — Plugin Topology (Authoritative)

> **Authoritative — regenerated 2026-05-30 from `plugin/src` (change 0018 audit).**
>
> This document is a faithful, line-cited description of the **current** VCV Rack plugin,
> which is the sole ground truth for the POGO hardware. Every fact below cites the source
> file and line(s). Where code *comments* disagree with code *behavior*, the behavior wins
> and the stale comment is flagged.

Source files:
- `plugin/src/Pogo.cpp` — module: param/input/output/light enums, `config*` calls, `process()` signal chain.
- `plugin/src/dsp/*.hpp` — per-block DSP: `InputBuffer`, `PreGain`, `LFO`, `ModBus`, `VcaBlock`, `LPFilter`, `BandpassSVF`, `Distortion`, `HPFilter`.

---

## 1. Counts (verified)

| Enum | Terminator | Count | `Pogo.cpp` line |
|---|---|---|---|
| `ParamId` | `NUM_PARAMS` | **53** | 163 |
| `InputId` | `NUM_INPUTS` | **24** | 177 |
| `OutputId` | `NUM_OUTPUTS` | **6** | 184 |
| `LightId` | `NUM_LIGHTS` | **5** | 190 |

`config(NUM_PARAMS, NUM_INPUTS, NUM_OUTPUTS, NUM_LIGHTS)` at `Pogo.cpp:194`. Member counts
verified by direct enumeration of the enum bodies (not just the trailing `// 53` comments).

---

## 2. Signal Chain Overview

The `process()` method (`Pogo.cpp:330`–506) runs, in order:

```
L_IN / R_IN ─► [A] InputBuffer (clamp ±11)  R normals to L (Pogo.cpp:336)
            ─► [1] PreGain (GAIN_PARAM: 1× / 5×, clip ±10.5)  (Pogo.cpp:341)
            ─► [VCA] VcaBlock (AMT bipolar + OFS floor; CV = VCA_IN normal→bus)  (Pogo.cpp:383)
            ─► [LP1] LPFilter ×2 (stereo TILT: L=base+tilt, R=base−tilt)  (Pogo.cpp:399)
            ─► [BP] TripleBandpass:  per band  Distortion ──► SVF  (dist runs BEFORE SVF)  (Pogo.cpp:449)
                    bandL/bandR feed BP1+BP2; ALT path (if patched) feeds BP3
                    bpOut = clamp(bandL·BP_BYPASS + wetSum·BP_WET, ±12)  (Pogo.cpp:475)
            ─► [HP] HPFilter ×2 (mono CV, f_ref 632)  (Pogo.cpp:483)
            ─► [LP2] LPFilter ×2 (mono CV, f_ref 632)  (Pogo.cpp:491)
            ─► [B] clamp ±11 ─► MAIN_L / MAIN_R  (Pogo.cpp:495)

Parallel:  LFO1, LFO2 ─► MOD_SRC switch ─► ModBusProcessor ─► 18 attenuverter destinations
BP3 tap:   bandpass{L,R}.prevOut[2] (post-SVF band, pre-mix) ─► BP3_L/R OUT (clamp ±11)  (Pogo.cpp:472,497)
```

### ALT path (BP3 injection)
`Pogo.cpp:344`–352, 439–441. `ALT_BP_L/R` are pre-gained through `ALT_GAIN_PARAM` (own 1×/5×
switch), bypass the main VCA→LP1 stages, and feed **BP3 only** (after running through the VCA
with the same `vcaAmt`/`vcaCV`). When no ALT cable is patched, BP3 uses the main `bandL/bandR`
(LP1 output). ALT R normals to ALT L when only L is patched (`Pogo.cpp:352`).

---

## 3. Parameter Enum (`ParamId`, 53 entries)

Types: **2-tog** = 2-position switch, **3-tog** = 3-position switch, **knob/slider** = continuous,
**att** = bipolar attenuverter trimpot (−1..+1, default 0). All `configParam`/`configSwitch` calls
are in `Pogo.cpp:197`–268.

| # | Name | Type | Range | Default | Label / Notes | Line |
|---|---|---|---|---|---|---|
| 0 | `GAIN_PARAM` | 2-tog | 0..1 | 0 | "Main Gain" {1×, 5×} | 197 |
| 1 | `ALT_GAIN_PARAM` | 2-tog | 0..1 | 0 | "Alt BP3 Gain" {1×, 5×} | 198 |
| 2 | `LFO1_RATE_PARAM` | knob | 0..1 | 0.3 | "LFO 1 Rate" (expo 0.05–20 Hz) | 201 |
| 3 | `LFO2_RATE_PARAM` | knob | 0..1 | 0.3 | "LFO 2 Rate" | 202 |
| 4 | `MOD_SRC_PARAM` | 3-tog | 0..2 | 0 | "Mod Source" {LFO 1, LFO 2, External} | 205 |
| 5 | `MOD_SCALE_PARAM` | trimpot | 0..1 | 0.5 | "Mod Scale" → 0.2×–5× gain | 206 |
| 6 | `MOD_OFFSET_PARAM` | trimpot | −1..1 | 0 | "Mod Offset" → ±5 V | 207 |
| 7 | `VCA_AMT_PARAM` | trimpot | −1..1 | 0 | "VCA Depth" (bipolar) | 208 |
| 8 | `VCA_OFS_PARAM` | trimpot | 0..1 | 0.5 | "VCA Floor Offset" (×5 V added to CV) | 209 |
| 9 | `LP1_FREQ_PARAM` | huge knob | −5..5 | 0 | "LP1 Freq" V/oct | 212 |
| 10 | `LP1_TILT_PARAM` | large knob | −1..1 | 0 | "LP1 Stereo Tilt" (×5 → ±5 V/oct) | 213 |
| 11 | `LP1_RES_PARAM` | large knob | 0..1 | 0 | "LP1 Resonance" | 214 |
| 12 | `LP1_FREQ_ATT_PARAM` | att | −1..1 | 0 | "LP1 Freq CV Depth" | 215 |
| 13 | `LP1_TILT_ATT_PARAM` | att | −1..1 | 0 | "LP1 Tilt CV Depth" | 216 |
| 14 | `LP1_RES_ATT_PARAM` | att | −1..1 | 0 | "LP1 Res CV Depth" | 217 |
| 15 | `BP_TILT_PARAM` | knob | −1..1 | 0 | "BP Tilt" V/oct (global stereo spread) | 220 |
| 16 | `BP_OFFSET_PARAM` | knob | −1.1..1.1 | 0 | "BP Master Offset" V/oct | 221 |
| 17 | `BP_BYPASS_PARAM` | knob | 0..1 | **1.0** | "BP Bypass" — dry (LP1) output scaler | 222 |
| 18 | `BP_WET_PARAM` | knob | 0..1 | **1.0** | "BP Wet" — wet (band sum) output scaler | 223 |
| 19 | `BP_FREQ_ATT_PARAM` | att | −1..1 | 0 | "BP Offset CV Depth" | 224 |
| 20 | `BP_TILT_ATT_PARAM` | att | −1..1 | 0 | "BP Tilt CV Depth" | 225 |
| 21 | `BP1_FREQ_PARAM` | huge knob | ±log₂10 (≈±3.322) | 0 | "BP1 Freq" (FormantFreqQuantity, fref=400) | 229 |
| 22 | `BP1_FOCUS_PARAM` | large knob | 0..1 | 0 | "BP1 Focus" (Q) | 230 |
| 23 | `BP1_TILT_PARAM` | large knob | −1..1 | 0 | "BP1 Tilt" V/oct | 231 |
| 24 | `BP1_DIST_PARAM` | large knob | 0..1 | 0.20 | "BP1 Drive" | 232 |
| 25 | `BP1_FREQ_ATT_PARAM` | att | −1..1 | 0 | "BP1 Freq CV Depth" | 233 |
| 26 | `BP1_TILT_ATT_PARAM` | att | −1..1 | 0 | "BP1 Tilt CV Depth" | 234 |
| 27 | `BP1_DIST_ATT_PARAM` | att | −1..1 | 0 | "BP1 Drive CV Depth" | 235 |
| 28 | `BP1_DIST_MODE_PARAM` | 3-tog | 0..2 | 0 | "BP1 Dist Mode" {Soft, Hard, Wavefold} | 236 |
| 29 | `BP2_FREQ_PARAM` | huge knob | ±3.322 | 0 | "BP2 Freq" (fref=400) | 239 |
| 30 | `BP2_FOCUS_PARAM` | large knob | 0..1 | 0 | "BP2 Focus" | 240 |
| 31 | `BP2_TILT_PARAM` | large knob | −1..1 | 0 | "BP2 Tilt" V/oct | 241 |
| 32 | `BP2_DIST_PARAM` | large knob | 0..1 | 0.20 | "BP2 Drive" | 242 |
| 33 | `BP2_FREQ_ATT_PARAM` | att | −1..1 | 0 | "BP2 Freq CV Depth" | 243 |
| 34 | `BP2_TILT_ATT_PARAM` | att | −1..1 | 0 | "BP2 Tilt CV Depth" | 244 |
| 35 | `BP2_DIST_ATT_PARAM` | att | −1..1 | 0 | "BP2 Drive CV Depth" | 245 |
| 36 | `BP2_DIST_MODE_PARAM` | 3-tog | 0..2 | 0 | "BP2 Dist Mode" {Soft, Hard, Wavefold} | 246 |
| 37 | `BP3_FREQ_PARAM` | huge knob | ±3.322 | 0 | "BP3 Freq" (fref=400) | 249 |
| 38 | `BP3_FOCUS_PARAM` | large knob | 0..1 | 0 | "BP3 Focus" | 250 |
| 39 | `BP3_TILT_PARAM` | large knob | −1..1 | 0 | "BP3 Tilt" V/oct | 251 |
| 40 | `BP3_DIST_PARAM` | large knob | 0..1 | 0.20 | "BP3 Drive" | 252 |
| 41 | `BP3_FREQ_ATT_PARAM` | att | −1..1 | 0 | "BP3 Freq CV Depth" | 253 |
| 42 | `BP3_TILT_ATT_PARAM` | att | −1..1 | 0 | "BP3 Tilt CV Depth" | 254 |
| 43 | `BP3_DIST_ATT_PARAM` | att | −1..1 | 0 | "BP3 Drive CV Depth" | 255 |
| 44 | `BP3_DIST_MODE_PARAM` | 3-tog | 0..2 | 0 | "BP3 Dist Mode" {Soft, Hard, Wavefold} | 256 |
| 45 | `HP_FREQ_PARAM` | slider | −5..5 | **−3** | "HP Freq" V/oct | 259 |
| 46 | `HP_RES_PARAM` | trimpot | 0..1 | 0 | "HP Resonance" | 260 |
| 47 | `HP_FREQ_ATT_PARAM` | att | −1..1 | 0 | "HP Freq CV Depth" | 261 |
| 48 | `HP_RES_ATT_PARAM` | att | −1..1 | 0 | "HP Res CV Depth" | 262 |
| 49 | `LP2_FREQ_PARAM` | slider | −5..5 | **+2** | "LP2 Freq" V/oct | 265 |
| 50 | `LP2_RES_PARAM` | trimpot | 0..1 | 0 | "LP2 Resonance" | 266 |
| 51 | `LP2_FREQ_ATT_PARAM` | att | −1..1 | 0 | "LP2 Freq CV Depth" | 267 |
| 52 | `LP2_RES_ATT_PARAM` | att | −1..1 | 0 | "LP2 Res CV Depth" | 268 |

**BP FREQ knob range:** `bpR = log2(10) ≈ 3.322` (`Pogo.cpp:228`); `400 × 2^±3.322 = [40 Hz, 4 kHz]`.
The `FormantFreqQuantity` display reads `fref × 2^value` with `fref = 400` for all three bands
(`Pogo.cpp:105`–113, 229/239/249).

---

## 4. Input Enum (`InputId`, 24 entries)

All `configInput` at `Pogo.cpp:271`–294. CV destinations route through `applyDestination`
(override + attenuverter) unless noted.

| # | Name | Label | Normalling / scaling | Line |
|---|---|---|---|---|
| 0 | `L_IN_INPUT` | "Audio L" | main left audio | 271 |
| 1 | `R_IN_INPUT` | "Audio R" | normals to L if unpatched (`:336`) | 272 |
| 2 | `ALT_BP_L_INPUT` | "Alt BP L" | ALT path → BP3 (pre-gain via ALT_GAIN) | 273 |
| 3 | `ALT_BP_R_INPUT` | "Alt BP R" | normals to ALT L if only L patched (`:352`) | 274 |
| 4 | `MOD_INPUT` | "Mod Source" | used **only** when MOD_SRC=2 (External); 0 V if unpatched (`:366`) | 275 |
| 5 | `VCA_INPUT` | "VCA CV" | normals to mod bus `busV` if unpatched (`:383`) | 276 |
| 6 | `LP1_FREQ_INPUT` | "LP1 Freq CV" | V/oct via attenuverter (`:394`) | 277 |
| 7 | `LP1_TILT_INPUT` | "LP1 Tilt CV" | added to tilt V (`:396`) | 278 |
| 8 | `LP1_RES_INPUT` | "LP1 Res CV" | att result ÷10, clamp [0,1] (`:397`) | 279 |
| 9 | `BP_FREQ_INPUT` | "BP Offset CV" | global BP offset (`:404`) | 280 |
| 10 | `BP_TILT_INPUT` | "BP Tilt CV" | global BP tilt (`:406`) | 281 |
| 11 | `BP1_FREQ_INPUT` | "BP1 Freq CV" | per-band V/oct (`:418`) | 282 |
| 12 | `BP1_TILT_INPUT` | "BP1 Tilt CV" | ×0.22 then added to group tilt (`:429`) | 283 |
| 13 | `BP1_DIST_INPUT` | "BP1 Drive CV" | added to drive, clamp [0,1] (`:434`) | 284 |
| 14 | `BP2_FREQ_INPUT` | "BP2 Freq CV" | per-band V/oct (`:419`) | 285 |
| 15 | `BP2_TILT_INPUT` | "BP2 Tilt CV" | ×0.22 (`:430`) | 286 |
| 16 | `BP2_DIST_INPUT` | "BP2 Drive CV" | clamp [0,1] (`:435`) | 287 |
| 17 | `BP3_FREQ_INPUT` | "BP3 Freq CV" | per-band V/oct (`:420`) | 288 |
| 18 | `BP3_TILT_INPUT` | "BP3 Tilt CV" | ×0.22 (`:431`) | 289 |
| 19 | `BP3_DIST_INPUT` | "BP3 Drive CV" | clamp [0,1] (`:436`) | 290 |
| 20 | `HP_FREQ_INPUT` | "HP Freq CV" | V/oct (`:479`) | 291 |
| 21 | `HP_RES_INPUT` | "HP Res CV" | att result ÷10, clamp [0,1] (`:481`) | 292 |
| 22 | `LP2_FREQ_INPUT` | "LP2 Freq CV" | V/oct (`:487`) | 293 |
| 23 | `LP2_RES_INPUT` | "LP2 Res CV" | att result ÷10, clamp [0,1] (`:489`) | 294 |

---

## 5. Output Enum (`OutputId`, 6 entries)

`configOutput` at `Pogo.cpp:297`–302; voltage writes at `Pogo.cpp:495`–501.

| # | Name | Label | Voltage / source | Line |
|---|---|---|---|---|
| 0 | `LFO1_OUTPUT` | "LFO 1" | `lfo1V = lfo1Raw × 5` (±5 V triangle) | 500 |
| 1 | `LFO2_OUTPUT` | "LFO 2" | `lfo2V = lfo2Raw × 5` (±5 V) | 501 |
| 2 | `BP3_L_OUTPUT` | "BP3 L" | `clamp(bandpassL.prevOut[2], ±11)` — post-SVF BP3 band, pre-mix | 497 |
| 3 | `BP3_R_OUTPUT` | "BP3 R" | `clamp(bp3OutR, ±11)`; **normals to BP3_L** if unpatched (`:498`) | 498 |
| 4 | `MAIN_L_OUTPUT` | "Audio L" | `clamp(LP2 outL, ±11)` | 495 |
| 5 | `MAIN_R_OUTPUT` | "Audio R" | `clamp(LP2 outR, ±11)` | 496 |

---

## 6. Light Enum (`LightId`, 5 entries)

`configLight` at `Pogo.cpp:305`–306 (only the LFO lights are config'd; the clip lights are set in
`process()` but not explicitly config'd). Brightness writes at `:454`–459, 504–505.

| # | Name | Source | Behavior | Line |
|---|---|---|---|---|
| 0 | `LFO1_LIGHT` | `(lfo1Raw + 1) × 0.5` | green "breathing" LED, 0..1 | 504 |
| 1 | `LFO2_LIGHT` | `(lfo2Raw + 1) × 0.5` | green | 505 |
| 2 | `BP1_CLIP_LIGHT` | `max(|bpInL[0]|,|bpInR[0]|) > 4.0` | red, monitors **distortion output** (pre-filter) | 454 |
| 3 | `BP2_CLIP_LIGHT` | band 1 dist output > 4.0 | red | 456 |
| 4 | `BP3_CLIP_LIGHT` | band 2 dist output > 4.0 | red | 458 |

There is **no** MOD_CLIP, MOD_POS, or MOD_NEG light. Clip LEDs watch the per-band distortion
stage output (which now precedes the SVF), not the SVF output.

---

## 7. Per-Block DSP

### Block A — InputBuffer (`InputBuffer.hpp`)
`process(v) = clamp(v, ±11)`. Models LM4562 follower + BAT54 clamp. R normals to L (`Pogo.cpp:336`).

### Block 1 — PreGain (`PreGain.hpp`)
`GAIN < 0.5 → v` (unity); else `clamp(5·v, ±10.5)`. Used on both main path (`GAIN_PARAM`) and
ALT path (`ALT_GAIN_PARAM`).

### Block VCA — VcaBlock (`VcaBlock.hpp`, `Pogo.cpp:383`–389)
THAT 2180 dB-law model. CV source: `VCA_INPUT` if patched else mod bus `busV`; then
`vcaCV = clamp(vcaCVraw + VCA_OFS·5, 0, 10)` (`:386`). `normCV = clamp(cvV/5, 0, 1)`.
- AMT ≥ 0: `control = 1 − AMT·(1−normCV)`
- AMT < 0: `control = 1 + AMT·normCV`
- `control` clamped [0,1]; gain `G = 10^(2·(control−1))` (0 dB at control=1, −40 dB at 0; hard 0 below control≤0.001).
AMT=0 ⇒ control=1 always (unity, CV inert). Applied identically to L and R, and to the ALT feed.

### Block LP1 — LPFilter ×2 (`LPFilter.hpp`, `Pogo.cpp:391`–400)
Andrew Simper trapezoidal 2-pole SVF, **LP tap = v2**. `f_ref = 632 Hz`, `f0 = 632·2^cutoffV`,
clamped `[10, fs·0.48]`. `g = tan(π·f0/fs)`, `Q = 0.5·4000^resParam` → [0.5, 2000] (self-oscillates
in top ~5%), `k = 1/Q`.
- **Stereo TILT (LP1 only):** `tiltV = LP1_TILT·5 + CV`; L cutoff = `base+tiltV`, R cutoff = `base−tiltV` (`:399`–400). `base = LP1_FREQ + freqCV`.
- Res CV: `clamp(LP1_RES + resCV/10, 0, 1)` (`:397`).

### Block BP — TripleBandpass + Distortion (`BandpassSVF.hpp`, `Distortion.hpp`, `Pogo.cpp:402`–476)
Three independent 2-pole SVF bandpass groups (`SVFGroup`, **BP tap = v1**, peak gain = 1, does
not self-oscillate).

- **f_ref = 400 Hz for ALL THREE bands** — `F_REF[3] = {400, 400, 400}` (`BandpassSVF.hpp:42`).
  ⚠️ The header *comment* on line 6 (`{200, 1500, 6000}`) is **stale and must not be used**.
- `f0 = 400·2^(freqV + tiltV)`, clamp `[10, fs·0.48]` (`:44`–45).
- **Q law:** `Q = 0.5·400^qParam` → **[0.5, 200]** (`:46`). `qParam` = `FOCUS` (clamped [0,1], `:422`).
- **Per-band frequency:** `freqV[i] = bpOffsetCv + BPi_FREQ + freqCV` where
  `bpOffsetCv = BP_OFFSET + offsetCV` (`:404`, 417–421).
- **Tilt:** `groupTiltV[i] = BPi_TILT + (tiltCV·0.22)` (`:429`–431); stereo spread
  `tiltL[i] = bpTiltCv + groupTiltV[i]`, `tiltR[i] = −(bpTiltCv + groupTiltV[i])`, where
  `bpTiltCv = BP_TILT + tiltCV` (`:406`, 462–463).
- **Distortion BEFORE the SVF (per band):** `bpInL/R[i] = Distortion::process(distIn, drive, mode)`,
  then `bandpassL/R.process(bpIn, ...)` (`:449`–465). Band inputs: BP1 & BP2 take LP1 output
  (`bandL/bandR`); BP3 takes the main/ALT feed (`bp3InL/R`, `:446`–447).
- **Distortion** (`Distortion.hpp`): input normalized `v/5` clamp ±1, processed, ×5 back.
  Drive `p∈[0,1]`: gain-control zone `p≤0.20` (mute→unity), drive zone `p>0.20` (`d=(p−0.20)/0.80`).
  - Mode 0 **Soft**: always-in diode tanh; `G = p/0.20` (p≤0.20) else `exp((p−0.20)/0.80·4)`; output `Vth·tanh(G·v/Vth)`, `Vth=0.28`.
  - Mode 1 **Hard**: `clamp((1+4d)·v, ±1.16)`.
  - Mode 2 **Wavefold**: `(1+4d)·v`, clamp ±20, then Buchla fold `Vth·asin(sin(π/2/Vth·y))·2/π`, `Vth=0.28`.
- **Output mix (NOT a crossfade):** `dSum = prevOut[0]+prevOut[1]+prevOut[2]`,
  `wet = clamp(dSum, ±10.5)`; `bpOut = clamp(band·BP_BYPASS + wet·BP_WET, ±12)` per channel
  (`:468`–476). `BP_BYPASS` and `BP_WET` are two **independent** scalers, both default 1.0.
  There is **no single BP_MIX crossfade** parameter. The dry term is `bandL`/`bandR` = LP1 output.
- **BP3 tap:** `bp3OutL/R = bandpassL/R.prevOut[2]` (post-SVF BP3 band, pre-mix), to BP3 OUT jacks (`:472`–473).

### Block HP — HPFilter ×2 (`HPFilter.hpp`, `Pogo.cpp:478`–484)
Same Simper SVF; **HP output = `−(x − k·v1 − v2)`** (negated for hardware summing-amp inversion).
`f_ref = 632 Hz`, `f0 = 632·2^cutoffV` clamp `[10, fs·0.48]`. `Q = 0.5·4000^resParam` → [0.5, 2000]
(self-oscillates). **Mono** (no tilt): same `hpFreqCv`/`hpResCv` feed L and R. Freq CV is raw V/oct
(`:479`); Res CV `clamp(HP_RES + resCV/10, 0, 1)` (`:481`). HP_FREQ default **−3 V**.

### Block LP2 — LPFilter ×2 (`Pogo.cpp:486`–492)
Same `LPFilter` as LP1 but **mono** (no tilt), independent of LP1. `f_ref = 632`. Freq CV raw V/oct;
Res CV `clamp(LP2_RES + resCV/10, 0, 1)`. LP2_FREQ default **+2 V**. Output → `MAIN_L/R`.

### Block B — Output
`MAIN_L/R = clamp(LP2 out, ±11)` (`:495`–496); `BP3_L/R = clamp(..., ±11)` (`:497`–498).

### LFO ×2 (`LFO.hpp`, `Pogo.cpp:354`–358)
Triangle, `speedHz = 0.05·400^speedParam` → ~0.05 Hz at 0, ~1 Hz at 0.5, ~20 Hz at 1. Raw triangle
in [−1,1] with a one-pole LP at 10× rate (slew/peak rounding). Output ×5 → ±5 V.

### Mod Bus (`ModBus.hpp`, `Pogo.cpp:360`–379)
- **Source select** (`MOD_SRC_PARAM`, 3-way): 0=LFO1 V, 1=LFO2 V, 2=External (`MOD_INPUT`; 0 V if
  unpatched — the jack is ignored when the switch is not on External) (`:363`–366).
- **ModBusProcessor::process:** `gain = 0.2·25^scale` → [0.2×, 5×]; `offset = MOD_OFFSET·5` → ±5 V;
  `busV = clamp(source·gain + offset, ±10)` (`ModBus.hpp:17`–26).
- **applyDestination(busV, overrideV, has, att):** `source = has ? overrideV : busV; return source·att`.
  i.e. each CV jack **overrides** the bus when patched, then is scaled by its attenuverter.

---

## 8. Mod-Bus Destination Map

18 attenuverter-routed destinations (each `modDest(cvInput, attParam)`, `Pogo.cpp:373`–379) plus
one raw VCA normal (VCA_IN normals to `busV` directly, no attenuverter — `:383`).

| Destination | CV input | Attenuverter | Applied at (line) | Extra scaling |
|---|---|---|---|---|
| LP1 Freq | `LP1_FREQ_INPUT` | `LP1_FREQ_ATT_PARAM` | 393 | V/oct |
| LP1 Tilt | `LP1_TILT_INPUT` | `LP1_TILT_ATT_PARAM` | 396 | added to tilt V |
| LP1 Res | `LP1_RES_INPUT` | `LP1_RES_ATT_PARAM` | 397 | ÷10, clamp [0,1] |
| BP Offset (global) | `BP_FREQ_INPUT` | `BP_FREQ_ATT_PARAM` | 404 | V/oct |
| BP Tilt (global) | `BP_TILT_INPUT` | `BP_TILT_ATT_PARAM` | 406 | V/oct |
| BP1 Freq | `BP1_FREQ_INPUT` | `BP1_FREQ_ATT_PARAM` | 418 | V/oct |
| BP1 Tilt | `BP1_TILT_INPUT` | `BP1_TILT_ATT_PARAM` | 429 | ×0.22 |
| BP1 Drive | `BP1_DIST_INPUT` | `BP1_DIST_ATT_PARAM` | 434 | clamp [0,1] |
| BP2 Freq | `BP2_FREQ_INPUT` | `BP2_FREQ_ATT_PARAM` | 419 | V/oct |
| BP2 Tilt | `BP2_TILT_INPUT` | `BP2_TILT_ATT_PARAM` | 430 | ×0.22 |
| BP2 Drive | `BP2_DIST_INPUT` | `BP2_DIST_ATT_PARAM` | 435 | clamp [0,1] |
| BP3 Freq | `BP3_FREQ_INPUT` | `BP3_FREQ_ATT_PARAM` | 420 | V/oct |
| BP3 Tilt | `BP3_TILT_INPUT` | `BP3_TILT_ATT_PARAM` | 431 | ×0.22 |
| BP3 Drive | `BP3_DIST_INPUT` | `BP3_DIST_ATT_PARAM` | 436 | clamp [0,1] |
| HP Freq | `HP_FREQ_INPUT` | `HP_FREQ_ATT_PARAM` | 479 | V/oct |
| HP Res | `HP_RES_INPUT` | `HP_RES_ATT_PARAM` | 481 | ÷10, clamp [0,1] |
| LP2 Freq | `LP2_FREQ_INPUT` | `LP2_FREQ_ATT_PARAM` | 487 | V/oct |
| LP2 Res | `LP2_RES_INPUT` | `LP2_RES_ATT_PARAM` | 489 | ÷10, clamp [0,1] |
| **VCA (raw normal)** | `VCA_INPUT` | — (none) | 383 | normals to `busV`; +`VCA_OFS·5`, clamp [0,10] |

---

## 9. Clamp / Voltage Reference

| Stage | Clamp | Line |
|---|---|---|
| Input buffer | ±11 | InputBuffer.hpp:9 |
| Pre-gain (5×) | ±10.5 | PreGain.hpp:12 |
| VCA CV | [0,10] | Pogo.cpp:386 |
| Mod bus output | ±10 | ModBus.hpp:25 |
| Res CV (all filters) | [0,1] after ÷10 | Pogo.cpp:397,481,489 |
| Distortion internal norm | ±1 | Distortion.hpp:52 |
| BP wet sum | ±10.5 | Pogo.cpp:470 |
| BP output mix | ±12 | Pogo.cpp:475 |
| BP3 / MAIN out | ±11 | Pogo.cpp:495–498 |
| LFO out | ±5 (×5 of [−1,1]) | Pogo.cpp:357,500 |

---

## 10. Notes & known stale comments in source

- `BandpassSVF.hpp:6` comment `f_ref = {200, 1500, 6000}` is **stale**; code uses `{400,400,400}`.
- `BandpassSVF.hpp:7` comment "Q = 0.5 × 400^qParam → [0.5, 200]" matches code (correct).
- `Pogo.cpp:163,177,184,190` trailing comments (`// 53`, `// 24`, `// 6`, `// 5`) match the
  verified member counts.
- `EnvelopeFollower.hpp` exists in `dsp/` but is **not included** by `Pogo.cpp` (LFOs replaced the
  envelope follower; see `LFO.hpp:4`). It is dead code in the current build.
