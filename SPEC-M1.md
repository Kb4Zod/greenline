---
title: "Greenline — Milestone 1 Specification"
doc_type: spec
scope: "M1 — Cash Flow Forecast (Core MVP)"
prd: Greenline_PRD_v1.2.md
version: 1.0
status: active
owner: Hugh
created: 2026-06-12
---

# Greenline — M1 Spec: Cash Flow Forecast

This document turns PRD §7/M1 into implementable detail. Scope is **Milestone 1
only**: CSV import, idempotent dedup, recurring-bill detection with user
confirmation, required-cash forecast over 7/14/30-day windows, and the check-in
home view. Variable-cost estimation (M2), budgets (M3), and goals (M4) are out
of scope here, but the data model leaves room for them.

Decisions referenced: 0002 (stack), 0003 (CSV-only, format-agnostic), 0004
(income model, cadence), 0005 (checking+savings), 0009 (CSV schema), 0010
(data dir), 0011 (fixtures).

---

## 1. Architecture

```
browser (localhost:5173 dev / served bundle)        %LOCALAPPDATA%\Greenline
        │  JSON over HTTP                                    │
        ▼                                                    ▼
FastAPI app (127.0.0.1:8537)  ──SQLAlchemy──▶  greenline.sqlite3
  importing/   bills/   forecast/   income/
```

- **Backend:** Python 3.12+, FastAPI, SQLAlchemy 2.0, Pydantic v2,
  pydantic-settings for config, uvicorn. Tests: pytest + httpx.
- **Frontend:** Vite + React + TypeScript + Tailwind. Dev server proxies
  `/api` to the backend.
- **Storage:** single SQLite file in the data dir (decision 0010). The repo
  tree is never written to at runtime.
- **Config:** env vars / `.env` (git-ignored), names per `.env.example`. All
  user-visible naming reads `GREENLINE_APP_NAME` (decision 0008).

### Money is integer cents

All amounts are stored and computed as **integer cents** (`amount_cents`).
Floats never touch money. Parsing converts decimal strings via `Decimal`;
the API serializes cents as integers and the frontend formats for display.

---

## 2. Data model (SQLite)

Tables created by the app at startup (no migration tool at M1; schema version
recorded in a `meta` table for later).

### `accounts`
| column | type | notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT | e.g. "Everyday Checking" |
| institution | TEXT | e.g. "General Bank" |
| type | TEXT | `checking` \| `savings` (decision 0005; CHECK constraint left open for later types) |
| balance_cents | INTEGER | running balance from the most recent imported transaction |
| balance_as_of | TEXT (ISO date) | date of that transaction |
| UNIQUE(name, institution) | | account identity within an import |

### `import_batches`
| column | type | notes |
|---|---|---|
| id | INTEGER PK | |
| filename | TEXT | original filename only — never a full client path |
| imported_at | TEXT (ISO datetime) | |
| parser | TEXT | parser key, e.g. `general_bank_csv` |
| rows_total / rows_added / rows_duplicate | INTEGER | the idempotency receipt |
| date_min / date_max | TEXT | transaction date range in the file |

### `transactions`
| column | type | notes |
|---|---|---|
| id | INTEGER PK | |
| account_id | FK accounts | |
| batch_id | FK import_batches | provenance |
| posted_date | TEXT (ISO date) | |
| amount_cents | INTEGER | signed: debit < 0, credit > 0 |
| description | TEXT | raw, as imported |
| payee_key | TEXT | normalized description (see §4.1), indexed |
| category_raw | TEXT NULL | bank-provided category if any (M2 will build real categories) |
| balance_cents | INTEGER NULL | running balance from the file, for validation |
| dedup_key | TEXT UNIQUE | see §3.3 |

### `bills`
| column | type | notes |
|---|---|---|
| id | INTEGER PK | |
| account_id | FK accounts | |
| payee_key | TEXT | links to the transaction group that produced it |
| display_name | TEXT | user-editable, defaults to a cleaned payee name |
| amount_cents | INTEGER | median of observed amounts; user-editable |
| cadence | TEXT | `weekly` \| `biweekly` \| `semimonthly` \| `monthly` \| `quarterly` \| `annual` |
| next_due | TEXT (ISO date) | rolled forward on read (§4.3) |
| status | TEXT | `detected` (draft) \| `confirmed` \| `dismissed` |
| confidence | REAL | 0–1, detection confidence (§4.2) |
| source | TEXT | `detected` \| `manual` |
| occurrences | INTEGER | observations backing the detection ("basis", PRD UX principle 5) |
| last_seen | TEXT (ISO date) | most recent matching transaction |

