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

## Gate checklist
- [ ] Stage 1 write/retrofit (4 parallel → binds on 10 decks + 1 new block-B deck)
- [ ] Stage 2 verify-intent (parallel adversarial)
- [ ] Stage 3 integrate (fix findings; all 7 gates green)
- [ ] Update `specs/SPICE-COVERAGE.md` (all remaining → FULL; the tracker's outstanding list cleared)
- [ ] PR `change/0029-spice-baselines-full` → `dev`

## Outstanding after this change
- block-6-svf2/svf3 + dist2/dist3 remain "covered by representative" (svf1/dist1 are identical copies).
- [NV] items (THAT2180 6.1mV/dB, log-pot tapers, Q-cell negative drive, zener/diode Vf) still await bench.
