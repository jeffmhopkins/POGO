# POGO Component Verification Report

> **Re-performed 2026-05-30 (change 0018)** by analysis + adversarial agents against the current
> `specs/components.yaml`, the `components/` registry, and the generated BOM. Supersedes the
> original `0015-component-audit` snapshot (which reported "476 refs" — now 718).

---

## 1. Counts

- **Component rows in `specs/components.yaml`: 718** (was 476 at change 0015; +242 from the 0018
  additions — ALT-BP VCA cell, per-band DRIVE VCAs, block-6 7-way split, BP3 selector, CLIP/LED).
- **Generated BOM (`kicad/pogo-bom.csv`): 718 rows**, 1:1 with components.yaml.
- **Per-board distribution:** audio 583 · control 54 · utility 46 · panel 35.

## 2. Reference uniqueness

- **No true cross-board collision.** Refs are unique per board (the invariant). The 35 audio-board
  refs that appear more than once are all **block-6 split-section repeats** — the same ref declared
  identically across `block-6-svf1/2/3` (or `-dist1/2/3`), one per identical bandpass group (the
  deliberate per-group scheme). A ref like `RV9`/`RV12`/`RV15`/`RV21` also appears on the *control*
  board (block-3 attenuverter pots) — a different board, so no global clash.
- All six component-side `--check` gates pass, confirming the generator's uniqueness rule accepts
  section-scoped refs.

## 3. Registry / footprints / datasheets

- **21 sourced parts** in `components/parts/*` — every one declares symbol + footprint + mpn +
  datasheet; all 9 footprint bindings (across 4 unique libraries) resolve to vendored `.pretty` dirs; all
  `matches[]` tokens cover every non-null `part:` in components.yaml. No missing registry entry,
  footprint, or datasheet.
- **MMBT3904** (the newest part, block-2 LED driver) is fully registered: symbol `npn`, footprint
  SOT-23, mpn, datasheet. Its datasheet is a product-page URL (no cached PDF/sha256) — allowed by
  `fetch_datasheets.py --check`, but less pinned than the sha256-locked ICs.

## 4. Check-gate results

| Gate | Result | Validates |
|---|---|---|
| `components.py --check` | PASS | panel-type→footprint bindings + registry structure (9 bindings, 21 parts) |
| `build_components.py --check` | PASS | fp-lib-table + BOM + footprint SVGs + manifest up to date |
| `fetch_datasheets.py --check` | PASS | datasheet-PDF integrity (sha256/bytes where a PDF is cached) |
| `generate_schematic.py --check` | PASS | symbol self-test + per-block pin coverage + structural + byte-drift |
| `build_panel.py --check` | PASS | panel DRC |
| `build_netlist_viz.py --check` | PASS | docs/netlist.html byte-drift |

## 5. Fixes applied this change

- **RV9 / RV12 / RV15 / RV21** (BP1/2/3 + LP2 Q_max trims) were `part: ~` with no value — now
  assigned `Bourns 3224W, 100kΩ` to match the analogous RV5 (LP1) and RV18 (HP). This closes the
  last open G6 part-assignment gap on the audio board.

## 6. Carry-forward findings (no code change here)

- **CD4053B is EOL** (7 units) — plan a CD4053BNSR/equivalent substitution (pinout unchanged).
- **THAT2180** is single-source + THT-only at **10 units** (the dominant sourcing/assembly concern);
  **THAT340S14-U** is single-source at 10 units (SMD). See `analog-design-review.md` §4.
