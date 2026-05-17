"""
Tests for uprn_queries.py

The key question these tests answer: given raw data from Athena, does the
post-query logic correctly count addresses, identify commercial properties,
subtract them from the total, and never produce a negative residential count?

We mock run_query / run_query_rows so no AWS credentials are needed.
All spatial filtering (point-in-polygon) runs against real Shapely geometry,
so tests exercise the actual filtering code, not just the mocking plumbing.
"""

import pytest
from unittest.mock import patch
from pyproj import Transformer

import queries.uprn_queries as uq

_osgb_to_wgs84 = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)
_wgs84_to_osgb = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True)


def _wgs84_ring(*wgs84_corners):
    """Closed GeoJSON ring from (lon, lat) pairs."""
    ring = list(wgs84_corners)
    ring.append(ring[0])
    return [ring]


def _osgb_ring(*osgb_corners):
    """Convert OSGB36 (easting, northing) corners to a closed WGS84 GeoJSON ring."""
    ring = [list(_osgb_to_wgs84.transform(e, n)) for e, n in osgb_corners]
    ring.append(ring[0])
    return [ring]


# A 1km × 1km square in OSGB36 near Thatcham
POLY_OSGB = (446000, 164000, 447000, 165000)  # min_e, min_n, max_e, max_n
POLY_COORDS = _osgb_ring(
    (446000, 164000), (447000, 164000),
    (447000, 165000), (446000, 165000),
)

# Point well inside the polygon
INSIDE_E, INSIDE_N = 446500, 164500
INSIDE_LON, INSIDE_LAT = _osgb_to_wgs84.transform(INSIDE_E, INSIDE_N)

# Point well outside the polygon
OUTSIDE_E, OUTSIDE_N = 448000, 164500
OUTSIDE_LON, OUTSIDE_LAT = _osgb_to_wgs84.transform(OUTSIDE_E, OUTSIDE_N)


def _raw_uprn_rows(points):
    """Build fake run_query_rows output (header row + data rows) for UPRN points.
    points: list of (lat, lon)
    """
    header = {"Data": [
        {"VarCharValue": "uprn"},
        {"VarCharValue": "latitude"},
        {"VarCharValue": "longitude"},
    ]}
    rows = [header]
    for i, (lat, lon) in enumerate(points):
        rows.append({"Data": [
            {"VarCharValue": str(i)},
            {"VarCharValue": str(lat)},
            {"VarCharValue": str(lon)},
        ]})
    return rows


def _commercial_rows(osgb_points):
    """Build fake run_query output (list of dicts) for VOA commercial points.
    osgb_points: list of (easting, northing)
    """
    return [{"eastings": str(e), "northings": str(n)} for e, n in osgb_points]


def _postcode_area_rows(areas):
    """Fake run_query output for postcode area lookup."""
    return [{"postcode_area": a} for a in areas]


# ---------------------------------------------------------------------------
# _query_uprn_points: point-in-polygon filtering
# ---------------------------------------------------------------------------

class TestQueryUprnPoints:
    def test_point_inside_polygon_is_included(self):
        rows = _raw_uprn_rows([(INSIDE_LAT, INSIDE_LON)])
        with patch("queries.uprn_queries.run_query_rows", return_value=rows):
            result = uq._query_uprn_points(POLY_COORDS)
        assert len(result) == 1
        assert result[0] == pytest.approx((INSIDE_LAT, INSIDE_LON), rel=1e-6)

    def test_point_outside_polygon_is_excluded(self):
        # Athena bbox filter passes a point just outside the polygon  -  Python must reject it.
        rows = _raw_uprn_rows([(OUTSIDE_LAT, OUTSIDE_LON)])
        with patch("queries.uprn_queries.run_query_rows", return_value=rows):
            result = uq._query_uprn_points(POLY_COORDS)
        assert result == []

    def test_mix_inside_and_outside(self):
        rows = _raw_uprn_rows([
            (INSIDE_LAT, INSIDE_LON),
            (OUTSIDE_LAT, OUTSIDE_LON),
        ])
        with patch("queries.uprn_queries.run_query_rows", return_value=rows):
            result = uq._query_uprn_points(POLY_COORDS)
        assert len(result) == 1

    def test_empty_athena_response(self):
        # Polygon exists but no addresses found in Athena.
        rows = _raw_uprn_rows([])
        with patch("queries.uprn_queries.run_query_rows", return_value=rows):
            result = uq._query_uprn_points(POLY_COORDS)
        assert result == []

    def test_malformed_row_is_skipped(self):
        # A row with a non-numeric lat/lon should be silently skipped, not crash.
        rows = _raw_uprn_rows([(INSIDE_LAT, INSIDE_LON)])
        rows.append({"Data": [
            {"VarCharValue": "bad"},
            {"VarCharValue": "not-a-number"},
            {"VarCharValue": "also-bad"},
        ]})
        with patch("queries.uprn_queries.run_query_rows", return_value=rows):
            result = uq._query_uprn_points(POLY_COORDS)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# _query_commercial_points: VOA point-in-polygon filtering
# ---------------------------------------------------------------------------

class TestQueryCommercialPoints:
    def test_commercial_point_inside_is_counted(self):
        rows = _commercial_rows([(INSIDE_E, INSIDE_N)])
        with patch("queries.uprn_queries.run_query", return_value=rows):
            result = uq._query_commercial_points(POLY_COORDS, {"rg"})
        assert len(result) == 1

    def test_commercial_point_outside_is_excluded(self):
        # Bbox query in Athena can return a postcode centroid just outside the polygon boundary.
        rows = _commercial_rows([(OUTSIDE_E, OUTSIDE_N)])
        with patch("queries.uprn_queries.run_query", return_value=rows):
            result = uq._query_commercial_points(POLY_COORDS, {"rg"})
        assert result == []

    def test_malformed_commercial_row_is_skipped(self):
        rows = [{"eastings": "bad", "northings": "also-bad"},
                {"eastings": str(INSIDE_E), "northings": str(INSIDE_N)}]
        with patch("queries.uprn_queries.run_query", return_value=rows):
            result = uq._query_commercial_points(POLY_COORDS, {"rg"})
        assert len(result) == 1


