# 0004 — Income model and cadence

**Date:** 2026-06-12

## Decided

- **Income:** regular *timing*, **variable amount.** Pay schedule is known/detected; the amount is estimated from a **trailing average of recent paychecks**, re-fit weekly.
- **Cadence:** **Friday** is the check-in ritual; **savings/contribution recommendations align to actual payday.**

## Why

- Hugh's income lands on a predictable schedule but the amount moves. So we can't hardcode an income number — we estimate it, using the same weekly learning loop we use for variable costs. Nice symmetry: income and variable spend are both "known-ish, estimated, sharpened over time."
- On cadence: the original idea was "every Friday." But the *payoff* number — "set aside $X" — only makes sense when cash actually arrives. So we split it: Friday keeps the habit loop alive (trigger → glance → reward), while the money recommendations key off payday so they're actionable when there's actually money to move.

## Note

This means the forecast engine treats expected income as another estimated, confidence-bearing quantity — not a fixed input. Spec needs to define the trailing-average window (how many recent paychecks) and how it handles an off-schedule or missing paycheck.

## Status

Active.
