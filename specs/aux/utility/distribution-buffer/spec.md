# aux: Distribution Buffer (Paralleled Op-Amp Fan-Out)

**Type:** `utility` · part of the [aux circuit library](../../_LIBRARY.md)

> Authored 2026-05-31. Fan-out / distribution buffer extracted from block-3 §H (the change-0020
> mod-bus depth fix): the two spare op-amp sections of MB_PROC_A re-enabled in parallel to drive
> V_MODBUS into 18 attenuverter destinations at full depth.

Design status: [x] draft → [ ] reviewed → [ ] validated on prototype

## Overview

A **distribution buffer** is a unity-gain op-amp follower whose job is *current* delivery, not gain:
one signal source feeds **many parallel loads** from a single low-impedance rail, so no load steals
depth from another and the source node is never throttled by the aggregate load. POGO uses it on the
mod bus, where one processed source (V_MODBUS) must reach **18 attenuverter destinations** (plus the
VCA raw normal) without amplitude loss.

The reusable insight is the *contrast* between two ways to feed many loads:

- **Un-buffered (the §H bug):** the source reaches each destination through a **series resistor**
  (the old 100 kΩ `R_SRC_NORM` per destination). With a ~3.3 kΩ destination load this forms a
  divider — the destination saw only `3.3k / (100k + 3.3k) ≈ 3 %` of the bus. Depth collapsed.
- **Buffered (the §H fix):** the source drives a **low-Z rail** directly from the op-amp output;
  each destination's load current is supplied by the buffer, not by a series resistor, so the
  destination sees ≈ full bus voltage (~98–99 %) regardless of how many loads hang off the rail.

To deliver the worst-case rail current (±10 V into the parallel-load equivalent ≈ ±18 mA on the
original 10 kΩ pots), **two op-amp halves are paralleled** — each half through a small (47 Ω) series
"share" resistor before the join. The share resistors split the load current between the two outputs
and prevent oscillation/contention when the two halves saturate at slightly different times.

## Schematic

ASCII (paralleled two-half unity buffer driving a low-Z rail to N loads):

```
                        R_share (47Ω)
            ┌────────[──┐
   V_in ───┤ U_C (+1)  │ ├──┐
            └────────[──┘    │
                             ├──● V_RAIL ──┬─ R_load,1 (dest 1)
            ┌────────[──┐    │             ├─ R_load,2 (dest 2)
   V_in ───┤ U_D (+1)  │ ├──┘              │     …
            └────────[──┘                  └─ R_load,N (dest N)
                        R_share (47Ω)

  Each U_x is a unity follower (G=+1); feedback taps the half's own output (before R_share).
  The N loads share one buffered rail — load current comes from the op-amps, not a series R.

  --- contrast (un-buffered fan-out — the bug it replaces) ---

   V_in ──[ R_series (100k) ]──● V_dest ── R_load (3.3k) ── (destination)
            divider: V_dest/V_in = R_load/(R_series+R_load) ≈ 3%  (DEPTH LOSS)
```

## Transfer Function

```
Buffered rail (ideal follower, load current supplied by op-amp):
  V_RAIL = V_in                       (depth ≈ 100 %, independent of N loads)

Un-buffered series-R fan-out (resistive divider per destination):
  V_dest = V_in · R_load / (R_series + R_load)
         = V_in · 3.3k / (100k + 3.3k) ≈ 0.032 · V_in   (≈ 3 % — the bug)

Worst-case buffer current (the reason two halves are paralleled):
  I_rail = V_rail / R_load,parallel
  R_load,parallel = R_pot / N = 10k / 18 ≈ 556 Ω → I_rail(±10V) ≈ ±18 mA
  per half ≈ ±9 mA (with two halves) — well inside a TL07x section's drive.
```

The buffer's gain is unity by construction; the *deliverable depth* is what changes. The share
resistors (47 Ω) are small vs the load (≥556 Ω equivalent), so they drop <1 % under the worst-case
balanced split and do not meaningfully reduce depth.

