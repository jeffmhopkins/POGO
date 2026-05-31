# 0034 — block-3 spec: attenuverter pot value staleness (10 kΩ → 50 kΩ)

- **Slug:** block3-pot-staleness  **Branch:** `change/0034-block3-pot-staleness`
- **Lane:** C (docs only — a stale value in prose; no DSP, panel geometry, components.yaml, or nets connectivity).
- **Status:** OPEN
- **Opened:** 2026-05-31
- **Blocks:** block-3   **Boards:** utility

## Intent
Fix the one outstanding **block-side** staleness surfaced by the aux-library reconciliation pass (change
0031): `specs/block-3/spec.md` §2/§3 still described the attenuverter pots as **10 kΩ**, contradicting the
change-0020 §H banner (line 177) and the nets — §H raised them to **50 kΩ** (with the −V_src inverters
10k→47k) so the bus load dropped to ~11 mA. Two prose spots carried the stale value + a load recompute on
the old basis.

## What changed (block-3/spec.md only)
- **Line 111** (§2 attenuverter description): "Bipolar attenuverter pot (10 kΩ …)" → **50 kΩ** (note "change
  0020 §H, was 10 kΩ").
- **Lines 145–150** (§2 distribution buffer): rewrote the load paragraph — the 18 destinations are now
  50 kΩ pots ∥ 47 kΩ inverter inputs (the §H ×5 hi-Z load), net bus load **~11 mA** (per §H, down from the
  pre-§H ~18 mA on 10 kΩ pots); each buffer half drives **~5.5 mA** (was ~9.5 mA). Now consistent with the
  §H banner (line 177) and the SPICE `modbus_depth` / aux `distribution-buffer` decks.

## Not changed (verified out of scope / already correct)
- All other "10 kΩ" mentions in block-3 are now historical/contextual (the §H banner + the before/after
  comparison) — correct as-is.
- block-5/7/8 R_VOCT, block-A LM4562 part-identity (documented harmless), block-7/5 R_Iabc — all already
  fixed in earlier changes (0024/0029) or documented.
- Deferred [NV]/Phase-3R items (IRES_AMP negative drive, THAT2180 dB law, etc.) — cannot close in-env.

## Verification
- No standalone stale "10 kΩ attenuverter pot" claim remains (grep). All 7 `--check` gates green
  (spec-prose change; schematic/netlist gates read nets, not prose).

## Gate checklist (Lane C)
- [x] Fix the stale value + the dependent load recompute
- [x] All 7 `--check` gates green
- [ ] PR `change/0034-block3-pot-staleness` → `dev`
