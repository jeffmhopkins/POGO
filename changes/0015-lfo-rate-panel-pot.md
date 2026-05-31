# Change 0015: LFO Rate uses a 9mm panel pot (like the attenuverters), not a 3296W trimmer

- **Slug:** lfo-rate-panel-pot   **Branch:** `change/lfo-rate-panel-pot`
- **Lane:** B (hardware-only — plugin LOCKED & unchanged: LFO1/2_RATE stay `Trimpot` widget / panel
  `type: trimpot`; only the hardware part + spec change. No DSP, no panel geometry, no VCV re-verify.)
- **Status:** IMPLEMENTED (awaiting CI green + merge)   **Blocks:** block-2   **Boards:** control
- **Opened:** 2026-05-30

## Intent
LFO Rate 1/2 (block-2 `RV1`/`RV2`) were specced as **Bourns 3296W** — a screwdriver board trimmer —
yet they are front-panel rate controls. The plugin (`Trimpot` widget) and panel (`type: trimpot`)
already treat them exactly like the attenuverters; only the BOM diverged. Make the hardware part
match the attenuverters: a **9mm log-taper panel pot** (RD901F family), player-adjustable. Maintainer
chose **log** taper (over linear) so rotation ≈ the plugin's `0.05×400^param` exponential sweep.

## What changed (no plugin/panel edit)
- `specs/components.yaml` RV1/RV2: `Bourns 3296W` / `through-hole` → **`log pot` / `9mm`** (resolves to
  Alpha RD901F-40, the attenuverter footprint). `1MΩ`, log taper.
- `specs/block-2/block-2.nets.yaml` RV1/RV2 `part:` → `log pot`. Connectivity unchanged (still a
  3-terminal divider on V_sq; `sym: trimpot`).
- `specs/block-2/spec.md` §1/§2/§3: rate control is a 9mm log panel pot, not a screwdriver preset; the
  drive-attenuator topology is **retained**; the log taper now provides the (≈exponential) rate-vs-
  rotation sweep. Added a Phase-3R **prototype-verify** note: a 1 MΩ pot's wiper source impedance
  (~R_pot/4) adds to R_INT (590 kΩ) and bends the f-vs-rotation curve — trim R_FLOOR/pot value or
  buffer the wiper on the prototype.
- `specs/aux/aux-lfo-core.md`: resolved the stale "Expo Taper vs Log Pot (Phase 3R open item)" and the
  superseded "vary-R_int rheostat" component table → drive-attenuator + 9mm log panel pot. (Doc is still
  `⚠️ STALE`-flagged for the unrelated LED/threshold content; only the rate section was in scope.)
- Regenerated `kicad/pogo-block-2.kicad_sch` + `kicad/pogo-bom.csv` (+ docs copy).

## Verification
- All 5 CI gates green. RV1/RV2 now share the RD901F-40 footprint with all 18 attenuverter rows.
- Cross-check gate (0013): nets `sym: trimpot` == part `log pot`→`symbol: trimpot` ✓.

## Decisions log
- 2026-05-30: 3296W trimmer was wrong for a panel control; use the attenuverter panel-pot family
  (maintainer). Taper = **log** (maintainer), for the exponential hand-sweep matching the DSP law.
- 2026-05-30: drive-attenuator topology kept (works with a log pot); pot value 1 MΩ / R_FLOOR 2.4 kΩ
  retained, with wiper-loading flagged as a prototype-trim item rather than redesigned here.
