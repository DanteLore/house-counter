import pytest
from pyproj import Transformer
from utils.area_analysis import PolygonAnalysis

_osgb_to_wgs84 = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)


def _osgb_ring(*osgb_corners):
    """Convert a sequence of (easting, northing) pairs to a closed GeoJSON ring [[lon, lat], ...]."""
    ring = [list(_osgb_to_wgs84.transform(e, n)) for e, n in osgb_corners]
    ring.append(ring[0])
    return [ring]

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


class TestAreaPrecision:
    """Exact-area tests using polygons defined in OSGB36 coordinates, where the true
    area is known to the metre.  We round-trip via the same transformer the app uses,
    so the tolerance reflects only floating-point noise, not projection error."""

    def test_1km_square_central_london(self):
        # 1000m × 1000m square = exactly 1,000,000 m²
        coords = _osgb_ring(
            (530000, 180000), (531000, 180000),
            (531000, 181000), (530000, 181000),
        )
        area = PolygonAnalysis(coords).area_m2
        assert area == pytest.approx(1_000_000, rel=1e-3), f"Got {area:.2f} m²"

    def test_1km_square_thatcham(self):
        # Same shape at a different latitude  -  confirms the projection handles
        # different parts of GB consistently.
        coords = _osgb_ring(
            (446000, 164000), (447000, 164000),
            (447000, 165000), (446000, 165000),
        )
        area = PolygonAnalysis(coords).area_m2
        assert area == pytest.approx(1_000_000, rel=1e-3), f"Got {area:.2f} m²"

    def test_right_triangle_known_area(self):
        # Right-angle triangle with legs 1000m and 2000m → area = ½ × 1000 × 2000 = 1,000,000 m²
        coords = _osgb_ring(
            (530000, 180000), (531000, 180000), (530000, 182000),
        )
        area = PolygonAnalysis(coords).area_m2
        assert area == pytest.approx(1_000_000, rel=1e-3), f"Got {area:.2f} m²"

    def test_2km_square_is_four_times_1km_square(self):
        # Scaling both sides by 2 should quadruple the area exactly.
        coords_1km = _osgb_ring(
            (530000, 180000), (531000, 180000),
            (531000, 181000), (530000, 181000),
        )
        coords_2km = _osgb_ring(
            (530000, 180000), (532000, 180000),
            (532000, 182000), (530000, 182000),
        )
        area_1km = PolygonAnalysis(coords_1km).area_m2
        area_2km = PolygonAnalysis(coords_2km).area_m2
        assert area_2km == pytest.approx(4 * area_1km, rel=1e-3)

    def test_winding_order_does_not_affect_area(self):
        # Area should be the same regardless of whether the ring is CW or CCW.
        cw = _osgb_ring(
            (530000, 180000), (531000, 180000),
            (531000, 181000), (530000, 181000),
        )
        ccw = [list(reversed(cw[0]))]
        assert PolygonAnalysis(cw).area_m2 == pytest.approx(
            PolygonAnalysis(ccw).area_m2, rel=1e-6
        )


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


class TestAreaHectares:
    def test_area_ha_is_area_m2_divided_by_10000(self):
        analysis = PolygonAnalysis(THATCHAM_RECT)
        assert analysis.area_ha == pytest.approx(analysis.area_m2 / 10_000)

    def test_1km_square_is_100_hectares(self):
        coords = _osgb_ring(
            (530000, 180000), (531000, 180000),
            (531000, 181000), (530000, 181000),
        )
        # Wait  -  this is 1000m × 1000m = 1,000,000 m² = 100 ha
        assert PolygonAnalysis(coords).area_ha == pytest.approx(100.0, rel=1e-3)

    def test_area_ha_positive(self):
        assert PolygonAnalysis(THATCHAM_RECT).area_ha > 0


class TestDensity:
    # ---- m² per address ----

    def test_m2_per_address_none_when_count_not_set(self):
        assert PolygonAnalysis(THATCHAM_RECT).density_m2_per_address is None

    def test_m2_per_address_none_when_count_zero(self):
        assert PolygonAnalysis(THATCHAM_RECT, uprn_count=0).density_m2_per_address is None

    def test_m2_per_address_calculation(self):
        analysis = PolygonAnalysis(THATCHAM_RECT, uprn_count=100)
        assert analysis.density_m2_per_address == pytest.approx(analysis.area_m2 / 100)

    def test_m2_per_address_decreases_with_more_addresses(self):
        sparse = PolygonAnalysis(THATCHAM_RECT, uprn_count=10)
        dense = PolygonAnalysis(THATCHAM_RECT, uprn_count=1000)
        assert sparse.density_m2_per_address > dense.density_m2_per_address

    def test_m2_per_address_single_dwelling(self):
        analysis = PolygonAnalysis(THATCHAM_RECT, uprn_count=1)
        assert analysis.density_m2_per_address == pytest.approx(analysis.area_m2)

    # ---- DPH ----

    def test_dph_none_when_count_not_set(self):
        assert PolygonAnalysis(THATCHAM_RECT).dwellings_per_hectare is None

    def test_dph_none_when_count_zero(self):
        assert PolygonAnalysis(THATCHAM_RECT, uprn_count=0).dwellings_per_hectare is None

    def test_dph_calculation(self):
        analysis = PolygonAnalysis(THATCHAM_RECT, uprn_count=100)
        assert analysis.dwellings_per_hectare == pytest.approx(
            100 / analysis.area_ha
        )

    def test_dph_increases_with_more_addresses(self):
        sparse = PolygonAnalysis(THATCHAM_RECT, uprn_count=10)
        dense = PolygonAnalysis(THATCHAM_RECT, uprn_count=1000)
        assert sparse.dwellings_per_hectare < dense.dwellings_per_hectare

    def test_dph_exact_1ha_100_dwellings(self):
        # 100m × 100m OSGB36 square = exactly 10,000 m² = 1 ha
        # 100 dwellings → exactly 100 DPH
        coords = _osgb_ring(
            (530000, 180000), (530100, 180000),
            (530100, 180100), (530000, 180100),
        )
        analysis = PolygonAnalysis(coords, uprn_count=100)
        assert analysis.dwellings_per_hectare == pytest.approx(100.0, rel=1e-3)

    def test_dph_exact_1ha_30_dwellings(self):
        # 1 ha, 30 dwellings → 30 DPH (typical suburban density)
        coords = _osgb_ring(
            (530000, 180000), (530100, 180000),
            (530100, 180100), (530000, 180100),
        )
        analysis = PolygonAnalysis(coords, uprn_count=30)
        assert analysis.dwellings_per_hectare == pytest.approx(30.0, rel=1e-3)

    def test_dph_single_dwelling(self):
        analysis = PolygonAnalysis(THATCHAM_RECT, uprn_count=1)
        assert analysis.dwellings_per_hectare == pytest.approx(1 / analysis.area_ha)

    # ---- DPH and m²/address are exact reciprocals (scaled by 10,000) ----

    def test_dph_and_m2_per_address_are_reciprocals(self):
        analysis = PolygonAnalysis(THATCHAM_RECT, uprn_count=250)
        assert analysis.dwellings_per_hectare == pytest.approx(
            10_000 / analysis.density_m2_per_address
        )

    def test_dph_times_m2_per_address_equals_10000(self):
        for count in [1, 10, 100, 1000]:
            analysis = PolygonAnalysis(THATCHAM_RECT, uprn_count=count)
            product = analysis.dwellings_per_hectare * analysis.density_m2_per_address
            assert product == pytest.approx(10_000.0), f"Failed for count={count}"


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
