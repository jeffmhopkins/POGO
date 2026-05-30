# 0019 — Documentation staleness sweep + design-review refresh

- **Lane:** B/C hybrid — primarily documentation; touches `specs/components.yaml` (complete 4
  unassigned trim parts) + `tools/build_components.py` (manifest source list). No plugin/panel/DSP
  or net-connectivity change. Plugin remains the locked ground truth.
- **Status:** OPEN
- **Opened:** 2026-05-30
- **Branch:** `change/0019-doc-staleness-refresh` off `dev`

## Intent

Post-0018, do a thorough markdown-staleness sweep across all live docs and re-perform the analog
design review (it had drifted to a 2026-05-27 pre-0018 snapshot). Also rework the README signal-chain
ASCII for readability. Triggered by: README ASCII hard to read + "do a full md staleness search."

## Scope / what changed

**README.md** — rewrote the signal-chain ASCII (cleaner left-aligned flow + correct BP range
~50 Hz–3.2 kHz / F_REF 400 Hz); fixed: 5→6 `--check` gates, 476→700+ components, gen_block6 removed,
block-6 split (7 sheets, `--block` example), docs/ artifacts (netlist.html etc.), 18-attenuverter+VCA.

**CLAUDE.md** — signal-chain box (two-scaler mix, per-band DIST_MODE, dist-before-SVF, 400 Hz,
ALT→VCA→BP3); modulation section (MOD_SRC switch, lights = LFO1/2 + BP1-3_CLIP, 18+VCA); gen_block6
superseded note; block-6 nets split exception; 5→6 gates (×2).

**Regenerated from plugin (full):** `docs/plugin-topology.md` — was a pre-implementation design doc
(42/46 params, 200/1500/6000 Hz, BP_MIX crossfade, MOD_CLIP/POS/NEG lights, dist-after-SVF). Now
authoritative against the shipped plugin: 53 params / 24 inputs / 6 outputs / 5 lights; two-scaler
BP_BYPASS+BP_WET; F_REF 400; per-band DIST_MODE; dist-before-SVF; MOD_SRC; RES÷10; BP3 prevOut[2]+normal.

**Re-performed design review (analysis + adversarial agents):**
- `specs/analog-design-review.md` — fresh device census, power budget (~326 mA/rail, recommend
  ≥400 mA bus; block-6 ~180 mA), trim inventory, parts sourcing (CD4053 EOL; THAT2180 ×10 THT
  single-source), noise allocation. Supersedes the 2026-05-27 snapshot.
- `specs/component-verification-report.md` — 718 rows (was 476), per-board ref-uniqueness, registry/
  footprint/datasheet coverage, all 6 gates pass.

**Aux library** — lifted stale STALE banners + fixed: aux-distortion (dist-before-SVF, per-band mode,
DRIVE VCA, no oversampling), aux-unity-buffer (HP = unity G=+1 follower, not G=−1), aux-cv-protection
(ENV OUT → BP3_R normal), aux-lfo-core (breathing-LED art), aux-vca-cell (SIP-8, not A14-U).

**Block specs** — block-5 line-ref drift; block-6 §2 superseded-banner + worst inline remnants
(global DIST → per-band; BP_MIX → two-scaler); block-7 "G=−1" → unity follower.

**STATUS.md / module-overview.md / layout-notes.md** — date, counts (476→718, 5 lights, 6 TL074,
4 THAT2180), MOD_SRC, removed MOD-bus LEDs, refreshed power table, aux-status rows.

**GENERATED.md + tools/build_components.py** — manifest source list referenced the deleted
`specs/block-6/block-6.nets.yaml` / `gen_block6.py`; replaced with the `docs/netlist.html` row;
regenerated GENERATED.md.

**specs/components.yaml** — assigned the 4 unassigned Q_max trims (RV9/RV12/RV15/RV21 →
`Bourns 3224W, 100kΩ`, matching RV5/RV18); BOM regenerated.

## Verification

All 6 `--check` gates + Python↔JS parity green. No plugin/panel/net-connectivity change.

## Decisions log

- 2026-05-30: README ASCII reworked for readability + full md staleness sweep (3 audit agents:
  root/tools, specs/aux, plugin-topology/block-specs). (user)
- 2026-05-30: plugin-topology.md → **full regenerate** from the plugin (user choice).
- 2026-05-30: dated design-review/verification snapshots → **re-perform** with analysis +
  adversarial agents (user choice), not just re-date.
- 2026-05-30: completed the 4 unassigned audio-board Q_max trims to match their siblings (RV5/RV18).

## Gate checklist

- [x] Adversarial fact-check of the regenerated/refreshed docs — plugin-topology.md fully clean;
      fixed power-total arithmetic (per-block column → 329/323 mA, block-6 161 not 180) in
      analog-design-review.md + module-overview.md; fixed verification-report nits (35 repeated
      refs not 37; "9 bindings / 4 libraries" wording).
- [x] All 6 `--check` gates + parity green on the branch (local).
- [ ] CI green on the branch (Actions)
- [ ] PR `change/0019-doc-staleness-refresh` → `dev`
