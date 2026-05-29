# POGO — Hardware Spec Status

Last updated: 2026-05-28 | Topology: 48HP | Source of truth: `tools/panel-data.yaml`

## Phase Key

| Symbol | Meaning |
|---|---|
| ✅ | Complete |
| ⚠️ | Complete with known deviation (documented) |
| 🔲 | Not started |
| 🚧 | In progress |

---

## Block Specs (`specs/block-N/spec.md`)

> **Design source of truth is now `tools/panel-data.yaml`** (as of 2026-05-28).
> §1 Intent sections re-verified against panel. §2/§3/§4 marked STALE pending re-verification.
> Do not use §2/§3/§4 for circuit construction until re-verified against the updated §1.

| Block | Name | §1 Intent | §2/§3/§4 | Notes |
|---|---|---|---|---|
| A | Input Buffer | ✅ panel-verified | ⚠️ STALE | OPA1612 follower, BAT54S clamp |
| 1 | Pre-Gain | ✅ panel-verified | ⚠️ STALE | OPA1612, 1×/5× switch; ALT_BP path |
| 2 | Dual LFO | ✅ panel-verified | ⚠️ STALE | Integrator+Schmitt; formula corrected; R_CCW_END 2×100MΩ |
| 3 | Mod Bus | ✅ panel-verified | ⚠️ STALE | 19 destinations; 7× TL074CDT |
| 4 | VCA | ✅ panel-verified | ⚠️ STALE | THAT 2180 dB-law; DSP updated to match |
| 5 | LP Filter 1 | ✅ panel-verified | ⚠️ STALE | OTA-C SVF; stereo tilt (symmetric ±V_tilt L/R) |
| 6 | Triple BP + Dist | ✅ **rewritten 2026-05-28** | ⚠️ STALE | Panel redesigned: per-band DIST switch, FOCUS, TILT; BP_BYPASS+WET model |
| 7 | HP Filter | ✅ panel-verified | ⚠️ STALE | OTA-C SVF; G=−1 buffer corrects SUM_AMP inversion |
| 8 | LP Filter 2 | ✅ panel-verified | ⚠️ STALE | OTA-C SVF; independent from LP1 |
| B | Output Buffer | ✅ panel-verified | ⚠️ STALE | TL072; MAIN_L/R from LP2 + BP3_L/R tap |

## aux/ Circuit Library (`specs/aux/aux-*.md`)

> All aux files marked STALE (2026-05-28) — pending re-verification against updated §1 Intent.

| File | Status | Notes |
|---|---|---|
| aux-ota-c-svf | ⚠️ STALE | ASCII schematic + full derivations |
| aux-expo-converter | ⚠️ STALE | Component values + trim procedure |
| aux-q-control | ⚠️ STALE | IRES_AMP driver + IC sharing plan |
| aux-vca-cell | ⚠️ STALE | THAT 2180 dB-law; DSP matches |
| aux-unity-buffer | ⚠️ STALE | G=+1 and G=−1 variants |
| aux-distortion | ⚠️ STALE | SC/HC/WF + CD4053 mux wiring |
| aux-attenuverter | ⚠️ STALE | Bipolar pot + TL074 inverter |
| aux-mod-bus-core | ⚠️ STALE | MB_AMP + MB_INV; ±10V clamp |
| aux-lfo-core | ⚠️ STALE | Integrator + Schmitt; 0.05–20 Hz |
| aux-cv-protection | ⚠️ STALE | Moved from shared/; content unchanged |
| aux-power-filter | ⚠️ STALE | Moved from shared/; content unchanged |

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
| `kicad/generate_schematic.py` | 🚧 48HP data-driven generator — framework done, **block-A complete** (1/10 blocks). Rollout plan: `kicad/SCHEMATIC-GEN-PLAN.md` |
| `kicad/nets/*.nets.yaml` | 🚧 per-block netlists — `block-A` done |
| `kicad/generate_control_board.py`, `generate_utility_board.py` | ⚠️ 40HP-era STALE (see kicad/README-STALE.md) |
| `kicad/validate_*.py` | ⚠️ 40HP-era STALE |
| `.github/workflows/build.yml` schematic gate | ✅ `generate_schematic.py --check` (validate + structural verify + drift) in all jobs |
| `.github/workflows/build.yml` KiCad (kiutils) job | Disabled |

---

## Next Up

**Phase 3R is complete for all blocks.** All previously documented DSP/hardware deviations are
now resolved — the plugin is a faithful behavioral model of the hardware. Intentional DSP
advantages retained: exact 1V/oct tracking, exact LFO rate law, LFO phase reset, extended Q
range (creative tool).

**Phase 4R (Panel) — DONE.** `tools/panel-data.yaml` DRC-clean. Panel is now the design source of truth.

**Panel-as-truth spec update complete (2026-05-28).** `tools/panel-data.yaml` declared design source of truth. All §1 Intent sections re-verified against panel. GAIN_MAIN_PARAM→GAIN_PARAM and GAIN_BP3_PARAM→ALT_GAIN_PARAM renamed in plugin to match panel. Block-6 §1 Intent fully rewritten to reflect per-band DIST_MODE switch, FOCUS, TILT, CLIP LED, and BP_BYPASS/WET additive model. module-overview.md parameter table and modulation destination table updated. All §2/§3/§4 and aux/ marked STALE.

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
1. **48HP KiCad schematic generator** — 🚧 in progress. Data-driven generator
   (`kicad/generate_schematic.py`) built and proven on **block-A**; replaces the
   40HP-era stale generators. Per-block netlists in `kicad/nets/*.nets.yaml`,
   footprints resolved from the `components/` registry, byte-stable output, pin-
   coverage + structural verification gated in CI. Remaining: transcribe blocks
   B, 1, 2, 4, 5, 6, 7, 8, 3. **Order, symbol gaps, and per-block checklist:
   `kicad/SCHEMATIC-GEN-PLAN.md`.**
2. **Phase 6R** — VCV Rack signal-path smoke tests (CI integration)

**THAT 2180 audio I/O resolved (2026-05-28):** Single-ended operation confirmed throughout
(IN+ = signal, IN− → AGND direct; OUT+ = signal out, OUT− → 10 kΩ → AGND via R_OUT_N_L/R).
Stage boundaries verified: Block 1→VCA −0.006 dB; VCA→LP1 −0.009 dB — both negligible.
Exact IN+ (~20 kΩ) and OUT+ (<100 Ω) impedance figures are typical values from THAT Corp
application notes; confirm from THAT 2180A14-U datasheet during PCB layout.

**Open prototype questions:** None. All resolved.
- block-2 LFO LED: pulsing confirmed (half-wave rectified via D_LED 1N4148W). Signal
  routing updated to include diode in path.
- block-6 WF Vth: diode-current dependency analyzed and documented (Vth 1.24–1.44 V
  across drive range; ±10% of DSP target at practical fold depths; accepted characteristic).

---

## Archive

Old 40HP specs (envelope follower, APCF, COMB, FB_DIST_BLEND, old block numbering):
`specs/archive/40hp-era-2026-05/`
