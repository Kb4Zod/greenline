"""Recurring-pattern detection over imported history (SPEC-M1 §4–5).

Bills: debit groups with a snapped cadence AND stable amounts (CV <= 0.35 —
this is what keeps groceries/fuel out of the bill list). Income: credit groups
with a snapped cadence; amount variability is allowed by design (decision
0004) and the expected amount is a trailing average of the last N paychecks.

Detection only ever touches `detected` drafts. `confirmed` and `dismissed`
are user verdicts and are never changed or resurrected here.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from statistics import mean, median

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import Settings
from .models import Account, Bill, IncomeStream, Transaction
from .util import (
    advance,
    amount_cv,
    confidence_score,
    display_name_from_payee,
    normalize_payee,  # noqa: F401  (re-export convenience for callers/tests)
    regularity,
    snap_cadence,
    stability_score,
)

MIN_OCCURRENCES = 3
MIN_CONFIDENCE = 0.5
MAX_BILL_AMOUNT_CV = 0.35
MIN_INCOME_REGULARITY = 0.6


@dataclass
class GroupAnalysis:
    cadence: str
    regularity: float
    cv: float
    confidence: float
    median_amount_cents: int
    last_seen: date
    next_due: date
    occurrences: int


def analyze_group(dates: list[date], amounts_cents: list[int]) -> GroupAnalysis | None:
    """Dates must be sorted ascending. Returns None when there's no rhythm."""
    if len(dates) < MIN_OCCURRENCES:
        return None
    intervals = [(b - a).days for a, b in zip(dates, dates[1:])]
    cadence = snap_cadence(intervals, dates)
    if cadence is None:
        return None
    reg = regularity(intervals, cadence)
    cv = amount_cv(amounts_cents)
    confidence = confidence_score(reg, stability_score(cv), len(dates))
    return GroupAnalysis(
        cadence=cadence,
        regularity=reg,
        cv=cv,
        confidence=confidence,
        median_amount_cents=int(median(abs(a) for a in amounts_cents)),
        last_seen=dates[-1],
        next_due=advance(dates[-1], cadence),
        occurrences=len(dates),
    )


def run_detection(session: Session, settings: Settings) -> None:
    for account in session.scalars(select(Account)):
        _detect_bills(session, account)
        _detect_income(session, account, settings)
    session.commit()


def _grouped(session: Session, account: Account, *, credits: bool) -> dict[str, list[Transaction]]:
    stmt = (
        select(Transaction)
        .where(Transaction.account_id == account.id)
        .where(Transaction.amount_cents > 0 if credits else Transaction.amount_cents < 0)
        .order_by(Transaction.posted_date, Transaction.id)
    )
    groups: dict[str, list[Transaction]] = defaultdict(list)
    for txn in session.scalars(stmt):
        groups[txn.payee_key].append(txn)
    return groups


def _detect_bills(session: Session, account: Account) -> None:
    existing = {
        b.payee_key: b
        for b in session.scalars(select(Bill).where(Bill.account_id == account.id))
    }
    for payee_key, txns in _grouped(session, account, credits=False).items():
        bill = existing.get(payee_key)
        if bill is not None and bill.status in ("confirmed", "dismissed"):
            if bill.status == "confirmed":
                bill.last_seen = txns[-1].posted_date
                bill.occurrences = len(txns)
            continue

        analysis = analyze_group(
            [t.posted_date for t in txns], [t.amount_cents for t in txns]
        )
        keep = (
            analysis is not None
            and analysis.cv <= MAX_BILL_AMOUNT_CV
            and analysis.confidence >= MIN_CONFIDENCE
        )
        if not keep:
            if bill is not None and bill.source == "detected":
                session.delete(bill)  # new data invalidated the draft
            continue

        assert analysis is not None
        if bill is None:
            bill = Bill(account_id=account.id, payee_key=payee_key, source="detected")
            session.add(bill)
        bill.display_name = display_name_from_payee(payee_key)
        bill.amount_cents = analysis.median_amount_cents
        bill.cadence = analysis.cadence
        bill.next_due = analysis.next_due
        bill.confidence = analysis.confidence
        bill.occurrences = analysis.occurrences
        bill.last_seen = analysis.last_seen
        bill.status = "detected"


def _detect_income(session: Session, account: Account, settings: Settings) -> None:
    existing = {
        s.payee_key: s
        for s in session.scalars(
            select(IncomeStream).where(IncomeStream.account_id == account.id)
        )
    }
    for payee_key, txns in _grouped(session, account, credits=True).items():
        stream = existing.get(payee_key)
        if stream is not None and stream.status == "dismissed":
            continue

        analysis = analyze_group(
            [t.posted_date for t in txns], [t.amount_cents for t in txns]
        )
        if analysis is None or analysis.regularity < MIN_INCOME_REGULARITY:
            if stream is not None and stream.status == "detected":
                session.delete(stream)
            continue

        trailing = [t.amount_cents for t in txns][-settings.income_trailing_n :]
        if stream is None:
            stream = IncomeStream(account_id=account.id, payee_key=payee_key)
            session.add(stream)
        stream.display_name = display_name_from_payee(payee_key)
        stream.cadence = analysis.cadence
        stream.next_expected = analysis.next_due
        stream.trailing_avg_cents = int(mean(trailing))
        stream.occurrences = analysis.occurrences
        if stream.status != "confirmed":
            stream.status = "detected"
