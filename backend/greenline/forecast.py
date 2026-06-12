"""Required-cash forecast over 7/14/30-day windows (SPEC-M1 §6).

Only confirmed bills move the numbers — a figure the user hasn't vouched for
must not silently change "required cash". Expected income is displayed but
deliberately does NOT flip a status: spending money that hasn't arrived is
the failure mode this app exists to prevent.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import Settings
from .models import Account, Bill, IncomeStream
from .util import advance, cadence_days, roll_forward

WINDOWS = (7, 14, 30)


@dataclass
class DueItem:
    bill_id: int
    name: str
    due: date
    amount_cents: int


@dataclass
class WindowForecast:
    days: int
    required_cents: int
    headroom_cents: int
    status: str  # covered | tight | shortfall
    due: list[DueItem] = field(default_factory=list)


@dataclass
class IncomeOutlook:
    id: int
    name: str
    next_expected: date
    expected_cents: int
    basis_n: int
    cadence: str
    overdue: bool
    status: str


@dataclass
class AccountSummary:
    id: int
    name: str
    institution: str
    type: str
    balance_cents: int
    as_of: date | None


@dataclass
class Forecast:
    as_of: date
    cash_on_hand_cents: int
    accounts: list[AccountSummary]
    windows: list[WindowForecast]
    income: list[IncomeOutlook]
    pending_review: int


def _status(required: int, headroom: int, tight_buffer: float) -> str:
    if headroom < 0:
        return "shortfall"
    if required == 0:
        return "covered"
    if headroom < required * tight_buffer:
        return "tight"
    return "covered"


def occurrences_in_window(bill: Bill, today: date, end: date) -> list[date]:
    """Every due date in [today, end] — a weekly bill lands several times in 30d."""
    occurrences = []
    due = roll_forward(bill.next_due, bill.cadence, today)
    while due <= end:
        occurrences.append(due)
        due = advance(due, bill.cadence)
    return occurrences


def bill_is_stale(bill: Bill, today: date) -> bool:
    """Confirmed but unseen for 2 full cadence periods (SPEC-M1 §4.3)."""
    if bill.last_seen is None:
        return False
    return (today - bill.last_seen).days > 2 * cadence_days(bill.cadence)


def build_forecast(session: Session, settings: Settings, today: date) -> Forecast:
    accounts = list(session.scalars(select(Account)))
    cash = sum(a.balance_cents or 0 for a in accounts)

    confirmed = list(session.scalars(select(Bill).where(Bill.status == "confirmed")))
    windows: list[WindowForecast] = []
    for days in WINDOWS:
        end = today + timedelta(days=days)
        due_items = [
            DueItem(bill_id=b.id, name=b.display_name, due=d, amount_cents=b.amount_cents)
            for b in confirmed
            for d in occurrences_in_window(b, today, end)
        ]
        due_items.sort(key=lambda i: (i.due, i.name))
        required = sum(i.amount_cents for i in due_items)
        headroom = cash - required
        windows.append(
            WindowForecast(
                days=days,
                required_cents=required,
                headroom_cents=headroom,
                status=_status(required, headroom, settings.tight_buffer),
                due=due_items,
            )
        )

    income = [
        IncomeOutlook(
            id=s.id,
            name=s.display_name,
            next_expected=s.next_expected,
            expected_cents=s.trailing_avg_cents,
            basis_n=min(s.occurrences, settings.income_trailing_n),
            cadence=s.cadence,
            overdue=today > s.next_expected + timedelta(days=settings.income_grace_days),
            status=s.status,
        )
        for s in session.scalars(
            select(IncomeStream).where(IncomeStream.status != "dismissed")
        )
    ]

    pending = (
        session.scalar(select(func.count()).where(Bill.status == "detected").select_from(Bill))
        or 0
    )

    return Forecast(
        as_of=today,
        cash_on_hand_cents=cash,
        accounts=[
            AccountSummary(
                id=a.id,
                name=a.name,
                institution=a.institution,
                type=a.type,
                balance_cents=a.balance_cents or 0,
                as_of=a.balance_as_of,
            )
            for a in accounts
        ],
        windows=windows,
        income=income,
        pending_review=pending,
    )
