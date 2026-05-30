# Change 0015: Adversarial component verification audit

- **Slug:** component-audit          **Branch:** `change/component-audit`
- **Lane:** C (audit / docs-only — produces a report, changes no DSP/panel/netlist)
- **Status:** OPEN
- **Blocks:** all (registry-wide)   **Boards:** audio | control | utility | panel
- **Opened:** 2026-05-30       **Closed:** —
- **PR:** —              **CI run:** —

> Lanes & gates are defined in `CLAUDE.md` → "Git Workflow & Change Process".

## Intent

Adversarially verify **every sourced component** in the registry against **primary
datasheets** — MPN reality, datasheet provenance/revision, package↔footprint geometry,
symbol pin-map↔datasheet pinout, and `matches[]` linkage — to catch errors the five CI
`--check` gates cannot (they verify *artifact self-consistency*, not correctness vs.
physical reality, per CLAUDE.md's enforcement note).

The deliverable is a graded discrepancy report. **No fixes are applied** in this change;
any fix found becomes its own Lane-B/Lane-C change for separate approval.

## Scope / Out of scope

**In scope (audit only):**
- 19 sourced parts `components/parts/<slug>/component.yaml` (+ committed `datasheet.pdf`)
- 16 symbol primitives `components/symbols/*.yaml` (pin number→function maps)
- Footprints `components/footprints/*.pretty/*.kicad_mod` (pad geometry vs. datasheet)
- `components/footprints.yaml` panel bindings + anchor offsets
- `specs/components.yaml` (476 refs): ref-uniqueness, value sanity, `part:`↔`matches[]`
- Generated `kicad/*.kicad_sch` + `kicad/pogo-bom.csv` (spot-audit; already gate-checked)

**Out of scope:**
- Any edit to `plugin/src/**`, `tools/panel-data.yaml`, DSP behavior (locked surfaces).
- Schematic/netlist regeneration. Footprint/symbol/registry **fixes** (recommended only).

## Method

Full web-sourced audit. Parallel adversarial agents, each treating a record as guilty
until proven correct against a primary source (local committed PDF via Read + manufacturer
/distributor pages via WebSearch/WebFetch). Per-part 6-point check: MPN reality ·
datasheet revision · package match · pinout match · `matches[]` linkage · footprint pad
coverage.

## Deliverable

`specs/component-verification-report.md` — every component graded ✅ verified /
⚠️ discrepancy / 🔲 unverifiable, each finding citing datasheet + page/section, plus a
prioritized list of recommended follow-up fixes.

## Decisions log

- 2026-05-30: Lane C audit, report-only, on `change/component-audit` off `dev` — per user.
- 2026-05-30: Agents Read committed local `datasheet.pdf` for pinout/package (WebFetch's
  summarizer is unreliable on raw PDF binaries); WebSearch used for MPN/revision cross-check.

## Seed discrepancy candidates (to confirm in run)

- `bzx84c10` has no committed `datasheet.pdf` though sibling `bzx84c5v1` does and they
  share the Nexperia `BZX84_SER` datasheet — likely should carry the same PDF + sha256.
- Jack symbol pins `1/2/3` vs. footprint pads `S/T/TN` (tolerated WARN) — needs a verdict.
- Supplier-page (NOPDF) parts — confirm each is genuinely catalog-only, not a missed PDF.

## Notes / Phase-3R flags

Audit only; advances no block's 1R–6R status. Findings may spawn Lane-B fixes.
