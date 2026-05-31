# 0023 — SPICE deck coverage for all blocks + promote gate to blocking

- **Lane:** B (build-system / tooling + test fixtures). Adds SPICE decks + flips the existing
  `build_spice.py --check` CI gate from advisory to blocking. No DSP, panel, `components.yaml`
  connectivity, or nets change.
- **Status:** OPEN
- **Opened:** 2026-05-31
- **Branch:** `change/0023-spice-coverage` off `dev`.

## Intent

Complete the SPICE harness rollout (0021 design → 0022 runner+advisory gate → **0023 full coverage +
blocking**): author behavioral decks for the blocks not yet covered, then promote the
`build_spice.py --check` gate to **blocking** so analog-behavior regressions fail CI like the other
six `--check` gates.

## Decks added (8 new → 15 total checked)

| Block | Deck | Validates (plugin law) |
|---|---|---|
| block-1 | pregain | 5× gain network (1+18k/4.7k=4.83×) + clip ±10.5V (`PreGain.hpp`) |
| block-A | input_clamp | unity follower + BAT54S over-voltage clamp ~±12.3V (`InputBuffer.hpp`) |
| block-6-svf1 | bp_fref | **BP cap = 68nF → 400Hz** (vs the 47nF "copy" trap → 582Hz); `BandpassSVF.hpp:42` F_REF=400 |
| block-6-dist1 | dist_clip | HC ±5.8V→±1.16 norm, WF/SC ±1.4V→0.28 norm vs `Distortion.hpp` clamp/Vth |
| block-7 | expo_voct, ota_svf_loop | HP expo divider + OTA tap/f_ref (mirror of block-5; mono, 632Hz) |
| block-8 | expo_voct, ota_svf_loop | LP2 expo divider + OTA tap/f_ref (mirror) |

Plus the 7 from 0022 (block-3 modbus_depth, block-4 vca_ecplus, block-5 expo/ota/q/tilt,
block-6-mix bp3_normal). **15 checked decks, all pass.**

Notable: `bp_fref.cir` makes the adversarial review's highest-value check a permanent regression —
it asserts the BP integrator cap is **68nF (→400Hz)**, and explicitly contrasts the **47nF copy-trap
(→582Hz)** so a future cap-value slip fails CI.

## Gate promoted to BLOCKING
- `.github/workflows/build.yml`: removed the advisory `|| ::warning::`; `build_spice.py --check` now
  fails the build on any assertion miss. Still skips cleanly (exit 0) if ngspice is unavailable on a
  given runner, so the gate degrades gracefully rather than blocking on a missing tool.

## Coverage status (per block)
- ✅ Covered: A, 1, 3, 4, 5, 6 (svf1 f_ref + dist1 clip + mix normal), 7, 8.
- ⚪ Not yet (acceptable — no distinct analog law beyond what's covered): block-2 (LFO rate — a
  time-domain oscillator; deck deferred), block-B (output buffers — same unity-follower physics as
  block-A's `input_clamp`), block-6 svf2/svf3/dist2/dist3 (identical to svf1/dist1 — one representative
  deck per repeated topology). These are documented as intentionally-representative, not gaps.

## Verification
- `build_spice.py --check` → OK (15 decks). `--list` shows coverage across 8 block dirs.
- ngspice-absent path still SKIP/exit 0. Six existing `--check` gates + parity unaffected; build.yml valid.

## Decisions log
- 2026-05-31: one representative deck per *repeated* topology (svf1/dist1 stand for svf2-3/dist2-3;
  block-A clamp stands for block-B) — covers the distinct physics without redundant fixtures.
- 2026-05-31: gate promoted to blocking now that every distinct sub-circuit has a passing deck.
- 2026-05-31: block-2 LFO (time-domain rate law) deck deferred — not a static-bias/level law like the
  rest; worth its own transient deck later if needed.

## Gate checklist
- [ ] CI green on the branch (SPICE gate now blocking)
- [ ] PR `change/0023-spice-coverage` → `dev`
