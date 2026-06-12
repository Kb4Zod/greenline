# Decision Journal

A chronological record of every meaningful decision made on Greenline, **and the real reasoning behind it.**

## What this is

- A running log. Numbered sequentially (`0001`, `0002`, …), oldest first, newest last.
- The **why**, captured while it's fresh — not reconstructed later from memory.
- The place to look when someone (including future-us) asks *"why did we do it this way?"*

## What this is NOT

- **Not ADRs.** No rigid template, no "Proposed / Accepted / Superseded" ceremony, no formality tax. Lighter and more honest than that.
- **Not the changelog.** The changelog records *what shipped*. This records *why we chose it* — including choices that never produced a line of code.
- **Not documentation.** Docs describe the system as it is now, cleaned up. This is the opposite.

## Dirty by design

This folder is **not meant to be cleaned up.** That's deliberate.

- Entries are **not edited or polished after the fact.** What was written at the time stays.
- Dead-ends, second-guessing, abandoned ideas, and "we weren't sure but went with X" all stay in. The messy thinking *is* the value.
- **Reversals get a NEW entry**, referencing the old one. We never go back and rewrite history to look like we were right all along.
- Truthful beats tidy. If the reasoning was uncertain, the entry should read uncertain.

## Public-repo note

Greenline is built entirely in public. These entries are public too — so they can contain reasoning and tradeoffs, but **never real financial data, account numbers, or secrets.** (Same rule as the rest of the repo.)

## Format

Loose. A typical entry has a date, what was decided, and why, plus alternatives considered if relevant. Use whatever structure serves the truth of the moment; don't force it.

Filename: `NNNN-short-kebab-title.md`. Numbers are monotonic and never reused or renumbered.
