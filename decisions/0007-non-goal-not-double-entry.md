# 0007 — Non-goal: Greenline is not double-entry accounting

**Date:** 2026-06-12

## Decided

Greenline is explicitly **not** a double-entry accounting system. Transactions are a simple one-sided list (date, amount, category, account). No debit/credit pairs, no chart of accounts, no books-must-balance constraint.

## Why

Greenline forecasts cash; it doesn't keep auditable books. The only question it serves is "what's coming and can I cover it." That needs a flat transaction list, nothing more.

Double-entry would mean a heavier data model and a pile of accounting machinery (journals, ledgers, reconciliation) that adds **zero** value to a forecast — while pulling against the "one glance answers the question" UX principle. It would slow the build and complicate the UI to support reporting nobody asked for.

Writing this down now as a guardrail: projects like this quietly drift toward "well, while we're here, let's make the books correct…" That drift is what this non-goal exists to stop.

## Boundary

If real tax-grade books or formal financial statements are ever needed, that's a *different tool's* job. The credit-card case (0005) gets the closest to double-entry flavor, and we still won't adopt double-entry to handle it.

## Status

Active. This is a firm non-goal, not a "maybe later."