### `income_streams`
| column | type | notes |
|---|---|---|
| id | INTEGER PK | |
| account_id | FK accounts | |
| payee_key | TEXT | |
| display_name | TEXT | |
| cadence | TEXT | same enum as bills |
| next_expected | TEXT (ISO date) | |
| trailing_avg_cents | INTEGER | mean of last N paychecks (§5) |
| occurrences | INTEGER | |
| status | TEXT | `detected` \| `confirmed` \| `dismissed` |

Forecast snapshots (PRD §9) are deferred to M2+ — nothing in M1 needs history
of forecasts yet, and we'd rather not invent the shape before streaks exist.

---

## 3. CSV import

### 3.1 Format-agnostic interface (decision 0003)

```python
class ParsedTransaction(BaseModel):
    external_id: str | None      # bank-side transaction id, if the format has one
    posted_date: date
    amount_cents: int            # signed
    description: str
    category_raw: str | None
    balance_cents: int | None
    account_name: str
    institution: str

class StatementParser(Protocol):
    key: str                                  # e.g. "general_bank_csv"
    def sniff(self, head: bytes) -> bool: ... # can this parser read the file?
    def parse(self, stream: IO[bytes]) -> ParsedStatement: ...
```

A registry tries `sniff()` in order; OFX/QFX/QBO later means adding a parser,
nothing else changes. M1 ships one parser: **`general_bank_csv`** (decision
0009 layout). Unknown layouts produce a clear "unsupported format" error
naming the headers we did find — never a silent wrong parse.

### 3.2 `general_bank_csv` parsing rules

- Required headers (exact, after BOM strip / whitespace trim): `Transaction ID,
  Posted Date, Description, Category, Debit, Credit, Amount, Balance,
  Account Name, Institution`.
- `Amount` is authoritative. If `Debit`/`Credit` disagree with it
  (`|amount| != debit+credit`), the row is rejected and reported — a wrong sign
  in a finance app is worse than a failed import.
- Dates must parse as `YYYY-MM-DD`.
- Account is upserted by `(Account Name, Institution)`; type defaults to
  `checking` (the seed data has no savings account yet; a savings import will
  need the user to set type — UI exposes it).
- Account balance/as-of update to the transaction with the latest
  `posted_date` (ties: last row wins, matching statement order).

### 3.3 Dedup — idempotent weekly re-import

`transactions.dedup_key` is UNIQUE; an import inserts rows whose key is new and
counts the rest as duplicates. Two key forms:

1. **Bank id (preferred):** `ext:{institution}|{account_name}|{external_id}`
   — used when the format provides a transaction id (General Bank does).
2. **Content hash (fallback):** `sha256(account|posted_date|amount_cents|payee_key|n)`
   where `n` is the row's occurrence index *within its own file* among
   identical `(date, amount, payee_key)` rows. Two genuinely identical
   same-day coffees in one statement both survive; re-importing the same
   statement matches them pairwise. Known honest limitation: if two *partial*
   exports each contain one identical-looking coffee, they merge — acceptable
   at M1, bank ids make it moot for the primary format.

The whole import is one DB transaction: a malformed row aborts the batch
(`rows_added = 0`, errors reported) rather than half-importing.

**Success criterion check (PRD M1):** re-importing any fixture file must yield
`rows_added == 0, rows_duplicate == rows_total`.

---

## 4. Recurring-bill detection

Runs automatically after every successful import; only re-evaluates groups,
never silently changes anything `confirmed` or `dismissed`. Detection is a
**draft**; the user is the source of truth (PRD M1).

### 4.1 Payee normalization

`payee_key` = description uppercased → store/sequence numbers stripped
(`#\d+`, trailing digit runs) → punctuation collapsed → whitespace collapsed.
`"CHEVRON #1419"` and `"CHEVRON #1515"` → `CHEVRON`. The raw description is
always preserved on the transaction.

### 4.2 Detection algorithm (debits only)

For each `(account, payee_key)` group with ≥ 3 occurrences:

1. **Intervals:** day gaps between consecutive posted dates. Median interval
   snaps to a cadence: 5–9 → weekly, 12–16 → biweekly, 13–17 with two fixed
   days-of-month → semimonthly, 26–35 → monthly, 80–100 → quarterly,
   330–400 → annual. No snap → not a bill.
2. **Regularity:** fraction of intervals within tolerance of the snapped
   cadence (tolerance: ±2d weekly/biweekly, ±4d monthly, ±10d quarterly+).
