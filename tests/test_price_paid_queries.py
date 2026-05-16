"""
Tests for price_paid_queries.py

The key questions these tests answer:
- Does _aggregate_by_year produce correct statistics from a list of prices?
- Are percentiles computed in the right order (p25 < median < p75)?
- Does the polygon filter correctly exclude sales from adjacent postcodes
  whose centroid falls just outside the boundary?
- Does fetch_price_stats_for_polygon return both yearly stats and raw prices?
- Are deleted records (record_status = 'D') excluded from statistics?
  (The SQL handles this, but we verify the query string contains the filter.)
- Does an empty polygon (no matching sales) return empty results gracefully?

We mock run_query so no AWS credentials are needed.
The point-in-polygon filtering runs against real Shapely geometry.
"""

import pytest
from unittest.mock import patch
from pyproj import Transformer

import queries.price_paid_queries as ppq

_osgb_to_wgs84 = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)


def _osgb_ring(*osgb_corners):
    ring = [list(_osgb_to_wgs84.transform(e, n)) for e, n in osgb_corners]
    ring.append(ring[0])
    return [ring]


# 1km × 1km square near Thatcham
POLY_COORDS = _osgb_ring(
    (446000, 164000), (447000, 164000),
    (447000, 165000), (446000, 165000),
)

INSIDE_E, INSIDE_N = 446500, 164500
OUTSIDE_E, OUTSIDE_N = 448000, 164500


def _sale(year, price, easting=INSIDE_E, northing=INSIDE_N):
    return {
        "year": year,
        "price": str(float(price)),
        "eastings": str(easting),
        "northings": str(northing),
    }


def _postcode_rows(areas=("rg",)):
    return [{"postcode_area": a} for a in areas]


# ---------------------------------------------------------------------------
# _aggregate_by_year: statistics correctness
# ---------------------------------------------------------------------------

class TestAggregateByYear:
    def test_count_is_correct(self):
        result = ppq._aggregate_by_year({"2020": [100_000, 200_000, 300_000]})
        assert result[0]["count"] == 3

    def test_min_and_max(self):
        result = ppq._aggregate_by_year({"2020": [150_000, 300_000, 225_000]})
        assert result[0]["min_price"] == 150_000
        assert result[0]["max_price"] == 300_000

    def test_median_single_value(self):
        result = ppq._aggregate_by_year({"2020": [250_000]})
        assert result[0]["median_price"] == pytest.approx(250_000)

    def test_median_even_count(self):
        result = ppq._aggregate_by_year({"2020": [100_000, 200_000, 300_000, 400_000]})
        assert result[0]["median_price"] == pytest.approx(250_000)

    def test_mean_is_arithmetic_mean(self):
        result = ppq._aggregate_by_year({"2020": [100_000, 200_000, 300_000]})
        assert result[0]["mean_price"] == pytest.approx(200_000)

    def test_p25_less_than_median_less_than_p75(self):
        # The percentile ordering is fundamental — if p25 > median a chart would look wrong.
        prices = [100_000, 150_000, 200_000, 250_000, 300_000, 350_000, 400_000, 450_000]
        result = ppq._aggregate_by_year({"2020": prices})
        r = result[0]
        assert r["p25_price"] < r["median_price"] < r["p75_price"]

    def test_p25_and_p75_bracket_majority_of_prices(self):
        # At least 50% of prices should fall between p25 and p75.
        prices = list(range(100_000, 500_001, 10_000))  # 41 values
        result = ppq._aggregate_by_year({"2020": prices})
        r = result[0]
        between = [p for p in prices if r["p25_price"] <= p <= r["p75_price"]]
        assert len(between) >= len(prices) * 0.5

    def test_results_sorted_by_year(self):
        data = {"2022": [300_000], "2020": [200_000], "2021": [250_000]}
        result = ppq._aggregate_by_year(data)
        years = [r["year"] for r in result]
        assert years == sorted(years)

    def test_multiple_years_each_have_independent_stats(self):
        data = {"2020": [100_000, 200_000], "2021": [300_000, 400_000]}
        result = ppq._aggregate_by_year(data)
        assert len(result) == 2
        assert result[0]["median_price"] < result[1]["median_price"]

    def test_empty_year_skipped(self):
        # Guard against a year key with no prices being emitted as a row.
        result = ppq._aggregate_by_year({"2020": [], "2021": [200_000]})
        assert len(result) == 1
        assert result[0]["year"] == "2021"

    def test_single_price_p25_equals_p75_equals_median(self):
        # With one data point all percentiles must be that price.
        result = ppq._aggregate_by_year({"2020": [250_000]})
        r = result[0]
        assert r["p25_price"] == r["median_price"] == r["p75_price"] == 250_000


