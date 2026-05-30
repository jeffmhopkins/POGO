# Change 0015: Adversarial component verification audit

- **Slug:** component-audit          **Branch:** `change/component-audit`
- **Lane:** B (hardware-only — registry/symbol/footprint/nets/spec fixes; plugin DSP untouched)
- **Status:** SCHEMATIC-DONE (fixes applied; all 5 `--check` gates green)
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

## Fixes applied (this change, per user request)

**HIGH — board-breaking:**
- **that2180** → MPN `THAT2180AL08-U` (grade A), `package: SIP-8`, footprint rebound to a
  newly **vendored SIP-8 footprint** `components/footprints/Package_SIP.pretty/SIP-8_2.54mm.kicad_mod`
  (2.54mm THT land pattern, datasheet-cited). Fixed `components.yaml` U4/U5 (`pkg: SIP-8`) and
  CLAUDE.md component philosophy.
- **bat54s** → symbol `components/symbols/bat54s.yaml` redrawn to the real **series** topology
  (1=A1, 2=K2, 3=K1;A2 junction). Netlists corrected by swapping pins 2↔3 on **all 24 BAT54S
  instances** (block-A D1/D2, block-1 D8/D9, block-3 D4+D3_1..18, block-4 D3): signal→pin3
  junction, +12V→pin2/K2, −12V→pin1/A1. Specs `aux-cv-protection.md` + `block-A/spec.md`
  corrected (both had the signal node mislabeled as pin 2; block-A also had D_low reversed).

**MEDIUM/LOW:**
- `R_INV_IN`/`R_INV_FB` → added `tol: "1%"` (header-required >60 dB null).
- `slide_pot_45mm` → MPN `RA4522F-20-15F1` (Alpha 45mm), supplier Rapid/Banzai, datasheet
  fixed; footprint kept 45mm per decision.
- `bzx84c10` → added `datasheet:` block (shared `BZX84_SER.pdf` committed + sha256/bytes match),
  MPN canonical `BZX84-C10` (matches[] keeps `BZX84C10` for components.yaml binding).
- `opa1612` → added `symbol: opamp2`.
- `bourns_3296w` version → `REV. 02/26`; `bourns_3224w` → `REV. 07/24`.
- `cd4053.yaml` pinout_datasheet → `SCHS047O`; `c.yaml` pin-1 name `+` → `~`.

**Deferred (not applied):** jack symbol↔footprint `S/T/TN` reconciliation — the codebase
explicitly designates it "its own change" (`generate_schematic.py` advisory); left as a
documented WARN. cd4053 `CD4053BM`→`CD4053BNSR` EOL re-source — noted, not changed (sourcing).

**Regenerated + verified:** all 10 `*.kicad_sch`, `pogo-bom.csv`, `fp-lib-table` (now 11 libs
incl. `POGO_Package_SIP`), footprint SVGs, manifest, panel. **All 5 `--check` gates pass**
(components, fetch_datasheets, build_components, generate_schematic, build_panel/DRC).

## Notes / Phase-3R flags

Plugin DSP unaffected (no `plugin/src/**` change). The THAT2180 SMD→THT package flip has a
**board-layout impact** (block-4 audio board) — flag for the 48HP layout review. The BAT54S
fix changes input/CV clamp connectivity — re-verify on the prototype.

## Notes / Phase-3R flags

Audit only; advances no block's 1R–6R status. Findings spawn Lane-B (that2180, bat54s,
slide_pot_45mm, jack) and Lane-C (metadata) fixes — each its own gated change.
