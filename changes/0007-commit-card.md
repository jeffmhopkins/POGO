# Change 0007: make "what happens on commit" a card (docs/ci.html)

- **Slug:** commit-card   **Branch:** `change/commit-card`
- **Lane:** C (docs only)
- **Status:** OPEN   **Blocks:** none   **Boards:** n/a
- **Opened:** 2026-05-29   **Closed:** —   **PR:** —

## Intent

The "What happens when you commit" content (added in 0006) was an inline section on the docs
landing page; it should be a card like the others. Move it to its own page and link a card to it.

## Summary

- `docs/ci.html` (new): the commit/CI pipeline explainer (five `--check` gates, cross-platform
  plugin builds, published artifacts, PR/merge flow).
- `docs/index.html`: remove the inline `commit` section (+ its CSS); add a **"What Happens on
  Commit"** card → `ci.html`.

## Verification

Docs-only; pages well-formed; `--check` gates unaffected (spot-checked green).
