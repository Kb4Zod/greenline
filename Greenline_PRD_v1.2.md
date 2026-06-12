---
title: "Greenline — Cash Flow Forecasting App"
subtitle: "Product Requirements Document (PRD)"
doc_type: prd
version: 1.2
status: decisions-locked
owner: Hugh
created: 2026-06-12
updated: 2026-06-12
codename: "Greenline (working name — rename later)"
built_in_public: true
---

# Greenline — Product Requirements Document (v1.2)

> **Status:** Decisions locked, ready for Spec. This is step 1 of 3 (PRD → Spec → Build).
> The goal here is to lock *what* we're building and *in what order*, not *how*.
> Implementation detail is deliberately held back for the spec document.
> *Working codename "Greenline" — rename with a find-and-replace later.*

---

## 1. Summary

Greenline is a **local-first personal cash-flow app**. Its single organizing question is:

> *"Given the bills coming up, how much cash do I actually need — and how much can I safely move toward my goals?"*

Each Friday the app runs a check-in (the habit ritual), and **savings/contribution recommendations are aligned to your actual payday**, across rolling **7-, 14-, and 30-day** windows. It learns from imported bank history, gets sharper every week as new history is added, estimates the variable costs you *haven't* spent yet (food, gas, etc.), and eventually tells you a single number per goal: *put this much away to stay on track.*

The product is built in layers (milestones), each one shippable and useful on its own.

---

## 2. Problem statement

Most budgeting apps are **backward-looking ledgers** — they tell you what you already spent. They're bad at the question that actually causes stress: *will I have enough cash for what's coming before my next paycheck clears?*

People end up either (a) over-conservative, hoarding cash they could be saving/investing, or (b) caught short by a cluster of bills they forgot were due. Variable spending (groceries, fuel, eating out) makes the math worse because it's never the same twice.

Greenline targets that gap: **forward-looking, cash-on-hand-aware, variable-cost-estimating** forecasting with a weekly cadence that fits real pay cycles.

---

## 3. Goals & non-goals

### Goals
- Predict cash required for **upcoming bills** over 7/14/30-day windows.
- Improve forecast accuracy automatically as more weekly history is imported.
- Estimate **not-yet-incurred variable costs** and fold them into the forecast.
- Turn forecasts into a **savings recommendation per goal**, refreshed every Friday/payday.
- Stay **100% local** — the user's financial data never leaves their machine.
- **Built entirely in public** — public code, private data; no secrets or real financial data ever committed.
- Frontend that is **scannable, low-friction, and habit-forming** (weekly "check-in" ritual).

### Non-goals (at least for v1.0)
- No direct bank API / Plaid / Open Banking connection (manual import only — see §8).
- No bill *payment* execution. We forecast and recommend; we don't move money.
- No multi-user / household sharing, no cloud sync, no mobile-native app.
- No investment portfolio tracking or tax features.
- Not a full double-entry accounting system.

---

## 4. Target user

Primary user is **you (Hugh)** first, then "a financially-literate individual who wants to optimize cash deployment." Comfortable downloading bank statements, motivated by a weekly ritual, wants clarity not hand-holding. Single household / individual finances.

---

## 5. Core concepts & terminology

| Term | Meaning |
|---|---|
| **Cash on hand** | Current known balance(s) across imported accounts. |
| **Known bill** | A recurring, predictable obligation (rent, utilities, subscriptions, loan payments). Detected from history or entered manually. |
| **Variable cost** | Recurring-in-aggregate but irregular spend (groceries, gas, dining). Estimated, not scheduled. |
| **Forecast window** | A rolling horizon: 7, 14, or 30 days forward from "today." |
| **Required cash** | Sum of known bills + estimated variable costs landing inside a window. |
| **Cash room** | Cash on hand + expected income − required cash, over a window. The "safe to allocate" number. |
| **Goal** | A target amount + target date the user wants to save toward. |
| **Weekly check-in** | The Friday/payday ritual: refresh forecast, show required cash + cash room + per-goal recommendation. |

