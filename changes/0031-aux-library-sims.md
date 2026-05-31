# 0031 — aux library sims + reconcile the 11 moved entries

- **Slug:** aux-library-sims  **Branch:** `change/0031-aux-library-sims`
- **Lane:** B (tooling + test fixtures) — possibly real spec/netlist fixes if reconciliation finds staleness.
- **Status:** OPEN
- **Opened:** 2026-05-31
- **Blocks:** none (aux library); may touch a block spec/nets if a divergence is confirmed.   **Boards:** n/a

## Intent
Phase 2 of the aux library. For each of the 11 entries moved in 0030, (1) **author `sim/` decks**
(hardcoded representative values, NO `netlist_bind` — generic library math per `_LIBRARY.md`) that verify
the entry's transfer function / topology, and (2) **reconcile the spec against the current
block/netlist/plugin** — catch any staleness (the valuable side effect, e.g. the R_Iabc 1M→100k class).

Library sims are auto-discovered + run by `build_spice.py --check` (globs `specs/**/sim/*.cir`).

## The 11 entries (adapt from the proven block decks, generalize to hardcoded library form)
| Type | Entry | Core law to sim | Adapt from |
|---|---|---|---|
| filter | ota-c-svf | gm-C corner f=gm/(2πC); LP/HP/BP tap signs | block-7/5 ota_svf_loop |
| filter | expo-converter | V/oct: V_T·ln2 mV/oct slope | block-7/5/8 expo_voct |
| filter | q-control | LM13700 Iabc→Q | block-7/5 q_cell |
| vca | vca-cell | THAT2180 I/V unity, AMT-symmetric (V_ctrl=0→unity) | block-4 iv_unity/amt_symmetric |
| distortion | overview | SC/HC/WF clip levels + mux pass-through | block-6-dist1 dist_clip/wf_fold |
| modulation | lfo-core | triangle osc f=(R5+R7)/(4·R7·R·C); Schmitt ratio | block-2 lfo_fmax/vth |
| modulation | mod-bus-core | inverting summer + scale/offset/clamp | block-3 mb_offset/gain/polarity |
| modulation | attenuverter | bipolar pot ±V_src; −V_src inverter | block-3 att_bipolar/att_inverter |
| utility | unity-buffer | G=+1 follower | block-A/B unity |
| utility | cv-protection | 100Ω + clamp level + clamp current | block-A input_clamp (reworked) |
| utility | power-filter | RC decoupling corner / ripple attenuation | (new — board power) |

## Pipeline
1. **Write/reconcile** [4 parallel agents by type] — author hardcoded sim decks + reconcile each spec vs
   the live block/netlist/plugin; escalate any divergence (don't fudge).
2. **Verify** [parallel adversarial] — Q1 (deck computes the claim) + Q2 (expect independently
   spec-derived, plugin_ref valid). Q3 is "the math holds / non-vacuous" (no netlist_bind to perturb —
   library decks are generic). Confirm each deck is falsifiable on its hardcoded topology.
3. **Integrate** — fix findings/staleness, full gate stack, update `_LIBRARY.md` status.

## Decisions log
- 2026-05-31: library sims are generic (hardcoded, no binds) per the 0029/_LIBRARY convention; the
  block-bound decks remain the netlist-vs-spec guards. These library decks guard the textbook math + give
  the reusable building block a self-contained correctness check.

## Gate checklist
- [ ] Stage 1 write/reconcile (4 parallel → sims for 11 entries + staleness findings)
- [ ] Stage 2 verify-intent (adversarial)
- [ ] Stage 3 integrate (fix findings; all 7 gates green)
- [ ] Update `specs/aux/_LIBRARY.md` (entry status: sims ✅ for the 11 moved)
- [ ] PR `change/0031-aux-library-sims` → `dev`

## Next
- **0032:** author the NEW extracted entries + sims + "Composes:" cross-links.