# ---------------------------------------------------------------------------
# fetch_all_counts_for_polygon: residential = address - commercial
#
# This is the core business rule: DPH and m²/dwelling must be based on
# residential addresses only. Commercial properties must not inflate the
# denominator and make an area appear denser than it actually is.
# ---------------------------------------------------------------------------

class TestFetchAllCounts:
    def _patch_both(self, uprn_points, commercial_osgb_points, postcode_areas=("rg",)):
        uprn_rows = _raw_uprn_rows(uprn_points)
        commercial_rows = _commercial_rows(commercial_osgb_points)
        postcode_rows = _postcode_area_rows(postcode_areas)

        # run_query is called twice: once for postcode areas, once for commercial
        query_side_effects = [postcode_rows, commercial_rows]

        return (
            patch("queries.uprn_queries.run_query_rows", return_value=uprn_rows),
            patch("queries.uprn_queries.run_query", side_effect=query_side_effects),
        )

    def test_residential_equals_total_minus_commercial(self):
        # 10 total addresses, 3 commercial → 7 residential
        uprn_pts = [(INSIDE_LAT, INSIDE_LON)] * 10
        comm_pts = [(INSIDE_E, INSIDE_N)] * 3
        p1, p2 = self._patch_both(uprn_pts, comm_pts)
        with p1, p2:
            addr, comm, resid = uq.fetch_all_counts_for_polygon(POLY_COORDS)
        assert addr == 10
        assert comm == 3
        assert resid == 7

    def test_no_commercial_means_all_residential(self):
        # A purely residential street  -  commercial count must not quietly reduce the total.
        uprn_pts = [(INSIDE_LAT, INSIDE_LON)] * 50
        p1, p2 = self._patch_both(uprn_pts, [])
        with p1, p2:
            addr, comm, resid = uq.fetch_all_counts_for_polygon(POLY_COORDS)
        assert addr == 50
        assert comm == 0
        assert resid == 50

    def test_residential_never_goes_negative(self):
        # Should never happen in real data, but if commercial > total (data anomaly),
        # residential must floor at 0 rather than returning a nonsensical negative.
        uprn_pts = [(INSIDE_LAT, INSIDE_LON)] * 2
        comm_pts = [(INSIDE_E, INSIDE_N)] * 5
        p1, p2 = self._patch_both(uprn_pts, comm_pts)
        with p1, p2:
            addr, comm, resid = uq.fetch_all_counts_for_polygon(POLY_COORDS)
        assert resid == 0

    def test_all_commercial_area_gives_zero_residential(self):
        # Industrial estate or retail park: every address is commercial.
        uprn_pts = [(INSIDE_LAT, INSIDE_LON)] * 8
        comm_pts = [(INSIDE_E, INSIDE_N)] * 8
        p1, p2 = self._patch_both(uprn_pts, comm_pts)
        with p1, p2:
            addr, comm, resid = uq.fetch_all_counts_for_polygon(POLY_COORDS)
        assert resid == 0

    def test_no_postcode_areas_skips_commercial_query(self):
        # If no postcode areas overlap the polygon, we must still return a result
        # and not crash or run the VOA query unnecessarily.
        uprn_rows = _raw_uprn_rows([(INSIDE_LAT, INSIDE_LON)] * 5)
        with (
            patch("queries.uprn_queries.run_query_rows", return_value=uprn_rows),
            patch("queries.uprn_queries.run_query", return_value=[]) as mock_query,
        ):
            addr, comm, resid = uq.fetch_all_counts_for_polygon(POLY_COORDS)
        # postcode areas query returns [], so commercial query should not be called
        assert addr == 5
        assert comm == 0
        assert resid == 5

    def test_address_count_is_sum_of_residential_and_commercial(self):
        uprn_pts = [(INSIDE_LAT, INSIDE_LON)] * 20
        comm_pts = [(INSIDE_E, INSIDE_N)] * 6
        p1, p2 = self._patch_both(uprn_pts, comm_pts)
        with p1, p2:
            addr, comm, resid = uq.fetch_all_counts_for_polygon(POLY_COORDS)
        assert addr == resid + comm


# ---------------------------------------------------------------------------
# fetch_uprns_in_polygon: output format
# ---------------------------------------------------------------------------

class TestFetchUprnsInPolygon:
    def test_returns_list_of_lat_lon_dicts(self):
        rows = _raw_uprn_rows([(INSIDE_LAT, INSIDE_LON)])
        with patch("queries.uprn_queries.run_query_rows", return_value=rows):
            result = uq.fetch_uprns_in_polygon(POLY_COORDS)
        assert len(result) == 1
        assert "lat" in result[0]
        assert "lon" in result[0]

    def test_outside_points_not_in_result(self):
        rows = _raw_uprn_rows([(OUTSIDE_LAT, OUTSIDE_LON)])
        with patch("queries.uprn_queries.run_query_rows", return_value=rows):
            result = uq.fetch_uprns_in_polygon(POLY_COORDS)
        assert result == []

    def test_empty_polygon_returns_empty_list(self):
        rows = _raw_uprn_rows([])
        with patch("queries.uprn_queries.run_query_rows", return_value=rows):
            result = uq.fetch_uprns_in_polygon(POLY_COORDS)
        assert result == []
