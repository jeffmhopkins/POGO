# aux: Source Selector (N-Way Switch Source Select)

**Type:** `modulation` · part of the [aux circuit library](../../_LIBRARY.md)

> Authored 2026-05-31 (change 0032). The reusable "N-way switch source select": one mechanical
> switch wires one of several signal sources to a single output node. Extracted from block-3
> MOD_SRC (LFO1 / LFO2 / EXT) and block-6 BP{n}_DIST_MODE (per-band SOFT/HARD/FOLD steering).

Design status: [x] draft → [ ] reviewed → [ ] validated on prototype

## Overview

The **source selector** is the simplest routing primitive: a mechanical (or logic) switch presents
**exactly one of N sources** at a shared output, with the de-selected sources disconnected (open) so
they do not reach the output. Unlike a buffer or summer it does no signal processing — its only job
is **connectivity / steering**.

POGO uses it in two places:

- **block-3 MOD_SRC** — a 3-way analog select wiring LFO1, LFO2, or EXT (MOD_IN jack) to the mod-bus
  source node V_SRC. Realized as a single **DPDT ON-ON-ON** toggle (Dailywell DW5): one pole steers
  the three throws to a common output; the second pole is bridged so the three switch positions each
  present one source at a time.
- **block-6 BP{n}_DIST_MODE** — a per-band 3-position switch selecting which of the three parallel
  distortion paths (SOFT/HARD/FOLD) is routed onward. (The block-6 realization uses a CD4053 CMOS mux
  driven by the switch — see [analog-mux](../../utility/analog-mux/spec.md) for the glitch-free mux
  path-select primitive; this entry covers the *switch-steering* abstraction common to both.)

The reusable insight: a switch select is **pure routing** — the selected source appears at the output
unchanged, the others contribute nothing. Any active scaling/summing belongs to a separate stage
(buffer, attenuverter, summer); the selector only chooses.

## Schematic

ASCII (3-way select via DPDT ON-ON-ON; the MOD_SRC realization):

```
   SRC_0 (LFO1) ──○ throw 1 ─┐
   SRC_1 (LFO2) ──○ throw 2 ─┼──○ A_COM ──► V_OUT (selected source)
   SRC_2 (EXT)  ──○ throw 3 ─┘
                              pos 0 → SRC_0 ; pos 1 → SRC_1 ; pos 2 → SRC_2

   DPDT ON-ON-ON: pole A steers the three throws to A_COM = V_OUT;
   pole B's throws are bridged (A2──B_COM) so each detent connects exactly one source.

   Generic N-way: one rotary/slide selects 1-of-N inputs onto one common output node.
   De-selected throws are OPEN — their sources do not reach V_OUT.
```

## Transfer Function

```
Selector law (sel ∈ {0…N−1}):
  V_OUT = SRC_sel                      (selected source passes unchanged)
  contribution of SRC_i (i ≠ sel) = 0  (de-selected throw is open)

No scaling, no summing: it is identity on the selected input and zero on the others.
```

This is a **steering / topology** law, not a transfer-math law — there is no gain or frequency
content to verify, only that the routing is correct (right source through, wrong sources blocked).

### DSP / plugin law it realizes

```
plugin (Pogo.cpp:366-369) — MOD_SRC selector:
  int modSrc = round(params[MOD_SRC_PARAM]);        // 0 / 1 / 2
  float modSrcV = (modSrc == 0) ? lfo1V
                : (modSrc == 1) ? lfo2V
                : (MOD_INPUT connected ? MOD_INPUT.getVoltage() : 0);
  → the nested ternary IS an N-way source select: one of {lfo1V, lfo2V, ext} reaches modSrcV.
    The analog DPDT ON-ON-ON reproduces this 1-of-3 steering.

plugin (Pogo.cpp:412-415) — per-band DIST_MODE:
  int distMode[3] = { round(BP1_DIST_MODE), round(BP2_DIST_MODE), round(BP3_DIST_MODE) };
  → each band's mode index selects one of three distortion laws (SOFT/HARD/FOLD); the analog
    realization is a per-band switch steering one of three parallel paths (via CD4053).
```

