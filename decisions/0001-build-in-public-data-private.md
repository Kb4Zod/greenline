# 0001 — How we work: built in public, data stays private

**Date:** 2026-06-12

## Decided

1. Greenline is developed **entirely in a public repository, from the first commit.**
2. Because of that, a hard rule: **no secrets and no real financial data ever get committed.** Public *code*, private *data*.
3. The repo carries this `decisions/` journal — chronological, dirty-by-design, distinct from ADRs and the changelog.

## Why

This is one of our first fully-build-in-public repos. Building in public is good for accountability and for showing the actual process — but personal finance data is exactly the kind of thing that must never leak. So the privacy posture can't be an afterthought bolted on later; it has to be true from commit #1.

The decision journal exists because "build in public" should include the *thinking*, not just the code. A clean repo hides the reasoning. We want the reasoning visible and honest — including the parts where we weren't sure.

## How we enforce the no-data rule (to be detailed in the Spec)

- `.gitignore` blocks data/secret patterns from the first commit (`*.csv`, `*.sqlite`, `*.db`, `.env`, etc.).
- Only **synthetic / obviously-fake** sample data is committed, for tests and demos.
- The live SQLite DB and any imported files default to a git-ignored path (ideally outside the repo tree).
- A committed `.env.example` documents config shape with no real values.
- Recommended: a pre-commit secret/data scan so this is a guardrail, not just a habit.

## Status

Active. This governs every later decision.
