# 0030 — aux library reorg: typed folders + reference sweep

- **Slug:** aux-library-reorg  **Branch:** `change/0030-aux-library-reorg`
- **Lane:** C (docs/structure — no DSP, no panel geometry, no components.yaml, no nets connectivity).
- **Status:** OPEN
- **Opened:** 2026-05-31
- **Blocks:** none (cross-cutting: `specs/aux/**` + reference sweep)   **Boards:** n/a

## Intent
Phase 1 of building a typed, sim-verified aux **circuit-design library** (user request). Move the 11
existing aux docs from a flat `specs/aux/aux-*.md` into a typed tree `specs/aux/<type>/<name>/spec.md`
(6 types: filter, vca, distortion, modulation, utility, led; `aux-` prefix dropped), add the
`_LIBRARY.md` index, and sweep every **live** reference to the new paths. No content/behavior change —
sims + reconciliation come in 0031, new extractions in 0032.

## What changed
- **Moved (git mv)** 11 aux → typed folders:
  filter/{ota-c-svf, expo-converter, q-control}; vca/{vca-cell}; distortion/{overview};
  modulation/{lfo-core, mod-bus-core, attenuverter}; utility/{unity-buffer, cv-protection, power-filter}.
- **Added** `specs/aux/_LIBRARY.md` (taxonomy, primitive→composed layering, sim convention, build-out
  status, how-to-add) and a `**Type:**` header linking each moved spec back to the index.
- **Reference sweep** over LIVE files only (block specs, nets.yaml comments, sim `.cir`/`.expect.yaml`
  `plugin_ref`s, CLAUDE.md repo-tree + aux template, README, STATUS.md) — old `aux-*` paths → new
  `aux/<type>/<name>/spec.md`. Fixed a stale alias (`aux-cv-input-protection` → `utility/cv-protection`).
- **Frozen `changes/` files were NOT edited** — they are historical records and keep their old `aux-*`
  references (describing the state at their time).

## Verification
- `grep -rE "aux-[a-z]"` over all live files (excl `changes/`) → **zero** stale references remain.
- All 7 `--check` gates green (the reorg is behavior-neutral; aux dirs have no nets.yaml so the
  schematic/netlist gates ignore them; build_spice finds no aux sims yet).

## Decisions log
- 2026-05-31: user chose 6-type taxonomy, full extraction (0032), blocking gate for aux sims, phased
  delivery. This change is Phase 1 (reorg only). Confirmed: drop `aux-` prefix; `distortion/overview/`
  for the moved aux-distortion.

## Gate checklist (Lane C)
- [x] Move + typed tree + `_LIBRARY.md` + Type headers
- [x] Live-reference sweep (zero stale `aux-` in live files)
- [x] All 7 `--check` gates green
- [ ] PR `change/0030-aux-library-reorg` → `dev`

## Next
- **0031:** author `sim/` decks for the 11 moved entries + reconcile each spec vs the current
  block/netlist/plugin.
- **0032:** author the NEW extracted entries (gm-c-integrator, voct-expo-divider, ref-injection-trim,
  soft-clip, hard-clip, wavefolder, inverting-summer, schmitt-trigger, output-buffer, clip-detector,
  led-breathing) + sims + "Composes:" cross-links.
