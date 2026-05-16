from shapely.geometry import Point, Polygon

from queries.athena import run_query, run_query_rows, ATHENA_DB
from utils.geo import bbox_partition_tiles, bbox_wgs84, polygon_osgb, wgs84_to_osgb

UPRN_TABLE = "os_open_uprn_uprn"
VOA_TABLE = "voa_rating_list_entries"
CODEPOINT_TABLE = "os_code_point_open_codepo"


def _postcode_areas_for_polygon(geojson_coords):
    """Return set of lowercase postcode area prefixes overlapping the polygon bbox."""
    osgb_pts = [wgs84_to_osgb(lon, lat) for lon, lat in geojson_coords[0]]
    min_e = min(p[0] for p in osgb_pts)
    max_e = max(p[0] for p in osgb_pts)
    min_n = min(p[1] for p in osgb_pts)
    max_n = max(p[1] for p in osgb_pts)

    sql = f"""
SELECT DISTINCT postcode_area
FROM {ATHENA_DB}.{CODEPOINT_TABLE}
WHERE eastings  BETWEEN {min_e:.0f} AND {max_e:.0f}
  AND northings BETWEEN {min_n:.0f} AND {max_n:.0f}
""".strip()

    rows = run_query(sql)
    return {r["postcode_area"] for r in rows if r.get("postcode_area")}


def _query_uprn_points(geojson_coords):
    """Return all UPRN (lat, lon) pairs within the exact polygon."""
    tiles = bbox_partition_tiles(geojson_coords)
    grid_e_vals = ", ".join(str(e) for e, _ in tiles)
    grid_n_vals = ", ".join(str(n) for _, n in tiles)
    min_lat, max_lat, min_lon, max_lon = bbox_wgs84(geojson_coords)

    sql = f"""
SELECT DISTINCT uprn, latitude, longitude
FROM {ATHENA_DB}.{UPRN_TABLE}
WHERE grid_e IN ({grid_e_vals})
  AND grid_n IN ({grid_n_vals})
  AND latitude  BETWEEN {min_lat} AND {max_lat}
  AND longitude BETWEEN {min_lon} AND {max_lon}
""".strip()

    rows = run_query_rows(sql)
    poly_wgs84 = Polygon(geojson_coords[0])
    points = []
    for row in rows[1:]:
        vals = row["Data"]
        try:
            lat = float(vals[1]["VarCharValue"])
            lon = float(vals[2]["VarCharValue"])
        except (KeyError, ValueError):
            continue
        if poly_wgs84.contains(Point(lon, lat)):
            points.append((lat, lon))
    return points


def _query_commercial_points(geojson_coords, postcode_areas):
    """Return OSGB (easting, northing) for all VOA entries within the polygon bbox."""
    areas_list = ", ".join(f"'{a}'" for a in postcode_areas)
    poly = polygon_osgb(geojson_coords)
    bounds = poly.bounds  # (min_e, min_n, max_e, max_n)

    sql = f"""
SELECT c.eastings, c.northings
FROM {ATHENA_DB}.{VOA_TABLE} v
JOIN {ATHENA_DB}.{CODEPOINT_TABLE} c
    ON c.postcode = v.postcode
   AND c.postcode_area = v.postcode_area
WHERE v.postcode_area IN ({areas_list})
  AND c.eastings  BETWEEN {bounds[0]:.0f} AND {bounds[2]:.0f}
  AND c.northings BETWEEN {bounds[1]:.0f} AND {bounds[3]:.0f}
""".strip()

    rows = run_query(sql)
    points = []
    for r in rows:
        try:
            e = float(r["eastings"])
            n = float(r["northings"])
        except (KeyError, ValueError):
            continue
        if poly.contains(Point(e, n)):
            points.append((e, n))
    return points


def fetch_uprns_in_polygon(geojson_coords):
    """Return list of {lat, lon} dicts for all addresses within the polygon."""
    return [{"lat": lat, "lon": lon} for lat, lon in _query_uprn_points(geojson_coords)]


def fetch_all_counts_for_polygon(geojson_coords):
    """Return (address_count, commercial_count, residential_count) for the polygon."""
    uprn_points = _query_uprn_points(geojson_coords)
    address_count = len(uprn_points)

    postcode_areas = _postcode_areas_for_polygon(geojson_coords)
    if postcode_areas:
        commercial_points = _query_commercial_points(geojson_coords, postcode_areas)
        commercial_count = len(commercial_points)
    else:
        commercial_count = 0

    residential_count = max(0, address_count - commercial_count)
    return address_count, commercial_count, residential_count
