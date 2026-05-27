# POGO — Hardware Spec Status

Last updated: 2026-05-27 | Topology: 48HP

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
| 2 | Dual LFO | ✅ | ✅ | 🔲 | Topology TBD (integrator+comparator vs VCO IC) |
| 3 | Mod Bus | ✅ | ✅ | 🔲 | 20 destinations, 11× TL074; full IC count at Phase 3R |
| 4 | VCA | ✅ | ✅ ⚠️ | ✅ | THAT 2180 dB-law vs DSP linear — intentional deviation |
| 5 | LP Filter 1 | ✅ | ✅ | ✅ | OTA-C SVF; stereo tilt (symmetric ±V_tilt L/R) |
| 6 | Triple BP + Dist | ✅ | ✅ | 🔲 | 3× OTA-C SVF + SC/HC/WF distortion; CD4053 mux |
| 7 | HP Filter | ✅ | ✅ | ✅ | OTA-C SVF; G=−1 buffer corrects SUM_AMP inversion |
| 8 | LP Filter 2 | ✅ | ✅ | ✅ | OTA-C SVF; independent from LP1; shares Q VCA LM13700 |
| B | Output Buffer | ✅ | ✅ | ✅ | TL072; MAIN_L/R from LP2 + BP3_L/R tap |

## aux/ Circuit Library (`specs/aux/aux-*.md`)

| File | Status | Notes |
|---|---|---|
| aux-ota-c-svf | 🚧 | Written; SVG placeholder |
| aux-expo-converter | 🚧 | Written; SVG placeholder |
| aux-q-control | 🚧 | Written; SVG placeholder |
| aux-vca-cell | 🚧 | Written; SVG placeholder |
| aux-unity-buffer | 🚧 | Written; SVG placeholder |
| aux-distortion | 🚧 | Written; SVG placeholder |
| aux-attenuverter | 🚧 | Written; SVG placeholder |
| aux-mod-bus-core | 🚧 | Written; SVG placeholder |
| aux-lfo-core | 🚧 | Written; SVG placeholder |
| aux-cv-protection | ✅ | Moved from shared/; content unchanged |
| aux-power-filter | ✅ | Moved from shared/; content unchanged |

SVG schematic diagrams: all placeholder (`.svg` files are empty). Fill in manually
using KiCad SVG export or Inkscape as a separate session.

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

Phase 3R remaining work:
1. **block-2** (LFO): Choose integrator+comparator topology; verify oscillation stability; add component values
2. **block-3** (Mod Bus): Full IC placement; LED driver resistors; add attenuverter R_Iabc detail
3. **block-6** (BP+Dist): Full distortion sub-circuit design; CD4053 wiring diagram; Q normalization network; power draw detail

After Phase 3R complete for all blocks:
- Replace aux/*.svg placeholders with real schematic diagrams (KiCad/Inkscape)
- Finalize components.yaml (all passive values, all ref designators unique and checked)
- Write 48HP KiCad generator (replaces 40HP-era generators)
- Phase 6R: VCV Rack signal-path smoke tests

---

## Archive

Old 40HP specs (envelope follower, APCF, COMB, FB_DIST_BLEND, old block numbering):
`specs/archive/40hp-era-2026-05/`
