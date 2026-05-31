# aux: Analog Mux (Glitch-Free CMOS Parallel-Path Select)

**Type:** `utility` · part of the [aux circuit library](../../_LIBRARY.md)

> Authored 2026-05-31 (change 0032). The reusable "parallel-path select": a CD4053 CMOS analog mux
> steers one of several **always-running** parallel signal paths to the output without a switching
> transient. Extracted from block-6 (per-band distortion mode select + BP3 input select).

Design status: [x] draft → [ ] reviewed → [ ] validated on prototype

## Overview

The **analog mux** is the glitch-free path-select primitive: several signal paths run continuously and
in parallel, and a CMOS analog multiplexer (CD4053 — triple SPDT / 2:1) routes **exactly one** of them
to the output under logic control. Because all paths are always live, switching the select line does
not gate a path on/off (no pop/click) — it merely changes which already-settled signal the mux passes.

The CD4053 channel is a bilateral CMOS switch: when ON it is a small on-resistance (Ron ≈ 200 Ω at
±12 V) in series with the path; when OFF it is a high-impedance open. With the next stage at ≥10 kΩ
input impedance, the 200 Ω Ron contributes <2 % attenuation — negligible — so the selected path passes
at ~unity and the de-selected path does not reach the output.

POGO uses it in block-6:
- **Per-band distortion mode select** — each BP group's SOFT/HARD/FOLD distortion cells run in
  parallel; the CD4053 (one per band, driven by BP{n}_DIST_MODE) selects which reaches the SVF. This is
  the realization of the [source-selector](../../modulation/source-selector/spec.md) abstraction for an
  *audio-rate, logic-driven* select (vs the mechanical DPDT used for MOD_SRC).
- **BP3 input select** — a CD4053 (U81) picks per channel between the LP1 band and the ALT-VCA voice.

[distortion/overview](../../distortion/overview/spec.md) **composes** this primitive (its §CD4053
Configuration is the per-band instance of this 2:1 select).

## Schematic

ASCII (2:1 CMOS mux path-select, one channel; the CD4053 SPDT cell):

```
   PATH_0 ──○ N0 ─┐
                  ├─[ Ron ≈ 200Ω ]── OUT ──► next stage (≥10kΩ / high-Z)
   PATH_1 ──○ N1 ─┘
                  ▲
              S (select logic 0/1)  → S=0 passes PATH_0, S=1 passes PATH_1
                                      (de-selected input is an OPEN channel)

   CD4053 = THREE such 2:1 cells (X/Y/Z), each its own select pin (S_A/S_B/S_C),
   INH (pin 6) tied LOW = enabled. ±12 V rails pass ±5 V audio without Ron distortion.

   Per-band 1-of-3 (SOFT/HARD/FOLD) is built by CASCADING two cells:
     cell B picks HC↔WF into a MID node; cell A picks SC↔MID  → 1-of-3 out.
```

## Transfer Function

```
2:1 select (S ∈ {0,1}):
  OUT = PATH_S · Rload/(Rload + Ron)  ≈ PATH_S      (Ron ≪ Rload → ~unity)
  de-selected PATH (1−S): open channel → contributes 0

Ron drop:  with Ron = 200 Ω, Rload = 10 kΩ:  10000/(10000+200) = 0.980 → ~2 % (negligible)

1-of-3 (two cascaded cells, block-6 distortion):
  MID = (S_B==1) ? WF : HC
  OUT = (S_A==1) ? MID : SC     → exactly one of {SC, HC, WF}
```

This is a **path-steering / topology** law: identity (within Ron) on the selected path, zero on the
de-selected path. The precise Ron-vs-load attenuation is a block-level concern; the reusable fact is
the steering correctness.

### DSP / plugin law it realizes

```
plugin (Pogo.cpp:412-415, Distortion::process dispatch on mode) — per-band mode index selects one of
  three distortion laws; the analog CD4053 mirrors the mode switch (selected path passes, rest blocked).
plugin (block-6 BP3 input select, ALT_L_DET) — picks LP1 band vs ALT-VCA voice per channel; the U81
  CD4053 realizes the same 1-of-2 choice.
```

The plugin's per-sample `switch(mode)` / conditional selection IS the mux: one path's value is used,
the others are computed-but-discarded (analog: computed-but-not-routed). The mux reproduces that.

