# POGO Module Overview — 48HP

## Signal Chain

```
Stereo Input (L + R)
  │
  ├── [Block A: Input Buffer]
  │   LM4562 unity-gain buffer; clamp ±11V; R normalizes to L when unpatched
  │
  ├── [Block 1: Pre-Gain]
  │   GAIN_MAIN switch: 1× (unity) or 5× (~14 dB); clip ±10.5V at 5×
  │
  ├── [Block VCA: Pre-LP1 VCA]
  │   THAT 2180 linear VCA; AMT bipolar (−1→+1 accent/duck/unity)
  │   VCA_OFS trimpot shifts CV floor; VCA_IN jack (normalizes to mod bus)
  │
  ├── [Block LP1: Lowpass Filter 1]
  │   2-pole OTA-C SVF (Andrew Simper trapezoidal), LP output
  │   LP1_FREQ (xl knob, ±5V/oct, f_ref=632Hz), LP1_TILT (stereo spread),
  │   LP1_RES (resonance, Q 0.5–2000)
  │
  │   ← ALT path: ALT_BP_L/R → GAIN_BP3 switch (1×/5×) → bypasses VCA+LP1
  │
  ├── [Block BP: Triple Bandpass SVF]
  │   Three independent 4-pole OTA-C SVF bandpass groups (BP1/BP2/BP3)
  │   f_refs: 200/1500/6000Hz. 2× oversampled.
  │   BP_OFFSET (master freq), BP_MIX (dry/wet), BP_POL (±polarity),
  │   BP_DIST (global mode: soft/hard/fold)
  │   Per-group: FREQ, FOCUS (Q), DIST (drive)
  │   BP_TILT CV: stereo spread across all 3 formants
  │   BP3_L/R_OUT: tap of BP3 formant after distortion
  │
  ├── [Block HP: Highpass Filter]
  │   2-pole OTA-C SVF, HP output
  │   HP_FREQ (slider, ±5V/oct), HP_RES (resonance)
  │
  ├── [Block LP2: Lowpass Filter 2]
  │   2-pole OTA-C SVF, LP output (same topology as LP1)
  │   LP2_FREQ (slider, ±5V/oct), LP2_RES (resonance)
  │
  └── [Block B: Output Buffer]
      Low-impedance ~1kΩ output; clamp ±11V → MAIN_L/R_OUT

───────────────────────────────────────────────────────────────────────────
MODULATION (runs in parallel)

LFO1 / LFO2: dual triangle LFO, 0.05–20Hz (exp)
  LFO1 → LFO1_OUT; normalizes into MOD_IN when unpatched
  LFO2 → LFO2_OUT (standalone)

Mod Bus:
  Source: MOD_IN jack (LFO1 when unpatched)
  MOD_SCALE trimpot (0.2×–5× exp) + MOD_OFFSET trimpot (±5V)
  → clamped ±10V → 22 CV destinations (each with override jack + attenuverter)
  Lights: MOD_CLIP (|bus|≥9.9V), MOD_POS, MOD_NEG
```

---

## Panel Specifications

| Property | Value |
|---|---|
| Width | 48HP (243.84mm) |
| Height | 3U Eurorack (128.5mm usable) |
| Params | 46 |
| CV Inputs | 24 |
| Outputs | 6 |
| LEDs | 5 |

Panel is generated from `tools/panel-data.yaml` via `tools/build_panel.py`.
See `specs/panel-design/panel-notes.md` for workflow.

---

## Power Budget (estimate — measure on prototype)

| Block | +12V | −12V |
|---|---|---|
| Block A: Input buffers | 5 mA | 5 mA |
| Block 1: Pre-Gain | 5 mA | 5 mA |
| Block LFO (dual) | 10 mA | 10 mA |
| Mod Bus + 22 attenuverters | 45 mA | 45 mA |
| Block VCA | 5 mA | 5 mA |
| Block LP1 | 15 mA | 15 mA |
| Block BP (3 groups, stereo) | 50 mA | 50 mA |
| Block 4: Distortion | 25 mA | 25 mA |
| Block HP | 10 mA | 10 mA |
| Block LP2 | 15 mA | 15 mA |
| Block B: Output buffers | 5 mA | 5 mA |
| **Total estimate** | **~190 mA** | **~190 mA** |

Measure actual draw during prototype bring-up. Update this table.

---

## DSP Implementation Summary

The VCV Rack plugin (`plugin/src/Pogo.cpp`) is the functional reference.

| Block | DSP Class | Notes |
|---|---|---|
| Input Buffer | `InputBuffer.hpp` | clamp ±11V |
| Pre-Gain | `PreGain.hpp` | 1× or 5×, clip ±10.5V |
| LFO | `LFO.hpp` | triangle, exp rate |
| Mod Bus | `ModBus.hpp` | scale+offset+clamp |
| VCA | `VcaBlock.hpp` | linear VCA, bipolar att |
| LP1, LP2 | `LPFilter.hpp` | Simper trapezoidal SVF |
| BP (triple) | `BandpassSVF.hpp` | 4-pole BP, 2× OS |
| Distortion | `Distortion.hpp` | soft/hard/wavefold |
| HP | `HPFilter.hpp` | Simper trapezoidal SVF |
| Output Buffer | inline in Pogo.cpp | clamp ±11V |

---

## Repository Quick Reference

| Path | Purpose |
|---|---|
| `plugin/` | VCV Rack plugin (src/, res/, Makefile, plugin.json) |
| `tools/build_panel.py` | Panel SVG generator + DRC checker |
| `tools/panel-data.yaml` | Panel source of truth (positions, types) |
| `docs/plugin-topology.md` | Authoritative plugin parameter reference |
| `kicad/` | KiCad schematics (control + utility boards) |
| `specs/` | Hardware design documentation |
| `design/panel-debug.html` | Interactive panel layer viewer |

Last updated: 2026-05-27
