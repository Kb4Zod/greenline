# 0005 — Account scope: checking + savings for the MVP

**Date:** 2026-06-12

## Decided

The MVP tracks **checking and savings only.** Credit cards and other account types are deferred to a later phase. The data model is built to accept them without a rewrite.

## Why

- Keeps the MVP's "cash on hand" definition simple and unambiguous: real cash in checking + savings.
- Credit cards introduce a genuinely different modeling problem — a card purchase is *spend now, bill later* — which is a future obligation, not current cash. Worth doing, but it muddies the MVP's core question ("can I cover what's coming?"). Better to nail the cash case first.

## Forward note (don't lose this)

When credit cards arrive, there's a whiff of double-entry thinking — the same purchase is an expense *and* a future liability. We are **not** adopting double-entry to handle it (see 0007). We'll model the card balance as a forecasted future bill. Keeping that line clean is why account scope is being staged deliberately rather than thrown in all at once.

## Status

Active for MVP; revisit when adding accounts.
