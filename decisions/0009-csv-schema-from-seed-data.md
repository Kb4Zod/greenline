# 0009 — CSV schema: adopt the "General Bank" seed-data layout

**Date:** 2026-06-12

## Decided

The M1 import parser is designed against the column layout of the synthetic seed
statements Hugh provided (three months, April–June 2026, "General Bank"):

```
Transaction ID, Posted Date, Description, Category, Debit, Credit, Amount, Balance, Account Name, Institution
```

Key properties we observed and are building on:

- **`Transaction ID`** is present and unique per row (`GB-YYYYMM-NNNN`). This is a
  gift for dedup — a stable bank-side identifier. We use it as the primary dedup
  key **when present**, with a content-hash fallback (date + amount + normalized
  description + account) for banks that don't provide one.
- **`Amount`** is signed (debits negative, credits positive); `Debit`/`Credit` are
  redundant unsigned columns. We treat `Amount` as authoritative and use
  Debit/Credit only for validation.
- **`Posted Date`** is ISO `YYYY-MM-DD`. No time component.
- **`Balance`** is a running balance after each row — usable to derive
  cash-on-hand from the most recent transaction, and as an import sanity check.
- **`Category`** comes pre-populated. Convenient, but we do NOT assume every bank
  provides it; the parser treats it as optional enrichment.
- One account per file (`Everyday Checking`); `Account Name` + `Institution`
  identify it.

## Why

Per HANDOFF §8.3 we were forbidden from inventing a schema. Hugh provided seed
files in `Seed Data/` (git-ignored — it's a bank-export drop folder by shape,
even though these particular files are synthetic). The layout is now real input,
not a guess.

## Honest caveats

- These are **synthetic** statements. The real bank's export may differ —
  different headers, MM/DD/YYYY dates, no Transaction ID, quoted commas. That's
  exactly why the parser sits behind the format-agnostic `StatementParser`
  interface (decision 0003): a real-bank layout becomes a second parser, not a
  rewrite.
- Seed paychecks are a constant $4000.00 biweekly. Decision 0004 says income
  amount is *variable* — the trailing-average model still applies; the seed data
  just won't exercise the variance until realistic data shows up.

## Status

Active for M1. Revisit when the first real (scrubbed) export appears.
