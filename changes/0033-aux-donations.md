# 0033 — aux library donations: 5 more reusable sub-circuits from the blocks

- **Slug:** aux-donations  **Branch:** `change/0033-aux-donations`
- **Lane:** B (tooling + test fixtures / library docs).
- **Status:** OPEN
- **Opened:** 2026-05-31
- **Blocks:** none (aux library; extracted FROM blocks but does not edit them).   **Boards:** n/a

## Intent
Second-wave library donations — scan of the blocks found 5 more genuinely-reusable sub-circuits not yet
captured. Each becomes a typed library entry (`spec.md` + hardcoded `sim/` deck), reconciled against its
source block(s). (The aux library reorg/sims/extractions were 0030/0031/0032; this is the follow-on "what
else can we donate" pass the user asked for.)

## The 5 new entries
| Type | Entry | From | Sim value |
|---|---|---|---|
| filter | **stereo-tilt-network** | block-5 LP1_TILT, block-6 BP_TILT | STRONG — L=base+tilt / R=base−tilt ±spread |
| utility | **gain-switch** | block-1 GAIN_MAIN, block-6 GAIN_BP3 | STRONG — 1×/5× selectable-gain ratio |
| utility | **distribution-buffer** | block-3 §H | THIN — paralleled-buffer fan-out to N loads (topology) |
| modulation | **source-selector** | block-3 MOD_SRC, block-6 DIST_MODE | THIN — 3-way DPDT analog source select (routing) |
| utility | **analog-mux** | block-6 CD4053 (overview composes it) | THIN — glitch-free 2:1 path select (Ron/topology) |

Also: add **SUM_AMP** (block-7) and the other newly-found instances to the relevant primitives' "Used By"
(SUM_AMP = the inverting-summer primitive; no new entry).

**Deferred (not donated):** IRES_AMP (block-7/5/8) — the resonance-current driver's negative-drive bias is
the open Phase-3R [NV] item; not meaningfully sim-able until specified. ALT path — composed of gain-switch
+ vca-cell, no new primitive.

## Pipeline
1. **Write** [2 parallel agents] — author the 5 entries' spec.md + hardcoded `sim/` decks, reconcile vs
   the source blocks, add Used-By/Composes links where relevant.
2. **Verify** [adversarial] — Q1/Q2 + Q3′ non-vacuous (honest about the thin-sim entries' scope).
3. **Integrate** — fix findings, full gate stack, update `_LIBRARY.md` (taxonomy + status + entry table).

## Decisions log
- 2026-05-31: user asked for additional block "donations"; chose (no-preference → assistant judgment) the
  full 5-entry set per the earlier "Everything reusable" intent. The thin-sim entries (distribution-buffer,
  source-selector, analog-mux) get reusable specs + honest light topology sims. block-3 spec 10k/50k fix
  kept as a separate change (one concern per change).

## Gate checklist
- [x] Stage 1 write (2 parallel → 5 entries + 8 sim decks; non-vacuity confirmed inline)
- [x] Stage 2 verify-intent — folded into the writers' inline perturbation probes (all 5 non-vacuous; thin entries honestly scoped)
- [x] Stage 3 integrate — _LIBRARY.md taxonomy+table updated; all 7 gates green; 89 decks
- [x] Update `specs/aux/_LIBRARY.md` (taxonomy + entry table; 27 entries)
- [ ] PR `change/0033-aux-donations` → `dev`