---

## 6. Product principles (UX)

These constrain every milestone's frontend.

1. **One glance answers the core question.** The home view shows required cash and cash room for the active window above the fold, no scrolling, no menu-diving.
2. **Scannable over comprehensive.** Big numbers, color-coded status (green = covered, amber = tight, red = shortfall), progressive disclosure for detail.
3. **Designed to be returned to.** The weekly check-in should feel rewarding: streaks, "you're on track for N of M goals," visible momentum on goals. Habit loop = trigger (Friday) → action (import + glance) → reward (clarity + progress).
4. **Fast.** Local app; every interaction should feel instant. No spinners on core views.
5. **Trustworthy with numbers.** Always show the *basis* for an estimate on demand (what history it came from), so the user can trust the forecast.

---

## 7. Milestones

Built so each milestone **ships a usable product**, not scaffolding. Order is strict — each depends on the prior.

---

### Milestone 1 — Cash Flow Forecast (Core MVP)

**Objective:** From imported bank history, forecast the cash needed to cover *known bills* over 7/14/30 days, and surface whether the user is covered.

**In scope**
- Import bank account history via file (CSV, and OFX/QFX if feasible — see §8).
- Parse transactions; store accounts, balances, transactions locally.
- Detect **recurring known bills** from history (same/similar payee + cadence + amount).
- Allow manual add/edit/confirm of bills (the user is the source of truth; detection is a draft).
- Compute **required cash** for each window from scheduled bills.
- Home "check-in" view: cash on hand, required cash (7/14/30), covered / tight / shortfall status.
- Weekly re-import flow that merges new transactions without duplicating.

**Out of scope (this milestone)**
- Variable-cost estimation, goals, budgeting.

**Success criteria**
- User imports 2–3 months of history and sees correctly identified recurring bills with ≥ ~80% precision on obvious recuratives (rent, known subscriptions).
- 7/14/30-day required-cash numbers reconcile against a manual spot-check.
- Second weekly import adds only new transactions (zero duplicates).

**Dependencies:** none (this is the foundation).

---

### Milestone 2 — Variable Cost Estimation

**Objective:** Estimate the costs the user *will* incur but hasn't yet (groceries, gas, dining, etc.) and fold them into the forecast.

**In scope**
- Transaction **categorization** (rules + history; user can correct, corrections persist).
- Per-category **variable spend model** (e.g., trailing average / weekly run-rate per category).
- Project variable spend into the 7/14/30 windows and add to required cash.
- **Estimate vs actual tracking**: as new history arrives, compare predicted variable spend to what actually happened; refine the model.
- Forecast view now distinguishes *scheduled bills* (high confidence) from *estimated variable* (lower confidence), visually.

**Out of scope:** goals, budgeting targets.

