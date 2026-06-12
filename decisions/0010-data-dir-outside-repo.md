# 0010 — Live data lives in the user profile, outside the repo tree

**Date:** 2026-06-12

## Decided

The live SQLite DB and any import staging default to a **per-user app-data
folder outside the repo**:

- Windows: `%LOCALAPPDATA%\Greenline`
- macOS/Linux: `~/.greenline`

Overridable via `GREENLINE_DATA_DIR` in `.env` (git-ignored). Nothing the app
writes at runtime ever lands inside the repo tree by default.

## Why

PRD §14 said "ideally outside the repo tree" and Hugh confirmed the
user-profile option when asked. The alternative — a git-ignored `data/` folder
inside the repo — is more discoverable but leaves the failure mode open where a
`.gitignore` edit (or an over-eager `git add -f`) exposes real data in a public
repo. Physically outside the tree, there is nothing for git to see. For a
public-repo finance app that asymmetry decides it.

Cost: slightly harder to find the DB for manual backup. Mitigation: the app
surfaces the data-dir path in its settings/about output, and the path is
documented in `.env.example`.

## Status

Active.
