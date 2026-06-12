"""Parser for the 'General Bank' CSV layout (decision 0009).

Columns: Transaction ID, Posted Date, Description, Category, Debit, Credit,
Amount, Balance, Account Name, Institution.

`Amount` is authoritative; Debit/Credit are validation only — a sign error is
worse than a failed import, so any disagreement rejects the row and the whole
batch aborts (SPEC-M1 §3.2).
"""

import csv
import io
from datetime import date
from typing import IO

from ..util import MoneyError, parse_money_cents
from .base import ParsedStatement, ParsedTransaction, ParseFailure, RowError

HEADERS = [
    "Transaction ID",
    "Posted Date",
    "Description",
    "Category",
    "Debit",
    "Credit",
    "Amount",
    "Balance",
    "Account Name",
    "Institution",
]


class GeneralBankCsvParser:
    key = "general_bank_csv"

    def sniff(self, head: bytes) -> bool:
        try:
            first_line = head.decode("utf-8-sig", errors="strict").splitlines()[0]
        except (UnicodeDecodeError, IndexError):
            return False
        found = [h.strip() for h in next(csv.reader([first_line]), [])]
        return found == HEADERS

    def parse(self, stream: IO[bytes]) -> ParsedStatement:
        text = io.TextIOWrapper(stream, encoding="utf-8-sig", newline="")
        reader = csv.DictReader(text)
        transactions: list[ParsedTransaction] = []
        errors: list[RowError] = []

        for index, row in enumerate(reader, start=1):
            try:
                transactions.append(self._parse_row(row))
            except (MoneyError, ValueError) as exc:
                errors.append(RowError(row=index, reason=str(exc)))

        if errors:
            raise ParseFailure(errors)
        return ParsedStatement(parser=self.key, transactions=transactions)

    def _parse_row(self, row: dict[str, str]) -> ParsedTransaction:
        amount = parse_money_cents(row["Amount"])
        debit_raw = (row.get("Debit") or "").strip()
        credit_raw = (row.get("Credit") or "").strip()

        if debit_raw and credit_raw:
            raise ValueError("row has both Debit and Credit")
        if debit_raw and parse_money_cents(debit_raw) != -amount:
            raise ValueError(f"Debit {debit_raw} disagrees with Amount {row['Amount']}")
        if credit_raw and parse_money_cents(credit_raw) != amount:
            raise ValueError(f"Credit {credit_raw} disagrees with Amount {row['Amount']}")
        if not debit_raw and not credit_raw:
            raise ValueError("row has neither Debit nor Credit")

        posted = date.fromisoformat(row["Posted Date"].strip())
        description = row["Description"].strip()
        if not description:
            raise ValueError("empty Description")

        account_name = row["Account Name"].strip()
        institution = row["Institution"].strip()
        if not account_name or not institution:
            raise ValueError("missing Account Name / Institution")

        balance_raw = (row.get("Balance") or "").strip()
        external_id = (row.get("Transaction ID") or "").strip() or None

        return ParsedTransaction(
            external_id=external_id,
            posted_date=posted,
            amount_cents=amount,
            description=description,
            category_raw=(row.get("Category") or "").strip() or None,
            balance_cents=parse_money_cents(balance_raw) if balance_raw else None,
            account_name=account_name,
            institution=institution,
        )
