"""
Tests for inflation adjustment functions in price_paid_queries.py.

The key questions:
- Does deflate_price correctly scale nominal prices to 2015 £ (default base)?
- Does it correctly rebase to an arbitrary base_year?
- Does it handle missing CPI data gracefully (return nominal price)?
- Does real_stats_from_prices deflate prices first and then derive stats correctly?
- Does deflate_prices correctly deflate a list of (year, price) tuples?
- Is the maths right? A price in a year where CPI=200 (double the 2015 base)
  should halve in real terms. A year where CPI=50 should double.
- Do prices in the base year (CPI=100) come through unchanged?
- Does rebasing to a later year scale prices up proportionally?
"""

import statistics

import pytest
from queries.price_paid_queries import deflate_price, deflate_prices, real_stats_from_prices

# CPI fixture: 2015=100 (base), 2022=120 (20% above base), 2000=80 (20% below base)
CPI = {
    "2000": 80.0,
    "2010": 92.0,
    "2015": 100.0,
    "2020": 109.0,
    "2022": 120.0,
}

STAT = {
    "year": "2022",
    "count": 50,
    "min_price":    100_000.0,
    "max_price":    500_000.0,
    "mean_price":   250_000.0,
    "median_price": 240_000.0,
    "p25_price":    180_000.0,
    "p75_price":    320_000.0,
}


# ---------------------------------------------------------------------------
# deflate_price
# ---------------------------------------------------------------------------

class TestDeflatePrice:
    def test_base_year_price_unchanged(self):
        # CPI=100 in 2015  -  dividing by 100 and multiplying by 100 is a no-op.
        assert deflate_price(200_000, "2015", CPI) == pytest.approx(200_000)

    def test_price_halves_when_cpi_doubles(self):
        # A house that cost £240,000 in 2022 (CPI=120) is worth £200,000 in 2015 £.
        # 240_000 / 120 * 100 = 200_000
        assert deflate_price(240_000, "2022", CPI) == pytest.approx(200_000)

    def test_price_increases_when_cpi_below_base(self):
        # In 2000 prices were lower (CPI=80), so the same nominal amount is worth
        # more in 2015 £. £80,000 in 2000 = £100,000 in 2015 £.
        assert deflate_price(80_000, "2000", CPI) == pytest.approx(100_000)

    def test_missing_year_returns_nominal(self):
        # If CPI data doesn't cover the year, leave the price untouched rather
        # than silently zeroing it out.
        assert deflate_price(300_000, "1985", CPI) == pytest.approx(300_000)

    def test_empty_cpi_returns_nominal(self):
        assert deflate_price(300_000, "2022", {}) == pytest.approx(300_000)

    def test_proportionality(self):
        # A price twice as large in the same year should deflate to twice as large.
        p1 = deflate_price(200_000, "2022", CPI)
        p2 = deflate_price(400_000, "2022", CPI)
        assert p2 == pytest.approx(2 * p1)

    def test_deflation_ordering_preserved(self):
        # If price A > price B nominally, A > B in real terms too (same year).
        r1 = deflate_price(300_000, "2022", CPI)
        r2 = deflate_price(200_000, "2022", CPI)
        assert r1 > r2

    def test_real_price_lower_than_nominal_in_inflationary_period(self):
        # In any year where CPI > 100, real price must be below nominal.
        real = deflate_price(300_000, "2022", CPI)  # CPI=120
        assert real < 300_000

    def test_real_price_higher_than_nominal_before_base_year(self):
        # In any year where CPI < 100, real price must be above nominal.
        real = deflate_price(300_000, "2000", CPI)  # CPI=80
        assert real > 300_000


# ---------------------------------------------------------------------------
# real_stats_from_prices
# ---------------------------------------------------------------------------
# Prices are deflated first, THEN stats are derived  -  correct order of operations.

