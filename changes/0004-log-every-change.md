# Change 0004: log every change + PR-title slug convention

- **Slug:** log-every-change   **Branch:** `change/log-every-change`
- **Lane:** C (process/docs — no DSP / panel / components / nets connectivity)
- **Status:** OPEN   **Blocks:** none   **Boards:** n/a
- **Opened:** 2026-05-29   **Closed:** —   **PR:** —

## Intent

Make `changes/` a complete audit trail. Two process refinements (noticed because the Lane C
README + CI-artifact changes left no record in `changes/`):

1. **Every change gets a `changes/NNNN-<slug>.md`** — drop the Lane C exemption. Lane C uses
   the minimal one-liner form. The file is committed as the **first commit on the branch,
   before the PR is opened**.
2. **PR title format `NNNN-slug: summary`** — ties a PR to its branch + change file at a glance.

## Summary

- `CLAUDE.md` "Git Workflow & Change Process": "Every non-trivial change" → "Every change";
  added the first-commit-before-PR rule + the PR-title convention; Lane C row now requires a
  minimal change file (was "no change file").
- `changes/_TEMPLATE.md`: updated the Lane C note accordingly.
- **Backfilled** the two missing records from the prior (Lane C) changes:
  `changes/0002-readme-refresh.md` (PR #25) and `changes/0003-publish-hw-artifacts.md` (PR #26).

## Decisions log

- 2026-05-29: Log every change incl. Lane C (minimal form), committed before the PR.
- 2026-05-29: PR title = `NNNN-slug: summary`.
- 2026-05-29: Enforcement stays honor-system; a CI gate requiring `change/**` diffs to touch
  `changes/` remains an optional future add (with the deferred `check_locked`/`check_drift`).

## Verification

Docs-only; the five `--check` gates are unaffected (spot-checked green).