3. **Amount stability:** coefficient of variation of amounts. CV ≤ 0.15 →
   stable; 0.15 < CV ≤ 0.35 → loose; CV > 0.35 → rejected (that's variable
   spend — M2's job, not a bill). This is what keeps groceries and fuel out
   of the bill list even when they're weekly-ish.
4. **Confidence:** `0.5·regularity + 0.3·amount_stability + 0.2·min(occurrences/6, 1)`,
   shown in the UI as the basis ("seen 3× monthly, ±$0.00").
   Confidence < 0.5 → discarded, not even drafted.
5. **Draft bill:** amount = median observed; `next_due` = last occurrence +
   cadence length.

Re-detection updates draft bills in place (new occurrences sharpen amount/
next_due) and creates new drafts; it never resurrects a `dismissed` payee.

### 4.3 Next-due roll-forward

On every read, `next_due < today` rolls forward by whole cadence periods until
≥ today. Calendar-aware for monthly+ (anchored to day-of-month, clamped to
month end: Jan 31 → Feb 28). A confirmed bill whose payee has produced no
matching transaction for 2 full cadence periods is flagged `stale` in API
output (not auto-dismissed).

### 4.4 Manual bills

`POST /api/bills` with name, amount, cadence, next_due, account →
`source=manual, status=confirmed, confidence=1.0`. Manual add/edit/confirm is
in M1 scope per the PRD.

---

## 5. Income model (decision 0004)

Same grouping as §4.2 but over **credits**, with a looser amount-stability gate
(income is variable-amount by decision): cadence must snap and regularity ≥
0.6; amount CV is not a rejection criterion.

- **Expected amount** = trailing average of the most recent
  `GREENLINE_INCOME_TRAILING_N` paychecks (default **4**), re-fit on every
  import — the weekly learning loop.
- **Next expected** = last paycheck + cadence, rolled forward like bills.
- **Missing paycheck:** if `next_expected` passes with no matching credit
  within a 3-day grace window, the stream is flagged `overdue` in the API and
  the UI shows it; the forecast stops assuming that occurrence (it is *not*
  counted in any window until it actually posts). Honest > optimistic.

M1 uses income for display and the "next payday" line. It is deliberately
**not** added into the M1 coverage status (§6.3) — see the design note there.

---

## 6. Forecast engine

### 6.1 Inputs

- `cash_on_hand` = Σ `accounts.balance_cents` (checking + savings).
- **Confirmed bills only.** Draft detections do not move the forecast; instead
  the check-in view shows "N detected bills awaiting review" until triaged.
  Rationale: a number the user hasn't vouched for must not silently change
  "required cash" — trust comes from the user having confirmed the inputs
  (PRD UX principle 5). The review flow is part of the first-run ritual.

### 6.2 Required cash per window

For each window `w ∈ {7, 14, 30}` days from `today` (inclusive of both ends):
enumerate each confirmed bill's due occurrences inside the window (a weekly
bill can land 2–5 times in a 30-day window — count each) and sum amounts.

`headroom = cash_on_hand − required_cash`

### 6.3 Status thresholds

| status | rule |
|---|---|
| `covered` (green) | headroom ≥ 15% of required_cash (or required_cash = 0) |
| `tight` (amber) | 0 ≤ headroom < 15% of required_cash |
| `shortfall` (red) | headroom < 0 |

The 15% buffer is `GREENLINE_TIGHT_BUFFER` (configurable; default 0.15).
**Design note:** M1 status uses cash on hand only — expected income is shown
alongside ("payday Fri Jun 26, ~$4,000 expected") but doesn't flip a red to
green. Spending money that hasn't arrived is exactly the failure mode the app
exists to prevent; "cash room" including income arrives with M4 where the PRD
defines it.

### 6.4 API response shape

```json
GET /api/forecast
{
  "as_of": "2026-06-12",
  "cash_on_hand_cents": 645210,
  "accounts": [{"id": 1, "name": "Everyday Checking", "balance_cents": 645210, "as_of": "2026-06-12"}],
  "windows": [
    {"days": 7, "required_cents": 18999, "headroom_cents": 626211, "status": "covered",
     "due": [{"bill_id": 3, "name": "Netflix", "due": "2026-06-15", "amount_cents": 2299}]}
  ],
  "income": [{"name": "Acme Industries payroll", "next_expected": "2026-06-26",
              "expected_cents": 400000, "basis_n": 4, "overdue": false}],
  "pending_review": 2
}
```

