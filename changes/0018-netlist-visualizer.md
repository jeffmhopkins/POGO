# Change 0018: Netlist Visualizer (interactive built artifact)

- **Slug:** netlist-visualizer    **Branch:** `change/netlist-visualizer` (fresh off `dev`)
- **Lane:** C (tooling / docs — reads nets, changes no connectivity)
- **Status:** BUILT (awaiting your in-browser review of `docs/netlist.html`)
- **Blocks:** none (read-only over all blocks)   **Boards:** audio, utility
- **Opened:** 2026-05-30       **Closed:** —
- **PR:** —              **CI run:** —

> Lane C rationale: adds a generator (`tools/build_netlist_viz.py`) + a generated artifact
> (`docs/netlist.html`) wired into CI. It **reads** `specs/<block>/<block>.nets.yaml`, the
> `components/parts/*/component.yaml` registry, `components/symbols/*.yaml`, and
> `components/footprints/`. It changes **no** DSP, no `panel-data.yaml` geometry, no
> `components.yaml`, and **no net connectivity**. Precedent: 0003/0005/0006/0007/0008 are all
> Lane C tooling/docs changes. **This stays Lane C only if it adds no field to the nets schema**
> (it doesn't — see "Reads, does not author" below).

---

## ⚠️ Branch provenance note (must read)

The originally-designated branch `claude/netlist-visualizer-concept-esofB` was pre-seeded at a
**stale commit ~63 commits behind `origin/dev`** (merge-base `5bd60c8`, an 0004-era tree). On
that stale tree nets lived in `kicad/nets/`, symbols were inline Python in `kicad/kicad_common.py`,
and there was no `components/symbols/` or `tools/footprint_svg.py`. Rather than force-push that
branch, this work uses a **fresh `change/netlist-visualizer` branch off current `origin/dev`**
(the stale branch is left untouched). The first adversarial review ran against the *stale* tree,
so its path-level findings (no `footprint_svg.py`, no `components/symbols/`, "11 blocks incl.
shared-q") were stale-tree artifacts and are **not** carried into this plan. The one
*substantive* finding — footprint coverage — was re-verified against `dev` and **is real**
(see R1).

## Intent  (G1)

A dynamic, in-browser **netlist visualizer**: components drawn as their real
footprints (where one exists) or schematic-symbol glyphs (passives), with lines running
pad-to-pad along shared nets, auto-placed by a force/spring layout that pulls co-net pads
together (short common-node lengths) while repelling overlaps. Dragging a component re-anneals
the neighbourhood. Shipped as a self-contained `docs/netlist.html` built artifact, generated in
CI alongside the BOM/panel/schematic outputs.

It is a **comprehension/sanity tool** — "does this netlist hang together the way the spec
says?" — not a PCB layout tool and not an authoritative artifact (the `.kicad_sch` /
`pogo-bom.csv` remain truth). Think ratsnest-meets-graph-view with block structure the
schematics don't show.

## Confirmed design decisions

| Decision | Choice | Status / implication |
|---|---|---|
| Footprint scale | **True physical mm** | Applies to the **272 footprinted parts**. The **608 passives have no footprint** (see R1) → they render as symbol glyphs at a nominal size. |
| Passive rendering | **Symbol glyph (A)** | 608 passives drawn as their schematic symbol (`r.yaml` rect / `c.yaml` cap glyph) at uniform nominal size; footprinted parts true-mm. No new components → **Lane C**. |
| Layout persistence | **Ephemeral auto-layout** | Force sim runs fresh each load, seeded. Drag re-anneals; nothing saved. Artifact purely derived → reproducible. |
| Wire endpoints | **True pads/pins when mappable** | Net pin token (`U49.11`, `D12.A`) maps to footprint pad / symbol pin by number/name equality; centroid fallback + `--check` warning on mismatch. |
| Default view | **All blocks collapsed**; power **hidden-as-flags** | Collapsed = labeled square exposing only authored `boundary:` ports. |

## Reads, does not author (Lane-C boundary)

- `specs/<block>/<block>.nets.yaml` — `parts{sym,part,value}`, `nets`, and the **authored
  `boundary:` list** (every block has one — use it directly; do **not** derive boundary from
  name collisions).
- `components/parts/<slug>/component.yaml` — `footprint:{lib,name}` + `symbol:` per sourced part
  (272 parts resolve here, e.g. cd4053 → `Package_SO/SOIC-16_3.9x9.9mm_P1.27mm`).
- `components/symbols/<token>.yaml` — drawable glyph graphics + numbered/named **pins** (incl.
  passives `r`/`c`, diode `A/K`, ICs numeric). Globbed by `tools/symbols.py`.
- `components/footprints/<lib>.pretty/<name>.kicad_mod` — pad geometry via
  `tools/footprint_svg.py::parse_footprint` (returns pad `num/x/y/rot/size` + body shapes).
- Authors nothing in those trees; emits only `docs/netlist.html` + a `--check`.

## Footprint coverage reality (verified on dev)

- **880 parts total.** **272 have a `part:` binding** → real footprint via the parts registry
  (ICs: `Package_SO`; THAT2180: `Package_SIP`; SOT/diode: `Package_TO_SOT_SMD`/`Diode_SMD`;
  panel parts: jacks/pots/switches/LED/IDC). **608 (69%) are passive R/C with no footprint**
  in the library (no 0603/R/C `.kicad_mod` exists).
- Passives **do** have schematic-symbol glyphs (`r.yaml` rectangle, `c.yaml` polyline) with
  pins `1`/`2` → renderable + wire-mappable without a footprint.

### Passive-rendering options (the open decision)
- **(A) Symbol glyph** — draw the 608 passives as their schematic symbol (rect/cap glyph) at a
  uniform nominal size; footprinted parts at true mm. Honest, no new components, **Lane C**.
  *Recommended.*
- **(B) Uniform value-box** — passives as small labeled boxes (`4k7`, `47nF`). Simplest, least
  "real," Lane C.
- **(C) Vendor a 0603 footprint** + add `part:`/footprint to all passives → every part true-mm
  real footprint. Most faithful, but edits nets + `components/` ⇒ **Lane B**, large diff, G6.

## Feature set (the interactive surface)

1. **Block on/off** — per-block visibility checkbox (10 blocks, grouped by board: audio×8,
   utility×2). Hiding a block drops its parts; a net still touching ≥2 visible pins remains;
   boundary nets to a hidden block degrade to edge stubs.
2. **Collapse / expand per block** — collapsed = a labeled square sized to part-count, exposing
   only its authored `boundary:` nets as perimeter ports. Default = all collapsed.
3. **Hide-power checkbox** — when on (default), `+12V`/`-12V`/`GND` stop being springs; each
   connected pin gets a local **power-flag** glyph (KiCad-style) so power can't blob the layout.
4. **Multi-select → grouping rectangle** — marquee/shift-select blocks; draw a bounding rect
   and render only the **boundary signals between the selected blocks** (internal nets dimmed).
   The "system interconnect" view.
5. **Real footprints / symbol glyphs** — 272 footprints at true mm; 608 passives per the chosen
   passive-rendering option; wires terminate at true pad/pin when mappable.
6. **Drag + re-anneal** — drag a part or collapsed block; release reheats the local sim.
7. **Hover/inspect** — hover pin → highlight whole net; hover part → ref/value/part/block
   tooltip; click net in side list → highlight.
8. **Readout** — total ratsnest length (HPWL proxy), net/part/crossing counts.

## Architecture / plan

**Extractor (Python, build time)**
- Load all 10 nets files; classify nets: power = `{+12V,-12V,GND}`; boundary = membership in a
  block's authored `boundary:` list; else internal signal.
- Resolve each part: footprinted (parts registry → `.kicad_mod` pad geometry via
  `footprint_svg.parse_footprint`) or passive (symbol glyph from `components/symbols/`). Cache
  one geometry blob per distinct footprint/symbol.
- Map each net endpoint `Ref.pin` → pad/pin by number/name equality; centroid fallback +
  `--check` warning when a symbol's pin set ≠ its footprint's pad-name set.
- Emit compact embedded JSON: `parts[]`, `geom{}` (by footprint/symbol id), `nets[]`
  (name, kind, endpoints[{ref, pin|centroid}]), `blocks[]` (board, boundary names).

**Layout engine (JS, runtime)**
- Hypergraph → **star model**: one invisible net-node per visible non-power net; each endpoint
  springs to it (net-node = label anchor + ratsnest hub; avoids N² clique on fat nets).
- Forces: spring (pin→net-node), many-body repulsion, **collision sized to each part's bbox**
  (footprint bbox for the 272; nominal for passives), block-clustering, mild centering. Seeded
  RNG → deterministic first frame.
- Power hidden-as-flags by default → those nets add no springs; each pin shows a local flag.
- Collapsed block = one super-node; boundary pins anchored on its square's perimeter.

**Render**: Canvas for parts/wires (scales to ~880 parts / block-6=418), SVG/HTML overlay for
labels, controls, selection rect. **CI is pure Python** (yaml + inkscape; no node/d3) and the
artifact is self-contained, so it fits the existing gate stack; no JS build step.

## Implementation milestones

1. Extractor + schema + `--check` (net classification, footprint/symbol resolution, pin map,
   coverage report). Unit-test boundary/power classification.
2. Static render — footprints true-mm + passive glyphs + pad-to-pad ratsnest on a trivial grid.
3. Force layout + power flags + collision-by-bbox. Tune.
4. Interaction — block on/off, collapse/expand, drag re-anneal, hover, readout.
5. Multi-select grouping rectangle (inter-block boundary view).
6. CI wire-up (`--check` in all 3 jobs; stage `docs/netlist.html` into `/tmp/hw`) + index card.

## Risks / open issues (revised against dev)

- **R1 Footprint coverage (REAL, critical-for-premise)** — 69% of parts (608 passives) have no
  footprint; resolved via passive-rendering option A/B (Lane C) or C (Lane B). Blocks the
  "every part as a real footprint at true mm" reading; needs the open decision closed.
- **R2 Pin↔pad equality** — works because net pin token == pad/symbol pin number/name (verified:
  diode `A/K`, ICs numeric). Not guaranteed for every symbol↔footprint pairing → verify + warn.
- **R3 Scale/perf** — ~880 parts / ~590 nets, block-6=418. Canvas + star-model + collapsed
  default should cope; block-6 expanded is the stress case.
- **R4 True-mm disparity** — IDC 2×20 header vs a passive glyph is a large span; collision by
  bbox + zoom mitigate; readability at full-system zoom is a concern.
- **R5 Parser coverage** — every footprinted part must parse; any unsupported pad shape →
  fallback box + `--check` warning (surface coverage holes, don't silently drop).
- **R6 Rails** — confirmed `{+12V,-12V,GND}` are the only globals; hardcode the hide-power set.

## Gate checklist (Lane C)

- [x] Fresh `change/netlist-visualizer` branch off `dev` (stale branch left untouched)
- [x] Passive-rendering decision closed → symbol glyph (A), Lane C
- [x] You approve the revised plan (2026-05-30) — incl. docs index card requirement
- [x] `--check` modes green locally (components / build_components / generate_schematic /
      build_panel / build_netlist_viz all OK)
- [ ] CI green (existing 5 `--check` gates + plugin build + new viz `--check`)
- [ ] You review `docs/netlist.html` in a browser

## Build result (2026-05-30)

`tools/build_netlist_viz.py` → `docs/netlist.html` (264 KB, self-contained, no deps).
Extraction: **880 parts** (272 real footprints / 608 symbol glyphs), **591 nets**, 10 blocks,
13 distinct geoms. **82 advisory pin-fallback warnings — all jacks** (footprint pads named
`T/S/TN` vs the netlist's symbol-pin numbers `1/2/3`; wires attach at the jack body centroid).
ICs/diodes/trimpots all map pad-exact. CI: `--check` added to all 3 build jobs; `docs/netlist.html`
regenerated on Linux and staged into the hardware artifact bundle. Docs index card added.

## Decisions log

- 2026-05-30: Footprint scale = true physical mm (for footprinted parts).
- 2026-05-30: Persistence = ephemeral auto-layout.
- 2026-05-30: Wire endpoints = true pads/pins by number/name equality, centroid fallback.
- 2026-05-30: Default view = all blocks collapsed; power hidden-as-flags.
- 2026-05-30: Lane = C (reads nets/registry/symbols/footprints; authors nothing there).
- 2026-05-30: **Fresh `change/netlist-visualizer` branch off `dev`** — designated `claude/...`
  branch was stale (~63 commits behind, pre-reorg); left untouched rather than force-pushed.
- 2026-05-30: Use the **authored `boundary:` field**, not derived name-collision (review finding).
- 2026-05-30: **Passive rendering = symbol glyph (A)** — 608 R/C as schematic glyphs; stays Lane C.

## Artifacts (paths / links)

- Generator: `tools/build_netlist_viz.py`
- Artifact:  `docs/netlist.html` (self-contained; staged into CI hw bundle)
- Reads: `specs/<block>/<block>.nets.yaml`, `components/parts/*/component.yaml`,
  `components/symbols/*.yaml`, `components/footprints/`
- Index card: `docs/index.html`
