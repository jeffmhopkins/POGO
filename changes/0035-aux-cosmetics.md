# 0034b — aux library cosmetics (D items from the SPICE-sprint outstanding list)

- **Slug:** aux-cosmetics  **Branch:** `change/0035-aux-cosmetics`
- **Lane:** C (test-fixture polish — a library deck improvement; no DSP, panel, components, or nets change).
- **Status:** OPEN
- **Opened:** 2026-05-31
- **Blocks:** none (aux library)   **Boards:** n/a

## Intent
Close the **D (cosmetic) items** from the SPICE-sprint outstanding list (user: "do D now").

## What changed
- **D11 (the real one): `vca/ref-injection-trim` part-B authority coupling.** The injection-authority
  section used standalone `±1.195 V` wiper literals decoupled from the part-A divider, so an R_top
  regression only falsified the *level* (part A), not the *authority* (part B). **Fixed:** the wiper is now
  the LIVE `refp`/`refn` divider node (via a high-Z `Ewp/Ewn` buffer — no extra divider load). **Proven:**
  regressing R_top 11.3k→45.3k (the pre-0025 bug) now collapses BOTH `ref_p` (1.195→0.322) AND `inj_hi_dB`
  (1.857→0.441), failing the deck — authority is now coupled to level, not just to R_inj. Baseline values
  unchanged (1.195 / 1.857 / −2.019, all PASS).

## D10 — verified, NO change needed
The "plugin_ref line numbers a few off" note (from the 0032 verify) was itself imprecise. I checked every
aux deck's `Pogo.cpp:` citation against the current source — **all correct**: tilt 402-403/466-467,
source-selector 366-369/412-415, clip-detector 459, led-breathing 508-509, output-buffer 499-500. No edits
(I won't "fix" correct citations to wrong ones).

## Verification
- All 7 `--check` gates green (89 decks). D11 baseline unchanged; the new coupling proven by perturbation.

## Gate checklist (Lane C)
- [x] D11 ref-injection part-B coupling fixed + proven
- [x] D10 verified (citations already correct — no change)
- [x] All 7 `--check` gates green
- [ ] PR `change/0035-aux-cosmetics` → `dev`

## Remaining outstanding (NOT in scope — hardware/design-blocked)
The A/B [NV]/Phase-3R items (Q-cell negative-drive bias, THAT2180 6.1 mV/dB, DRIVE dB law, D12 clamp,
THAT340 tempco, + the q-control derivation passages that wait on the bias design) and the C tooling
follow-ups (check_locked.py, check_drift.py, boundary-net cross-sheet check) remain tracked.
