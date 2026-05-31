# 0029 — SPICE baselines → FULL (sprint): bind + verify all remaining blocks

- **Slug:** spice-baselines-full  **Branch:** `change/0029-spice-baselines-full`
- **Lane:** B (tooling + test fixtures) — possibly real netlist/spec fixes if binds surface divergence.
  Touches `specs/<block>/sim/**` (+ a new `specs/block-B/sim/`); nets/components only if a bug is found.
- **Status:** OPEN
- **Opened:** 2026-05-31
- **Blocks:** block-5, block-8, block-1, block-A, block-6-svf1, block-6-mix, block-B   **Boards:** mixed

## Intent

One sprint to bring **every remaining block to 🟢 FULL coverage**. The five distinct-physics blocks are
already FULL (block-7/4/3/6-dist1/2). The rest are baseline decks (from 0022/0023) that predate
`netlist_bind` (built in 0024) and were never adversarially verified — so they are deck-literal-vs-spec,
not netlist-vs-spec. This change retrofits `netlist_bind` to all of them + runs the adversarial-verify
stage, and authors a new deck for block-B (output buffers, ⚪ NONE).

Same gap class the verify stage found in block-4/block-3 (a hardcoded value that wouldn't catch a netlist
regression) — so each promotion gets a real Q3 perturbation, not just a passing run.

## Scope (10 existing decks to bind+verify + 1 new)
| Block | Decks | Action |
|---|---|---|
| **block-5** LP1 | expo_voct, ota_svf_loop, q_cell, lp1_tilt_passive | bind (mirror block-7) + verify |
| **block-8** LP2 | expo_voct, ota_svf_loop | bind + verify |
| **block-1** Pre-Gain | pregain | bind (R3/R4 5× + clip) + verify |
| **block-A** Input | input_clamp | bind (R_prot) + verify |
| **block-6-svf1** | bp_fref | bind (68nF→400Hz) + verify |
| **block-6-mix** | bp3_normal | bind (BP3 buffer Rs) + verify |
| **block-B** Output | — (NONE) | AUTHOR a new deck (output-buffer unity + ±11V clamp) |

## Pipeline (scaled for a multi-block sprint)
1. **Write/retrofit** [4 parallel agents, disjoint block dirs] — each reads its block's deck(s) + nets +
   spec + plugin, adds `netlist_bind` for every load-bearing value (resolving against nets.yaml),
   confirms PASS + self-Q3, escalates any divergence. block-B's agent authors a new deck.
2. **Verify** [parallel adversarial, isolated git worktrees] — three killer questions per deck; Q3 load-bearing.
3. **Integrate** — fix findings, full gate stack, coverage → FULL for all.

(Derive is folded into the writers — the decks mostly exist; the work is binding + verifying, not new
math discovery. block-B's writer derives its one deck inline.)

## Decisions log
- 2026-05-31: user requested all remaining blocks to FULL in one sprint. Grouped 4 writers by physics:
  W1=block-5 (resonant filter, 4 decks); W2=block-8 + block-6-svf1 (filter f_ref/OTA); W3=block-1 + block-A
  (gain/clamp); W4=block-6-mix + block-B (mix normal + new output buffer).

## Stage 1 — write/retrofit (4 parallel) ✅ — 10 decks bound + 1 new (block-B), all PASS
- **W1 block-5:** expo (R63/R231), ota_svf (C11), q_cell (R57/R58=100k), tilt (R63/R55/R231). No `.cir` change.
- **W2 block-8 + svf1:** block-8 expo (R86/R230) + ota_svf (C33A); svf1 bp_fref (C15=68nF; 47nF trap unbound).
- **W3 block-1 + block-A:** pregain (R3L/R4L → 4.83×; clip [NV]); input_clamp (R1=100R; clamp [NV]).
- **W4 block-6-mix + block-B:** mix bp3_normal (honest no-bind — load-bearing Rs live in block-B);
  block-B out_buffer NEW (div_ratio bound to R34=1k; unity topology; clamp [NV]).
- No netlist↔spec divergences found (all baseline values already correct).

## Stage 2 — verify-intent (4 parallel adversarial, isolated worktrees) ✅
- **V1 block-5:** all 4 SOUND, all 6 binds load-bearing (tilt deck is bind+topology). Flagged stale spec.md §3.
- **V2 block-8 + svf1:** all 3 SOUND; bp_fref bound-68nF/unbound-47nF structure confirmed honest.
  (Optional note: block-8 expo mv_lo/mv_hi are geometry-derived brackets — same as block-7 precedent.)
- **V3 block-1 + block-A:** block-1 fully SOUND. **block-A WEAK — 2 real defects:** the R1 bind was
  vacuous (no measurement depended on R1 — series Rs fed dangling nodes) and clamp_hi was circular.
- **V4 block-6-mix + block-B:** both SOUND. block-6-mix no-bind verified honest (cross-block bind
  unsupported; falsifiable on wiring + match). block-B div_ratio genuinely bound to R34, clamp [NV] honest.
  Cosmetic: bp3_normal plugin_ref line range.

## Stage 3 — integrate ✅ (defects fixed; gates green)
- **block-A `input_clamp` REWORKED** (the substantive fix): added a `clamp_i` measurement = clamp current
  through R1 = (17−12.3)/R1. **Proven R1-load-bearing:** perturbing Rprot 100→1k moves clamp_i 0.047→0.0047
  (was: nothing moved). The vacuous bind + circular clamp_hi are resolved — R1 now genuinely exercised.
- **block-5 spec.md §3:** stale R_Iabc "1 MΩ … 0.74 µA → Q 0.70" → "100 kΩ (R57/R58, change 0020 §D) …
  Q ≈ 0.74", resolving the §3-vs-§D contradiction (the q_cell deck already used the live 100k).
- **block-6-mix** bp3_normal plugin_ref Pogo.cpp:497-499 → **501-503** (cosmetic line-range).
- **block-8 expo** mv_lo/mv_hi annotated as geometry-derived trim-authority brackets (honesty note).
- All 7 `--check` gates green; **47 decks total**.

## Gate checklist
- [x] Stage 1 write/retrofit (4 parallel → binds on 10 decks + 1 new block-B deck)
- [x] Stage 2 verify-intent (4 parallel adversarial → block-A WEAK found + fixed; rest SOUND)
- [x] Stage 3 integrate (reworked block-A; fixed stale spec.md + cosmetics; all 7 gates green)
- [x] Update `specs/SPICE-COVERAGE.md` (ALL blocks → FULL; outstanding list cleared; status COMPLETE)
- [ ] PR `change/0029-spice-baselines-full` → `dev`

## Outstanding after this change
- block-6-svf2/svf3 + dist2/dist3 remain "covered by representative" (svf1/dist1 are identical copies).
- [NV] items (THAT2180 6.1mV/dB, log-pot tapers, Q-cell negative drive, zener/diode Vf) still await bench.