**Success criteria**
- **Matured target:** once ~6–8 weeks of history exist, variable-cost projection for a window lands **within ~10% of actuals**.
- **Cold-start honesty:** before that, the UI always shows the *confidence/basis* of an estimate (how much history it's built on) and never presents a low-confidence number as if it were certain. Accuracy ramps as data accumulates.
- User-corrected categories stick and improve future categorization.

**Dependencies:** M1 (transactions, windows, forecast engine).

---

### Milestone 3 — Budgeting & Planning

**Objective:** Let the user set intentional targets per category and plan against the forecast, instead of only observing.

**In scope**
- Set **budget targets** per category/period.
- Plan view: planned vs estimated vs actual, with variance.
- Adjust the forecast based on *intended* behavior (e.g., "I'm capping dining at $200 this month").
- Surface where the plan conflicts with the forecast (you've budgeted more than your cash room allows).

**Out of scope:** goal-based savings recommendations (next milestone).

**Success criteria**
- User can set a budget and see, on the check-in view, whether they're tracking to it.
- Budgets feed back into required cash / cash room calculations.

**Dependencies:** M1, M2.

---

### Milestone 4 — Goals & Savings Guidance

**Objective:** The payoff. Input goals; every Friday/payday, get told exactly how much to set aside per goal.

**In scope**
- Define **goals**: name, target amount, target date, priority.
- Compute **cash room** (cash on hand + expected income − required cash − budgeted spend).
- Allocate cash room across goals based on timeframe + priority → **per-goal weekly contribution**.
- Weekly check-in now ends with: *"Set aside $X toward [Goal A], $Y toward [Goal B] this week."*
- Goal progress tracking + projected completion date; warn if a goal is off-track given current cash room.
- Handle the constrained case gracefully (cash room < total needed → prioritize, show the shortfall honestly).

**Out of scope:** automated transfers (we recommend, user acts).

**Success criteria**
- Given goals + forecast, the app outputs a concrete, defensible per-goal contribution each week.
- Changing a goal's date or amount updates the weekly recommendation immediately.
- Progress and projected-completion update as contributions/actuals are recorded.

**Dependencies:** M1–M3.

---

## 8. Technical approach *(decided)*

> ✅ Locked during PRD review on 2026-06-12.

- **Architecture:** Local-first single-machine app. FastAPI backend service + local web UI, **opened in the browser at `localhost`**. Optionally Dockerized (matches the coffee-tracker precedent).
- **Backend:** Python + **FastAPI**.
- **Storage:** **SQLite** (single local file; easy to back up; no server).
- **Frontend:** **React (Vite) + Tailwind** for the scannable / habit-forming UI.
- **Bank data ingestion:** **CSV import only for the MVP.** Parser built behind a format-agnostic interface so OFX/QFX/QBO can be added later without rework. No Plaid / bank API — fully local.
- **Accounts (MVP):** **Checking + savings only.** Data model leaves room for credit cards and other account types in a later phase.
- **Income model:** **Regular timing, variable amount.** Pay schedule is known/detected; the *amount* is estimated from a trailing average of recent paychecks (re-fit weekly, same learning loop as variable costs).
- **Cadence:** **Friday check-in ritual; recommendations align to the user's payday.**
- **Packaging:** runs via `docker compose up` or a local launch script; opens at `localhost`.

---

## 9. High-level data model (conceptual)

Just the entities, not the schema (that's the spec):

- **Account** — name, type, current balance, source institution.
- **Transaction** — account, date, amount, raw description, category, import-batch id.
- **Bill** — payee, amount (or range), cadence, next due date, confidence, confirmed-by-user flag.
- **Category** — name, type (fixed/variable), estimation model params.
- **ImportBatch** — file, date imported, dedup key range (enables idempotent weekly imports).
- **Goal** — name, target amount, target date, priority, current saved, status.
- **Forecast snapshot** — window, required cash, cash room, generated-on date (for history/streaks).

---

## 10. Forecasting approach (conceptual)

Held light on purpose; the spec will pin the math.

- **Known bills:** schedule-based. Sum bills whose next-due falls inside each window.
- **Variable costs:** statistical. Per-category run-rate (trailing average, optionally day-of-week / month-phase aware) projected across window days.
- **Confidence layering:** the forecast is explicitly *bills (high confidence) + variable (estimated)*; the UI never blends them into one opaque number without letting the user see the split.
- **Learning loop:** each weekly import re-fits the variable models against newly-realized actuals → forecasts tighten over time. This is the core reason for the weekly ritual.
- **Cash room → goals:** cash room is computed first; goal allocation is a separate, transparent step the user can see and adjust.

---

## 11. Privacy & data handling

- **All data stays local.** No telemetry, no cloud, no third-party API calls with financial data.
- Local DB file is the single source of truth; user can back it up / delete it.
- Imported statement files are processed locally and can be discarded after import.

---

## 12. Decisions log (resolved 2026-06-12)

All v1.0 open questions are now resolved:

1. **Stack:** FastAPI + SQLite + React, opened in browser at `localhost`. ✅
2. **Bank export formats:** CSV only for MVP; parser built to extend to OFX/QFX/QBO later. ✅
3. **Income modeling:** Regular timing, **variable amount** → estimated via trailing average of recent paychecks, re-fit weekly. ✅
4. **Cadence:** **Friday** check-in ritual; **recommendations align to payday**. ✅
5. **Accounts:** **Checking + savings** for MVP; credit cards / other accounts deferred to a later phase (data model leaves room). ✅
6. **App name:** Working codename **"Greenline"**; final name TBD (find-and-replace later). ✅
7. **Variable forecast trust bar:** **~10% of actual** as the matured target (after ~6–8 weeks); confidence/basis always shown during cold-start. ✅
8. **Built in public:** developed in a public repo from commit #1; **no secrets or real financial data ever committed** (public code, private data). ✅
9. **Decision journal:** repo carries a `decisions/` folder — chronological, numbered, dirty-by-design, distinct from ADRs and the changelog. ✅

*Remaining detail (specific CSV column layouts from your bank, exact estimation window math, category taxonomy) is intentionally deferred to the Spec document.*

---

## 13. Out of scope / future ideas (post-v1)

- Direct bank linking (Plaid / Open Banking) as an *optional* convenience layer.
- Scenario / "what-if" planning ("what if rent goes up $200?").
- Anomaly alerts (unusual spend, a bill that didn't arrive).
- Mobile companion / native app.
- Multi-account household mode.
- Automated transfers to savings (execution, not just recommendation).

---

## 14. Built in public & repository hygiene

Greenline is developed **entirely in a public repository, from the first commit.** That makes one rule non-negotiable: **no secrets and no real financial data ever get committed.** Public *code*, private *data.*

This must be enforced by the build, not by good intentions:

- **No real bank data in the repo.** Imported CSVs, exported statements, the SQLite database file, and anything derived from real transactions are git-ignored.
- **Synthetic data only.** Tests and demos use clearly-fake sample data committed to the repo; real data never is.
- **No secrets in the repo.** Config, keys, and machine-specific paths live in environment variables or an untracked local config (`.env`, git-ignored). A committed `.env.example` documents the shape with no real values.
- **Data lives outside version control.** The live SQLite DB and user files default to a git-ignored path, ideally outside the repo tree.
- **Guardrails:** a `.gitignore` blocking data/secret patterns from commit #1, plus (recommended) a pre-commit secret/data scan.

This reinforces the local-first / no-telemetry stance in §11.

### Decision journal

The repo carries a top-level **`decisions/`** folder: a chronological, sequentially-numbered log of every meaningful decision and the *real* reasoning behind it — including uncertainty and abandoned ideas. It is **dirty by design**: entries are not polished or rewritten after the fact, and reversals get a new entry rather than edits to the old one. Distinct from ADRs (lighter, no ceremony) and from the changelog (what shipped, not why). See `decisions/README.md`. Decisions `0001`–`0008` already capture everything resolved in this PRD.

---

## Appendix A — Milestones at a glance

| # | Milestone | Core deliverable | Ships value as | Depends on |
|---|---|---|---|---|
| 1 | Cash Flow Forecast | Required cash for 7/14/30d from known bills | "Am I covered before my next pay?" | — |
| 2 | Variable Cost Estimation | Estimated future variable spend folded in | A *realistic* forecast, not just bills | M1 |
| 3 | Budgeting & Planning | Targets + planned/actual/variance | Intentional control, not just observation | M1, M2 |
| 4 | Goals & Savings Guidance | Per-goal weekly "set aside $X" | The payoff: forecast → action | M1–M3 |

---

*End of PRD v1.0 — review, answer §12, and the next artifact is the Spec.*
