# POGO — Hardware Spec Status

Last updated: 2026-05-27 | Topology: 48HP | Phase 3R: all blocks complete

## Phase Key

| Symbol | Meaning |
|---|---|
| ✅ | Complete |
| ⚠️ | Complete with known deviation (documented) |
| 🔲 | Not started |
| 🚧 | In progress |

---

## Block Specs (`specs/block-N/spec.md`)

| Block | Name | Phase 1R | Phase 2R | Phase 3R | Notes |
|---|---|---|---|---|---|
| A | Input Buffer | ✅ | ✅ | ✅ | OPA1612 follower, BAT54S clamp |
| 1 | Pre-Gain | ✅ | ✅ | ✅ | OPA1612, 1×/5× switch; ALT_BP path |
| 2 | Dual LFO | ✅ | ✅ | ✅ | Integrator+Schmitt; 47nF C0G; formula corrected; R_CCW_END 2×100MΩ for f_min=0.058 Hz |
| 3 | Mod Bus | ✅ | ✅ | ✅ | 19 destinations; 7× TL074CDT; 470kΩ SCALE pot |
| 4 | VCA | ✅ | ✅ | ✅ | THAT 2180 dB-law; DSP updated to match |
| 5 | LP Filter 1 | ✅ | ✅ | ✅ | OTA-C SVF; stereo tilt (symmetric ±V_tilt L/R) |
| 6 | Triple BP + Dist | ✅ | ✅ | ✅ | SC/HC/WF + CD4053; BP_MIX polarity corrected (U48=wet restorer; SW_POL default via U27-B) |
| 7 | HP Filter | ✅ | ✅ | ✅ | OTA-C SVF; G=−1 buffer corrects SUM_AMP inversion |
| 8 | LP Filter 2 | ✅ | ✅ | ✅ | OTA-C SVF; independent from LP1; shares Q VCA LM13700 |
| B | Output Buffer | ✅ | ✅ | ✅ | TL072; MAIN_L/R from LP2 + BP3_L/R tap |

## aux/ Circuit Library (`specs/aux/aux-*.md`)

| File | Status | Notes |
|---|---|---|
| aux-ota-c-svf | ✅ | ASCII schematic + full derivations |
| aux-expo-converter | ✅ | Component values + trim procedure |
| aux-q-control | ✅ | IRES_AMP driver + IC sharing plan |
| aux-vca-cell | ✅ | THAT 2180 dB-law; DSP matches |
| aux-unity-buffer | ✅ | G=+1 and G=−1 variants |
| aux-distortion | ✅ | SC/HC/WF + CD4053 mux wiring |
| aux-attenuverter | ✅ | Bipolar pot + TL074 inverter |
| aux-mod-bus-core | ✅ | MB_AMP + MB_INV; ±10V clamp |
| aux-lfo-core | ✅ | Integrator + Schmitt; 0.05–20 Hz |
| aux-cv-protection | ✅ | Moved from shared/; content unchanged |
| aux-power-filter | ✅ | Moved from shared/; content unchanged |

No SVG files — ASCII schematics within each `.md` are the source of truth.
Circuit diagrams in spec text must be self-sufficient.

## Global Component Registry

| File | Status |
|---|---|
| `specs/components.yaml` | ✅ Complete — 267 entries; all boards; all ICs, discretes, and key passives with values; qty field for repeated identical parts |

## Panels & Layout

| File | Status |
|---|---|
| `tools/panel-data.yaml` | ✅ DRC-clean (48HP topology) |
| `specs/board-layout/layout-notes.md` | ✅ |

## KiCad Generators

| File | Status |
|---|---|
| `kicad/generate_*.py` | ⚠️ 40HP-era STALE (see kicad/README-STALE.md) |
| `kicad/validate_*.py` | ⚠️ 40HP-era STALE |
| `.github/workflows/build.yml` KiCad step | Disabled |

---

## Next Up

**Phase 3R is complete for all blocks.** All previously documented DSP/hardware deviations are
now resolved — the plugin is a faithful behavioral model of the hardware. Intentional DSP
advantages retained: exact 1V/oct tracking, exact LFO rate law, LFO phase reset, extended Q
range (creative tool).

**Phase 4R (Panel) — DONE.** `tools/panel-data.yaml` DRC-clean.

**Analog design review complete** (`specs/analog-design-review.md` — 2026-05-27).
All review findings resolved. See §7 Completed Action Items in that file for the full list.
Key corrections: THAT340 SOIC-8→SOIC-14; BAT85→SS14 (SMD); block-3 clamp zeners + cal trims
added; MB_PROC_A distribution buffer corrected; destination count 22→19; block-4 AMT pot
loading addressed; block-1 NE5532D→OPA1612 + R_g lowered for noise; all 12 SUM_AMP ICs→OPA1612
(1.1 nV/√Hz); OPA1612 Iq corrected (5.5 mA/dual-IC per rail); block-1 noise % corrected;
block-6 WF topology replaced with true symmetric precision folder (no prototype stability risk).

**DSP alignment complete** (2026-05-27). Plugin updated to match hardware:
- VCA: dB-law G = 10^(2×(control−1)); THAT 2180 characteristic
- BP: 2-pole SVF per group (was 4-pole); unity peak gain (was 1/Q²)
- BP_MIX: additive dry+wet (was crossfade); no oversampling (was 2×)
- Distortion: SC diode chain ±1.4V; HC ±5.8V; WF Vth=±1.4V (~18 folds)
- LFO: one-pole peak rounding at 10× rate (integrator slew model)

**Pre-layout verification complete (2026-05-28).** Adversarial Phase 1 (DSP↔spec cross-check),
Phase 2 (IC allocation), Phase 3 (signal-path trace), and Phase 4 (BOM completeness) all passed.
Corrections applied: LFO formula + R_CCW_END; Q_min deviation documented; HP Q spare cell
termination specified; R_TILT_INV tolerance flags added; block-1 signal-routing stale values
corrected; block-B output Z attenuation corrected; BP_MIX wet polarity circuit corrected.

**Remaining work before PCB layout:**
1. **Write 48HP KiCad generator** — replaces 40HP-era stale generators; inputs from components.yaml + panel-data.yaml
2. **Phase 6R** — VCV Rack signal-path smoke tests (CI integration)

**THAT 2180 audio I/O resolved (2026-05-28):** Single-ended operation confirmed throughout
(IN+ = signal, IN− → AGND direct; OUT+ = signal out, OUT− → 10 kΩ → AGND via R_OUT_N_L/R).
Stage boundaries verified: Block 1→VCA −0.006 dB; VCA→LP1 −0.009 dB — both negligible.
Exact IN+ (~20 kΩ) and OUT+ (<100 Ω) impedance figures are typical values from THAT Corp
application notes; confirm from THAT 2180A14-U datasheet during PCB layout.

**Open prototype questions (Phase 3R advisory, not blocking):**
- block-2: LFO LED: confirm pulsing (half-wave rectified) vs breathing (no diode) — prototype preference
- block-6: WF fold threshold Vth diode-current dependency — bench characterization of fold shape at various drive levels (informational; topology is correct)

---

## Archive

Old 40HP specs (envelope follower, APCF, COMB, FB_DIST_BLEND, old block numbering):
`specs/archive/40hp-era-2026-05/`
