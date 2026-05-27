# Archive: 40HP Era Specs (2026-05)

These specs were written during the 40HP module design phase and are superseded by the
48HP topology redesign completed 2026-05.

## What changed

| Block | Old (40HP) | New (48HP) |
|---|---|---|
| Block 2 | Envelope Follower | **Replaced by dual LFO** |
| Block 3 | Triple Bandpass APCF | **Replaced by Triple Bandpass SVF** |
| Module width | 40HP (203.2mm) | **48HP (243.84mm)** |
| Signal order | LP1 → LP2 → HP | **LP1 → BP → HP → LP2** |
| Panel design | Hand-edited SVG | **tools/panel-data.yaml (data-driven)** |
| Board layout | 3-board split | **Under architectural review for 48HP** |

## Contents

| File | Was |
|---|---|
| `block-2-envelope-follower/spec.md` | specs/block-2-envelope-follower/spec.md |
| `block-3-apcf/spec.md` | specs/block-3-apcf/spec.md |
| `module-overview.md` | specs/module-overview.md |
| `panel-notes.md` | specs/panel-design/panel-notes.md |
| `panel.svg` | specs/panel-design/panel.svg |
| `layout-notes.md` | specs/board-layout/layout-notes.md |

## Active specs (not archived)

Blocks unchanged from 40HP era: `block-A`, `block-1`, `block-4`, `block-B`,
`shared/`, `kicad-process.md`.

Blocks updated in-place: `block-VCA`, `block-5-lp1`, `block-6-lp2`, `block-7-hp`,
`mod-architecture.md`.

Net-new: `block-LFO/`, `block-3-triple-bp/`.
