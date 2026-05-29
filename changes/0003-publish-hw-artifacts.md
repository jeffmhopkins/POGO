# Change 0003: publish hardware outputs as a downloadable CI artifact

- **Slug:** publish-hw-artifacts   **Branch:** `change/publish-hw-artifacts`
- **Lane:** C (CI only — no DSP / panel / components / nets connectivity)
- **Status:** CLOSED   **Blocks:** none   **Boards:** n/a
- **Opened:** 2026-05-29   **Closed:** 2026-05-29   **PR:** #26

> Backfilled record (created retroactively in change 0004). The work merged via PR #26.

## Intent

CI only uploaded the `.vcvplugin`; the BOM + schematics were committed-and-drift-gated but
not downloadable from a run. Publish them as a per-run artifact.

## Summary

Added `POGO-hardware-<run>` artifact, uploaded once from the Linux job (OS-independent),
bundling: `kicad/pogo-block-*.kicad_sch` + `pogo-shared-q.kicad_sch`, `kicad/pogo-bom.csv`,
`plugin/res/Pogo.svg`, `design/panel-debug.html`. Staged after the five `--check` gates;
excludes the STALE 40HP board schematics. `.vcvplugin` artifacts unchanged.

Deferred: rendered schematic PDFs (needs `kicad-cli` in CI).

## Verification

`build.yml` parses; the two new steps are present in the `build-linux` job only.
