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
| A | Input Buffer | ✅ | ✅ | ✅ | LM4562 follower, BAT54S clamp |
| 1 | Pre-Gain | ✅ | ✅ | ✅ | NE5532D, 1×/5× switch; ALT_BP path |
| 2 | Dual LFO | ✅ | ✅ | ✅ | Integrator+Schmitt; 47nF C0G; 1MΩ log pot + end R |
| 3 | Mod Bus | ✅ | ✅ | ✅ | 20 destinations; 7× TL074CDT; 470kΩ SCALE pot |
| 4 | VCA | ✅ | ✅ ⚠️ | ✅ | THAT 2180 dB-law vs DSP linear — intentional deviation |
| 5 | LP Filter 1 | ✅ | ✅ | ✅ | OTA-C SVF; stereo tilt (symmetric ±V_tilt L/R) |
| 6 | Triple BP + Dist | ✅ | ✅ | ✅ ⚠️ | SC/HC/WF sub-circuits + CD4053; BP_MIX+POL; Q norm deviation |
| 7 | HP Filter | ✅ | ✅ | ✅ | OTA-C SVF; G=−1 buffer corrects SUM_AMP inversion |
| 8 | LP Filter 2 | ✅ | ✅ | ✅ | OTA-C SVF; independent from LP1; shares Q VCA LM13700 |
| B | Output Buffer | ✅ | ✅ | ✅ | TL072; MAIN_L/R from LP2 + BP3_L/R tap |

## aux/ Circuit Library (`specs/aux/aux-*.md`)

| File | Status | Notes |
|---|---|---|
| aux-ota-c-svf | ✅ | ASCII schematic + full derivations |
| aux-expo-converter | ✅ | Component values + trim procedure |
| aux-q-control | ✅ | IRES_AMP driver + IC sharing plan |
| aux-vca-cell | ✅ | THAT 2180; DSP deviation documented |
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
| `specs/components.yaml` | 🚧 Partial — audio board + utility/control board populated; block-6 abbreviated; passive values TBD in some rows |

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

**Phase 3R is complete for all blocks.** Known deviations documented:
- block-4: THAT 2180 dB-law vs DSP linear VCA (intentional)
- block-6: Q normalization: hardware peak = 1 (constant), DSP peak = 1/Q (no hardware compensation)
- block-6: BP_MIX: hardware adds wet on top of dry; DSP crossfades (acceptable)
- block-6: HC clip threshold ±5.8V vs DSP ±5V (zener tolerance, acceptable)
- block-6: WF fold approximation requires prototype bench verification

**Phase 4R (Panel) — DONE.** `tools/panel-data.yaml` DRC-clean.

**Remaining work before PCB layout:**
1. **Finalize components.yaml** — fill all passive values (R, C); verify ref designator uniqueness per board; cross-check block-6 distortion BOM (abbreviated in first pass)
2. **Write 48HP KiCad generator** — replaces 40HP-era stale generators; inputs from components.yaml + panel-data.yaml
3. **Phase 6R** — VCV Rack signal-path smoke tests (CI integration)

**Open prototype questions (Phase 3R advisory, not blocking):**
- block-2: WF fold stage stability (phase margin with diode feedback at all drive levels)
- block-2: LED: confirm pulsing (half-wave rectified) vs breathing (no diode) — prototype preference
- block-6: WF transfer characteristic bench measurement vs DSP asin(sin(x)) reference
- block-6: BP_MIX gain compensation resistor value (to match DSP level at MIX=max)

---

## Archive

Old 40HP specs (envelope follower, APCF, COMB, FB_DIST_BLEND, old block numbering):
`specs/archive/40hp-era-2026-05/`
