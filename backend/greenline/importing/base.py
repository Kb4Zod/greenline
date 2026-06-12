"""Format-agnostic statement parsing (decision 0003, SPEC-M1 §3.1).

Adding OFX/QFX/QBO later means writing one parser class and appending it to
PARSERS — nothing downstream changes.
"""

from datetime import date
from typing import IO, Protocol, runtime_checkable

from pydantic import BaseModel


class ParsedTransaction(BaseModel):
    external_id: str | None
    posted_date: date
    amount_cents: int  # signed: debit < 0, credit > 0
    description: str
    category_raw: str | None
    balance_cents: int | None
    account_name: str
    institution: str


class ParsedStatement(BaseModel):
    parser: str
    transactions: list[ParsedTransaction]


class RowError(BaseModel):
    row: int  # 1-based data-row number (excludes header)
    reason: str


class ParseFailure(Exception):
    """The file matched a parser but contained bad rows. Whole batch aborts."""

    def __init__(self, errors: list[RowError]):
        self.errors = errors
        super().__init__(f"{len(errors)} bad row(s)")


class UnsupportedFormat(Exception):
    def __init__(self, found_headers: list[str] | None):
        self.found_headers = found_headers or []
        super().__init__("no parser recognizes this file")


@runtime_checkable
class StatementParser(Protocol):
    key: str

    def sniff(self, head: bytes) -> bool: ...
    def parse(self, stream: IO[bytes]) -> ParsedStatement: ...


def _registry() -> list[StatementParser]:
    from .general_bank_csv import GeneralBankCsvParser

    return [GeneralBankCsvParser()]


def find_parser(head: bytes) -> StatementParser | None:
    for parser in _registry():
        if parser.sniff(head):
            return parser
    return None
