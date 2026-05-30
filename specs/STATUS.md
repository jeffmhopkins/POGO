# POGO — Hardware Spec Status

Last updated: 2026-05-29 | Topology: 48HP | Source of truth: `tools/panel-data.yaml`

> **Change process:** all changes follow the gated, plugin-first, one-change-per-branch
> workflow in `CLAUDE.md` → "Git Workflow & Change Process" (Lanes A/B/C, Steps 0–8, gates
> G1–G6), tracked in `changes/NNNN-<slug>.md`. The Phase 1R–6R milestones below are the
> whole-project maturity track; the per-change Steps 0–8 are orthogonal to them.

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
| A | Input Buffer | ✅ panel-verified | ✅ re-verified 2026-05-30 | OPA1612 follower, BAT54S clamp; no behavioral divergence vs locked plugin (change 0018) |
| 1 | Pre-Gain | ✅ panel-verified | ✅ re-verified 2026-05-30 | OPA1612, 1×/5× switch; ALT_BP path → VCA → BP3-only (corrected, 0018); ALT VCA cell/BP3 selector tracked in block-4/6 |
| 2 | Dual LFO | ✅ panel-verified | ✅ rate net FINALIZED 2026-05-29 | Integrator+Schmitt; drive-attenuator rate control (fixed R_INT + trimpot attenuator) |
| 3 | Mod Bus | ✅ panel-verified | ✅ re-verified 2026-05-30 | MOD_SRC 3-way (SW7 DW5) wired; 18 attenuverters + raw VCA normal; 6× TL074; ±10V zener; MOD LEDs removed; FOCUS→TILT (0018) |
| 4 | VCA | ✅ panel-verified | ✅ re-verified 2026-05-30 | THAT 2180 current-in/I-V-out; +ALT-BP VCA cell (4 cells total, shared V_ctrl → BP3); VCA_OFS placement fixed; RV24/25→RV44/45 (0018) |
| 5 | LP Filter 1 | ✅ panel-verified | ✅ re-verified 2026-05-30 | OTA-C SVF; per-channel expo (true tilt); reaches self-oscillation (matches plugin); hosts shared U9/U10 Q-VCAs (co-owned block-8); doc/banner cleanup (0018) |
| 6 | Triple BP + Dist | ✅ panel-verified | 🚧 **split into 7 sections (0018); plugin-alignment pending** | Monolith split into `block-6-{svf1,svf2,svf3,dist1,dist2,dist3,mix}` (behavior-preserving, all gates green). Per-section alignment to plugin **still pending**: DIST→SVF reorder (0017 core), BP3 input selector (← block-4 ALT-VCA), CLIP-LED repoint, per-band TILT ×0.22 CV. U73 shared svf1/svf2. |
| 7 | HP Filter | ✅ panel-verified | ✅ transcribed 2026-05-29 | OTA-C SVF; HP inverting output buffer; own Q-VCAs; IRES_AMP + buffer pulldowns added |
| 8 | LP Filter 2 | ✅ panel-verified | ✅ transcribed 2026-05-29 | OTA-C SVF; mono (single expo); Q via the shared U9/U10 cell B (hosted on block-5); IRES_AMP + buffer pulldowns added |
| B | Output Buffer | ✅ panel-verified | ⚠️ STALE | TL072; MAIN_L/R from LP2 + BP3_L/R tap |

## aux/ Circuit Library (`specs/aux/aux-*.md`)

> All aux files marked STALE (2026-05-28) — pending re-verification against updated §1 Intent.

| File | Status | Notes |
|---|---|---|
| aux-ota-c-svf | ⚠️ STALE | ASCII schematic + full derivations |
| aux-expo-converter | ⚠️ STALE | Component values + trim procedure |
| aux-q-control | ⚠️ STALE | IRES_AMP driver + IC sharing plan |
| aux-vca-cell | ✅ CORRECTED 2026-05-29 | THAT 2180 current-in/I-V-out; Ec+ control |
| aux-unity-buffer | ⚠️ STALE | G=+1 and G=−1 variants |
| aux-distortion | ⚠️ STALE | SC/HC/WF + CD4053 mux wiring |
| aux-attenuverter | ⚠️ STALE | Bipolar pot + TL074 inverter |
| aux-mod-bus-core | ✅ transcribed 2026-05-29 | MB_AMP + MB_INV; ±10V BZX84C10 clamp |
| aux-lfo-core | ⚠️ STALE | Integrator + Schmitt; 0.05–20 Hz |
| aux-cv-protection | ⚠️ STALE | Moved from shared/; content unchanged |
| aux-power-filter | ⚠️ STALE | Moved from shared/; content unchanged |

