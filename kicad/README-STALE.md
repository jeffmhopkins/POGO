# KiCad Generators — 40HP Era (STALE — Do Not Regenerate)

> **Status: 40HP-era, superseded by 48HP topology. Do not run these generators.**

These Python scripts (`generate_control_board.py`, `generate_utility_board.py`) and validators
(`validate_schematic.py`, `validate_utility_board.py`) were written for the 40HP revision of POGO.

## What They Contain (40HP topology)

- Envelope follower as primary mod source (replaced by LFO1 in 48HP)
- APCF / COMB filter blocks (removed in 48HP)
- FB_DIST_BLEND feedback routing (removed in 48HP)
- 40HP panel dimensions and reference designators
- Old block numbering: block-5-lp1, block-7-hp, block-6-lp2 (superseded by block-5, block-7, block-8)

## What Replaced Them

The 48HP hardware design lives in `specs/` (see `specs/STATUS.md`).

### 48HP schematic generator (data-driven) — `generate_schematic.py`

The new generator is **data-driven** and replaces the hand-encoded per-net Python
in the stale board generators:

- Connectivity lives in `kicad/nets/<block>.nets.yaml` (net name → list of
  `REF.PIN`), transcribed from the block + aux specs. Name-based: pins on the
  same net get matching global labels.
- `generate_schematic.py` resolves each part's symbol/pin geometry from
  `kicad_common.py` and its footprint/MPN from the `components/` registry
  (`tools/components.py`), then emits `kicad/pogo-<block>.kicad_sch`.
- Output is **byte-stable** (deterministic UUIDs); a pin-coverage validator
  asserts every pin of every part is wired or explicitly `no_connect`.
- A **structural verifier** re-parses the emitted `.kicad_sch` as an s-expression
  (independently of the generator), re-derives every pin's connection point from
  the `lib_symbols` geometry, and confirms each global label lands exactly on a
  pin and each pin is labeled or an intended no-connect. This is the
  "would it connect in KiCad?" check, done without KiCad — it catches malformed
  s-expr, dangling `lib_id`s, and any drift between `sym_*()` geometry and the
  `*_pins()` helpers.
- CI gate: `python3 kicad/generate_schematic.py --check` (validate + structural
  verify + byte-drift).

First vertical slice: **block-A** (input buffers — OPA1612 followers, BAT54S
clamps, 100Ω series, R→L normalling). Add a block by adding a `*.nets.yaml`.
All block-A parts have vendored footprints (BAT54S → `Package_TO_SOT_SMD:SOT-23`).

> **Switch parts (48HP):** all toggle switches are now Thonk-sourced Dailywell 2M
> sub-mini toggles — `SW_Dailywell_DW3_DPDT` (2-position ON-ON: GAIN_MAIN, GAIN_BP3)
> and `SW_Dailywell_DW5_DPDT` (3-position ON-ON-ON: BP1/2/3_DIST_MODE; MOD_SRC is
> planned/unimplemented), in `kicad/footprints/Button_Switch_THT.pretty/`. The 40HP generators
> below still emit generic `SW_SPDT`/`SW_SP3T` symbols and must NOT be used; the
> Phase 3R generator will assign the Dailywell footprints.

## Archive

The generated 40HP-era schematics live in `specs/archive/40hp-era-2026-05/`. They are
retained for reference only and must not be used as a basis for the 48HP build.

**Last valid use: 40HP prototype (pre-2026-05-27)**
