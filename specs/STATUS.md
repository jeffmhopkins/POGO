# POGO Design Status

No Phase 6 (code) work begins until every row shows ✅ for Phases 1–3
**and** Phases 4 and 5 are ✅ (module-level — one decision applies to all blocks).

| Block                        | Phase 1: Audio Spec | Phase 2: Analog Model | Phase 3: Circuit Design | Phase 4: Panel Design | Phase 5: Board Layout | Phase 6: Code |
|------------------------------|---------------------|-----------------------|-------------------------|-----------------------|-----------------------|---------------|
| Mod Architecture             | ✅                  | ✅                    | ✅                      | ✅                    | ✅                    | ✅             |
| Block A: Input Buffer        | ✅                  | ✅                    | ✅                      | ✅                    | ✅                    | ✅             |
| Block 1: Pre-Gain            | ✅                  | ✅                    | ✅                      | ✅                    | ✅                    | ✅             |
| Block 2: Envelope Follower   | ✅                  | ✅                    | ✅                      | ✅                    | ✅                    | ✅             |
| Block 3: Triple APF Comb     | ✅                  | ✅                    | ✅                      | ✅                    | ✅                    | ✅             |
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
- **CN_UTIL_L/R**: Expanded from 34-pin to 40-pin; 3 GND guard pins interleaved in I_abc group (H2)
- **layout-notes.md**: New routing rules M1–M4, THAT340 power island (H5), H6 post-dist tap,
  bring-up checklist (Section 12)

Full audit findings: `specs/shared/noise-audit.md`

## Next Steps

1. Per-block Phases 1–3: ✅ complete for all blocks
2. Phase 4: panel design ✅ — panel.html + panel.svg complete; all docs synced
3. Phase 5: board layout ✅ — 4-board split documented in specs/board-layout/layout-notes.md
4. **Noise audit** ✅ — completed 2026-05-24; see specs/shared/noise-audit.md
5. Phase 6 (VCV Rack code): ✅ **complete** — all DSP blocks implemented (A, 1, 2, mod bus,
   3, 4, VCA, 5, 6, 7, B). Full signal chain wired in `src/Pogo.cpp`. Blocks 3+4 run at
   2× oversampled rate (dsp::Upsampler/Decimator). `onSampleRateChange()` resets filter
   state. Panel widget with all 47 params / 22 inputs / 6 outputs registered.
   **Remaining before hardware validation**: replace placeholder `res/Pogo.svg` panel art.

Last updated: 2026-05-25