The plugin's `?:` ternary cascade is exactly the analog selector: it returns one source value and
ignores the others. The hardware switch must match that 1-of-N choice.

## Design Choices & Rationale

### DPDT ON-ON-ON for a 3-way analog select
A 3-position toggle that makes exactly one connection per detent is the cheapest panel-friendly 1-of-3
select. The DW5's two poles let one pole carry the steered source while the other is bridged to
enforce single-source presentation; the contact sequence is verified against the datasheet at
Phase-3R (swap throw assignments if the physical position↔param order differs — block-3 spec note).

### Selector vs mux (mechanical vs CMOS)
A mechanical switch is the right primitive when the select is a **panel control** (MOD_SRC) and the
source rate is slow (no audible switching artifact concern). When the selected node is an **audio
path** that must switch without a click, or when a *logic* line (not a panel detent) drives the
select, the CMOS analog mux ([analog-mux](../../utility/analog-mux/spec.md)) is preferred — it
steers parallel always-running paths glitch-free. block-6 uses the mux form for the per-band distortion
select; block-3 uses the mechanical form for MOD_SRC. Same steering abstraction, different realization.

### Keep the selector pure
The selected source is presented unbuffered to the next stage (the SCALE pot / summer input for
MOD_SRC). Any impedance conversion or scaling is a *downstream* stage — the selector itself adds no
gain so it cannot color the source or imbalance the three throws.

## Component Values (POGO-specific)

| Ref (generic) | Part | Package | Value | Notes |
|---|---|---|---|---|
| SW_SEL | Dailywell DW5 | DPDT ON-ON-ON | — | 3-way analog select (block-3 MOD_SRC: SW7) |
| (sources) SRC_0..2 | — | — | — | LFO1 / LFO2 / EXT for MOD_SRC; SC/HC/WF for DIST_MODE |
| (output) V_OUT | — | — | — | Selected source → next stage (SCALE pot for MOD_SRC) |

For the per-band distortion select, the steering element is a CD4053 CMOS mux driven by the
BP{n}_DIST_MODE switch — see [analog-mux](../../utility/analog-mux/spec.md) and
[distortion/overview](../../distortion/overview/spec.md) §CD4053 Configuration.

## Performance Characteristics

| Parameter | Value | Condition |
|---|---|---|
| Selected-source gain | ×1 (identity) | Pure routing, no scaling |
| De-selected leakage | 0 (open throw) | Mechanical switch; CMOS mux ~off-isolation |
| Positions | 3 (extensible to N) | DW5 ON-ON-ON |
| Switching artifact | n/a (slow panel select) | MOD_SRC; use mux for audio-rate steering |

## Known Gotchas / Assembly Notes

- **Sim scope (honest):** the deck is a **steering / routing topology check**, NOT a transfer-math
  check (there is no gain or frequency to verify). It instantiates the selector at sel = 0 / 1 / 2 in
  parallel and confirms (a) the SELECTED source value reaches V_OUT and (b) the de-selected sources do
  NOT. The "math" is identity-vs-zero. It does NOT model contact resistance, break-before-make timing,
  or DW5 contact sequencing (those are mechanical/datasheet facts, verified at Phase-3R bring-up).
- Verify the DW5 ON-ON-ON contact sequence against the datasheet; swap throw assignments if the
  physical position order differs from the param order (block-3 spec note).
- EXT throw for MOD_SRC carries the standard 100 Ω + BAT54S input protection (it is a panel jack); the
  LFO throws are internal and need no protection.
- The selector presents the source impedance of the chosen throw to the next stage — keep the next
  stage high-Z (or buffer) so the three sources see a consistent load.

## Used By

| Block | Instance | Board | Notes |
|---|---|---|---|
| block-3 | MOD_SRC select (SW7, DW5 ON-ON-ON) | control | 1-of-3: LFO1 / LFO2 / EXT → V_SRC (Pogo.cpp:366-369) |
| block-6 | BP{n}_DIST_MODE per-band select (×3) | control | 1-of-3 distortion-path steering via CD4053 (Pogo.cpp:412-415; see analog-mux) |
