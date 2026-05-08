import math
from pyproj import Transformer
from shapely.geometry import Polygon, Point

_wgs84_to_osgb = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True)


def wgs84_to_osgb(lon, lat):
    return _wgs84_to_osgb.transform(lon, lat)


def polygon_area_m2(geojson_coords):
    """Return area in square metres for a GeoJSON coordinate ring (WGS84), projected to OSGB36."""
    ring = geojson_coords[0]  # outer ring only
    projected = [wgs84_to_osgb(lon, lat) for lon, lat in ring]
    return abs(Polygon(projected).area)


def bbox_partition_tiles(geojson_coords):
    """Return set of (grid_e, grid_n) partition tiles that the polygon's bounding box overlaps."""
    ring = geojson_coords[0]
    osgb_points = [wgs84_to_osgb(lon, lat) for lon, lat in ring]
    eastings = [p[0] for p in osgb_points]
    northings = [p[1] for p in osgb_points]
    min_e, max_e = min(eastings), max(eastings)
    min_n, max_n = min(northings), max(northings)

    tiles = set()
    ge = math.floor(min_e / 100_000)
    while ge <= math.floor(max_e / 100_000):
        gn = math.floor(min_n / 100_000)
        while gn <= math.floor(max_n / 100_000):
            tiles.add((ge, gn))
            gn += 1
        ge += 1
    return tiles


def polygon_wkt_ring(geojson_coords):
    """Return the WKT coordinate string for the outer ring of a GeoJSON polygon."""
    ring = geojson_coords[0]
    pairs = " ".join(f"{lon} {lat}" for lon, lat in ring)
    return pairs


def bbox_wgs84(geojson_coords):
    """Return (min_lat, max_lat, min_lon, max_lon) bounding box."""
    ring = geojson_coords[0]
    lons = [p[0] for p in ring]
    lats = [p[1] for p in ring]
    return min(lats), max(lats), min(lons), max(lons)
