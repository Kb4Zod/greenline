# 0011 — Committed synthetic fixtures: a narrow, explicit whitelist

**Date:** 2026-06-12

## Decided

Tests and demos need CSVs in the repo, but `.gitignore` blocks `*.csv` globally
(decision 0001). Resolution: a single, deliberately narrow exception —

```
!backend/tests/fixtures/synthetic_*.csv
```

Rules that keep this safe:

1. Only files matching `synthetic_*.csv`, only in that one directory. Never
   widen this to a directory wildcard.
2. Fixture content must be **obviously fake on sight**: fake institution
   ("General Bank"), fake merchants, fake employer, round numbers where it
   helps. Anyone glancing at the file should know it's not a real statement.
3. Hugh's `Seed Data/` folder stays git-ignored even though its current
   contents are synthetic. By *shape* it's a bank-export drop folder, and the
   habit we're protecting is "downloaded statements are never committable" —
   no exceptions that depend on a human remembering which folder is safe.
   Committed fixtures are *copies*, renamed into the whitelisted path.

## Why

Two bad alternatives:
- No committed fixtures → tests would synthesize CSVs in code, demos would have
  nothing to import. Workable but the demo/import path goes untested in a
  realistic way.
- Whitelisting `Seed Data/` directly → trains the reflex that some statement
  folders are committable. That reflex is the thing 0001 exists to kill.

The `synthetic_` filename prefix doubles as a content contract: if a file in
that path isn't fake, its name is lying, which is easy to spot in review.

## Status

Active.
