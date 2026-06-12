import io

import pytest

from greenline.importing.base import ParseFailure, find_parser
from greenline.importing.general_bank_csv import GeneralBankCsvParser

from .conftest import fixture_bytes

HEADER = (
    "Transaction ID,Posted Date,Description,Category,Debit,Credit,"
    "Amount,Balance,Account Name,Institution"
)


def test_sniff_accepts_general_bank_layout():
    data = fixture_bytes("synthetic_general_bank_2026-04.csv")
    parser = find_parser(data[:4096])
    assert isinstance(parser, GeneralBankCsvParser)


def test_sniff_rejects_unknown_layout():
    assert find_parser(b"Date,Payee,Amount\n2026-01-01,X,1.00\n") is None


def test_parse_full_fixture():
    parser = GeneralBankCsvParser()
    parsed = parser.parse(io.BytesIO(fixture_bytes("synthetic_general_bank_2026-04.csv")))
    assert len(parsed.transactions) == 125

    first = parsed.transactions[0]
    assert first.external_id == "GB-202604-0001"
    assert first.posted_date.isoformat() == "2026-04-01"
    assert first.amount_cents == -215000  # debit is negative, integer cents
    assert first.balance_cents == 345000
    assert first.account_name == "Everyday Checking"
    assert first.institution == "General Bank"

    payroll = next(t for t in parsed.transactions if "PAYROLL" in t.description)
    assert payroll.amount_cents == 400000  # credit is positive


def _row(**overrides) -> bytes:
    fields = {
        "Transaction ID": "GB-1",
        "Posted Date": "2026-04-01",
        "Description": "TEST PAYEE",
        "Category": "Test",
        "Debit": "10.00",
        "Credit": "",
        "Amount": "-10.00",
        "Balance": "100.00",
        "Account Name": "Everyday Checking",
        "Institution": "General Bank",
    }
    fields.update(overrides)
    line = ",".join(fields[h] for h in HEADER.split(","))
    return f"{HEADER}\n{line}\n".encode()


@pytest.mark.parametrize(
    "overrides, reason_fragment",
    [
        ({"Debit": "11.00"}, "disagrees"),  # sign/value mismatch must abort
        ({"Debit": "", "Credit": ""}, "neither"),
        ({"Debit": "10.00", "Credit": "10.00", "Amount": "10.00"}, "both"),
        ({"Posted Date": "04/01/2026"}, "Invalid isoformat"),
        ({"Description": ""}, "empty Description"),
    ],
)
def test_bad_rows_abort_with_reason(overrides, reason_fragment):
    parser = GeneralBankCsvParser()
    with pytest.raises(ParseFailure) as exc_info:
        parser.parse(io.BytesIO(_row(**overrides)))
    assert reason_fragment.lower() in exc_info.value.errors[0].reason.lower()
    assert exc_info.value.errors[0].row == 1
