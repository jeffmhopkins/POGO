# POGO Design Status — 48HP Topology

## Paradigm: Code-First Reverse Engineering

The working VCV Rack plugin (`plugin/src/Pogo.cpp`) and panel (`tools/panel-data.yaml`)
are the source of truth. Hardware design documentation is reverse-engineered from them.

**Phases:**
- **Phase 1R** — Extract functional spec from working plugin code
- **Phase 2R** — Map DSP behavior to analog model (bilinear transform inverse)
- **Phase 3R** — Circuit design constrained by Phase 2R spec
- **Phase 4R** — Panel (DONE — `tools/panel-data.yaml` is source of truth, DRC clean)
- **Phase 5R** — Board layout (48HP, architecture under review)
- **Phase 6R** — Code validation (CI green, signal-path smoke tests)

---

## Per-Block Status

| Block | Phase 1R: Extract | Phase 2R: Analog | Phase 3R: Circuit | Phase 6R: Code |
|---|---|---|---|---|
| Mod Architecture | ✅ | [ ] | [ ] | ✅ |
| Block A: Input Buffer | ✅ | ✅ | ✅ | ✅ |
| Block 1: Pre-Gain | ✅ | ✅ | ✅ | ✅ |
| Block LFO (dual triangle) | ✅ skeleton | [ ] | [ ] | ✅ |
| Block VCA (+ VCA_OFS) | ✅ | [ ] | [ ] | ✅ |
| Block LP1 (+ TILT) | ✅ | [ ] | [ ] | ✅ |
| Block BP (Triple SVF, 2× OS) | ✅ skeleton | [ ] | [ ] | ✅ |
| Block 4: Distortion | ✅ | ✅ | ✅ | ✅ |
| Block HP | ✅ | [ ] | [ ] | ✅ |
| Block LP2 | ✅ | [ ] | [ ] | ✅ |
| Block B: Output Buffer | ✅ | ✅ | ✅ | ✅ |

Legend: ✅ complete · ✅ skeleton = Phase 1R written, Phase 2R/3R are stubs · [ ] not started

**Phase 1R notes:**
- Block LFO and Block BP: spec files written with full functional detail and Phase 2R/3R
  placeholders, but Phase 2R (analog math) and Phase 3R (circuit design) are not done
- All other Phase 1R items: fully extracted from plugin code

---

## Module-Level Phases

- ✅ **Phase 4R: Panel** — `tools/panel-data.yaml` defines all 48HP positions; DRC clean;
  CI regenerates `plugin/res/Pogo-source.svg` on every push.

- 🔄 **Phase 5R: Board Layout** — Architecture under review for 48HP (243.84mm wide).
  40HP 3-board split archived at `specs/archive/40hp-era-2026-05/layout-notes.md`.
  Options documented in `specs/board-layout/layout-notes.md`.

- ✅ **Phase 6R: Code** — CI passing on Linux/Windows/macOS. Plugin builds clean.

---

## Next Up: Phase 2R

All blocks need Phase 2R (analog behavior model). Suggested order:

1. **Block LFO** — triangle oscillator; simplest analog model; good starting point
2. **Block VCA** — THAT 2180 is well-documented; gain law derivation is straightforward
3. **Block LP1 / LP2 / HP** — same OTA-C SVF topology; bilinear transform inverse; do once, apply three times
4. **Block BP (Triple SVF)** — same SVF math as LP1/HP; main challenge is 1/Q² normalization and 3× group scaling
5. **Block 4: Distortion** — nonlinear; tanh / clipping / arcsin(sin) analog equivalents
6. **Mod Architecture** — op-amp summer + attenuverter; well-understood

---

## Source of Truth References

| Topic | File |
|---|---|
| Plugin params / signal chain | `docs/plugin-topology.md` |
| Panel positions / DRC | `tools/panel-data.yaml` |
| Plugin code | `plugin/src/Pogo.cpp`, `plugin/src/dsp/*.hpp` |
| Panel SVG (generated) | `plugin/res/Pogo-source.svg` |

Last updated: 2026-05-27