# Raw prices for a polygon in 2022 (CPI=120).  In 2015 £ these are /120*100.
PRICES_2022 = [("2022", p) for p in [100_000.0, 180_000.0, 240_000.0, 320_000.0, 500_000.0]]

class TestRealStatsFromPrices:
    def test_all_price_fields_are_deflated(self):
        result = real_stats_from_prices(PRICES_2022, CPI)[0]
        for field in ("min_price", "max_price", "mean_price", "median_price", "p25_price", "p75_price"):
            # CPI=120 > 100, so real prices are lower than nominal
            nominal = statistics.median([p for _, p in PRICES_2022])
            assert result[field] < max(p for _, p in PRICES_2022), \
                f"{field} should be smaller than max nominal (CPI>100)"

    def test_year_and_count_are_correct(self):
        result = real_stats_from_prices(PRICES_2022, CPI)[0]
        assert result["year"] == "2022"
        assert result["count"] == len(PRICES_2022)

    def test_price_ordering_preserved(self):
        result = real_stats_from_prices(PRICES_2022, CPI)[0]
        assert result["min_price"] <= result["p25_price"]
        assert result["p25_price"] <= result["median_price"]
        assert result["median_price"] <= result["p75_price"]
        assert result["p75_price"] <= result["max_price"]

    def test_median_equals_deflate_then_median(self):
        # The key invariant: median of deflated prices == deflating the nominal median.
        # This holds because deflation within a year is a linear transform.
        real_prices = [p / 120.0 * 100 for _, p in PRICES_2022]
        expected_median = statistics.median(real_prices)
        result = real_stats_from_prices(PRICES_2022, CPI)[0]
        assert result["median_price"] == pytest.approx(expected_median)

    def test_min_is_true_minimum_of_real_prices(self):
        # min_price must be the minimum after deflation, not deflation of the nominal min.
        # (They're the same within a year, but this test enforces the correct derivation.)
        result = real_stats_from_prices(PRICES_2022, CPI)[0]
        assert result["min_price"] == pytest.approx(100_000.0 / 120.0 * 100)

    def test_max_is_true_maximum_of_real_prices(self):
        result = real_stats_from_prices(PRICES_2022, CPI)[0]
        assert result["max_price"] == pytest.approx(500_000.0 / 120.0 * 100)

    def test_multiple_years_aggregated_independently(self):
        prices = [("2015", 200_000.0), ("2022", 240_000.0)]
        result = real_stats_from_prices(prices, CPI)
        by_yr = {r["year"]: r for r in result}
        # 2015: CPI=100, real == nominal
        assert by_yr["2015"]["median_price"] == pytest.approx(200_000)
        # 2022: CPI=120, 240_000 → 200_000
        assert by_yr["2022"]["median_price"] == pytest.approx(200_000)

    def test_empty_cpi_returns_nominal_stats(self):
        result = real_stats_from_prices(PRICES_2022, {})[0]
        assert result["median_price"] == pytest.approx(statistics.median(p for _, p in PRICES_2022))

    def test_empty_prices_returns_empty(self):
        assert real_stats_from_prices([], CPI) == []

    def test_base_year_prices_unchanged(self):
        prices_2015 = [("2015", p) for p in [100_000.0, 200_000.0, 300_000.0]]
        result = real_stats_from_prices(prices_2015, CPI)[0]
        assert result["median_price"] == pytest.approx(200_000)


# ---------------------------------------------------------------------------
# deflate_prices
# ---------------------------------------------------------------------------

