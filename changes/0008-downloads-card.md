# Change 0008: add a plugin downloads card (Actions builds)

- **Slug:** downloads-card   **Branch:** `change/downloads-card`
- **Lane:** C (docs only)
- **Status:** OPEN   **Blocks:** none   **Boards:** n/a
- **Opened:** 2026-05-29   **Closed:** —   **PR:** —

## Intent

Surface the Linux / Windows / macOS `.vcvplugin` builds from the docs landing page, pointing at
the actual CI runs that produced them (no stale/manual copies).

## Summary

- `docs/index.html`: new **Plugin Builds** card → the "Build VCV Rack Plugin" Actions workflow
  (`actions/workflows/build.yml`) — pick the latest green run → Artifacts → `POGO-linux-x64` /
  `POGO-win-x64` / `POGO-mac`. Notes the GitHub-login + ~30-day-retention caveat.
- `docs/ci.html`: link the word "artifact" to the same Actions page.

## Decisions log

- 2026-05-29: GitHub Actions artifacts have no stable public URL (login + ~30-day expiry), so the
  card links to the workflow runs (the builds themselves) rather than deep-linking a file. (Public
  permanent downloads would need GitHub Releases — deferred.)

## Verification

Docs-only; pages well-formed; `--check` gates unaffected.
