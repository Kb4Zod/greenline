"""Import a statement idempotently (SPEC-M1 §3.3).

Dedup key: the bank-side transaction id when the format provides one,
otherwise a content hash that includes an occurrence index so identical
same-day rows within one file both survive while re-imports match pairwise.
The whole import is one DB transaction — a malformed row aborts the batch.
"""

import hashlib
import io
from collections import Counter
from datetime import datetime
from typing import Sequence

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Account, ImportBatch, Transaction
from ..util import normalize_payee
from .base import ParsedTransaction, UnsupportedFormat, find_parser


class ImportReceipt(BaseModel):
    batch_id: int
    parser: str
    filename: str
    rows_total: int
    rows_added: int
    rows_duplicate: int
    accounts: list[str]


def _dedup_key(txn: ParsedTransaction, payee_key: str, occurrence: int) -> str:
    if txn.external_id:
        return f"ext:{txn.institution}|{txn.account_name}|{txn.external_id}"
    raw = "|".join(
        [
            txn.institution,
            txn.account_name,
            txn.posted_date.isoformat(),
            str(txn.amount_cents),
            payee_key,
            str(occurrence),
        ]
    )
    return "sha:" + hashlib.sha256(raw.encode()).hexdigest()


def _upsert_account(session: Session, name: str, institution: str) -> Account:
    account = session.scalar(
        select(Account).where(Account.name == name, Account.institution == institution)
    )
    if account is None:
        account = Account(name=name, institution=institution, type="checking")
        session.add(account)
        session.flush()
    return account


def import_statement(session: Session, filename: str, data: bytes) -> ImportReceipt:
    """Parse + dedup + persist. Raises UnsupportedFormat / ParseFailure."""
    parser = find_parser(data[:4096])
    if parser is None:
        first_line = data[:4096].decode("utf-8-sig", errors="replace").splitlines()
        raise UnsupportedFormat(first_line[0].split(",") if first_line else None)

    parsed = parser.parse(io.BytesIO(data))
    rows = parsed.transactions

    accounts: dict[tuple[str, str], Account] = {}
    for txn in rows:
        ident = (txn.account_name, txn.institution)
        if ident not in accounts:
            accounts[ident] = _upsert_account(session, *ident)

    # Dedup keys, with per-file occurrence counters for the hash fallback.
    occurrence_counter: Counter[tuple] = Counter()
    keyed: list[tuple[ParsedTransaction, str, str]] = []
    for txn in rows:
        payee_key = normalize_payee(txn.description)
        group = (txn.account_name, txn.institution, txn.posted_date, txn.amount_cents, payee_key)
        key = _dedup_key(txn, payee_key, occurrence_counter[group])
        occurrence_counter[group] += 1
        keyed.append((txn, payee_key, key))

    existing = _existing_keys(session, [key for _, _, key in keyed])

    batch = ImportBatch(
        filename=filename,
        imported_at=datetime.now(),
        parser=parsed.parser,
        rows_total=len(rows),
        rows_added=0,
        rows_duplicate=0,
        date_min=min((t.posted_date for t in rows), default=None),
        date_max=max((t.posted_date for t in rows), default=None),
    )
    session.add(batch)
    session.flush()

    added = 0
    for txn, payee_key, key in keyed:
        if key in existing:
            continue
        account = accounts[(txn.account_name, txn.institution)]
        session.add(
            Transaction(
                account_id=account.id,
                batch_id=batch.id,
                posted_date=txn.posted_date,
                amount_cents=txn.amount_cents,
                description=txn.description,
                payee_key=payee_key,
                category_raw=txn.category_raw,
                balance_cents=txn.balance_cents,
                dedup_key=key,
            )
        )
        added += 1

    batch.rows_added = added
    batch.rows_duplicate = len(rows) - added
    _update_balances(rows, accounts)
    session.commit()

    return ImportReceipt(
        batch_id=batch.id,
        parser=parsed.parser,
        filename=filename,
        rows_total=batch.rows_total,
        rows_added=batch.rows_added,
        rows_duplicate=batch.rows_duplicate,
        accounts=[a.name for a in accounts.values()],
    )


def _existing_keys(session: Session, keys: Sequence[str]) -> set[str]:
    found: set[str] = set()
    chunk = 500  # keep sqlite's bound-parameter limit comfortable
    for start in range(0, len(keys), chunk):
        stmt = select(Transaction.dedup_key).where(
            Transaction.dedup_key.in_(keys[start : start + chunk])
        )
        found.update(session.scalars(stmt))
    return found


def _update_balances(rows: list[ParsedTransaction], accounts: dict[tuple, Account]) -> None:
    """Account balance follows the latest transaction in the file (ties: last row)."""
    latest: dict[tuple, ParsedTransaction] = {}
    for txn in rows:
        ident = (txn.account_name, txn.institution)
        if ident not in latest or txn.posted_date >= latest[ident].posted_date:
            latest[ident] = txn
    for ident, txn in latest.items():
        account = accounts[ident]
        if txn.balance_cents is None:
            continue
        if account.balance_as_of is None or txn.posted_date >= account.balance_as_of:
            account.balance_cents = txn.balance_cents
            account.balance_as_of = txn.posted_date