## Design Choices & Rationale

### Parallel paths + mux vs gating a single path
Switching a gain stage or path on/off produces a transient (charge injection, settling step) — an
audible pop. Running all paths continuously and selecting the output with a bilateral switch means the
selected signal is already settled, so the only switching artifact is the CD4053's <10 ns channel
break-before-make — inaudible. This is why the distortion bank pre-builds SC/HC/WF and muxes the output
rather than switching the active circuit.

### CD4053 (triple 2:1) and ±12 V rails
The CD4053 passes signals between its VSS and VDD rails; on ±12 V it passes ±5 V audio with no
signal-dependent Ron distortion. Three SPDT cells per package give a 1-of-2 per channel, or two cells
cascade to a 1-of-3 (the per-band distortion select); the third cell is spare or used for the stereo
partner. INHIBIT (pin 6) tied LOW keeps the mux enabled. Logic-high vs VDD = +12 V is marginal per the
datasheet (V_IH ≈ 0.7·VDD) — POGO drives the select lines from a +5 V logic rail and flags the level
margin for Phase-3R (block-6 spec note).

### Ron and the next stage
Keep the next stage input ≥10 kΩ so the 200 Ω Ron is <2 % — negligible. Do not feed the mux output
into a low-Z load, or the Ron divider attenuates the selected path measurably.

## Component Values (POGO-specific)

| Ref (generic) | Part | Package | Value | Notes |
|---|---|---|---|---|
| U_MUX | CD4053BM96 | SOIC-16 | — | Triple 2:1 CMOS analog mux; one per BP group (distortion select) + U81 (BP3 input select) |
| (select) S_A / S_B | logic | — | 0/5 V | From BP{n}_DIST_MODE switch via +5 V logic rail (2 lines → 1-of-3) |
| (next stage) R_load | — | — | ≥10 kΩ | High-Z so Ron ≈ 200 Ω drop is <2 % |
| C_VDD / C_VSS | Ceramic bypass | 0603 | 100 nF | Per supply pin |

## Performance Characteristics

| Parameter | Value | Condition |
|---|---|---|
| Selected-path gain | ~unity (−2 % max) | Ron 200 Ω into ≥10 kΩ |
| De-selected isolation | open channel (~0) | OFF channel high-Z |
| Ron | ~200 Ω | ±12 V supply |
| Switching transient | <10 ns, inaudible | Parallel always-on paths |
| Signal range | ±5 V | On ±12 V rails, no Ron distortion |

## Known Gotchas / Assembly Notes

- **Sim scope (honest):** the deck is a **path-steering topology check**, NOT a precision-Ron or
  distortion check. It models the selected channel as a series Ron (200 Ω) into a high-Z node and the
  de-selected channel as open, then confirms the SELECTED path passes ~unity and the DE-SELECTED path
  does not reach the output (a routing fact, generalized from `distortion/overview/sim/mux_select.cir`).
  It does NOT model charge injection, the <10 ns break-before-make, level-margin of the logic drive, or
  the exact Ron-vs-signal nonlinearity (those are datasheet/bring-up facts).
- Logic-high margin at VDD = +12 V is marginal (V_IH ≈ 0.7·VDD = 8.4 V vs a +5 V logic rail); POGO
  flags this for Phase-3R — drive selects from a level adequate to the chosen VDD or lower VDD.
- Keep the next stage ≥10 kΩ so Ron is negligible; a low-Z load turns Ron into an audible divider.
- INHIBIT (pin 6) must be tied LOW (enabled); floating it disables the mux.
- For a 1-of-3, cascade two cells (B picks HC↔WF, A picks SC↔MID) — see distortion/overview §CD4053.

## Used By

| Block | Instance | Board | Notes |
|---|---|---|---|
| block-6 | BP{n} distortion mode mux (×3, CD4053) | control | 1-of-3 SC/HC/WF select per band (composed by distortion/overview) |
| block-6 | BP3 input select (U81, CD4053) | control | 1-of-2: LP1 band vs ALT-VCA voice, per channel (ALT_L_DET) |
| aux/distortion/overview | CD4053 mux (per BP group) | — | **Composes** this primitive (§CD4053 Configuration) |