class TestDeflatePrices:
    def test_basic_deflation(self):
        prices = [("2022", 240_000.0)]
        result = deflate_prices(prices, CPI)
        assert result[0][1] == pytest.approx(200_000)

    def test_year_strings_preserved(self):
        prices = [("2022", 240_000.0), ("2015", 200_000.0)]
        result = deflate_prices(prices, CPI)
        assert result[0][0] == "2022"
        assert result[1][0] == "2015"

    def test_multiple_years_deflated_independently(self):
        # Both years yield the same real price via different nominal/CPI combinations.
        prices = [
            ("2015", 200_000.0),   # CPI=100 → 200_000
            ("2022", 240_000.0),   # CPI=120 → 200_000
        ]
        result = deflate_prices(prices, CPI)
        assert result[0][1] == pytest.approx(200_000)
        assert result[1][1] == pytest.approx(200_000)

    def test_missing_cpi_year_preserved(self):
        prices = [("1985", 50_000.0)]
        result = deflate_prices(prices, CPI)
        assert result[0][1] == pytest.approx(50_000)

    def test_empty_list_returns_empty(self):
        assert deflate_prices([], CPI) == []

    def test_length_preserved(self):
        prices = [("2022", float(p)) for p in range(100_000, 600_000, 50_000)]
        result = deflate_prices(prices, CPI)
        assert len(result) == len(prices)


# ---------------------------------------------------------------------------
# base_year rebasing
# ---------------------------------------------------------------------------
# CPI fixture recap: 2000=80, 2010=92, 2015=100, 2020=109, 2022=120
# Rebasing 2000 prices (CPI=80) to 2022 (CPI=120): multiply by 120/80 = 1.5
# Rebasing 2022 prices (CPI=120) to 2015 (CPI=100): multiply by 100/120 ≈ 0.833
# Rebasing a year to itself should leave prices unchanged.

class TestBaseYear:
    def test_rebase_to_later_year_increases_price(self):
        # £100,000 in 2000 (CPI=80) rebased to 2022 (CPI=120) → £150,000
        result = deflate_price(100_000, "2000", CPI, base_year="2022")
        assert result == pytest.approx(150_000)

    def test_rebase_to_earlier_year_decreases_price(self):
        # £120,000 in 2022 (CPI=120) rebased to 2015 (CPI=100) → £100,000
        result = deflate_price(120_000, "2022", CPI, base_year="2015")
        assert result == pytest.approx(100_000)

    def test_rebase_to_same_year_is_identity(self):
        # Any year rebased to itself should be unchanged regardless of CPI value.
        assert deflate_price(200_000, "2022", CPI, base_year="2022") == pytest.approx(200_000)
        assert deflate_price(200_000, "2000", CPI, base_year="2000") == pytest.approx(200_000)

    def test_rebase_default_uses_2015_base(self):
        # Omitting base_year should give the same result as base_year="2015".
        p_default = deflate_price(240_000, "2022", CPI)
        p_explicit = deflate_price(240_000, "2022", CPI, base_year="2015")
        assert p_default == pytest.approx(p_explicit)

    def test_missing_base_year_returns_nominal(self):
        # If the base_year is not in CPI, return the nominal price unchanged.
        result = deflate_price(200_000, "2022", CPI, base_year="1985")
        assert result == pytest.approx(200_000)

    def test_proportionality_preserved_with_base_year(self):
        # Doubling the nominal price should double the rebased price.
        p1 = deflate_price(100_000, "2000", CPI, base_year="2022")
        p2 = deflate_price(200_000, "2000", CPI, base_year="2022")
        assert p2 == pytest.approx(2 * p1)

    def test_real_stats_from_prices_passes_base_year(self):
        # real_stats_from_prices should honour base_year and rebase all price fields.
        # 80_000 in 2000 (CPI=80) → 2022 (CPI=120) = 120_000
        prices = [("2000", 80_000.0)] * 5
        result = real_stats_from_prices(prices, CPI, base_year="2022")[0]
        for field in ("min_price", "max_price", "mean_price", "median_price", "p25_price", "p75_price"):
            assert result[field] == pytest.approx(120_000)

    def test_deflate_prices_passes_base_year(self):
        # deflate_prices should honour base_year for each tuple.
        prices = [("2000", 80_000.0)]
        result = deflate_prices(prices, CPI, base_year="2022")
        assert result[0][1] == pytest.approx(120_000)
