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
| Mod Architecture | ⚠️ needs update | [ ] | [ ] | ✅ |
| Block A: Input Buffer | ✅ | ✅ | ✅ | ✅ |
| Block 1: Pre-Gain | ✅ | ✅ | ✅ | ✅ |
| **Block LFO (dual triangle)** | [ ] | [ ] | [ ] | ✅ |
| Block VCA (+ VCA_OFS) | ⚠️ needs VCA_OFS | [ ] | [ ] | ✅ |
| Block LP1 (+ TILT) | ⚠️ needs TILT | [ ] | [ ] | ✅ |
| **Block BP (Triple SVF, 2× OS)** | [ ] | [ ] | [ ] | ✅ |
| Block 4: Distortion | ✅ | ✅ | ✅ | ✅ |
| Block HP | ⚠️ needs position update | [ ] | [ ] | ✅ |
| Block LP2 | ⚠️ needs position update | [ ] | [ ] | ✅ |
| Block B: Output Buffer | ✅ | ✅ | ✅ | ✅ |

Legend: ✅ complete · ⚠️ exists but needs update · [ ] not started

---

## Module-Level Phases

- ✅ **Phase 4R: Panel** — `tools/panel-data.yaml` defines all 48HP positions; DRC clean;
  CI regenerates `plugin/res/Pogo-source.svg` on every push
  → `tools/panel-data.yaml`, `tools/build_panel.py`

- 🔄 **Phase 5R: Board Layout** — Architecture under review for 48HP (243.84mm wide).
  40HP 3-board split archived at `specs/archive/40hp-era-2026-05/layout-notes.md`.
  Options being evaluated: 3-board (wider), 2-board (combined utility+audio), other.
  → `specs/board-layout/layout-notes.md` (TBD)

---

## Documentation To-Do (Phase 1R completion)

| Task | File | Status |
|---|---|---|
| Create LFO spec | `specs/block-LFO/spec.md` | [ ] |
| Create Triple BP SVF spec | `specs/block-3-triple-bp/spec.md` | [ ] |
| Update mod-architecture | `specs/mod-architecture.md` | [ ] |
| Update block-VCA (add VCA_OFS) | `specs/block-VCA/spec.md` | [ ] |
| Update block-LP1 (add TILT, update position) | `specs/block-5-lp1/spec.md` | [ ] |
| Update block-LP2 (update chain position) | `specs/block-6-lp2/spec.md` | [ ] |
| Update block-HP (update chain position) | `specs/block-7-hp/spec.md` | [ ] |
| Write module overview | `specs/module-overview.md` | [ ] |
| Write panel-design stub | `specs/panel-design/panel-notes.md` | [ ] |
| Write board layout analysis | `specs/board-layout/layout-notes.md` | [ ] |

---

## Source of Truth References

| Topic | File |
|---|---|
| Plugin params / signal chain | `docs/plugin-topology.md` |
| Panel positions / DRC | `tools/panel-data.yaml` |
| Plugin code | `plugin/src/Pogo.cpp`, `plugin/src/dsp/*.hpp` |
| Panel SVG (generated) | `plugin/res/Pogo-source.svg` |

Last updated: 2026-05-27
