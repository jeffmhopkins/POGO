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
A new KiCad generator will be written after the Phase 3R specs are complete and the
component registry (`specs/components.yaml`) is finalized.

> **Switch parts (48HP):** all toggle switches are now Thonk-sourced Dailywell 2M
> sub-mini toggles — `SW_Dailywell_DW3_DPDT` (2-position ON-ON: GAIN_MAIN, GAIN_BP3,
> BP_POL) and `SW_Dailywell_DW5_DPDT` (3-position ON-ON-ON: BP1/2/3_DIST_MODE,
> MOD_SRC), in `kicad/footprints/Button_Switch_THT.pretty/`. The 40HP generators
> below still emit generic `SW_SPDT`/`SW_SP3T` symbols and must NOT be used; the
> Phase 3R generator will assign the Dailywell footprints.

## Archive

The generated 40HP-era schematics live in `specs/archive/40hp-era-2026-05/`. They are
retained for reference only and must not be used as a basis for the 48HP build.

**Last valid use: 40HP prototype (pre-2026-05-27)**
