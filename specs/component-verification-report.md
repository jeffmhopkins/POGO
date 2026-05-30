# POGO Component Verification Report — Adversarial Audit

- **Change:** `0015-component-audit` (Lane B — audit + fixes applied; see `changes/0015-component-audit.md` → "Fixes applied")
- **Status:** Findings below are the original audit. Most were subsequently **fixed in this
  same change** (THAT2180 SIP-8, BAT54S series-pinout + nets, R_INV tol, slider sourcing,
  bzx84c10 datasheet, opa1612 symbol, version strings). The jack `S/T/TN` divergence is the
  main item left deferred (its own change, per the codebase). All 5 `--check` gates green.
- **Date:** 2026-05-30
- **Scope:** all 19 sourced parts (`components/parts/`), 16 symbol primitives
  (`components/symbols/`), vendored footprints (`components/footprints/`),
  `components/footprints.yaml`, `specs/components.yaml` (476 refs), and the generated
  `kicad/pogo-bom.csv` / `fp-lib-table`.
- **Method:** full web-sourced adversarial audit. Six parallel agents treated every record
  as guilty-until-proven against **primary datasheets** (committed PDFs read directly +
  manufacturer/distributor cross-checks). The two board-breaking findings (THAT2180 package,
  BAT54S topology) were independently re-verified by the lead.

