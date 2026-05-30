# Change 0017: distortion before bandpass + MOD SRC switch

- **Slug:** dist-before-bandpass          **Branch:** `change/dist-before-bandpass`
- **Lane:** A (behavioral)
- **Status:** OPEN
- **Blocks:** block-6 (triple BP + distortion), block-2/block-3 (mod source)   **Boards:** audio, control, panel
- **Opened:** 2026-05-30       **Closed:** —
- **PR:** —              **CI run:** —

> Lanes & gates are defined in `CLAUDE.md` → "Git Workflow & Change Process".

## Intent  (G1)

User: "Rewrite the plugin to match the current panel. Add a topological change:
distortion goes BEFORE the bandpass filters, not after."

Restatement (confirmed via clarifying Q&A 2026-05-30):

1. **Distortion → before bandpass, per-band.** Within each of the 3 bands the order
   flips from `BPn → DISTn` to `DISTn → BPn`; the 3 band outputs are then summed/mixed
   as before. Each band keeps its own 3-way DIST mode (soft/hard/wavefold), DIST amount
   knob, DIST CV + attenuverter, and CLIP LED. The CLIP LED now monitors the distortion
   stage output (which is now pre-filter).
2. **DIST mode switches stay 3-way.** (Panel `toggle_dw5` = Dailywell DW5 = 3-position;
   plugin already has exactly 3 modes. No panel-type or mode-count change — the earlier
   "5-position" reading was a mislabel.)
3. **MOD SRC → implemented as a 3-way switch: LFO1 / LFO2 / EXT.** New `MOD_SRC_PARAM`
   (pos 0 = LFO1, 1 = LFO2, 2 = EXT = MOD_IN jack only, 0 V if unpatched). Replaces the
   old "MOD_IN if patched, else LFO1" auto-normal. Panel `MOD_SRC_SW` (already drawn,
   `toggle_dw5`) gains its `cpp_param` binding.
4. **BP3 L/R OUT = post-BP3 band, pre-mix** (the distorted-then-bandpassed BP3 voice,
   before it is summed into the main wet bus).

## Scope / Out of scope

- **In:** `plugin/src/dsp/BandpassSVF.hpp` (per-band input API), `plugin/src/dsp/Distortion.hpp`
  (unchanged math; new call site), `plugin/src/Pogo.cpp` (chain reorder, MOD_SRC param +
  widget + wiring), `tools/panel-data.yaml` (MOD_SRC cpp_param binding), regenerated panel.
- **Out:** No new components/jacks/lights. No change to filter math, LFO, VCA, HP/LP2, or
  the BP control bus. Dist-mode count stays 3. No 5-position anything.

## Gate checklist

- [x] G1 intent restatement confirmed (clarifying Q&A)
- [ ] G2 panel layout approved (you)            — MOD_SRC cpp_param binding only; no geometry change
- [ ] G3 behavior verified in VCV Rack (you)
- [ ] G4 spec §1 + functional approved (you)
- [ ] G5 topology approved (you)
- [ ] G6a/b — none (no new components)
- [ ] CI green (5 `--check` gates + plugin build)

## Decisions log

- 2026-05-30: Distortion placed per-band (x→DISTn→BPn), not a single shared stage — keeps
  the 3 panel DIST controls 1:1. (user)
- 2026-05-30: MOD SRC positions = LFO1 / LFO2 / EXT; EXT = MOD_IN jack only (0 V if
  unpatched); jack does nothing in LFO positions. (user)
- 2026-05-30: BP3 OUT taps post-BP3 band (pre-mix). (user)
- 2026-05-30: `toggle_dw5` is the 3-position DW5 part, not 5 positions — DIST stays 3-way,
  no panel type change. (investigation)
- 2026-05-30: `MOD_SRC_PARAM` placed in the Zone 0c enum group for readability; this shifts
  later param indices, so saved patches from prior versions won't map 1:1 (acceptable for a
  behavioral rewrite / prototype).

## Component additions

| ref | board | block | part | pkg | val | datasheet? | fn |
|-----|-------|-------|------|-----|-----|-----------|----|
| —   | —     | —     | —    | —   | —   | —         | none |

## Lock record  (Step 4)

`Plugin LOCKED @ <pending G3>`

## Artifacts  (paths / links, not copies)

- Plugin:    CI run <pending>
- Panel:     `plugin/res/Pogo.svg`, `docs/panel-debug.html`
- Specs:     `specs/block-6/spec.md` (and mod-source note in block-2/block-3)
- STATUS.md row updated: pending

## Notes / Phase-3R flags

- Moving distortion ahead of the bandpass changes the hardware signal order for block-6:
  the distortion cells now sit between LP1/ALT feed and the SVF inputs. Spec §2/§3 + netlist
  (Lane B follow-up) must reflect this; flagged for the hardware pass.
