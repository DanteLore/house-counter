"""
Tests for bua_queries.py

The key questions these tests answer:
- Does fetch_bua_as_geojson_coords correctly parse a WKT Polygon into a GeoJSON ring?
- For a MultiPolygon (e.g. a BUA with detached suburbs), does it pick the
  largest part, not just the first? Getting this wrong would silently return
  the wrong boundary for places like Southampton, which has satellite settlements.
- Are holes (interior rings) discarded? We store simple polygons only.
- Does the function handle missing/empty geometry gracefully?
- Does SQL injection in BUA codes get escaped?
"""

import pytest
from unittest.mock import patch
from shapely.geometry import Polygon, MultiPolygon
from shapely import wkt as shapely_wkt

import queries.bua_queries as bq


def _wkt_polygon(min_lon, min_lat, max_lon, max_lat):
    return (
        f"POLYGON (({min_lon} {min_lat}, {max_lon} {min_lat}, "
        f"{max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))"
    )


def _wkt_multipolygon(parts):
    """parts: list of (min_lon, min_lat, max_lon, max_lat) tuples"""
    def ring(a, b, c, d):
        return f"({a} {b}, {c} {b}, {c} {d}, {a} {d}, {a} {b})"
    polys = ", ".join(f"({ring(*p)})" for p in parts)
    return f"MULTIPOLYGON ({polys})"


# ---------------------------------------------------------------------------
# fetch_bua_as_geojson_coords: WKT parsing and geometry selection
# ---------------------------------------------------------------------------

class TestFetchBuaAsGeojsonCoords:
    def test_simple_polygon_returns_coordinate_ring(self):
        wkt = _wkt_polygon(-1.5, 51.0, -1.4, 51.1)
        with patch("queries.bua_queries.run_query", return_value=[{"geometry_wgs84_wkt": wkt}]):
            result = bq.fetch_bua_as_geojson_coords("E34000001")
        assert result is not None
        assert isinstance(result, list)
        assert isinstance(result[0], list)  # outer ring wrapper
        # First and last coordinate should be equal (closed ring)
        ring = result[0]
        assert ring[0] == ring[-1]

    def test_coordinate_order_is_lon_lat(self):
        # GeoJSON convention: [longitude, latitude] — not [lat, lon].
        # Getting this wrong would place polygons in the wrong hemisphere.
        wkt = _wkt_polygon(-1.5, 51.0, -1.4, 51.1)
        with patch("queries.bua_queries.run_query", return_value=[{"geometry_wgs84_wkt": wkt}]):
            result = bq.fetch_bua_as_geojson_coords("E34000001")
        ring = result[0]
        lons = [p[0] for p in ring]
        lats = [p[1] for p in ring]
        # Longitudes should be negative (west of meridian), latitudes ~51
        assert all(-2.0 < lon < 0.0 for lon in lons)
        assert all(50.0 < lat < 52.0 for lat in lats)

    def test_multipolygon_returns_largest_part(self):
        # Small suburb (1°×1° box) and large main settlement (5°×5° box).
        # Must return the large one.
        small = (-1.5, 51.0, -1.4, 51.1)   # 0.1° × 0.1°
        large = (-1.9, 51.0, -1.4, 51.5)   # 0.5° × 0.5°
        wkt = _wkt_multipolygon([small, large])
        with patch("queries.bua_queries.run_query", return_value=[{"geometry_wgs84_wkt": wkt}]):
            result = bq.fetch_bua_as_geojson_coords("E34000002")
        ring = result[0]
        lons = [p[0] for p in ring]
        lats = [p[1] for p in ring]
        lon_span = max(lons) - min(lons)
        lat_span = max(lats) - min(lats)
        # The returned ring should correspond to the large polygon, not the small one
        assert lon_span > 0.3, "Should have returned the large polygon"
        assert lat_span > 0.3, "Should have returned the large polygon"

    def test_multipolygon_does_not_return_smallest_part(self):
        # Three parts of different sizes — confirm the smallest is never returned.
        tiny   = (-1.51, 51.00, -1.50, 51.01)   # 0.01°
        medium = (-1.60, 51.00, -1.55, 51.05)   # 0.05°
        large  = (-1.90, 51.00, -1.40, 51.50)   # 0.5°
        wkt = _wkt_multipolygon([tiny, medium, large])
        with patch("queries.bua_queries.run_query", return_value=[{"geometry_wgs84_wkt": wkt}]):
            result = bq.fetch_bua_as_geojson_coords("E34000003")
        ring = result[0]
        lons = [p[0] for p in ring]
        lon_span = max(lons) - min(lons)
        assert lon_span > 0.3

    def test_holes_are_discarded(self):
        # A polygon with an interior ring (hole) — e.g. a park within a BUA.
        # We only store the exterior; holes would complicate all downstream geometry.
        wkt = (
            "POLYGON ((-1.9 51.0, -1.4 51.0, -1.4 51.5, -1.9 51.5, -1.9 51.0), "
            "(-1.7 51.1, -1.6 51.1, -1.6 51.2, -1.7 51.2, -1.7 51.1))"
        )
        with patch("queries.bua_queries.run_query", return_value=[{"geometry_wgs84_wkt": wkt}]):
            result = bq.fetch_bua_as_geojson_coords("E34000004")
        # Result should be a single ring (exterior only), not a list with interior rings
        assert len(result) == 1

    def test_no_rows_returns_none(self):
        with patch("queries.bua_queries.run_query", return_value=[]):
            result = bq.fetch_bua_as_geojson_coords("DOESNOTEXIST")
        assert result is None

    def test_empty_wkt_returns_none(self):
        with patch("queries.bua_queries.run_query", return_value=[{"geometry_wgs84_wkt": ""}]):
            result = bq.fetch_bua_as_geojson_coords("E34000005")
        assert result is None

    def test_sql_injection_in_bua_code_is_escaped(self):
        # A malicious BUA code containing a single quote must have it doubled (SQL escaping).
        # Doubling means the quote is treated as a literal character, not a string terminator.
        captured = {}
        def capture(sql):
            captured["sql"] = sql
            return []
        with patch("queries.bua_queries.run_query", side_effect=capture):
            bq.fetch_bua_as_geojson_coords("E1234' OR '1'='1")
        assert "''" in captured["sql"], "Single quotes must be escaped by doubling"
        # The injected OR clause should not appear as valid SQL syntax
        assert "OR '1'='1" not in captured["sql"]


# ---------------------------------------------------------------------------
# search_buas: SQL injection and result passthrough
# ---------------------------------------------------------------------------

class TestSearchBuas:
    def test_returns_run_query_result_directly(self):
        fake = [{"bua24cd": "E34000001", "bua24nm": "Newbury"}]
        with patch("queries.bua_queries.run_query", return_value=fake):
            result = bq.search_buas("Newbury")
        assert result == fake

    def test_sql_injection_in_search_name_escaped(self):
        captured = {}
        def capture(sql):
            captured["sql"] = sql
            return []
        with patch("queries.bua_queries.run_query", side_effect=capture):
            bq.search_buas("test' OR '1'='1")
        assert "''" in captured["sql"], "Single quotes must be escaped by doubling"
        assert "OR '1'='1" not in captured["sql"]

    def test_empty_results_returns_empty_list(self):
        with patch("queries.bua_queries.run_query", return_value=[]):
            result = bq.search_buas("ZZZnonexistent")
        assert result == []
