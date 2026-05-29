# Change 0002: refresh README for current status + change process

- **Slug:** readme-refresh   **Branch:** `change/readme-refresh`
- **Lane:** C (docs only — no DSP / panel / components / nets connectivity)
- **Status:** CLOSED   **Blocks:** none   **Boards:** n/a
- **Opened:** 2026-05-29   **Closed:** 2026-05-29   **PR:** #25

> Backfilled record (created retroactively in change 0004, after the policy moved to
> "log every change"). The work itself merged via PR #25.

## Intent

Root `README.md` predated the schematic generator and the change process. Refresh both:
fix the stale status and add the update methodology.

## Summary

- Replaced the "KiCad generators are 40HP-era stale / schematics in Phase 5R" section with
  the current data-driven per-block generator (10/10 blocks + shared-q, `--check`); scoped
  the STALE note to the legacy board generators only.
- Repository Structure: fixed `kicad/` tree, added `components/` + `changes/`, corrected
  `components.yaml` count (265 → 476), fixed block-A/block-1 ICs (→ OPA1612).
- CI line: five `--check` gates + `change/**` trigger.
- Added "How Changes Are Made" (lanes A/B/C, `change/<slug>` → dev, plugin-leads),
  orthogonal to Phase 1R–6R.

## Verification

All five `--check` gates pass (schematic 11/11, panel DRC PASS, components/datasheets OK).
