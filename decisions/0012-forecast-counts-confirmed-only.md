# 0012 — Two M1 judgment calls: confirmed-only forecast, income shown but not counted

**Date:** 2026-06-12

## Decided (during the M1 build)

1. **Only user-confirmed bills move the forecast.** Detected drafts show up as
   an amber "N detected bills await review" nudge on the check-in view, but
   contribute $0 to required cash until confirmed.
2. **Expected income is displayed ("Next payday: Fri Jul 10 · ~$4,000") but
   does not affect the covered/tight/shortfall status in M1.** Status compares
   cash on hand against required cash, full stop.

## Why

On (1): the PRD says detection is a draft and the user is the source of truth.
The alternative — counting high-confidence drafts immediately — gives a
non-empty forecast on first run, which is tempting. But then "required cash"
contains numbers the user never vouched for, and the first thing the app does
is assert something it might be wrong about. Trust is the product. The cost is
an extra step in the first-run flow; the review nudge makes that step obvious.

On (2): the whole point is "will I have enough cash for what's coming *before*
money arrives." Letting an expected-but-unarrived paycheck flip a red status
to green is exactly the optimism the app exists to kill. The PRD's "cash room"
(which does include expected income) arrives with M4, where it's a separate,
clearly-labeled number — not a blended status.

Honest uncertainty: (2) might feel too conservative once real use starts — a
payday tomorrow plus rent in five days will read "shortfall" today even though
it's fine. If that grates in practice, revisit with a new entry; the income
figure is already computed and displayed, so the change would be small.

## Status

Active for M1. Both are spec'd in SPEC-M1 §6.
