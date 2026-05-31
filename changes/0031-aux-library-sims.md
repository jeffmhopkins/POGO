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

## Stage 1 — write/reconcile (4 parallel) ✅ — 21 library decks across 11 entries, all PASS
filter (gm_c_corner, svf_taps [fixed a broken self-referencing-integrator deck], voct_slope,
expo_octave, q_iabc_law, q_dsp_map); vca-cell (iv_unity, amt_symmetric, db_law_shape); distortion/
overview (clip_levels, mux_select); lfo-core (lfo_oscillation `.tran`, lfo_threshold_ratio);
mod-bus-core (mb_summer_gain, mb_offset_polarity, mb_clamp); attenuverter (att_bipolar, att_inverter);
utility (unity_follower, clamp_current, supply_rc_corner). All hardcoded, NO netlist_bind (library form).

### Reconciliation findings (aux-spec staleness FIXED) + block-side flag
- **q-control** R_Iabc 1MΩ→100kΩ (0020 §D/M5); flagged lines 41/123/140 (superseded +0.74V V_ires model)
  as Phase-3R deferred (the negative-drive bias is an open design item — not rewritten).
- **attenuverter** R_inv 10k→47k + pots 10k→50k (0020 §H).
- **mod-bus-core** stale distribution design → low-Z normal + C/D buffer (0020 §H); noted the offset
  ±5V-ref form vs block-3's 240k/±12V (same result, documented).
- **lfo-core** superseded vary-R_INT derivation → banner to the fixed-R_INT+attenuator scheme.
- **FLAGGED (block-side, NOT edited):** block-3 spec lines 111/145/191 say 10kΩ attenuverter pots vs
  nets + §H banner (line 176) = 50kΩ — a block-spec internal inconsistency for a separate block change.

## Stage 2 — verify-intent (2 parallel adversarial) ✅ — all SOUND; 1 real + minor findings
Library bar: Q1 (computes claim), Q2 (expect independently derived), Q3′ (non-vacuous via DECK
perturbation — no netlist to bind). The svf_taps repair + the `.tran` oscillator both confirmed genuine.
- **P1 (real):** `supply_rc_corner` was near-vacuous — Rs was DERIVED from fpick+C, pinning fc to 1000
  regardless of C. **gm_c_corner had the same pattern.**
- **P2:** `mux_select` unity tol too loose to pin Ron (passes for Ron up to ~100k).
- Minor: clip_levels redundant assertion; q_dsp_map is a DSP-formula echo (no analog topology); svf_taps
  checks tap magnitude only (not HP sign); lfo comment typo.

## Stage 3 — integrate ✅ (findings fixed; gates green)
- **P1 fixed:** `supply_rc_corner` + `gm_c_corner` now use INDEPENDENT Rs/C (resp. gm/C) literals (not
  derived from the target f). **Proven non-vacuous:** C/10 now moves the corner 1kHz→10kHz in both.
- **P2:** `mux_select` description relabeled to a PATH-STEERING topology check (Ron modeled negligible,
  not precision-pinned — a block-level concern), honest about scope.
- Minor: q_dsp_map + svf_taps descriptions annotated with their scope/coverage limits; lfo typo fixed.
- All 7 `--check` gates green; **68 decks total** (47 block + 21 aux library).

## Gate checklist
- [x] Stage 1 write/reconcile (4 parallel → 21 decks for 11 entries + 4 staleness fixes + 1 block flag)
- [x] Stage 2 verify-intent (2 adversarial → all SOUND; found the supply_rc_corner vacuity)
- [x] Stage 3 integrate (P1/P2 fixed + honesty notes; all 7 gates green)
- [x] Update `specs/aux/_LIBRARY.md` (11 moved entries → sims ✅ 0031)
- [ ] PR `change/0031-aux-library-sims` → `dev`

## Next
- **0032:** author the NEW extracted entries + sims + "Composes:" cross-links.
