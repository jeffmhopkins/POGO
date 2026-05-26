# POGO Design Status

No Phase 6 (code) work begins until every row shows ✅ for Phases 1–3
**and** Phases 4 and 5 are ✅ (module-level — one decision applies to all blocks).

| Block                        | Phase 1: Audio Spec | Phase 2: Analog Model | Phase 3: Circuit Design | Phase 4: Panel Design | Phase 5: Board Layout | Phase 6: Code |
|------------------------------|---------------------|-----------------------|-------------------------|-----------------------|-----------------------|---------------|
| Mod Architecture             | ✅                  | ✅                    | ✅                      | ✅                    | ✅                    | ✅             |
| Block A: Input Buffer        | ✅                  | ✅                    | ✅                      | ✅                    | ✅                    | ✅             |
| Block 1: Pre-Gain            | ✅                  | ✅                    | ✅                      | ✅                    | ✅                    | ✅             |
| Block 2: Envelope Follower   | ✅                  | ✅                    | ✅                      | ✅                    | ✅                    | ✅             |
| Block 3: Triple Bandpass SVF | ✅                  | ✅                    | ✅                      | ✅                    | ✅                    | ✅             |
| Block 4: Distortion          | ✅                  | ✅                    | ✅                      | ✅                    | ✅                    | ✅             |
| Block VCA (pre-LP1)          | ✅                  | ✅                    | ✅                      | ✅                    | ✅                    | ✅             |
| Block 5: LP Filter 1         | ✅                  | ✅                    | ✅                      | ✅                    | ✅                    | ✅             |
| Block 6: LP Filter 2         | ✅                  | ✅                    | ✅                      | ✅                    | ✅                    | ✅             |
| Block 7: HP Filter           | ✅                  | ✅                    | ✅                      | ✅                    | ✅                    | ✅             |
| Block B: Output Buffer       | ✅                  | ✅                    | ✅                      | ✅                    | ✅                    | ✅             |

**Phase 4 and Phase 5 are module-level gates** — when complete, all rows flip to ✅ at once.

Phase 4 deliverables → `specs/panel-design/panel-notes.md` + `specs/panel-design/panel.svg` + `design/panel.html` (SVG)
Phase 5 deliverables → `specs/board-layout/layout-notes.md`

⚠️ = in progress / decision pending
Last updated: 2026-05-24

## Noise & Inter-Block Connection Audit — 2026-05-24

A full IC-level noise and inter-block impedance audit was completed. Key design changes:
- **Block A**: TL072CDT → LM4562MA (2.7 nV/√Hz; 6.7× noise improvement at first active stage)
- **Block 1**: TL072CDT → NE5532D (5 nV/√Hz; reduces boost-mode noise floor 3.6×)
- **Block 3**: Added 10 nF Iabc bypass caps (H3), 10 kΩ POLARITY bleeder resistor (H4)
- **Block 5**: Added 10 nF Iabc bypass caps at Q-VCA; documented OTA-C noise limitation (D1, D2)
- **Block 6**: Added GND stitching via array spec between LP1 and LP2 sections (M5)
- **Block B**: Added BAND OUT phase verification note for Phase 6 (D3)
- **STK_AUDIO_L/R**: 40-pin stacking headers replacing IDC ribbon for Utility→Audio connection; GND guard pins retained in pinout for I_abc group (H2)
- **layout-notes.md**: New routing rules M1–M4, THAT340 power island (H5), H6 post-dist tap,
  bring-up checklist (Section 12)

Full audit findings: `specs/shared/noise-audit.md`

## Next Steps

1. Per-block Phases 1–3: ✅ complete for all blocks
2. Phase 4: panel design ✅ — panel.html + panel.svg complete; all docs synced
3. Phase 5: board layout ✅ — 3-board split documented in specs/board-layout/layout-notes.md
4. **Noise audit** ✅ — completed 2026-05-24; see specs/shared/noise-audit.md
5. Phase 6 (VCV Rack code): ✅ **complete** — all DSP blocks implemented (A, 1, 2, mod bus,
   3, 4, VCA, 5, 6, 7, B). Full signal chain wired in `src/Pogo.cpp`. Blocks 3+4 run at
   2× oversampled rate (dsp::Upsampler/Decimator). `onSampleRateChange()` resets filter
   state. Panel widget with all 47 params / 22 inputs / 6 outputs registered.
   `res/Pogo.svg` panel art is complete — all 56 widget positions verified against C++ layout.

Last updated: 2026-05-26

---

## ⚠️ TOPOLOGY INVESTIGATION IN PROGRESS — spec/audio-intent freeze

**Branch:** `topology_change`

The signal chain order is under active experimentation in the plugin. **Do not update
per-block specs, audio intent, or circuit designs until the plugin experiments are
complete and a topology is chosen.** Plugin code changes come first; spec rewrites follow
only after the routing is confirmed.

**Candidate new routing:** Input → PreGain → Envelope → **VCA → LP1 → Triple BP → HP → LP2** → Output
(current code: PreGain → Triple BP → VCA → LP1 → LP2 → HP)

Items frozen pending topology decision:
- Block 3 (Triple BP) Phase 1–3 spec
- Block VCA Phase 1–3 spec  
- Block 5 LP1 Phase 1–3 spec
- Block 6 LP2 Phase 1–3 spec
- Block 7 HP Phase 1–3 spec
- `CLAUDE.md` signal chain table
- All schematic SVGs in `specs/block-*/`

---

## ⚠️ TESTING DIVERGENCE — DSP vs. Spec (2026-05-26)

**Branch:** `topology_change`

| Item | Spec (Phase 3) | DSP (current code) |
|---|---|---|
| Block 3 SVF pole count | 2-pole per group | **4-pole** (two cascaded 2-pole stages) |
| Rolloff per side | 6 dB/octave | 12 dB/octave |
| Effective bandwidth at same Q | BW = f₀/Q | BW ≈ 0.644 × f₀/Q |
| Peak gain at resonance | Q | Q² (at max FB: 2500×; clamped downstream) |
| LM13700 integrators (Block 3, per channel) | 3 | **6** (if hardware follows) |
| Power (Block 3) | ~12 mA | ~18 mA (if hardware follows) |
| FB_DIST_BLEND → SVF input path | Post-dist signal additively mixes into SVF input | **Removed** — SVF input is clean audio only; FB_DIST_BLEND knob/CV still registered on panel but inactive |
| FB parameter label | FB (Feedback) | Renamed `qParam` in code — controls Q directly; param IDs (FB_1/2/3_PARAM) unchanged |

**What changed in code:**
- `SVFGroup`: two cascaded 2-pole stages (`ic1a/ic2a` → `ic1b/ic2b`)
- `TripleBandpass::process()`: removed `distTap[]` and `blend` args; SVF input = `x` only
- `Pogo.cpp`: `fbParam` → `qParam`; `blend` variable removed; process() calls updated

**Knob/CV still wired (no effect):** FB_DIST_BLEND knob and BLEND_CV attenuverter are
registered and visible on panel but their values are never read. Dead code until a decision
is made.

**Decision pending:**
1. 4-pole vs 2-pole: evaluate subjectively — tighter formant peaks vs hardware cost?
2. FB_DIST_BLEND: repurpose the knob/CV for something else, or remove from panel entirely?
