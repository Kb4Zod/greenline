# 0006 — Variable-forecast trust bar: ~10%, but honest while learning

**Date:** 2026-06-12

## Decided

The variable-cost forecast (food, gas, dining, etc.) targets **within ~10% of actuals** — but only as a **matured** target, after roughly 6–8 weeks of history. Before that, the UI always shows the **confidence / basis** of an estimate and never presents a thin estimate as if it were certain.

## Why

Hugh wants tight — within ~10%. Fair, that's the bar for actually trusting the "cash room" number enough to act on it.

But I pushed back on one thing: **10% is impossible at cold-start.** Week one has almost no history to estimate from; any number that confident would be a lie. So we don't promise 10% from day one — we promise it *after the model has data*, and in the meantime we're honest about how shaky the estimate is.

This is why the forecast UI must visibly separate **scheduled bills (high confidence)** from **estimated variable spend (lower, improving confidence)** rather than blending them into one opaque number. Trust comes from showing the seams, not hiding them.

## Status

Active. Spec defines the exact estimation window and how "confidence" is computed and surfaced.
