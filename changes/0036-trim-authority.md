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

## Gate checklist
- [ ] Stage 1 derive → manifest (datasheet bands + checks)
- [ ] Stage 2 write decks (parallel)
- [ ] Stage 3 verify-intent (adversarial)
- [ ] Stage 4 integrate (all 7 gates green; SPICE-COVERAGE §C updated)
- [ ] PR `change/0036-trim-authority` → `dev`
