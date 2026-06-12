# Changelog

What shipped, by milestone. The *why* lives in `decisions/`.

## [0.1.0] — 2026-06-12 — Milestone 1: Cash Flow Forecast (unreleased)

First working build. Local-only; nothing published yet.

### Added
- CSV statement import behind a format-agnostic parser interface
  (General Bank layout), with row-level validation — bad rows abort the batch.
- Idempotent re-import: dedup on bank transaction ids with a content-hash
  fallback; import history with added/duplicate receipts.
- Recurring-bill detection (cadence + amount-stability) producing drafts the
  user confirms, dismisses, edits, or supplements manually.
- Income-stream detection with trailing-average expected amount and next
  payday projection.
- Required-cash forecast over 7/14/30-day windows with covered/tight/shortfall
  status; only confirmed bills count.
- Check-in UI (cash on hand, window cards, due-bill basis, payday line),
  bills review UI, import UI.
- Privacy guardrails: data-blocking `.gitignore` from commit #1, data dir
  outside the repo tree, `scripts/check_hygiene.py` scanner.
