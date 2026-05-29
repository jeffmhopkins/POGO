# Change NNNN: <Title>

- **Slug:** <slug>          **Branch:** `change/<slug>`
- **Lane:** A (behavioral) | B (hardware-only) | C (trivial)
- **Status:** OPEN | PLUGIN-LOCKED | SPEC-DONE | SCHEMATIC-DONE | CLOSED | ABANDONED
- **Blocks:** block-N[, ...]   **Boards:** audio | utility | control | panel
- **Opened:** YYYY-MM-DD       **Closed:** YYYY-MM-DD
- **PR:** <link>              **CI run:** <Actions link>

> Lanes & gates are defined in `CLAUDE.md` → "Git Workflow & Change Process".
> Lane A runs Steps 0–8 / G1–G6. Lane B enters at Step 5 (G4–G6 + `--check`).
> Lane C uses the minimal one-liner form (see the example at the bottom of this file).
> Every change gets a file, committed as the first commit on the branch, before the PR.
> PR title: `NNNN-slug: summary`.

## Intent  (G1)

What the change is for. For Lane A: the user-stated **audio/UX intent**, then the
assistant's restatement (G1 confirms the restatement is correct).

## Scope / Out of scope

What this change does and explicitly does not touch.

## Gate checklist

- [ ] G1 intent restatement confirmed (you)        — Lane A
- [ ] G2 panel layout approved (you)               — Lane A; panel only
- [ ] G3 behavior verified in VCV Rack (you)       — Lane A; DSP correctness
- [ ] G4 spec §1 + functional approved (you)       — Lane A/B
- [ ] G5 topology approved (you)                   — Lane A/B
- [ ] G6a each new component approved (you)        — Lane A/B
- [ ] G6b footprint exists (resolved / vendored)   — Lane A/B
- [ ] CI green (5 `--check` gates + plugin build)

## Decisions log

- YYYY-MM-DD: <decision> — <rationale>

## Component additions

| ref | board | block | part | pkg | val | datasheet? | fn |
|-----|-------|-------|------|-----|-----|-----------|----|
| —   | —     | —     | —    | —   | —   | —         | none |

## Lock record  (Step 4)

`Plugin LOCKED @ <blob-hashes>`  (plugin/src/** DSP + tools/panel-data.yaml frozen)
<!-- blob hash per file: `git hash-object <path>` — survives squash-merge -->

## Artifacts  (paths / links, not copies)

- Plugin:    CI run <link> (`.vcvplugin`; artifacts expire ~30 days)
- Panel:     `plugin/res/Pogo.svg`, `design/panel-debug.html`
- Schematic: `kicad/pogo-<block>.kicad_sch` (+ `kicad/nets/<block>.nets.yaml`)
- BOM:       `kicad/pogo-bom.csv`
- Specs:     `specs/block-N/spec.md`
- STATUS.md row updated: yes / no

## Notes / Phase-3R flags

---

<!--
Minimal Lane C example (the floor):

# Change 0007: fix CD4053 symbol comment typo
- Lane: C   Status: CLOSED   Blocks: block-6
Intent: doc-only typo fix in a kicad_common comment. No gates. CI --check green. PR #NN.
-->
