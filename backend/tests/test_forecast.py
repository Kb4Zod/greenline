"""Window math against hand-computed values, with a frozen 'today'."""

from datetime import date

from greenline.forecast import build_forecast
from greenline.models import Account, Bill, IncomeStream

from .conftest import TODAY, upload

FILES = [
    "synthetic_general_bank_2026-04.csv",
    "synthetic_general_bank_2026-05.csv",
    "synthetic_general_bank_2026-06.csv",
]


def _account(session, balance_cents: int) -> Account:
    account = Account(
        name="Test Checking",
        institution="General Bank",
        type="checking",
        balance_cents=balance_cents,
        balance_as_of=TODAY,
    )
    session.add(account)
    session.flush()
    return account


def _bill(session, account, name, amount_cents, cadence, next_due, status="confirmed"):
    bill = Bill(
        account_id=account.id,
        payee_key=name.upper(),
        display_name=name,
        amount_cents=amount_cents,
        cadence=cadence,
        next_due=next_due,
        status=status,
        confidence=1.0,
        source="manual",
    )
    session.add(bill)
    session.flush()
    return bill


def test_hand_computed_windows(session, settings):
    account = _account(session, 100000)  # $1,000.00
    _bill(session, account, "Rent-ish", 30000, "monthly", date(2026, 6, 15))
    _bill(session, account, "Weekly thing", 5000, "weekly", date(2026, 6, 13))
    session.commit()

    forecast = build_forecast(session, settings, TODAY)
    by_days = {w.days: w for w in forecast.windows}

    # 7d  (through Jun 19): monthly Jun 15 + weekly Jun 13          = $350
    # 14d (through Jun 26): monthly Jun 15 + weekly Jun 13, 20      = $400
    # 30d (through Jul 12): monthly Jun 15 + weekly 13,20,27,4,11   = $550
    assert by_days[7].required_cents == 35000
    assert by_days[14].required_cents == 40000
    assert by_days[30].required_cents == 55000
    assert [w.status for w in forecast.windows] == ["covered", "covered", "covered"]


def test_status_thresholds(session, settings):
    # required 7d = $350; tight buffer 15% -> $52.50
    cases = [
        (40300, "covered"),   # headroom $53.00 >= 52.50
        (36000, "tight"),     # headroom $10
        (30000, "shortfall"), # headroom -$50
    ]
    for balance, expected in cases:
        session.query(Account).delete()
        session.query(Bill).delete()
        account = _account(session, balance)
        _bill(session, account, "Rent-ish", 30000, "monthly", date(2026, 6, 15))
        _bill(session, account, "Weekly thing", 5000, "weekly", date(2026, 6, 13))
        session.commit()
        forecast = build_forecast(session, settings, TODAY)
        assert forecast.windows[0].status == expected, f"balance={balance}"


def test_past_due_rolls_forward_and_drafts_are_excluded(session, settings):
    account = _account(session, 100000)
    # next_due in the past: monthly Jun 1 rolls to Jul 1 -> only the 30d window
    _bill(session, account, "Rolled", 10000, "monthly", date(2026, 6, 1))
    # drafts must not move the forecast
    _bill(session, account, "Draft", 99900, "monthly", date(2026, 6, 14), status="detected")
    session.commit()

    forecast = build_forecast(session, settings, TODAY)
    by_days = {w.days: w for w in forecast.windows}
    assert by_days[7].required_cents == 0
    assert by_days[14].required_cents == 0
    assert by_days[30].required_cents == 10000
    assert by_days[30].due[0].due == date(2026, 7, 1)
    assert forecast.pending_review == 1


def test_income_overdue_flag(session, settings):
    account = _account(session, 100000)
    session.add(
        IncomeStream(
            account_id=account.id,
            payee_key="PAYROLL",
            display_name="Payroll",
            cadence="biweekly",
            next_expected=date(2026, 6, 5),  # grace is 3 days; today is Jun 12
            trailing_avg_cents=400000,
            occurrences=5,
            status="confirmed",
        )
    )
    session.commit()
    forecast = build_forecast(session, settings, TODAY)
    assert forecast.income[0].overdue is True


def test_end_to_end_forecast_over_fixtures(client):
    for name in FILES:
        upload(client, name)

    # Confirm every draft — the user triages, then the forecast moves.
    for draft in client.get("/api/bills?status=detected").json():
        client.patch(f"/api/bills/{draft['id']}", json={"status": "confirmed"})

    forecast = client.get("/api/forecast", params={"as_of": "2026-06-12"}).json()

    account = client.get("/api/accounts").json()[0]
    assert forecast["cash_on_hand_cents"] == account["balance_cents"]
    assert forecast["pending_review"] == 0

    # Rent posted Jun 1 -> due again Jul 1: inside 30d, outside 7/14d.
    windows = {w["days"]: w for w in forecast["windows"]}
    rent_due = [i for i in windows[30]["due"] if "Harbor View" in i["name"]]
    assert rent_due and rent_due[0]["due"] == "2026-07-01"
    assert not any("Harbor View" in i["name"] for i in windows[14]["due"])

    assert windows[7]["required_cents"] <= windows[14]["required_cents"] <= windows[30]["required_cents"]

    payroll = forecast["income"][0]
    # The June statement already contains the Jun 26 paycheck -> next is Jul 10.
    assert payroll["next_expected"] == "2026-07-10"
    assert payroll["expected_cents"] == 400000
    assert payroll["overdue"] is False