# ---------------------------------------------------------------------------
# fetch_price_stats_for_polygon: point-in-polygon filtering
# ---------------------------------------------------------------------------

class TestFetchPriceStatsForPolygon:
    def _run(self, sales, postcode_areas=("rg",)):
        query_results = [_postcode_rows(postcode_areas), sales]
        with patch("queries.price_paid_queries.run_query", side_effect=query_results):
            return ppq.fetch_price_stats_for_polygon(POLY_COORDS)

    def test_sale_inside_polygon_is_included(self):
        yearly, all_prices = self._run([_sale("2020", 250_000)])
        assert len(yearly) == 1
        assert yearly[0]["count"] == 1

    def test_sale_outside_polygon_is_excluded(self):
        # A postcode centroid in an adjacent area — Athena bbox passes it through
        # but the Python polygon filter must catch it.
        yearly, all_prices = self._run([_sale("2020", 250_000, OUTSIDE_E, OUTSIDE_N)])
        assert yearly == []
        assert all_prices == []

    def test_mix_inside_and_outside(self):
        sales = [
            _sale("2020", 200_000, INSIDE_E, INSIDE_N),
            _sale("2020", 500_000, OUTSIDE_E, OUTSIDE_N),
        ]
        yearly, all_prices = self._run(sales)
        assert yearly[0]["count"] == 1
        assert yearly[0]["median_price"] == pytest.approx(200_000)

    def test_returns_all_prices_as_tuples(self):
        sales = [
            _sale("2020", 200_000),
            _sale("2021", 300_000),
        ]
        yearly, all_prices = self._run(sales)
        assert len(all_prices) == 2
        assert all(isinstance(t, tuple) and len(t) == 2 for t in all_prices)
        assert all_prices[0][0] in ("2020", "2021")

    def test_no_postcode_areas_returns_empty(self):
        # If the polygon falls outside any postcode coverage (e.g. sea, moorland),
        # we must return empty rather than querying the whole PPD table.
        with patch("queries.price_paid_queries.run_query", return_value=[]):
            yearly, all_prices = ppq.fetch_price_stats_for_polygon(POLY_COORDS)
        assert yearly == []
        assert all_prices == []

    def test_empty_sales_returns_empty(self):
        yearly, all_prices = self._run([])
        assert yearly == []
        assert all_prices == []

    def test_malformed_price_row_skipped(self):
        sales = [
            {"year": "2020", "price": "not-a-number", "eastings": str(INSIDE_E), "northings": str(INSIDE_N)},
            _sale("2020", 250_000),
        ]
        yearly, all_prices = self._run(sales)
        assert yearly[0]["count"] == 1

    def test_multiple_years_aggregated_separately(self):
        sales = [
            _sale("2019", 200_000),
            _sale("2019", 220_000),
            _sale("2023", 350_000),
        ]
        yearly, _ = self._run(sales)
        assert len(yearly) == 2
        years = [r["year"] for r in yearly]
        assert "2019" in years and "2023" in years

    def test_deleted_records_excluded_by_sql(self):
        # record_status = 'D' filtering happens in SQL. Verify the filter is present
        # in the generated query string rather than relying on Python post-processing.
        captured = {}
        original_run_query = ppq.run_query if hasattr(ppq, "run_query") else None

        call_count = [0]
        def capture_sql(sql):
            call_count[0] += 1
            if call_count[0] == 1:
                return _postcode_rows()
            captured["sql"] = sql
            return []

        with patch("queries.price_paid_queries.run_query", side_effect=capture_sql):
            ppq.fetch_price_stats_for_polygon(POLY_COORDS)

        assert "record_status" in captured.get("sql", ""), \
            "SQL must filter out deleted records (record_status != 'D')"


# ---------------------------------------------------------------------------
# _aggregate_by_year: edge cases for unusual market conditions
# ---------------------------------------------------------------------------

class TestAggregateEdgeCases:
    def test_identical_prices_all_percentiles_equal(self):
        # Unusual but valid: all sales at the same price (e.g. new-build estate).
        result = ppq._aggregate_by_year({"2020": [250_000] * 20})
        r = result[0]
        assert r["min_price"] == r["max_price"] == r["median_price"] == 250_000

    def test_two_prices_median_is_mean(self):
        result = ppq._aggregate_by_year({"2020": [100_000, 300_000]})
        assert result[0]["median_price"] == pytest.approx(200_000)

    def test_large_price_spread_does_not_error(self):
        # Studio flat vs mansion in same postcode
        result = ppq._aggregate_by_year({"2020": [50_000, 10_000_000]})
        assert result[0]["min_price"] == 50_000
        assert result[0]["max_price"] == 10_000_000
