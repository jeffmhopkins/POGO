# 0036 — trim-authority verification across device-constant tolerance bands

- **Slug:** trim-authority  **Branch:** `change/0036-trim-authority`
- **Lane:** B (tooling + test fixtures).
- **Status:** OPEN
- **Opened:** 2026-05-31
- **Blocks:** block-4, block-6 (DRIVE), block-7/5/8 (V/oct) + aux ref-injection-trim, voct-expo-divider.

## Intent
Convert three of the deferred A/B [NV] items from "deferred until bench" → **"trim-authority verified
in-env."** The absolute device constant stays [NV], but we verify the **trim pot has enough range to hit
the target across that constant's datasheet tolerance band** — a pure-circuit, bench-free guarantee that
the design is *calibratable*. (User's reframe: "can a/b be verified that it'll work with trim pots to
adjust?" — yes, for these three.)

The method (per [NV] discipline): sweep the device constant across its datasheet min/nominal/max as
PARALLEL instances, and assert the adjustable element's range still brackets the target at BOTH extremes
(a "target reachable" / "authority ≥ required" check), not the absolute.

## The three items
| Item | Device constant (band from datasheet) | Trim | Check |
|---|---|---|---|
| **VCA Ec+** (block-4 vca_ecplus + aux ref-injection-trim) | THAT2180 gain const ≈ 6.1 mV/dB ± datasheet tol | RV unity-inject | the ±injection still spans ≥ the required unity-null authority at the worst-case (max) mV/dB |
| **DRIVE dB law** (block-6) | THAT2180 mV/dB band | DRIVE knob+CV → Ec+ | the knob+CV span still covers the needed drive-dB range across the band |
| **THAT340 V/oct** (block-7/5/8 + aux voct-expo-divider) | V_T·ln2 drift (+3333 ppm/K) + tempco-R tol | RV_1VOCT | the 1V/oct trim still centers on V_T·ln2 across the temperature/tempco band |

## NOT in this change (still genuinely blocked)
- **Q-cell negative-drive bias** (block-7/5/8) + **D12 clamp** — needs the negative-drive bias network
  *designed* first (Phase-3R); there's no trim circuit to authority-check until that topology exists.

## Manifest (Stage 1) ✅ — datasheet/physics bands extracted
| Constant | Band {min,nom,max} | Basis |
|---|---|---|
| THAT2180 Ec+ gain const | **6.0 / 6.1 / 6.2 mV/dB** | THAT2180 datasheet (Doc 600029) EC table — all grades identical; worst case = 6.2 (least dB authority) |
| V_T·ln2 (THAT340 expo) | 16.32 / 17.92 / 19.30 mV/oct (0/25/50 °C) | physics V_T=kT/q; cross-checks to +0.336 %/K = the THAT2180 +0.33 %/°C tempco |

**Three checks:** `vca_unity_band` (block-4), `drive_db_band` (block-6-dist1), `voct_slope_band` (block-7).
Each sweeps the constant across the band as parallel instances and asserts the trim still reaches/brackets
the target at the WORST extreme (6.2 mV/dB for the THAT2180 ones).

**Band-framing decision (assistant, physics):** for `voct_slope_band` the trim-authority band is the
**room-temp calibration spread** (R_VOCT ±1 %, R_T tol, expo part spread — a few %), NOT the full 0–50 °C
V_T swing — temperature drift is the **tempco resistor's** job (its raison d'être), not the one-time trim.
So the 10k netlist pot's ±~10 % span is ample; the check PASSES on the correct band.

**Finding to flag (the deriver surfaced it):** RV_1VOCT is **10k in the netlist** but the block-7 spec
calibration table says **20k**. Under the correct room-temp band both are adequate (10k ±10 %, 20k ±20 %),
so it's a **documentation inconsistency**, not a failing trim result — flag it for reconciliation, don't
fail the check on the over-strict full-temperature premise.

**DRIVE scope (open spec dep):** the knob→Ec+ full-scale voltage is Phase-3R-undefined, so `drive_db_band`
proves "the summer+injection topology has ample (≫10×) headroom to command the SOFT +34.75 dB target across
the mV/dB band" — the calibratability claim — with that scope stated explicitly (escalate the spec gap).

## Pipeline
1. **Derive** [1 agent] — read the THAT2180 / THAT340 / LM13700 datasheets (`components/parts/*`) to
   establish DEFENSIBLE tolerance bands; read the existing authority decks; emit a manifest of the
   trim-authority checks (band endpoints + the "target reachable" assertion per item).
