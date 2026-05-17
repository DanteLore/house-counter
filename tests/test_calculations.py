"""
Tests for price_paid/calculations.py  -  market summary metrics.

Each function is tested for:
  - Correct mathematical result (hand-verified)
  - Edge/boundary conditions (empty data, single year, missing values)
  - Correct exclusion of latest_year (always incomplete)
  - Correct year-range filtering
  - Correct handling of None / non-numeric inputs

Statistical methods used:
  - CAGR: compound annual growth rate = (Vn/V0)^(1/n) - 1
  - CV:   coefficient of variation = stdev(medians) / mean(medians)
  - Turnover: mean(annual_sales) / address_stock
  - Premium: mean(polygon_median / baseline_median) per year
"""

import pytest
from price_paid.calculations import (
    _safe_float,
    _filtered_stats,
    price_growth_cagr,
    price_volatility,
    annual_turnover_rate,
    average_new_build_share,
    average_premium_vs_baseline,
    rank_polygons,
    build_cross_polygon_narrative,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_stats(years_and_medians, count=100):
    """Build minimal stats rows: {year, median_price, count}."""
    return [
        {"year": str(y), "median_price": float(m), "count": count,
         "min_price": m * 0.5, "max_price": m * 2,
         "mean_price": m, "p25_price": m * 0.8, "p75_price": m * 1.2}
        for y, m in years_and_medians
    ]


def make_mix(years_and_counts, new_build_frac=0.1):
    """Build minimal mix rows with a fixed new-build fraction."""
    rows = []
    for year, total in years_and_counts:
        new_cnt = int(total * new_build_frac)
        old_cnt = total - new_cnt
        rows.append({"year": str(year), "count": new_cnt, "old_new": "Y"})
        rows.append({"year": str(year), "count": old_cnt, "old_new": "N"})
    return rows


LATEST = "2025"


# ---------------------------------------------------------------------------
# _safe_float
# ---------------------------------------------------------------------------

class TestSafeFloat:
    def test_int(self):
        assert _safe_float(200_000) == 200_000.0

    def test_float_string(self):
        assert _safe_float("250000.5") == pytest.approx(250_000.5)

    def test_none_returns_none(self):
        assert _safe_float(None) is None

    def test_empty_string_returns_none(self):
        assert _safe_float("") is None

    def test_non_numeric_string_returns_none(self):
        assert _safe_float("n/a") is None

    def test_zero_returns_zero(self):
        assert _safe_float(0) == 0.0


# ---------------------------------------------------------------------------
# _filtered_stats
# ---------------------------------------------------------------------------

class TestFilteredStats:
    ROWS = make_stats([(2020, 200_000), (2021, 210_000), (2022, 220_000), (2023, 230_000)])

    def test_latest_year_excluded(self):
        result = _filtered_stats(self.ROWS, latest_year="2023")
        years = [r["year"] for r in result]
        assert "2023" not in years
        assert len(result) == 3

    def test_from_year_inclusive(self):
        result = _filtered_stats(self.ROWS, latest_year=LATEST, from_year="2021")
        assert all(r["year"] >= "2021" for r in result)
        assert "2020" not in [r["year"] for r in result]

    def test_to_year_inclusive(self):
        result = _filtered_stats(self.ROWS, latest_year=LATEST, to_year="2021")
        assert all(r["year"] <= "2021" for r in result)
        assert "2022" not in [r["year"] for r in result]

    def test_range_both_ends(self):
        result = _filtered_stats(self.ROWS, latest_year=LATEST, from_year="2021", to_year="2022")
        years = [r["year"] for r in result]
        assert years == ["2021", "2022"]

    def test_empty_rows(self):
        assert _filtered_stats([], latest_year=LATEST) == []

    def test_all_excluded_by_latest(self):
        rows = make_stats([(2025, 300_000)])
        assert _filtered_stats(rows, latest_year="2025") == []


# ---------------------------------------------------------------------------
# price_growth_cagr
# ---------------------------------------------------------------------------
# CAGR formula: (Vn / V0) ^ (1 / n) - 1
# Example: £200k → £242k over 2 years = (242/200)^0.5 - 1 = 0.1 = 10%/yr

class TestPriceGrowthCagr:
    def test_known_cagr_10pct(self):
        # 200_000 → 242_000 in 2 years: CAGR = (242/200)^(1/2) - 1 = 10%
        rows = make_stats([(2020, 200_000), (2021, 220_000), (2022, 242_000)])
        result = price_growth_cagr(rows, latest_year=LATEST)
        assert result is not None
        cagr, y0, yn = result
        assert cagr == pytest.approx(10.0, rel=1e-4)
        assert y0 == "2020"
        assert yn == "2022"

    def test_flat_prices_give_zero_cagr(self):
        rows = make_stats([(2020, 250_000), (2021, 250_000), (2022, 250_000)])
        cagr, *_ = price_growth_cagr(rows, latest_year=LATEST)
        assert cagr == pytest.approx(0.0, abs=1e-6)

    def test_declining_prices_give_negative_cagr(self):
        # 400_000 → 324_000 over 2 years: (324/400)^0.5 - 1 = -0.1 = -10%
        rows = make_stats([(2020, 400_000), (2021, 360_000), (2022, 324_000)])
        cagr, *_ = price_growth_cagr(rows, latest_year=LATEST)
        assert cagr == pytest.approx(-10.0, rel=1e-4)

    def test_single_year_returns_none(self):
        rows = make_stats([(2022, 250_000)])
        assert price_growth_cagr(rows, latest_year=LATEST) is None

    def test_empty_returns_none(self):
        assert price_growth_cagr([], latest_year=LATEST) is None

    def test_latest_year_excluded_from_cagr(self):
        # 2025 is LATEST and must not be used as the end-point, inflating the CAGR.
        rows = make_stats([(2020, 200_000), (2022, 242_000), (2025, 999_999)])
        cagr, y0, yn = price_growth_cagr(rows, latest_year="2025")
        assert yn == "2022"
        assert cagr == pytest.approx(10.0, rel=1e-4)

    def test_year_range_respected(self):
        rows = make_stats([(2018, 100_000), (2020, 200_000), (2022, 242_000)])
        cagr, y0, yn = price_growth_cagr(rows, latest_year=LATEST, from_year="2020")
        assert y0 == "2020"
        assert yn == "2022"

    def test_cagr_is_annualised(self):
        # Over 4 years, doubling = CAGR of 2^(1/4)-1 ≈ 18.92%
        rows = make_stats([(2018, 100_000), (2022, 200_000)])
        cagr, *_ = price_growth_cagr(rows, latest_year=LATEST)
        expected = (2.0 ** (1 / 4) - 1) * 100
        assert cagr == pytest.approx(expected, rel=1e-4)


# ---------------------------------------------------------------------------
# price_volatility
# ---------------------------------------------------------------------------
# CV = stdev(medians) / mean(medians) * 100
# High CV = prices swung a lot year to year; low CV = smooth trend.
# Requires at least 3 years to be meaningful.

class TestPriceVolatility:
    def test_known_cv(self):
        import statistics as st
        medians = [200_000, 250_000, 300_000, 200_000, 250_000]
        rows = make_stats(list(zip(range(2018, 2023), medians)))
        result = price_volatility(rows, latest_year=LATEST)
        expected = st.stdev(medians) / st.mean(medians) * 100
        assert result == pytest.approx(expected, rel=1e-4)

    def test_perfectly_flat_prices_give_zero_cv(self):
        rows = make_stats([(y, 250_000) for y in range(2018, 2023)])
        assert price_volatility(rows, latest_year=LATEST) == pytest.approx(0.0, abs=1e-6)

    def test_fewer_than_3_years_returns_none(self):
        rows = make_stats([(2020, 200_000), (2021, 210_000)])
        assert price_volatility(rows, latest_year=LATEST) is None

    def test_single_year_returns_none(self):
        assert price_volatility(make_stats([(2022, 200_000)]), latest_year=LATEST) is None

    def test_empty_returns_none(self):
        assert price_volatility([], latest_year=LATEST) is None

    def test_latest_year_excluded(self):
        # If LATEST were included, CV would be inflated by the outlier.
        rows = make_stats([(2020, 200_000), (2021, 200_000), (2022, 200_000), (2025, 999_999)])
        cv = price_volatility(rows, latest_year="2025")
        assert cv == pytest.approx(0.0, abs=1e-6)

    def test_higher_swings_give_higher_cv(self):
        stable   = make_stats([(y, 200_000 + y * 1_000) for y in range(5)])
        volatile = make_stats([(0, 100_000), (1, 400_000), (2, 150_000), (3, 350_000), (4, 200_000)])
        cv_s = price_volatility(stable,   latest_year=LATEST)
        cv_v = price_volatility(volatile, latest_year=LATEST)
        assert cv_v > cv_s


# ---------------------------------------------------------------------------
# annual_turnover_rate
# ---------------------------------------------------------------------------
# turnover = mean(annual_sales_count) / address_stock * 100
# Represents what fraction of the housing stock changes hands each year.

class TestAnnualTurnoverRate:
    def test_known_turnover(self):
        # 100 sales/yr out of 2000 addresses = 5% per year
        rows   = make_stats([(2020, 200_000), (2021, 210_000), (2022, 220_000)], count=100)
        result = annual_turnover_rate(rows, uprn_count=2000, latest_year=LATEST)
        assert result is not None
        rate, stock = result
        assert rate == pytest.approx(5.0)
        assert stock == 2000

    def test_no_uprn_count_returns_none(self):
        rows = make_stats([(2020, 200_000)], count=100)
        assert annual_turnover_rate(rows, uprn_count=None, latest_year=LATEST) is None

    def test_zero_uprn_count_returns_none(self):
        rows = make_stats([(2020, 200_000)], count=100)
        assert annual_turnover_rate(rows, uprn_count=0, latest_year=LATEST) is None

    def test_empty_stats_returns_none(self):
        assert annual_turnover_rate([], uprn_count=1000, latest_year=LATEST) is None

    def test_turnover_averages_across_years(self):
        # Year 1: 50 sales, Year 2: 150 sales → mean = 100 → 10% of 1000
        rows = [
            {"year": "2020", "count": 50,  "median_price": 200_000},
            {"year": "2021", "count": 150, "median_price": 210_000},
        ]
        rate, _ = annual_turnover_rate(rows, uprn_count=1000, latest_year=LATEST)
        assert rate == pytest.approx(10.0)

    def test_latest_year_excluded(self):
        # The 2025 row has 9999 sales which would wildly inflate the rate.
        rows = make_stats([(2020, 200_000), (2021, 200_000), (2025, 200_000)], count=100)
        rows[-1]["count"] = 9999
        rate, _ = annual_turnover_rate(rows, uprn_count=2000, latest_year="2025")
        assert rate == pytest.approx(5.0)  # only 2020 and 2021 contribute


# ---------------------------------------------------------------------------
# average_new_build_share
# ---------------------------------------------------------------------------
# Computed per-year (new_builds / total_that_year) then averaged across years.
# Per-year averaging prevents years with more total sales from dominating.

class TestAverageNewBuildShare:
    def test_known_share(self):
        # 10 new out of 100 total each year = 10%
        mix    = make_mix([(2020, 100), (2021, 100), (2022, 100)], new_build_frac=0.10)
        result = average_new_build_share(mix, latest_year=LATEST)
        assert result == pytest.approx(10.0, rel=1e-4)

    def test_zero_new_builds(self):
        mix = make_mix([(2020, 100), (2021, 100)], new_build_frac=0.0)
        assert average_new_build_share(mix, latest_year=LATEST) == pytest.approx(0.0, abs=1e-6)

    def test_all_new_builds(self):
        mix = make_mix([(2020, 100), (2021, 100)], new_build_frac=1.0)
        assert average_new_build_share(mix, latest_year=LATEST) == pytest.approx(100.0, rel=1e-4)

    def test_empty_returns_none(self):
        assert average_new_build_share([], latest_year=LATEST) is None

    def test_per_year_average_not_pooled(self):
        # Year 1: 10/100 = 10%.  Year 2: 90/100 = 90%.  Per-year average = 50%.
        # Pooled average would be 100/200 = 50% (same here, but test the distinct paths).
        # Use asymmetric year sizes to reveal pooling vs per-year difference:
        # Year 1: 10/1000 = 1%.  Year 2: 90/100 = 90%.  Per-year = 45.5%.  Pooled = 100/1100 ≈ 9.1%.
        mix = [
            {"year": "2020", "count": 10,  "old_new": "Y"},
            {"year": "2020", "count": 990, "old_new": "N"},
            {"year": "2021", "count": 90,  "old_new": "Y"},
            {"year": "2021", "count": 10,  "old_new": "N"},
        ]
        result = average_new_build_share(mix, latest_year=LATEST)
        # Per-year: (1% + 90%) / 2 = 45.5%
        assert result == pytest.approx(45.5, rel=1e-4)

    def test_latest_year_excluded(self):
        mix = make_mix([(2022, 100), (2025, 100)], new_build_frac=0.10)
        # Add a 100% new-build year in 2025 to contaminate if not excluded
        mix += [{"year": "2025", "count": 1000, "old_new": "Y"}]
        result = average_new_build_share(mix, latest_year="2025")
        assert result == pytest.approx(10.0, rel=1e-4)


# ---------------------------------------------------------------------------
# average_premium_vs_baseline
# ---------------------------------------------------------------------------
# Per-year: polygon_median / baseline_median * 100, then averaged across years.
# 100 = at baseline; 120 = 20% premium; 80 = 20% discount.

class TestAveragePremiumVsBaseline:
    def test_at_parity(self):
        stats = make_stats([(2020, 200_000), (2021, 210_000)])
        cmp   = {"2020": {"median_price": 200_000}, "2021": {"median_price": 210_000}}
        result = average_premium_vs_baseline(stats, cmp, latest_year=LATEST)
        assert result == pytest.approx(100.0)

    def test_consistent_20pct_premium(self):
        stats = make_stats([(2020, 240_000), (2021, 252_000)])
        cmp   = {"2020": {"median_price": 200_000}, "2021": {"median_price": 210_000}}
        result = average_premium_vs_baseline(stats, cmp, latest_year=LATEST)
        assert result == pytest.approx(120.0)

    def test_consistent_discount(self):
        stats = make_stats([(2020, 160_000), (2021, 168_000)])
        cmp   = {"2020": {"median_price": 200_000}, "2021": {"median_price": 210_000}}
        result = average_premium_vs_baseline(stats, cmp, latest_year=LATEST)
        assert result == pytest.approx(80.0)

    def test_no_overlap_returns_none(self):
        stats = make_stats([(2020, 200_000)])
        cmp   = {"2019": {"median_price": 190_000}}
        assert average_premium_vs_baseline(stats, cmp, latest_year=LATEST) is None

    def test_empty_stats_returns_none(self):
        assert average_premium_vs_baseline([], {}, latest_year=LATEST) is None

    def test_latest_year_excluded(self):
        stats = make_stats([(2022, 300_000), (2025, 999_999)])
        cmp   = {"2022": {"median_price": 200_000}, "2025": {"median_price": 100_000}}
        result = average_premium_vs_baseline(stats, cmp, latest_year="2025")
        assert result == pytest.approx(150.0)

    def test_per_year_average_not_pooled(self):
        # Year 1: 100% of baseline.  Year 2: 200% of baseline.  Mean = 150%.
        stats = make_stats([(2020, 200_000), (2021, 400_000)])
        cmp   = {"2020": {"median_price": 200_000}, "2021": {"median_price": 200_000}}
        result = average_premium_vs_baseline(stats, cmp, latest_year=LATEST)
        assert result == pytest.approx(150.0)


# ---------------------------------------------------------------------------
# rank_polygons
# ---------------------------------------------------------------------------

class TestRankPolygons:
    SUMMARIES = [
        {"name": "A", "cagr": 5.0},
        {"name": "B", "cagr": 3.0},
        {"name": "C", "cagr": 7.0},
    ]

    def test_higher_is_better_ranks_correctly(self):
        ranks = rank_polygons(self.SUMMARIES, "cagr", higher_is_better=True)
        assert ranks["C"] == 1
        assert ranks["A"] == 2
        assert ranks["B"] == 3

    def test_lower_is_better_ranks_correctly(self):
        summaries = [{"name": n, "volatility": v}
                     for n, v in [("A", 5.0), ("B", 2.0), ("C", 8.0)]]
        ranks = rank_polygons(summaries, "volatility", higher_is_better=False)
        assert ranks["B"] == 1  # lowest CV = most stable = best
        assert ranks["A"] == 2
        assert ranks["C"] == 3

    def test_missing_key_omitted(self):
        summaries = [{"name": "A", "cagr": 5.0}, {"name": "B"}]
        ranks = rank_polygons(summaries, "cagr")
        assert "A" in ranks
        assert "B" not in ranks

    def test_single_polygon(self):
        ranks = rank_polygons([{"name": "A", "cagr": 5.0}], "cagr")
        assert ranks["A"] == 1

    def test_empty_returns_empty(self):
        assert rank_polygons([], "cagr") == {}


# ---------------------------------------------------------------------------
# build_cross_polygon_narrative
# ---------------------------------------------------------------------------

class TestBuildCrossPolygonNarrative:
    def test_single_polygon_returns_empty(self):
        assert build_cross_polygon_narrative([{"name": "A", "cagr": 5.0}]) == []

    def test_empty_returns_empty(self):
        assert build_cross_polygon_narrative([]) == []

    def test_large_cagr_spread_mentioned(self):
        summaries = [{"name": "A", "cagr": 7.0}, {"name": "B", "cagr": 2.0}]
        sentences = build_cross_polygon_narrative(summaries)
        text = " ".join(sentences)
        assert "A" in text
        assert "B" in text
        assert "growth" in text.lower()

    def test_similar_cagr_lockstep_message(self):
        summaries = [{"name": "A", "cagr": 5.0}, {"name": "B", "cagr": 5.2}]
        sentences = build_cross_polygon_narrative(summaries)
        assert any("lockstep" in s or "similar" in s for s in sentences)

    def test_large_volatility_spread_mentioned(self):
        summaries = [{"name": "A", "volatility": 3.0}, {"name": "B", "volatility": 12.0}]
        sentences = build_cross_polygon_narrative(summaries)
        assert any("stability" in s.lower() or "volatile" in s.lower() for s in sentences)

    def test_large_premium_spread_mentioned(self):
        summaries = [{"name": "A", "vs_national": 130.0}, {"name": "B", "vs_national": 85.0}]
        sentences = build_cross_polygon_narrative(summaries)
        assert any("premium" in s.lower() for s in sentences)

    def test_no_duplicate_sentences_for_same_metric(self):
        summaries = [{"name": "A", "cagr": 7.0, "volatility": 3.0},
                     {"name": "B", "cagr": 2.0, "volatility": 12.0}]
        sentences = build_cross_polygon_narrative(summaries)
        growth_sentences = [s for s in sentences if "growth" in s.lower()]
        assert len(growth_sentences) == 1
