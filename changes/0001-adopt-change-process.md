# Change 0001: adopt the per-change process

- **Slug:** adopt-change-process     **Branch:** `change/adopt-change-process`
- **Lane:** C (process/docs — no DSP, panel, components, or nets connectivity touched)
- **Status:** OPEN
- **Blocks:** none                    **Boards:** n/a
- **Opened:** 2026-05-29              **Closed:** —
- **PR:** —                           **CI run:** —

> First change under the new process — also the worked example of a Lane C change file.
> Lanes & gates: `CLAUDE.md` → "Git Workflow & Change Process".

## Intent

Define and adopt a gated, plugin-first, one-change-per-branch process so future changes
follow a consistent path (intent → plugin+panel → verify → lock → spec → topology →
schematic → close), and reconcile the docs that contradicted it.

## Scope / Out of scope

**In:** rewrite the CLAUDE.md "Git Workflow" section into "Git Workflow & Change Process"
(3 lanes, Steps 0–8, gates G1–G6, invariants, 1R–6R-vs-Step note); add `change/**` to the
`build.yml` push trigger; add `changes/_TEMPLATE.md`; add this change file; point
`specs/STATUS.md` at the process and bump its date.

**Out (tracked follow-ups, by decision honor-system for now):** the enforcement tooling
`tools/check_locked.py`, `tools/check_drift.py`, and a boundary-net cross-sheet check.
No DSP, panel, components, or netlist connectivity changes.

## Decisions log

- 2026-05-29: Change file = persistent `changes/NNNN-slug.md` (ADR-style, never deleted).
- 2026-05-29: Process lives in CLAUDE.md + `changes/_TEMPLATE.md`.
- 2026-05-29: Build = CI produces `.vcvplugin`; user verifies in VCV Rack (no Rack-SDK in CI).
- 2026-05-29: Branch convention `change/<slug>` → PR to `dev` (squash-merge).
- 2026-05-29: Per-change steps renamed "Step 0–8" to avoid colliding with project Phase 1R–6R.
- 2026-05-29: Lock recorded as git **blob hashes** (survive squash-merge), not commit SHA.
- 2026-05-29: 3 lanes (A behavioral / B hardware-only / C trivial); Lane B = current
  schematic-transcription work (`SCHEMATIC-GEN-PLAN.md`).
- 2026-05-29: Enforcement = honor-system + the existing five `--check` gates now; the lock /
  drift / boundary-net CI gates are deferred to a follow-up change.
- 2026-05-29: Adversarial + review agents critiqued the draft; their findings folded in
  (CLAUDE.md "develop on dev" contradiction, CI trigger gap, lanes, the five-gate invariant,
  abandonment/version/footprint/boundary-net handling).

## Component additions

| ref | board | block | part | pkg | val | datasheet? | fn |
|-----|-------|-------|------|-----|-----|-----------|----|
| —   | —     | —     | —    | —   | —   | —         | none |

## Lock record

n/a (no plugin/panel change).

## Artifacts

- Docs: `CLAUDE.md`, `specs/STATUS.md`, `changes/_TEMPLATE.md`, `changes/0001-adopt-change-process.md`
- CI: `.github/workflows/build.yml` (added `change/**` push trigger)

## Notes / Phase-3R flags

Honor-system enforcement is explicit in CLAUDE.md's "Enforcement note." The deferred
`check_locked` / `check_drift` / boundary-net gates are the path to making the invariants
machine-enforced rather than discipline-enforced.