2. **Write** [parallel] — extend/author the decks: sweep the constant across the band, assert authority
   covers target at both extremes. Hardcoded library form for the aux decks; the block decks may keep
   their existing binds.
3. **Verify** [adversarial] — does the deck actually prove reachability across the band? Is the band
   datasheet-defensible (not reverse-engineered to pass)? Would it FAIL if the trim were too small?
4. **Integrate** — full gate; update `specs/SPICE-COVERAGE.md` §C (move these from deferred → trim-authority
   verified, keeping the absolute as [NV]).

## Stage 2 — write (2 parallel + 1 self-authored) ✅ — 4 decks, all PASS
- Group A (THAT2180 6.0–6.2 mV/dB): `vca_unity_band` (block-4), `drive_db_band` (block-6-dist1).
- Group B (THAT340 V_T·ln2): `voct_slope_band` (block-7 + aux mirror — room-temp trim authority).
- + self-authored after the user's "modules heat up" point: `voct_tempco_tracking` (block-7 — the FULL
  0–50 °C temperature-tracking check, the more realistic condition).

## Stage 3 — verify-intent (1 adversarial) ✅ — 3 SOUND, 1 WEAK (fixed), real findings
- `vca_unity_band` **SOUND** (band datasheet-confirmed 6.0/6.1/6.2; worst case 6.2; perturbation fails).
- `drive_db_band` **SOUND** (scope: reachability not knob-scaling, Phase-3R — stated; falsifiable).
- `voct_tempco_tracking` **SOUND** (residual −2.1/+1.5% independently confirmed; tempco-off → ±8–10% fails).
- `voct_slope_band` **WEAK → FIXED:** the deck modeled the 1V/oct pot as **10k**, but the sourced part is
  **20 kΩ** (components.yaml; block-7 spec.md:185; RV17 symbolic → netlist_bind blind, exactly the drift
  class verify exists to catch). Corrected both decks (block-7 + aux mirror) to 20k: span 14.10–19.65
  mV/oct, target reached at ~24.5% travel (NOT mid — the old "mid lands on target" narrative was wrong),
  still brackets the ±5% band with more margin. PASS; falsifiability (2k trim) intact.

## Stage 4 — integrate ✅
- Fixed `voct_slope_band` (block-7 + aux) 10k→20k pot + corrected narrative (the MEDIUM verify defect).
- Fixed the aux `voct-expo-divider/spec.md` §Temperature-compensation: the claim "the slope trim absorbs
  the ~20% TCR excess" is **physically wrong** (a one-time room-temp null cannot correct a tempco *slope*
  mismatch — the residual is permanent). Rewrote to the correct physics: ideal tempco ≈ +3394 ppm/K; the
  POGO +4110 ppm/K over-comps ~21% → permanent ≈±2% cutoff residual (ok for a filter); a ~+3300–3400 ppm/K
  part would track ≈8× tighter.
- Corrected my own mis-attribution: CLAUDE.md does NOT cite +3300 ppm — the +3300–3500 target is in the aux
  specs (now reconciled).
- **SPICE-COVERAGE §C:** VCA Ec+ / DRIVE / THAT340-V/oct moved deferred → **trim-authority/temperature
  verified**. Logged the +4110-vs-ideal tempco finding + the pre-existing `expo_voct` 10k-pot follow-up.
- All 7 `--check` gates green; 4 new decks (5 with the aux mirror).

## Findings for the user (decisions, not blockers)
1. **Tempco part value:** the +4110 ppm/K Vishay TFPT over-compensates → ≈±2% cutoff tracking over 0–50 °C.
   Fine for a filter, but a ~+3300–3400 ppm/K part would track ≈8× tighter (≈±0.25%). Component choice.
2. **expo_voct/voct_octave 10k-pot model** (pre-existing, block-7/5/8 + aux) vs the 20k sourced part — a
   conservative inaccuracy; recommend a focused deck-cleanup change to reconcile.

## Gate checklist
- [x] Stage 1 derive → manifest (datasheet bands + checks)
- [x] Stage 2 write decks (4 decks: vca_unity_band, drive_db_band, voct_slope_band, voct_tempco_tracking)
- [x] Stage 3 verify-intent (3 SOUND, 1 WEAK→fixed; found the 20k-pot drift + the wrong tempco claim)
- [x] Stage 4 integrate (fixes applied; SPICE-COVERAGE §C updated; all 7 gates green)
- [ ] PR `change/0036-trim-authority` → `dev`
