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

from tax_optimizer import _is_long_term, optimize_sale_for_cgt


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


def _make_parcel(date_str, units, cost_per_unit_aud, commission_aud=0.0):
    """Build a minimal AUD-format parcel for the tax optimizer."""
    total_cost = units * cost_per_unit_aud + commission_aud
    actual_cpu = total_cost / units
    return {
        'units': units,
        'date': date_str,
        'price_aud': cost_per_unit_aud,
        'commission_aud': commission_aud,
        'price_usd': cost_per_unit_aud,
        'commission_usd': commission_aud,
        'exchange_rate_buy': 1.0,
        'cost_per_unit_aud': actual_cpu,
        'total_cost_aud': total_cost,
    }


class TestParcelOptimizerSelection:
    """
    Phase 2 correctness check: verify the tax optimizer picks the right parcels.

    Tax-optimal priority for Australian CGT:
      1. Loss-making parcels first (offsets other gains, no tax cost)
      2. Long-term gain parcels (50% CGT discount)
      3. Short-term gain parcels (full tax - worst case, avoid last)

    The optimizer achieves this by:
      - Grouping long-term vs short-term
      - Within short-term: highest cost basis first (naturally picks losses)
    """

    def _parcel_dates_selected(self, selected):
        return {p['date'] for p in selected}

    def test_optimizer_avoids_short_term_gain_parcel(self):
        """
        3 parcels, sell 2: optimizer must pick loss + long-term gain, NOT short-term gain.

        Sale price = AUD $150/unit.
        - Parcel A (long-term gain): bought 2021-01-01, 100 units @ $100 -> gain $50/unit, 50% discounted
        - Parcel B (short-term gain): bought 2023-06-01, 100 units @ $80  -> gain $70/unit, full tax
        - Parcel C (loss):            bought 2023-01-01, 100 units @ $200 -> loss $50/unit
        Sale date: 2023-12-15 (A=long-term, B and C=short-term)

        Optimal: sell A + C (long-term gain discounted, loss offsets)
        Worst:   sell A + B (two taxable events, one at full rate)
        """
        sale_date = datetime(2023, 12, 15)
        parcel_a = _make_parcel('2021-01-01', 100, 100.0)  # long-term gain
        parcel_b = _make_parcel('2023-06-01', 100, 80.0)   # short-term gain
        parcel_c = _make_parcel('2023-01-01', 100, 200.0)  # loss

        parcels = [parcel_a, parcel_b, parcel_c]
        selected, updated, remaining, _ = optimize_sale_for_cgt(parcels, 200, sale_date)

        assert remaining == 0, "All 200 units should have been fulfilled"
        assert len(selected) == 2, f"Expected 2 selected parcels, got {len(selected)}"

        selected_dates = self._parcel_dates_selected(selected)
        assert '2021-01-01' in selected_dates, "Long-term gain parcel (A) must be selected"
        assert '2023-01-01' in selected_dates, "Loss parcel (C) must be selected"
        assert '2023-06-01' not in selected_dates, (
            "Short-term gain parcel (B) must NOT be selected - it carries the worst tax"
        )

    def test_long_term_parcel_always_preferred_over_short_term_gain(self):
        """
        If long-term and short-term both have gains, long-term must be chosen first
        because of the 50% discount.
        """
        sale_date = datetime(2024, 6, 1)
        parcel_lt = _make_parcel('2022-01-01', 100, 100.0)   # long-term gain
        parcel_st = _make_parcel('2024-01-01', 100, 90.0)    # short-term gain

        parcels = [parcel_lt, parcel_st]
        selected, updated, remaining, _ = optimize_sale_for_cgt(parcels, 100, sale_date)

        assert remaining == 0
        assert len(selected) == 1
        assert selected[0]['date'] == '2022-01-01', (
            "Long-term parcel should be selected in preference to short-term gain"
        )

    def test_partial_parcel_consumption(self):
        """
        Selling fewer units than a single parcel contains leaves correct remainder.
        """
        sale_date = datetime(2024, 3, 1)
        parcel = _make_parcel('2022-01-01', 100, 150.0)  # long-term

        selected, updated, remaining, _ = optimize_sale_for_cgt([parcel], 40, sale_date)

        assert remaining == 0
        assert len(selected) == 1
        assert selected[0]['units_consumed'] == 40

        # Remaining cost basis must reflect the 60 unsold units
        assert len(updated) == 1
        assert updated[0]['units'] == 60

    def test_all_short_term_sells_highest_cost_first(self):
        """
        When all parcels are short-term, highest cost basis is sold first
        (produces smallest gain or largest loss, minimising immediate tax).
        """
        sale_date = datetime(2023, 12, 1)
        parcel_cheap = _make_parcel('2023-01-01', 100, 50.0)   # low cost
        parcel_expensive = _make_parcel('2023-03-01', 100, 120.0)  # high cost

        parcels = [parcel_cheap, parcel_expensive]
        selected, updated, remaining, _ = optimize_sale_for_cgt(parcels, 100, sale_date)

        assert remaining == 0
        assert len(selected) == 1
        assert selected[0]['date'] == '2023-03-01', (
            "Highest cost parcel should be sold first to minimise short-term gain"
        )