> **Premise.** All five CI `--check` gates currently **pass**. They verify *artifact
> self-consistency* (yaml↔sch, committed-PDF sha256, DRC, BOM drift) — **not** correctness
> against physical reality (per CLAUDE.md's enforcement note). Every finding below is a
> reality-vs-registry gap the gates cannot catch.

---

## Verdict at a glance

| # | Part / artifact | Verdict | Severity |
|---|---|---|---|
| 1 | **that2180** — fabricated MPN + wrong package/footprint (SIP-8, not SOIC-8) | ⚠️ | **HIGH (board-breaking)** |
| 2 | **bat54s** — symbol draws common-cathode (BAT54C); real BAT54S is series | ⚠️ | **HIGH (board-breaking)** |
| 3 | **R_INV_IN / R_INV_FB** — missing `tol: 1%` though header requires it (38 parts) | ⚠️ | MEDIUM |
| 4 | **thonkiconn jack** — symbol pins `1/2/3` vs footprint pads `S/T/TN` (30 jacks) | ⚠️ | MEDIUM |
| 5 | **slide_pot_45mm** — no MPN; datasheet link is a *20mm* slider; supplier conflict | 🔲 | MEDIUM |
| 6 | **bzx84c10** — no `datasheet:` block at all (sibling has full provenance) | ⚠️ | MEDIUM |
| 7 | **bourns_3296w** — `version: rev 2019-08-07` but committed PDF is REV. 02/26 | ⚠️ | LOW–MED |
| 8 | **opa1612** — only registered part with no `symbol:` field | ⚠️ | LOW |
| 9 | 4 parts (alpha pot, DW3, DW5, jack) settle for supplier page; real PDFs exist | ⚠️ | LOW |
| 10 | DW3/DW5 placeholder MPNs (`DW3`/`DW5`, not Dailywell 2M ordering codes) | ⚠️ | LOW |
| 11 | cd4053 symbol cites SCHS059 vs sourced SCHS047O; CD4053BM EOL | ⚠️ | LOW |
| 12 | 6 orphan vendored footprints (4× IDC, 1× pin-header, Alps RS4515N) | ⚠️ | LOW |
| 13 | c.yaml labels pin-1 "+" on non-polarized `Device:C`; misc version-string drift | ⚠️ | COSMETIC |

**Confirmed correct (no action):** opa1612 pinout, tl072, tl074, lm13700 (16/16 pins),
that340 (pin groups + SUB), cd4053 (16/16 pins), 1n4148w, bzx84c5v1, bourns_3224w,
led_3mm, all ref-uniqueness (476/476), all `part:`↔`matches[]` linkage (24 strings, 1:1),
BOM drift (13/13 sampled). TL072/TL074 sharing one PDF is **correct** (TI's combined TL07xx
datasheet). PJ301M-12 and THAT340S14-U exact-string matches verified.

---

## HIGH severity (board-breaking)

### 1. THAT2180 — fabricated MPN + wrong package class
`components/parts/that2180/component.yaml`, `specs/components.yaml` (U4, U5), CLAUDE.md.

- **MPN `THAT2180LD` does not exist.** THAT Corp ships only `2180AL08-U / 2180BL08-U /
  2180CL08-U` (grade A/B/C). Farnell confirms `THAT2180CL08-U`. The "LD" suffix is invalid.
- **Package is wrong.** The 2180 is **8-pin SIP, 2.54 mm / 0.100″ through-hole only**
  (datasheet Doc 600029 Rev 02, p.1 + Fig.15 "Package Style: 8 Pin SIP"; Farnell "SIP-8").
  **There is no SOIC/SMD variant.** The registry declares `package: SOIC-8` bound to
  `SOIC-8_3.9x4.9mm_P1.27mm` (1.27 mm SMD) — a board-breaking footprint mismatch.
- **Contamination:** the error propagates to `specs/components.yaml` U4/U5 (`pkg: SOIC-8`)
  **and to CLAUDE.md's component philosophy** ("Signal VCA: THAT 2180 (SOIC-8)").
- **Pinout is fine** (vca.yaml matches Table 1 pin-for-pin); only the physical package is wrong.
- **Fix (Lane B):** MPN → `THAT2180CL08-U`; `package` → `SIP-8`; vendor a SIP-8 2.54 mm
  through-hole footprint; correct U4/U5 in `components.yaml` and the CLAUDE.md line.

### 2. BAT54S — symbol misrepresents internal topology
`components/symbols/bat54s.yaml` (affects all BAT54S nets: D1/D2/D8/D9 input/ALT clamps,
the 19× `D_CLAMP`, MOD_IN clamp).

- The symbol draws **both cathode bars meeting at the center node wired to pin 2 (`COM`)** —
  a **common-cathode** device (that is **BAT54C** topology). Pin 3 is labeled `K2` but drawn
  as an anode.
- Real **BAT54S is a *series* dual**: **pin 1 = A1, pin 2 = K2, pin 3 = K1;A2** (the series
  junction is on **pin 3**), per Nexperia/Vishay/onsemi BAT54S datasheets and the committed
  Diodes Inc. DS11005.
- Both the topology *and* the common-node pin number are wrong; it also contradicts the
  part's own prose ("Dual series Schottky").
- **Fix (Lane B) — decide intent first:** either (a) the symbol should be the BAT54S series
  pinout (1=A1, 2=K2, 3=junction), or (b) the *part* should be BAT54C/BAT54A if a
  common-cathode/anode clamp is what the clamps actually need. The clamp circuit's intent
  (block-A, block-1, block-3) determines which. **Do not trust any BAT54S net until resolved.**

---

## MEDIUM severity

### 3. R_INV_IN / R_INV_FB missing `tol: 1%`
`specs/components.yaml:494–495`. The file header (line 14) lists the block-3 attenuverter
inverter resistors as **precision 1%-required** (10 kΩ, "center null depth >60 dB"), but
neither entry carries a `tol` field → both default to the file's "5% OK" rule. 19 destinations
× 2 = **38 parts**. With 5% resistors the attenuverter center-null degrades well below the
>60 dB spec. CI has no header↔entry tol cross-check. **Fix:** add `tol: "1%"` to both.
(Also: header name `R_inv_f` vs actual ref `R_INV_FB` — minor naming drift.)

### 4. Jack symbol ↔ footprint pad mismatch
`thonkiconn_pj398sm`: jack symbol pins `1/2/3` vs footprint pads `S/T/TN` — zero overlap
(affects all 30 jacks J1–J30). Pre-existing and deliberately CI-warn-only
(`tools/generate_schematic.py:357` `footprint_pad_advisory()`; docstring names it "a known,
pre-existing divergence to reconcile in its own change"). **Real exposure:** at PCB netlist
time the three jack connections silently fail to map unless a pad alias is applied. Note the
panel-hardware agent flagged a sharper sub-case: the symbol's third terminal is named `SW`
while the pad is `TN` — if any binder maps by *name*, the tip-normalling terminal won't
connect even after the 1/2/3 issue is solved. **Fix:** reconcile symbol pin numbers/names to
the footprint pad names (S/T/TN), or add an explicit pad-alias map.

### 5. slide_pot_45mm — unsourced + supplier/travel contradiction
`components/parts/slide_pot_45mm/`. `mpn: '~'`, manufacturer hedged "Alpha/Alps", and the
`datasheet.url` points at **Thonk's 20mm slider page** while the part (and the footprint's
~51 mm pad span) claim **45mm**. Thonk stocks RA2045F = **20mm** travel; true 45mm Alpha is
RA4522F (via Rapid), or an Alps part. The part's own note already admits the conflict.
**Fix:** pin the real MPN + supplier (decide 20mm-to-match-Thonk vs 45mm-from-Rapid/Alps)
before any BOM/netlist use.

### 6. bzx84c10 — no datasheet provenance
`components/parts/bzx84c10/`. The shared-datasheet claim is **verified TRUE** (C10 = marking
"Z9" in the committed `BZX84_SER.pdf`; series spans 2.4–75 V), but the part commits **no
`datasheet:` block at all** (no url/version/sha256/bytes) while its sibling `bzx84c5v1`
commits full provenance. A CI hash/provenance check has nothing to verify here. Minor: MPN
spelled `BZX84C10` vs Nexperia's canonical `BZX84-C10`; stray `panel_types: []`.
**Fix:** add a `datasheet:` block referencing the shared `BZX84_SER.pdf` with matching
sha256/bytes/version (or formally model a shared-datasheet reference).

---

## LOW severity / cosmetic

### 7. bourns_3296w stale version string
`version: rev 2019-08-07`, but the committed (sha-matching) PDF is **REV. 02/26**; the string
"2019-08-07" appears nowhere in the file. sha256/bytes/url all correct → metadata mislabel,
not a wrong file. **Fix:** `version: "REV. 02/26"`. (bourns_3224w `rev 2024` vs file
`REV. 07/24` — acceptable, could be tightened.)

### 8. opa1612 missing `symbol:` field
The only registered part without an explicit `symbol:` binding (affects 15 OPA1612
placements). The matching primitive `opamp2.yaml` (name `OPA1612`) exists and is already used
by `tl072`. **Fix:** add `symbol: opamp2`.

### 9. Weak datasheet fields where real PDFs exist
`alpha_rd901f`, `dailywell_dw3`, `dailywell_dw5`, `thonkiconn_pj398sm` settle for supplier
landing pages, but real manufacturer/Thonk-hosted PDFs exist (Alpha RD901F PDF, Dailywell 2M
PDF, `Thonkiconn_Jack_Datasheet.pdf`). **Only `led_3mm` is genuinely catalog-only** (commodity
generic, `mpn: ~`). **Fix:** upgrade the four to actual PDFs.

### 10. DW3 / DW5 placeholder MPNs
`mpn: DW3 (2M DPDT ON-ON)` / `DW5 (...ON-ON-ON)` are Thonk nicknames, not orderable Dailywell
2M-series ordering codes. Fine for prototyping; expand for procurement. (Their footprints/
symbols are byte-identical — **correct by design**: both share the same physical 2M DPDT body;
only contact logic differs. 6 lugs ↔ 6 symbol pins ✓. Only cost is two files to keep in sync.)

### 11. cd4053 doc-number drift + EOL
Symbol `cd4053.yaml` cites `pinout_datasheet: …(SCHS059)` while the sourced datasheet is
**SCHS047O** (both real TI docs, identical pinout). Also `CD4053BM` (MIL/SOIC-16 grade) is
TI "no longer in production" — pinout/package unaffected; consider `CD4053BNSR` for sourcing.

### 12. Orphan vendored footprints
6 `.kicad_mod` files referenced by nothing: `IDC-Header_2x08/2x12/2x17/2x20`,
`PinHeader_2x20`, `Potentiometer_Alps_RS4515N_Vertical_15mm`. The IDC/pin-header set is an
expected gap (no inter-board connector components defined yet; board layout under review); the
Alps RS4515N is a stale alternate to the bound 45mm slider. No functional impact.

### 13. Cosmetic
- `c.yaml` labels pin-1 `+` on a non-polarized `Device:C` (misleading if an electrolytic uses
  it; no connectivity impact).
- `expo.yaml` (THAT340) doesn't tag NPN (Q1/Q2) vs PNP (Q3/Q4) — `components.yaml` already
  correctly scopes expo cells to the NPN pair, so no error, but the symbol invites mis-reading.
- THAT340 per-pin C/B/E direction is corroborated from the datasheet figure topology (the
  PDF's inner labels are non-extractable graphics); a reviewer should eyeball Fig. 3 pre-tapeout.
- `1n4148w` `version: DS30086` is a doc number, not a dated revision (style inconsistency).
- zener symbol declares 2 pins (1=A, 3=K) vs 3-pad SOT-23 (pin 2 = NC, conventional).

---

## Recommended follow-up changes (each its own gated change; nothing applied here)

**Lane B (hardware-only, gates G4–G6 + `--check`):**
1. **that2180** — real MPN `THAT2180CL08-U`, `package: SIP-8`, vendor SIP-8 footprint, fix
   U4/U5 + CLAUDE.md. *(Highest priority; board-breaking.)*
2. **bat54s** — reconcile symbol topology vs the clamp circuits' actual intent (series vs
   common-cathode); fix symbol or part choice. *(Board-breaking; needs an intent decision.)*
3. **slide_pot_45mm** — resolve MPN + supplier + travel.
4. **jack** — reconcile symbol pins/names ↔ footprint pads (S/T/TN, incl. SW↔TN).

**Lane C (trivial, metadata/registry):**
5. Add `tol: "1%"` to `R_INV_IN` / `R_INV_FB` (functional-but-data-only). *(Borderline — if a
   net's BOM tol is considered behavioral, treat as Lane B.)*
6. Add `datasheet:` block to bzx84c10 (+ canonical `BZX84-C10` spelling).
7. Add `symbol: opamp2` to opa1612.
8. Fix bourns_3296w `version` to `REV. 02/26`; tighten 3224w to `REV. 07/24`.
9. Upgrade alpha_rd901f / dw3 / dw5 / jack datasheets to real PDFs; expand DW3/DW5 MPNs.
10. Align cd4053 symbol doc number to SCHS047O; note CD4053BM EOL.
11. Remove or document the 6 orphan footprints; fix `c.yaml` "+" label; tag NPN/PNP in expo.yaml.

> Per CLAUDE.md, fixes that touch symbols/footprints/`components.yaml`/nets are **Lane B**
> (plugin already LOCKED for these blocks); pure metadata/version-string fixes are **Lane C**.
> The plugin is ground truth and is **unaffected** by every finding here — these are all
> spec/registry/schematic-layer errors.
