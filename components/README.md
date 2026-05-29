# `components/` — POGO component registry

Canonical home for sourced parts. Tools resolve footprints and part metadata
through `tools/components.py` instead of hardcoding paths.

## Layout

```
components/
  footprints.yaml          panel component-type -> KiCad footprint + panel anchor (ox,oy).
                           Source of truth for tools/panel_kicad._FOOTPRINT_MAP.
                           ORDER IS SIGNIFICANT (feeds the git-tracked editor payload).
  parts/<slug>/
    component.yaml         one sourced part: mpn, manufacturer, supplier, package,
                           matches[] (the components.yaml `part:` strings this part
                           covers, for BOM enrichment), footprint{lib,name},
                           datasheet{url,version,sha256,bytes}, panel_types,
                           tapers (pots), notes. Hand-maintained except datasheet
                           sha256/bytes (written by fetch_datasheets.py).
    datasheet.pdf          the part's datasheet, committed alongside (PDF parts only;
                           supplier-page parts have no PDF). Fetched by fetch_datasheets.py.
```

Footprints themselves live in `components/footprints/*.pretty/` (KiCad-native libraries);
`component.yaml` and `footprints.yaml` *reference* them by `{lib, name}`.

## Tools

```
python3 tools/components.py --check        validate registry (CI gate)
python3 tools/components.py --list         list footprint bindings + parts
python3 tools/build_components.py --gen-fplib   generate kicad/fp-lib-table (POGO_* namespaced)
python3 tools/build_components.py --gen-bom     generate kicad/pogo-bom.csv (manufacturing BOM)
python3 tools/build_components.py --all          regenerate both
python3 tools/build_components.py --check        CI drift gate (both up to date)
python3 tools/fetch_datasheets.py          download PDF datasheets -> components/parts/<slug>/datasheet.pdf (committed) + record sha256/bytes
python3 tools/fetch_datasheets.py --check  offline: every PDF datasheet has sha256/bytes (CI gate)
```

Datasheet PDFs are committed per-part as `components/parts/<slug>/datasheet.pdf`; their
`sha256`+`bytes` are recorded in each `component.yaml` for integrity (`--check` verifies
the committed PDF matches). Supplier/landing-page datasheets (panel hardware) have no PDF.

`kicad/fp-lib-table` and `kicad/pogo-bom.csv` are **generated** (CI fails if stale).
The BOM is a derived view of the authoritative, hand-maintained `specs/components.yaml`,
enriched from this registry via each part's `matches[]`; rerun `--gen-bom` after editing
`components.yaml` or a part record. Rerun `--gen-fplib` after adding a `*.pretty` library.

## Scope (Phase 1)

This is the de-risked first slice (see the adversarially-reviewed plan):

- Sourced parts have folders; footprints resolve dynamically; KiCad gets a valid
  `fp-lib-table`. Zero panel-geometry change — `panel_kicad`, DRC, and the editor
  payload are byte-identical to before.
- `specs/components.yaml` remains the **hand-maintained** BOM source; the loader is the
  programmatic read API and `kicad/pogo-bom.csv` is a generated, registry-enriched view.

## Deferred (until a real consumer exists — the 48HP KiCad schematic/netlist generator)

- Passives as first-class parts (need vendored `R_0603`/`C_0603` footprints).
- *Regenerating* `specs/components.yaml` and the per-block spec BOM tables from the
  registry (block-6 uses descriptive refs + has unresolved `D_WF`/`R_sum` count
  ambiguities to reconcile first). The flat manufacturing BOM (`pogo-bom.csv`) is done.
- KiCad schematic symbols / `sym-lib-table` + wired schematics (the netlist isn't
  machine-readable; gated on the 48HP schematic-gen rewrite).
