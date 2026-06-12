from datetime import date

import pytest

from greenline.util import (
    advance,
    normalize_payee,
    parse_money_cents,
    roll_forward,
    snap_cadence,
)


def test_parse_money():
    assert parse_money_cents("2150.00") == 215000
    assert parse_money_cents("-62.18") == -6218
    assert parse_money_cents("4,000.00") == 400000
    with pytest.raises(Exception):
        parse_money_cents("12.345")  # sub-cent
    with pytest.raises(Exception):
        parse_money_cents("abc")


def test_normalize_payee_strips_store_numbers():
    assert normalize_payee("CHEVRON #1419") == normalize_payee("CHEVRON #1515") == "CHEVRON"
    assert normalize_payee("NETFLIX.COM") == "NETFLIX COM"
    assert normalize_payee("RENT PAYMENT - HARBOR VIEW APARTMENTS") == (
        "RENT PAYMENT HARBOR VIEW APARTMENTS"
    )


def test_advance_monthly_clamps_to_month_end():
    assert advance(date(2026, 1, 31), "monthly") == date(2026, 2, 28)
    assert advance(date(2026, 1, 15), "monthly") == date(2026, 2, 15)


def test_advance_semimonthly_anchor_pair():
    assert advance(date(2026, 6, 1), "semimonthly") == date(2026, 6, 16)
    assert advance(date(2026, 6, 16), "semimonthly") == date(2026, 7, 1)


def test_roll_forward():
    # monthly bill last due June 1, today June 12 -> July 1
    assert roll_forward(date(2026, 6, 1), "monthly", date(2026, 6, 12)) == date(2026, 7, 1)
    # already in the future stays put
    assert roll_forward(date(2026, 6, 20), "weekly", date(2026, 6, 12)) == date(2026, 6, 20)


def test_snap_cadence():
    assert snap_cadence([30, 31], [date(2026, 4, 1), date(2026, 5, 1), date(2026, 6, 1)]) == "monthly"
    assert snap_cadence([14, 14, 14], [date(2026, 4, 3), date(2026, 4, 17), date(2026, 5, 1), date(2026, 5, 15)]) == "biweekly"
    # 1st & 16th pattern -> semimonthly, not biweekly
    dates = [date(2026, 4, 1), date(2026, 4, 16), date(2026, 5, 1), date(2026, 5, 16)]
    assert snap_cadence([15, 15, 15], dates) == "semimonthly"
    # daily-ish noise has no cadence
    assert snap_cadence([2, 3, 2, 1], [date(2026, 4, d) for d in (1, 3, 6, 8, 9)]) is None
