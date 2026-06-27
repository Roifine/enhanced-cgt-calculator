#!/usr/bin/env python3
"""
End-to-end tests for Australian CGT correctness.

Covers critical tax law rules, boundary conditions, and the full calculation pipeline.
"""

import os
import sys
import pytest
from datetime import datetime

# Set up src path
_tests_dir = os.path.dirname(os.path.abspath(__file__))
_src_dir = os.path.join(os.path.dirname(_tests_dir), 'src')
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from tax_optimizer import _is_long_term


class TestLongTermHoldingRule:
    """Verify the Australian 50% CGT discount eligibility rule."""

    def test_exactly_12_months_not_eligible(self):
        """Holding for EXACTLY 12 calendar months does NOT qualify for the discount."""
        purchase = datetime(2023, 1, 1)
        sale = datetime(2024, 1, 1)
        assert not _is_long_term(purchase, sale), (
            "Selling on the exact 12-month anniversary should NOT get the 50% discount"
        )

    def test_one_day_over_12_months_eligible(self):
        """12 months + 1 day qualifies for the discount."""
        purchase = datetime(2023, 1, 1)
        sale = datetime(2024, 1, 2)
        assert _is_long_term(purchase, sale), (
            "12 months + 1 day SHOULD qualify for the 50% CGT discount"
        )

    def test_june_boundary_not_eligible(self):
        """Objective scenario: buy 1 Jun 2022, sell 1 Jun 2023 - exactly 12 months."""
        purchase = datetime(2022, 6, 1)
        sale = datetime(2023, 6, 1)
        assert not _is_long_term(purchase, sale)

    def test_june_boundary_plus_one_day_eligible(self):
        """Objective scenario: buy 1 Jun 2022, sell 2 Jun 2023 - 12 months + 1 day."""
        purchase = datetime(2022, 6, 1)
        sale = datetime(2023, 6, 2)
        assert _is_long_term(purchase, sale)

    def test_short_term_clearly_not_eligible(self):
        """6-month holding period is clearly not eligible."""
        purchase = datetime(2023, 1, 1)
        sale = datetime(2023, 7, 1)
        assert not _is_long_term(purchase, sale)

    def test_two_years_eligible(self):
        """Holding for 2 years is clearly eligible."""
        purchase = datetime(2021, 1, 1)
        sale = datetime(2023, 1, 15)
        assert _is_long_term(purchase, sale)

    def test_leap_year_purchase_exact_boundary(self):
        """Buying on Feb 29 (leap year) - 12-month anniversary is Feb 28 next year."""
        purchase = datetime(2024, 2, 29)
        # 12-month anniversary is Feb 28, 2025 (no Feb 29 in non-leap year)
        sale_on_anniversary = datetime(2025, 2, 28)
        assert not _is_long_term(purchase, sale_on_anniversary), (
            "Feb 28 (12-month anniversary of Feb 29 purchase) should NOT get discount"
        )

    def test_leap_year_purchase_one_day_after(self):
        """Buying on Feb 29 (leap year) - Mar 1 next year is eligible."""
        purchase = datetime(2024, 2, 29)
        sale_day_after = datetime(2025, 3, 1)
        assert _is_long_term(purchase, sale_day_after)

    def test_leap_year_crossing_purchase(self):
        """Buying in non-leap year, holding through a leap year February."""
        # 2024 is a leap year; buy Jan 1 2023, sell Jan 1 2024 = 365 days
        purchase = datetime(2023, 1, 1)
        sale = datetime(2024, 1, 1)
        assert not _is_long_term(purchase, sale), (
            "Exactly 12 calendar months (Jan 1 to Jan 1) should NOT get discount, "
            "even when the year contains a leap day"
        )

    def test_same_day_sale_not_eligible(self):
        """Buying and selling the same day is not eligible."""
        d = datetime(2023, 6, 15)
        assert not _is_long_term(d, d)
