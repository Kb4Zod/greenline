# Greenline

> Working codename — final name TBD (see `decisions/0008`).

**Greenline is a local-first personal cash-flow forecasting app.** It answers one
question every week:

> *"Given the bills coming up, how much cash do I actually need — and how much can
> I safely move toward my goals?"*

It imports your bank history (manual CSV download — no bank APIs, no cloud),
detects your recurring bills, and forecasts the cash required over rolling
**7 / 14 / 30-day** windows, with a Friday check-in ritual aligned to payday.

## Built in public, data stays private

This repo is developed entirely in public, from the first commit. The hard rule
that makes that possible:

**No secrets and no real financial data are ever committed.**

- All `*.csv`, `*.sqlite*`, `*.db`, and `.env` files are git-ignored from commit #1.
- Live data lives in a per-user app-data folder **outside the repo tree**.
- The only data in the repo is obviously-synthetic fixture data for tests/demos.
- See `decisions/0001` and PRD §14.

## Status

| Milestone | State |
|---|---|
| PRD | ✅ Locked — [`Greenline_PRD_v1.2.md`](Greenline_PRD_v1.2.md) |
| Spec (M1) | ✅ [`SPEC-M1.md`](SPEC-M1.md) |
| M1 — Cash Flow Forecast | ✅ Built — import, dedup, bill detection, 7/14/30d forecast, check-in UI |
| M2 — Variable Cost Estimation | ⬜ Not started |
| M3 — Budgeting & Planning | ⬜ Not started |
| M4 — Goals & Savings Guidance | ⬜ Not started |

## Quickstart

```powershell
.\scripts\dev.ps1   # starts the API (127.0.0.1:8537) + UI, opens localhost:5173
```

Then import a bank CSV on the Import tab, review the detected bills on the
Bills tab, and the check-in view does the rest. Backend tests:
`cd backend; .venv\Scripts\python -m pytest`.

## Stack

- **Backend:** Python + FastAPI
- **Storage:** SQLite (single local file)
- **Frontend:** React (Vite) + Tailwind
- Runs locally, opens in the browser at `localhost`. No telemetry, ever.

## Repo map

```
├── Greenline_PRD_v1.2.md   # the locked PRD — what we're building and why
├── HANDOFF.md              # onboarding doc for collaborators (human or AI)
├── decisions/              # the decision journal — dirty by design, read its README
├── backend/                # FastAPI app + SQLite + tests
└── frontend/               # React (Vite + Tailwind) check-in UI
```

## The decision journal

Every meaningful decision — including the messy reasoning behind it — is logged
chronologically in [`decisions/`](decisions/). It is deliberately unpolished and
never rewritten. Start with [`decisions/README.md`](decisions/README.md).
