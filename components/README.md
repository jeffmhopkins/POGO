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
                           footprint{lib,name}, datasheet{url,version}, panel_types,
                           tapers (pots), notes. Hand-maintained.
```

Footprints themselves stay in `kicad/footprints/*.pretty/` (KiCad-native libraries);
`component.yaml` and `footprints.yaml` *reference* them by `{lib, name}`.

## Tools

```
python3 tools/components.py --check        validate registry (CI gate)
python3 tools/components.py --list         list footprint bindings + parts
python3 tools/build_components.py --gen-fplib   generate kicad/fp-lib-table (POGO_* namespaced)
```

`kicad/fp-lib-table` is **generated** (`DO NOT EDIT`); rerun `--gen-fplib` after adding a
`*.pretty` library.

## Scope (Phase 1)

This is the de-risked first slice (see the adversarially-reviewed plan):

- Sourced parts have folders; footprints resolve dynamically; KiCad gets a valid
  `fp-lib-table`. Zero panel-geometry change — `panel_kicad`, DRC, and the editor
  payload are byte-identical to before.
- `specs/components.yaml` remains the **hand-maintained** BOM; this loader is the
  programmatic read API (not a generator) for now.

## Deferred (until a real consumer exists — the 48HP KiCad netlist generator)

- Passives as first-class parts (need vendored `R_0603`/`C_0603` footprints).
- Generating `specs/components.yaml` and per-block BOM tables from the registry
  (block-6 uses descriptive refs + has a real `qty 6 vs 12` conflict to reconcile first).
- Datasheet PDF fetch/cache script (today: `datasheet.url` + `version` text only;
  several URLs are marked `version: verify` and should be confirmed before manufacture).
- KiCad schematic symbols / `sym-lib-table` (gated on the 48HP schematic-gen rewrite).
