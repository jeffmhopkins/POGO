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

## Result

Audit complete. Report: `specs/component-verification-report.md`. 6 parallel adversarial
agents (5 web-sourced part batches + 1 registry-internal). Two board-breaking findings
independently re-verified by the lead.

**HIGH (board-breaking):**
- `that2180` — MPN `THAT2180LD` does not exist (real: `2180{A,B,C}L08-U`); package is
  **8-pin SIP through-hole only**, not SOIC-8 SMD. Error propagated to `components.yaml`
  U4/U5 and CLAUDE.md's component philosophy.
- `bat54s` — symbol draws **common-cathode (BAT54C)** topology with the common node on
  pin 2; real BAT54S is a **series** dual (1=A1, 2=K2, 3=K1;A2). Affects all clamp nets.

**MEDIUM:** `R_INV_IN`/`R_INV_FB` missing `tol:1%` (header requires it; 38 parts); jack
symbol pins `1/2/3` ↔ pads `S/T/TN` (+ `SW`↔`TN`); `slide_pot_45mm` unsourced + 20mm/45mm
supplier conflict; `bzx84c10` no `datasheet:` block.

**LOW/cosmetic:** `bourns_3296w` stale `version`; `opa1612` no `symbol:` field; 4 weak
supplier-page datasheets; DW3/DW5 placeholder MPNs; cd4053 doc-number drift + EOL; 6 orphan
footprints; `c.yaml` "+" on non-polarized cap; misc version-string style.

**Verified correct:** all pinouts (opa1612, tl072/74, lm13700 16/16, that340, cd4053 16/16,
that2180 pins, diodes/zeners), ref-uniqueness 476/476, `part:`↔`matches[]` 24×1:1, BOM 13/13.

No fixes applied (report-only). Follow-ups listed in the report (Lane B / Lane C).

## Notes / Phase-3R flags

Audit only; advances no block's 1R–6R status. Findings spawn Lane-B (that2180, bat54s,
slide_pot_45mm, jack) and Lane-C (metadata) fixes — each its own gated change.