### DSP / plugin law it realizes

Analog-only — there is no DSP node for the distribution buffer. In `plugin/src/Pogo.cpp` the processed
bus value `busV` (≈373) is read by every destination at full value (a software variable has no fan-out
loss); the hardware distribution buffer exists solely to **reproduce that loss-free fan-out** in
analog. The §H fix (block-3 spec §H, change 0020; SPICE `specs/block-3/sim/modbus_depth.cir`) is the
plugin-parity correction: without it the analog bus delivered ~3 % depth where the plugin delivers
100 %.

`plugin_ref:` `plugin/src/Pogo.cpp:373` (busV read undivided by all destinations — analog-only fan-out).

## Design Choices & Rationale

### Buffered low-Z rail vs series-R normal
A series resistor per destination (the simplest "normal to the bus") forms a divider with the
destination's input impedance — fatal when many low-Z loads sit on the bus. A buffered rail decouples
the source from the load count entirely: the op-amp's low output impedance (<<1 Ω closed-loop) holds
the rail at V_in no matter the load.

### Why parallel two halves (not one)
The worst-case rail current exceeds a comfortable single-section continuous drive once you account for
the ±10 V swing into the aggregate load. Two halves in parallel halve the per-section current and add
thermal headroom; the spare U3 C/D sections were already on the board, so the fix costs only two 47 Ω
resistors.

### Why the 47 Ω share resistors
Directly tying two op-amp outputs together invites contention: tiny offset/slew differences make one
output fight the other. A small series resistor on each output (47 Ω) decouples them — each half sees
its own output for feedback, and the resistors force current sharing instead of a low-impedance
output-to-output fight. They are small enough (<<load) to not reintroduce depth loss.

## Component Values (POGO-specific)

| Ref (generic) | Part | Package | Value | Notes |
|---|---|---|---|---|
| U_C, U_D | TL074CDT | SOIC-14 | — | Two sections of MB_PROC_A in parallel (G=+1) |
| R_share (×2) | Resistor | 0603 | 47 Ω | One per half before the join; current-share + anti-contention |
| (load, representative) R_load,parallel | — | — | ≈556 Ω | 18 × 10 kΩ pots in parallel (original); ≈3.3 kΩ per-dest equiv |
| (replaced) R_SRC_NORM | Resistor | 0603 | 100 kΩ | The series normal REMOVED by §H (the bug source) |

## Performance Characteristics

| Parameter | Value | Condition |
|---|---|---|
| Rail gain | ×1 (unity) | Closed-loop follower |
| Delivered depth (buffered) | ~98–99 % | Into the parallel destination load |
| Delivered depth (un-buffered, bug) | ~3 % | 100 kΩ series into ~3.3 kΩ destination |
| Worst-case rail current | ±18 mA | ±10 V into ≈556 Ω (split ±9 mA/half) |
| Output impedance | <<1 Ω | Op-amp closed-loop, before R_share |

## Known Gotchas / Assembly Notes

- **Sim scope (honest):** the deck is a **topology / depth check**, not a drive-current check. Ideal
  op-amp followers do NOT model output-current limits or saturation, so the sim proves the *buffered
  low-Z rail passes ~unity into a representative load* and that the *un-buffered series-R divider
  throttles depth* (the §H before/after) — it does NOT verify the ±18 mA fan-out is within the
  TL07x's real drive (that is a datasheet/sourcing fact, checked by the paralleling, not by SPICE).
- Match the two 47 Ω share resistors; a large mismatch unbalances the current split.
- Keep the rail trace low-impedance and star-routed to the destinations so no single destination's
  return current modulates another's voltage.
- The buffer must be unity (no gain) — any gain would re-scale the whole mod bus.

## Used By

| Composed cell / Block | Instance | Board | Notes |
|---|---|---|---|
| block-3 | MB_PROC_A halves C+D (paralleled), R227/R228 47 Ω | control | V_MODBUS rail → 18 attenuverters + VCA raw normal (§H, change 0020) |
