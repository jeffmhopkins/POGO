# Change 0014: stale-markdown scrub (post symbol/restructure work)

- **Slug:** stale-md-scrub   **Branch:** `change/stale-md-scrub` (stacks on #37 — merge that first)
- **Lane:** C (docs only — no DSP math, no panel geometry, no components.yaml, no nets connectivity)
- **Status:** OPEN
- **Opened:** 2026-05-30

Thorough pass after 0009–0013 (repo consolidation, design→docs, scripts→tools, kicad_common slim,
data-driven + per-file symbols). Fixes stale prose that contradicts current reality. Excludes:
frozen `changes/*` records, the 40HP `specs/archive/**` (correct as history), and aux docs that
already self-flag `⚠️ STALE`.

Fixes:
- README.md — tools tree missing `symbols.py` + kicad_common mis-described; `components/` tree missing
  `symbols/<token>.yaml`; "Symbols/pinouts in kicad_common.py" → `components/symbols/` via symbols.py;
  "10 blocks + the shared-Q sheet" → 10/10 blocks, Q-VCAs hosted on block-5 (no separate sheet).
- tools/SCHEMATIC-GEN-PLAN.md — `sym_cd4053`/`cd4053_pins` → the CD4053 symbol (now
  `components/symbols/cd4053.yaml`); "(like shared-q)" wording; `power_sym()` alternative (removed).
- specs/block-6/spec.md — "like the shared-q sheet" + "wrong in kicad_common.py" → current locations.
- specs/module-overview.md — "20 CV destinations" → 19 (matches its own table + block-3).
- specs/aux/aux-mod-bus-core.md — "22 attenuverters/loads" → 19.
- specs/block-1/spec.md — `aux/unity-buffer.svg` → `.md` (no SVG specs exist).
- docs/plugin-topology.md — `GAIN_MAIN_PARAM`→`GAIN_PARAM`, `GAIN_BP3_PARAM`→`ALT_GAIN_PARAM`
  (renamed in plugin; verified against plugin/src/Pogo.cpp).

Noted, NOT changed (design-narrative, not a stale reference): aux-lfo-core.md Phase-3R rate-taper
open item that block-2 §2 closed (drive-attenuator) — left for a hardware-lane spec sync.
