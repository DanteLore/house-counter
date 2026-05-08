import pytest
from area_analysis import PolygonAnalysis

# A small rectangle near Thatcham, Berkshire (~1km x ~1km).
# Corners in WGS84 [lon, lat], closed ring (first == last).
# Approx extents: lon -1.27 to -1.26, lat 51.39 to 51.40
THATCHAM_RECT = [[
    [-1.27, 51.39],
    [-1.26, 51.39],
    [-1.26, 51.40],
    [-1.27, 51.40],
    [-1.27, 51.39],
]]

# Tiny 10m x 10m square in central London for a near-zero area sanity check.
# At lat 51.5, 1° lon ≈ 69.5km, 1° lat ≈ 111km.
# 0.000144° lon ≈ 10m, 0.000090° lat ≈ 10m
TINY_RECT = [[
    [-0.1276, 51.5074],
    [-0.1275, 51.5074],
    [-0.1275, 51.5075],
    [-0.1276, 51.5075],
    [-0.1276, 51.5074],
]]


class TestArea:
    def test_thatcham_rect_area_ballpark(self):
        # The rectangle spans ~0.01° lon x 0.01° lat near Thatcham.
        # At this latitude 1° lon ≈ 69.3km, 1° lat ≈ 111km.
        # Expected area ≈ 693m x 1110m ≈ 769,230 m²  (~0.77 km²).
        # Accept ±10% to allow for projection variation.
        analysis = PolygonAnalysis(THATCHAM_RECT)
        area = analysis.area_m2
        assert 690_000 < area < 850_000, f"Unexpected area: {area:.0f} m²"

    def test_area_is_positive(self):
        analysis = PolygonAnalysis(THATCHAM_RECT)
        assert analysis.area_m2 > 0

    def test_tiny_rect_is_much_smaller(self):
        big = PolygonAnalysis(THATCHAM_RECT).area_m2
        small = PolygonAnalysis(TINY_RECT).area_m2
        assert small < big / 100


class TestDensity:
    def test_density_none_when_count_not_set(self):
        analysis = PolygonAnalysis(THATCHAM_RECT)
        assert analysis.density_m2_per_address is None

    def test_density_none_when_count_zero(self):
        analysis = PolygonAnalysis(THATCHAM_RECT, uprn_count=0)
        assert analysis.density_m2_per_address is None

    def test_density_calculation(self):
        analysis = PolygonAnalysis(THATCHAM_RECT, uprn_count=100)
        expected = analysis.area_m2 / 100
        assert analysis.density_m2_per_address == pytest.approx(expected)

    def test_density_decreases_with_more_addresses(self):
        sparse = PolygonAnalysis(THATCHAM_RECT, uprn_count=10)
        dense = PolygonAnalysis(THATCHAM_RECT, uprn_count=1000)
        assert sparse.density_m2_per_address > dense.density_m2_per_address


class TestFetchCount:
    def test_fetch_count_uses_fetcher(self):
        fake_fetcher = lambda coords: 42
        analysis = PolygonAnalysis(THATCHAM_RECT)
        analysis.fetch_count(fake_fetcher)
        assert analysis.uprn_count == 42

    def test_fetch_count_passes_coords_to_fetcher(self):
        received = {}

        def capturing_fetcher(coords):
            received["coords"] = coords
            return 5

        analysis = PolygonAnalysis(THATCHAM_RECT)
        analysis.fetch_count(capturing_fetcher)
        assert received["coords"] == THATCHAM_RECT

    def test_fetch_count_updates_density(self):
        analysis = PolygonAnalysis(THATCHAM_RECT)
        assert analysis.density_m2_per_address is None
        analysis.fetch_count(lambda _: 200)
        assert analysis.density_m2_per_address is not None
        assert analysis.density_m2_per_address == pytest.approx(analysis.area_m2 / 200)

    def test_rectangular_polygon_count_trusts_fetcher(self):
        # For a rectangle, bbox == polygon, so whatever Athena returns is the ground truth.
        # We verify the class faithfully uses that value without modification.
        analysis = PolygonAnalysis(THATCHAM_RECT)
        analysis.fetch_count(lambda _: 317)
        assert analysis.uprn_count == 317
