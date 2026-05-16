from shapely import wkt as shapely_wkt
from shapely.geometry import MultiPolygon

from queries.athena import run_query, ATHENA_DB

BUA_TABLE = "ons_bua_boundaries_bua"


def search_buas(name):
    """Return list of {bua24cd, bua24nm} whose name contains the search string."""
    safe = name.replace("'", "''")
    sql = f"""
SELECT bua24cd, bua24nm
FROM {ATHENA_DB}.{BUA_TABLE}
WHERE LOWER(bua24nm) LIKE LOWER('%{safe}%')
ORDER BY bua24nm
LIMIT 50
""".strip()

    return run_query(sql)


def fetch_bua_as_geojson_coords(bua24cd):
    """
    Return GeoJSON coordinate ring [[lon, lat], ...] for the given BUA code.

    For MultiPolygons, returns the exterior ring of the largest part.
    Holes are discarded.
    """
    safe = bua24cd.replace("'", "''")
    sql = f"""
SELECT geometry_wgs84_wkt
FROM {ATHENA_DB}.{BUA_TABLE}
WHERE bua24cd = '{safe}'
LIMIT 1
""".strip()

    rows = run_query(sql)
    if not rows:
        return None

    wkt_str = rows[0].get("geometry_wgs84_wkt", "")
    if not wkt_str:
        return None

    geom = shapely_wkt.loads(wkt_str)

    parts = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]
    largest = max(parts, key=lambda p: p.area)

    exterior = [[lon, lat] for lon, lat in largest.exterior.coords]
    return [exterior]