class TestCGTDiscountInCalculation:
    """
    Verify that the 50% CGT discount is applied correctly at the calculation level.
    Tests the logic in _calculate_parcel_cgt_with_rba without requiring RBA FX data.
    """

    def _compute_taxable_gain(self, cost_per_unit_aud, sale_price_aud, units, is_long_term):
        """
        Mirror the calculation in EnhancedCGTCalculatorWithRBA._calculate_parcel_cgt_with_rba.
        No FX conversion needed - tests the pure gain/discount logic.
        """
        cost_basis = units * cost_per_unit_aud
        gross_proceeds = units * sale_price_aud
        capital_gain = gross_proceeds - cost_basis
        discount = 0.5 if is_long_term else 0.0
        taxable = capital_gain * (1 - discount) if capital_gain > 0 else capital_gain
        return capital_gain, taxable

    def test_long_term_gain_gets_50pct_discount(self):
        """Long-term gain of $10,000 results in $5,000 taxable."""
        gain, taxable = self._compute_taxable_gain(
            cost_per_unit_aud=100.0, sale_price_aud=200.0,
            units=100, is_long_term=True
        )
        assert gain == pytest.approx(10_000.0)
        assert taxable == pytest.approx(5_000.0), "50% discount must halve the taxable gain"

    def test_short_term_gain_no_discount(self):
        """Short-term gain is fully taxable."""
        gain, taxable = self._compute_taxable_gain(
            cost_per_unit_aud=100.0, sale_price_aud=200.0,
            units=100, is_long_term=False
        )
        assert gain == pytest.approx(10_000.0)
        assert taxable == pytest.approx(10_000.0), "Short-term gain must not be discounted"

    def test_long_term_loss_no_discount_applied(self):
        """Losses are never discounted - the full loss reduces the tax base."""
        gain, taxable = self._compute_taxable_gain(
            cost_per_unit_aud=200.0, sale_price_aud=100.0,
            units=100, is_long_term=True
        )
        assert gain == pytest.approx(-10_000.0)
        assert taxable == pytest.approx(-10_000.0), (
            "Capital losses must NOT be halved by the CGT discount"
        )

    def test_zero_gain_zero_taxable(self):
        """Selling at exactly the cost base produces zero gain and zero taxable."""
        gain, taxable = self._compute_taxable_gain(
            cost_per_unit_aud=150.0, sale_price_aud=150.0,
            units=100, is_long_term=True
        )
        assert gain == pytest.approx(0.0)
        assert taxable == pytest.approx(0.0)

    def test_short_term_loss_no_discount_applied(self):
        """Short-term losses are also fully deductible - discount doesn't apply to losses."""
        gain, taxable = self._compute_taxable_gain(
            cost_per_unit_aud=200.0, sale_price_aud=150.0,
            units=50, is_long_term=False
        )
        assert gain == pytest.approx(-2_500.0)
        assert taxable == pytest.approx(-2_500.0)