No SVG files — ASCII schematics within each `.md` are the source of truth.
Circuit diagrams in spec text must be self-sufficient.

## Global Component Registry

| File | Status |
|---|---|
| `specs/components.yaml` | ✅ Complete — 476 entries; all boards; all ICs, discretes, and key passives with values; qty field for repeated identical parts |

## Panels & Layout

| File | Status |
|---|---|
| `tools/panel-data.yaml` | ✅ DRC-clean (48HP topology) |
| `specs/board-layout/layout-notes.md` | ✅ |

## KiCad Generators

| File | Status |
|---|---|
| `tools/generate_schematic.py` | ✅ 48HP data-driven generator — **all 10 blocks complete (10/10)**. Multi-unit op-amp placement + short-detection fixed 2026-05-29; CD4053 symbol pinout datasheet-corrected for block-6. Rollout plan: `tools/SCHEMATIC-GEN-PLAN.md` |
| `specs/block-*/*.nets.yaml` | ✅ per-block netlist SOURCES (live with each block spec) — `block-A/B/1/2/3/4/5/6/7/8` all done (10/10); the shared Q-VCAs are hosted on block-5 |
| `components/footprints/*.pretty` | ✅ vendored KiCad footprint libs (moved from kicad/; resolved via generated `kicad/fp-lib-table`) |
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
   (`tools/generate_schematic.py`) built and proven on **block-A**; replaces the
   40HP-era stale generators (now removed). Per-block netlists in `specs/block-*/*.nets.yaml`,
   footprints resolved from the `components/` registry, byte-stable output, pin-
   coverage + structural verification gated in CI. **All 10 blocks done (10/10).**
   **Order, symbol gaps, and per-block checklist:
   `tools/SCHEMATIC-GEN-PLAN.md`.**
2. **Phase 6R** — VCV Rack signal-path smoke tests (CI integration)

**THAT 2180 I/O CORRECTED (2026-05-29):** The earlier "single-ended IN+/IN−/OUT+/OUT−,
no output op-amp, OUT− → 10 kΩ" conclusion was **wrong** — it assumed a differential
*voltage* part. The committed datasheet (Doc 600029 Rev 02, Table 1) shows the THAT2180
is **current-in (pin 1 Input) / current-out (pin 8 Output)**, pinout
Input=1, Ec+=2, Ec−=3, Sym=4, V−=5, Gnd=6, V+=7, Output=8. The corrected block-4 cell
uses **R_in (V→I)** at the input and a **transimpedance op-amp (I→V) per channel** at the
output (inverting, unity at 0 dB; the inversion is compensated by LP1's inverting SUM_AMP).
Gain via Ec+ (+6.1 mV/dB; Ec+ = 244 mV·(control−1)); Ec−/Sym/Gnd → AGND. The bogus
R_OUT_N_L/R were removed and an I/V op-amp (U6) + CV-conditioning op-amp (U63) added.
See `specs/block-4/block-4.nets.yaml`, `specs/aux/aux-vca-cell.md`, `specs/block-4/spec.md`.

**Open prototype questions:** None. All resolved.
- block-2 LFO LED: pulsing confirmed (half-wave rectified via D_LED 1N4148W). Signal
  routing updated to include diode in path.
- block-6 WF Vth: diode-current dependency analyzed and documented (Vth 1.24–1.44 V
  across drive range; ±10% of DSP target at practical fold depths; accepted characteristic).

---

## Archive

Old 40HP specs (envelope follower, APCF, COMB, FB_DIST_BLEND, old block numbering):
`specs/archive/40hp-era-2026-05/`
