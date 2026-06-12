"""Bill/income detection over the full three-month synthetic history."""

import pytest

from .conftest import upload

FILES = [
    "synthetic_general_bank_2026-04.csv",
    "synthetic_general_bank_2026-05.csv",
    "synthetic_general_bank_2026-06.csv",
]


@pytest.fixture
def loaded(client):
    for name in FILES:
        assert upload(client, name).status_code == 201
    return client


def _drafts(client) -> dict[str, dict]:
    return {b["payee_key"]: b for b in client.get("/api/bills?status=detected").json()}


def test_obvious_monthly_bills_are_drafted(loaded):
    drafts = _drafts(loaded)
    rent = drafts.get("RENT PAYMENT HARBOR VIEW APARTMENTS")
    assert rent is not None, f"rent not detected; got {sorted(drafts)}"
    assert rent["cadence"] == "monthly"
    assert rent["amount_cents"] == 215000
    assert rent["confidence"] >= 0.8
    assert rent["occurrences"] == 3

    assert "NETFLIX COM" in drafts
    assert drafts["NETFLIX COM"]["cadence"] == "monthly"
    assert "AUTO INSURANCE NORTHSTAR MUTUAL" in drafts
    assert "INTERNET FIBERLINE COMMUNICATIONS" in drafts


def test_variable_spend_is_not_a_bill(loaded):
    """Groceries/fuel recur but vary in amount — the CV gate must reject them."""
    drafts = _drafts(loaded)
    for payee in ("FRESH MART", "CHEVRON"):
        assert payee not in drafts, f"{payee} wrongly drafted as a bill"


def test_income_stream_detected_with_trailing_average(loaded):
    streams = loaded.get("/api/income").json()
    payroll = next(s for s in streams if "ACME" in s["payee_key"])
    assert payroll["cadence"] == "biweekly"
    # Paychecks: Apr 3, Apr 17, May 1, May 15, May 29, Jun 12, Jun 26 — all $4000.
    assert payroll["occurrences"] == 7
    assert payroll["trailing_avg_cents"] == 400000
    assert payroll["next_expected"] == "2026-07-10"


def test_dismissal_is_sticky_across_reimport(loaded):
    rent = _drafts(loaded)["RENT PAYMENT HARBOR VIEW APARTMENTS"]
    loaded.patch(f"/api/bills/{rent['id']}", json={"status": "dismissed"})

    upload(loaded, FILES[-1])  # re-import triggers re-detection

    bills = loaded.get("/api/bills").json()
    rent_after = next(b for b in bills if b["id"] == rent["id"])
    assert rent_after["status"] == "dismissed"
    assert "RENT PAYMENT HARBOR VIEW APARTMENTS" not in _drafts(loaded)


def test_confirmed_bill_survives_and_updates(loaded):
    rent = _drafts(loaded)["RENT PAYMENT HARBOR VIEW APARTMENTS"]
    confirmed = loaded.patch(
        f"/api/bills/{rent['id']}", json={"status": "confirmed"}
    ).json()
    assert confirmed["status"] == "confirmed"

    upload(loaded, FILES[-1])
    bills = loaded.get("/api/bills?status=confirmed").json()
    assert any(b["id"] == rent["id"] for b in bills)


def test_manual_bill(loaded):
    account_id = loaded.get("/api/accounts").json()[0]["id"]
    created = loaded.post(
        "/api/bills",
        json={
            "account_id": account_id,
            "display_name": "Gym Membership",
            "amount_cents": 4500,
            "cadence": "monthly",
            "next_due": "2026-06-20",
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "confirmed"
    assert body["source"] == "manual"