---

## 7. API surface

All under `/api`, JSON, no auth (localhost, single user — see §9).

| method & path | purpose |
|---|---|
| `POST /api/imports` | multipart CSV upload → import receipt (batch id, added, duplicates, errors) |
| `GET /api/imports` | import history (the idempotency receipts) |
| `GET /api/accounts` / `PATCH /api/accounts/{id}` | list; edit name/type |
| `GET /api/transactions` | filter: `account_id`, `from`, `to`, `q`; paged, newest first |
| `GET /api/bills` | all bills incl. drafts; `?status=` filter |
| `POST /api/bills` | manual bill |
| `PATCH /api/bills/{id}` | confirm / dismiss / edit amount, cadence, next_due, name |
| `GET /api/income` | income streams |
| `PATCH /api/income/{id}` | confirm / dismiss / edit |
| `GET /api/forecast` | §6.4 |
| `GET /api/health` | `{status, app_name, data_dir}` (surfaces the 0010 path) |

Errors: RFC-7807-style `{detail}` with correct status codes; import errors
enumerate row numbers and reasons.

---

## 8. Frontend — the check-in view

Single-page app, three routes. UX principles from PRD §6 govern.

### 8.1 `/` — Check-in (home)

Above the fold, no scrolling:
- **Cash on hand** — the biggest number on the page, with per-account split on
  hover/expand (progressive disclosure).
- **Three window cards (7 / 14 / 30):** required cash, headroom, and a
  green/amber/red status. The active card expands to list the bills due inside
  the window with dates (the "basis", always one click away).
- **Payday line:** "Next payday: Fri Jun 26 · ~$4,000 expected (avg of last 4)".
- **Review nudge:** if `pending_review > 0`, an amber chip — "2 detected bills
  await review" → links to `/bills`. This is the first-run path.
- Empty state (no data): a single import dropzone, nothing else.

### 8.2 `/bills` — Review & manage

Drafts on top (sorted by confidence, each showing its basis: "seen 3×
monthly · last May 30 · ±$0.00") with one-tap **Confirm / Dismiss**; confirmed
bills below with inline edit; manual "Add bill" form. Every mutation reflects
optimistically — no spinners on core interactions (PRD: instant).

### 8.3 `/import` — Import & history

Dropzone (`.csv`) → upload → receipt card: "129 rows · 129 added · 0
duplicates" or "124 rows · 0 added · 124 duplicates — already imported".
Batch history table below. Errors listed per-row, plainly.

### 8.4 Visual language

Tailwind; status palette green/amber/red with sufficient contrast; tabular
numerals for money; app name rendered from config, not hardcoded (decision
0008). Dark-friendly neutral base.

---

## 9. Non-functional

- **Binding:** uvicorn binds `127.0.0.1` only. No telemetry, no external
  requests of any kind from backend or frontend (no CDN fonts — system font
  stack).
- **Performance:** forecast endpoint < 50 ms at 10k transactions (it's three
  indexed scans and arithmetic); import of a 1k-row CSV < 1 s.
- **Repo hygiene:** runtime writes only to the data dir; fixtures policy per
  decision 0011; `python scripts/check_hygiene.py` greps the index for
  ignored-pattern violations as a pre-commit-able guard.

## 10. Testing (synthetic fixtures only)

- Parser: layout acceptance, BOM, amount-sign validation, malformed-row abort.
- Dedup: import → re-import same file → zero added; overlapping-range file →
  only new rows added; hash-fallback same-day duplicates.
- Bill detection: fixtures derived from the General Bank seed (rent, insurance,
  internet, utilities, Netflix monthly; groceries/fuel correctly rejected by
  amount CV); dismissal is sticky across re-detection.
- Income: biweekly stream detected; trailing-average over last 4; overdue flag.
- Forecast: hand-computed expected values for a frozen `today`; window
  boundary inclusivity; multiple occurrences of a weekly bill in 30d;
  status thresholds at the 15% boundary.
- All date-dependent tests inject a fixed clock — no wall-clock flakiness.

## 11. Out of scope at M1 (explicit)

Variable-cost estimation and categorization (M2), budgets (M3), goals/cash
room (M4), forecast snapshots/streaks, OFX/QFX/QBO parsers, credit-card
accounts, Docker packaging polish (a `docker-compose.yml` may exist but the
supported path is the local launch script).

---

*Spec v1.0 — 2026-06-12. Deviations discovered during the build get a decision
entry, not a silent divergence.*
