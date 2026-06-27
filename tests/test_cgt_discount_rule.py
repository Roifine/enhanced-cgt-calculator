#!/usr/bin/env python3
"""
Tests for the Australian 50% CGT discount 12-month holding rule.

Australian law: the discount applies only if the asset was held for STRICTLY
MORE than 12 calendar months. Exactly 12 months is NOT eligible.

ATO reference: CGT event happens more than 12 months after acquisition.
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tax_optimizer import _is_long_term


# --- Boundary cases ---

def test_exactly_12_months_not_eligible():
    """Buy Jan 1 2022, sell Jan 1 2023: exactly 12 months = NOT eligible."""
    buy = datetime(2022, 1, 1)
    sell = datetime(2023, 1, 1)
    assert not _is_long_term(buy, sell), (
        "Holding of exactly 12 months must NOT qualify for CGT discount"
    )


def test_one_day_over_12_months_eligible():
    """Buy Jan 1 2022, sell Jan 2 2023: 12 months + 1 day = eligible."""
    buy = datetime(2022, 1, 1)
    sell = datetime(2023, 1, 2)
    assert _is_long_term(buy, sell), (
        "Holding of more than 12 months must qualify for CGT discount"
    )


def test_exactly_12_months_mid_year_not_eligible():
    """Buy Jun 1 2022, sell Jun 1 2023: exactly 12 months = NOT eligible."""
    buy = datetime(2022, 6, 1)
    sell = datetime(2023, 6, 1)
    assert not _is_long_term(buy, sell)


def test_one_day_over_mid_year_eligible():
    """Buy Jun 1 2022, sell Jun 2 2023: 12 months + 1 day = eligible."""
    buy = datetime(2022, 6, 1)
    sell = datetime(2023, 6, 2)
    assert _is_long_term(buy, sell)


def test_leap_year_exactly_12_months_not_eligible():
    """Buy Jan 1 2020, sell Jan 1 2021: exactly 12 months, but 366 days (2020 is leap)."""
    buy = datetime(2020, 1, 1)
    sell = datetime(2021, 1, 1)
    assert not _is_long_term(buy, sell), (
        "366-day holding spanning a leap year but exactly 12 calendar months must NOT qualify"
    )


def test_leap_year_one_day_over_eligible():
    """Buy Jan 1 2020, sell Jan 2 2021: 366 days + 1 = eligible."""
    buy = datetime(2020, 1, 1)
    sell = datetime(2021, 1, 2)
    assert _is_long_term(buy, sell)


def test_clearly_long_term():
    """Buy Jan 1 2020, sell Jun 30 2022: well over 12 months."""
    buy = datetime(2020, 1, 1)
    sell = datetime(2022, 6, 30)
    assert _is_long_term(buy, sell)


def test_clearly_short_term():
    """Buy Jan 1 2022, sell Jun 30 2022: 6 months = short term."""
    buy = datetime(2022, 1, 1)
    sell = datetime(2022, 6, 30)
    assert not _is_long_term(buy, sell)


def test_feb29_purchase_leap_year():
    """Buy Feb 29 2020 (leap day), sell Feb 28 2021: exactly 12 months by ATO rounding."""
    buy = datetime(2020, 2, 29)
    sell = datetime(2021, 2, 28)
    # 12 months after Feb 29 2020 = Feb 28 2021 (since Feb 29 2021 doesn't exist)
    # Selling ON Feb 28 2021 = exactly 12 months = NOT eligible
    assert not _is_long_term(buy, sell), (
        "Selling on the 12-month anniversary (adjusted for non-existent date) must NOT qualify"
    )


def test_feb29_purchase_one_day_over():
    """Buy Feb 29 2020, sell Mar 1 2021: more than 12 months = eligible."""
    buy = datetime(2020, 2, 29)
    sell = datetime(2021, 3, 1)
    assert _is_long_term(buy, sell)


def test_fy_boundary_typical():
    """
    Typical FY25 tax scenario: buy in FY23, sell in FY25.
    Buy Aug 1 2022, sell Aug 2 2023 = more than 12 months = eligible.
    Buy Aug 1 2022, sell Aug 1 2023 = exactly 12 months = NOT eligible.
    """
    buy = datetime(2022, 8, 1)
    assert not _is_long_term(buy, datetime(2023, 8, 1))
    assert _is_long_term(buy, datetime(2023, 8, 2))
