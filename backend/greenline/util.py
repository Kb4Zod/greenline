"""Shared primitives: money parsing, payee normalization, cadence math.

Money is integer cents everywhere (SPEC-M1 §1); floats never touch amounts.
"""

import calendar
import re
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from statistics import median, pstdev
from statistics import mean as _mean

CADENCES = ("weekly", "biweekly", "semimonthly", "monthly", "quarterly", "annual")

# Nominal interval length and per-interval tolerance, in days (SPEC-M1 §4.2).
_NOMINAL = {
    "weekly": 7.0,
    "biweekly": 14.0,
    "semimonthly": 15.2,
    "monthly": 30.4,
    "quarterly": 91.3,
    "annual": 365.25,
}
_TOLERANCE = {
    "weekly": 2,
    "biweekly": 2,
    "semimonthly": 3,
    "monthly": 4,
    "quarterly": 10,
    "annual": 10,
}


class MoneyError(ValueError):
    pass


def parse_money_cents(raw: str) -> int:
    """'2150.00' -> 215000. Rejects sub-cent precision and garbage."""
    text = raw.strip().replace(",", "")
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise MoneyError(f"not a money value: {raw!r}") from exc
    cents = value * 100
    if cents != cents.to_integral_value():
        raise MoneyError(f"sub-cent precision not supported: {raw!r}")
    return int(cents)


_STORE_NUMBER = re.compile(r"#\s*\d+")
_NON_ALNUM = re.compile(r"[^A-Z0-9]+")


def normalize_payee(description: str) -> str:
    """'CHEVRON #1419' and 'CHEVRON #1515' -> 'CHEVRON' (SPEC-M1 §4.1)."""
    text = description.upper()
    text = _STORE_NUMBER.sub(" ", text)
    text = _NON_ALNUM.sub(" ", text)
    return " ".join(text.split())


def display_name_from_payee(payee_key: str) -> str:
    return payee_key.title()


def _clamp_day(year: int, month: int, day: int) -> date:
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def add_months(d: date, n: int) -> date:
    month_index = d.month - 1 + n
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    return _clamp_day(year, month, d.day)


def advance(d: date, cadence: str) -> date:
    """One cadence period forward, calendar-aware for monthly+ (SPEC-M1 §4.3)."""
    if cadence == "weekly":
        return d + timedelta(days=7)
    if cadence == "biweekly":
        return d + timedelta(days=14)
    if cadence == "semimonthly":
        # Anchor pair is (day, day+15): 1st<->16th style. Clamped at month end.
        if d.day <= 13:
            return _clamp_day(d.year, d.month, d.day + 15)
        nxt = add_months(d, 1)
        return _clamp_day(nxt.year, nxt.month, max(1, d.day - 15))
    if cadence == "monthly":
        return add_months(d, 1)
    if cadence == "quarterly":
        return add_months(d, 3)
    if cadence == "annual":
        return add_months(d, 12)
    raise ValueError(f"unknown cadence: {cadence}")


def roll_forward(d: date, cadence: str, today: date) -> date:
    while d < today:
        d = advance(d, cadence)
    return d


def cadence_days(cadence: str) -> float:
    return _NOMINAL[cadence]


def snap_cadence(intervals: list[int], dates: list[date]) -> str | None:
    """Median interval -> cadence, or None when there is no rhythm (§4.2)."""
    if not intervals:
        return None
    med = median(intervals)
    if 5 <= med <= 9:
        return "weekly"
    if 12 <= med <= 17:
        # Semimonthly pins to <=2 days-of-month (1st/16th style); biweekly
        # anchors to a weekday, so its day-of-month drifts across the month.
        clusters = _day_of_month_clusters([dt.day for dt in dates])
        if len(clusters) <= 2:
            return "semimonthly"
        return "biweekly"
    if 26 <= med <= 35:
        return "monthly"
    if 80 <= med <= 100:
        return "quarterly"
    if 330 <= med <= 400:
        return "annual"
    return None


def _day_of_month_clusters(days: list[int]) -> list[list[int]]:
    clusters: list[list[int]] = []
    for day in sorted(set(days)):
        if clusters and day - clusters[-1][-1] <= 1:
            clusters[-1].append(day)
        else:
            clusters.append([day])
    return clusters


def regularity(intervals: list[int], cadence: str) -> float:
    nominal, tol = _NOMINAL[cadence], _TOLERANCE[cadence]
    if not intervals:
        return 0.0
    hits = sum(1 for i in intervals if abs(i - nominal) <= tol)
    return hits / len(intervals)


def amount_cv(amounts_cents: list[int]) -> float:
    """Coefficient of variation of absolute amounts."""
    values = [abs(a) for a in amounts_cents]
    avg = _mean(values)
    if avg == 0:
        return 0.0
    return pstdev(values) / avg


def stability_score(cv: float) -> float:
    return max(0.0, 1.0 - cv / 0.35)


def confidence_score(reg: float, stability: float, occurrences: int) -> float:
    return 0.5 * reg + 0.3 * stability + 0.2 * min(occurrences / 6, 1.0)
