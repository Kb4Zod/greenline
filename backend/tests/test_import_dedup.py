"""PRD M1 success criterion: weekly re-import adds zero duplicates."""

from .conftest import upload

APRIL = "synthetic_general_bank_2026-04.csv"
MAY = "synthetic_general_bank_2026-05.csv"

HEADER = (
    "Transaction ID,Posted Date,Description,Category,Debit,Credit,"
    "Amount,Balance,Account Name,Institution"
)


def test_first_import_adds_everything(client):
    receipt = upload(client, APRIL).json()
    assert receipt["rows_total"] == 125
    assert receipt["rows_added"] == 125
    assert receipt["rows_duplicate"] == 0
    assert receipt["accounts"] == ["Everyday Checking"]


def test_reimport_is_idempotent(client):
    upload(client, APRIL)
    receipt = upload(client, APRIL).json()
    assert receipt["rows_added"] == 0
    assert receipt["rows_duplicate"] == 125

    total = client.get("/api/transactions").json()["total"]
    assert total == 125  # zero duplicates in the store


def test_overlapping_files_add_only_new_rows(client):
    upload(client, APRIL)
    receipt = upload(client, MAY).json()
    assert receipt["rows_added"] == receipt["rows_total"]
    assert receipt["rows_duplicate"] == 0


def _csv(*rows: str) -> bytes:
    return ("\n".join([HEADER, *rows]) + "\n").encode()


# Two identical same-day rows WITHOUT a bank transaction id — the
# content-hash fallback must keep both, and re-import must match pairwise.
TWIN_ROWS = _csv(
    ",2026-06-01,LOCAL COFFEE #1,Coffee,5.00,,-5.00,95.00,Everyday Checking,General Bank",
    ",2026-06-01,LOCAL COFFEE #2,Coffee,5.00,,-5.00,90.00,Everyday Checking,General Bank",
)


def test_hash_fallback_keeps_identical_same_day_rows(client):
    first = client.post(
        "/api/imports", files={"file": ("twins.csv", TWIN_ROWS, "text/csv")}
    ).json()
    assert first["rows_added"] == 2  # same date/amount/payee, both kept

    again = client.post(
        "/api/imports", files={"file": ("twins.csv", TWIN_ROWS, "text/csv")}
    ).json()
    assert again["rows_added"] == 0
    assert again["rows_duplicate"] == 2


def test_malformed_row_aborts_whole_batch(client):
    bad = _csv(
        "GB-1,2026-06-01,GOOD ROW,Misc,5.00,,-5.00,95.00,Everyday Checking,General Bank",
        "GB-2,2026-06-01,BAD ROW,Misc,5.00,,-6.00,90.00,Everyday Checking,General Bank",
    )
    response = client.post("/api/imports", files={"file": ("bad.csv", bad, "text/csv")})
    assert response.status_code == 422
    assert response.json()["detail"]["rows"][0]["row"] == 2

    assert client.get("/api/transactions").json()["total"] == 0  # nothing half-imported


def test_balance_follows_latest_transaction(client):
    upload(client, APRIL)
    account = client.get("/api/accounts").json()[0]
    assert account["balance_as_of"] == "2026-04-30"

    upload(client, MAY)
    account = client.get("/api/accounts").json()[0]
    assert account["balance_as_of"] == "2026-05-31"
