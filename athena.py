import time
import boto3
from shapely.geometry import Polygon, Point
from geo import bbox_partition_tiles, bbox_wgs84, polygon_osgb

AWS_PROFILE = "dantelore"
AWS_REGION = "eu-west-1"
ATHENA_DB = "incoming"
ATHENA_TABLE = "os_open_uprn_uprn"
RESULTS_BUCKET = "s3://dantelore.queryresults/"
VOA_TABLE = "voa_rating_list_entries"
CODEPOINT_TABLE = "os_code_point_open_codepo"


def _client():
    session = boto3.Session(profile_name=AWS_PROFILE)
    return session.client("athena", region_name=AWS_REGION)



def _fetch_all_rows(client, execution_id):
    rows = []
    kwargs = {"QueryExecutionId": execution_id}
    while True:
        resp = client.get_query_results(**kwargs)
        rows.extend(resp["ResultSet"]["Rows"])
        token = resp.get("NextToken")
        if not token:
            break
        kwargs["NextToken"] = token
    return rows


def _query_uprns(geojson_coords):
    """Run Athena bbox query and return rows within the exact polygon as (lat, lon) tuples."""
    tiles = bbox_partition_tiles(geojson_coords)
    grid_e_vals = ", ".join(str(e) for e, _ in tiles)
    grid_n_vals = ", ".join(str(n) for _, n in tiles)
    min_lat, max_lat, min_lon, max_lon = bbox_wgs84(geojson_coords)

    sql = f"""
SELECT DISTINCT uprn, latitude, longitude
FROM {ATHENA_DB}.{ATHENA_TABLE}
WHERE grid_e IN ({grid_e_vals})
  AND grid_n IN ({grid_n_vals})
  AND latitude  BETWEEN {min_lat} AND {max_lat}
  AND longitude BETWEEN {min_lon} AND {max_lon}
""".strip()

    client = _client()
    response = client.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": ATHENA_DB},
        ResultConfiguration={"OutputLocation": RESULTS_BUCKET},
    )
    execution_id = response["QueryExecutionId"]

    while True:
        status = client.get_query_execution(QueryExecutionId=execution_id)
        state = status["QueryExecution"]["Status"]["State"]
        if state == "SUCCEEDED":
            break
        if state in ("FAILED", "CANCELLED"):
            reason = status["QueryExecution"]["Status"].get("StateChangeReason", state)
            raise RuntimeError(f"Athena query {state}: {reason}")
        time.sleep(1)

    rows = _fetch_all_rows(client, execution_id)

    poly = Polygon(geojson_coords[0])
    points = []
    for row in rows[1:]:
        vals = row["Data"]
        try:
            lat = float(vals[1]["VarCharValue"])
            lon = float(vals[2]["VarCharValue"])
        except (KeyError, ValueError):
            continue
        if poly.contains(Point(lon, lat)):
            points.append((lat, lon))
    return points


def count_uprns_in_polygon(geojson_coords):
    return len(_query_uprns(geojson_coords))


def fetch_uprns_in_polygon(geojson_coords):
    """Return list of {lat, lon} dicts for all addresses within the polygon."""
    return [{"lat": lat, "lon": lon} for lat, lon in _query_uprns(geojson_coords)]


def _postcode_areas_for_polygon(geojson_coords):
    """Return set of lowercase postcode area prefixes (e.g. {'rg', 'ox'}) overlapping the polygon bbox."""
    from geo import wgs84_to_osgb
    osgb_pts = [wgs84_to_osgb(lon, lat) for lon, lat in geojson_coords[0]]
    min_e = min(p[0] for p in osgb_pts)
    max_e = max(p[0] for p in osgb_pts)
    min_n = min(p[1] for p in osgb_pts)
    max_n = max(p[1] for p in osgb_pts)

    sql = f"""
SELECT DISTINCT postcode_area
FROM {ATHENA_DB}.{CODEPOINT_TABLE}
WHERE eastings BETWEEN {min_e:.0f} AND {max_e:.0f}
  AND northings BETWEEN {min_n:.0f} AND {max_n:.0f}
""".strip()

    client = _client()
    resp = client.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": ATHENA_DB},
        ResultConfiguration={"OutputLocation": RESULTS_BUCKET},
    )
    eid = resp["QueryExecutionId"]
    while True:
        s = client.get_query_execution(QueryExecutionId=eid)
        state = s["QueryExecution"]["Status"]["State"]
        if state == "SUCCEEDED":
            break
        if state in ("FAILED", "CANCELLED"):
            raise RuntimeError(f"Athena query {state}: {s['QueryExecution']['Status'].get('StateChangeReason', '')}")
        time.sleep(1)
    rows = _fetch_all_rows(client, eid)
    return {row["Data"][0]["VarCharValue"] for row in rows[1:] if row["Data"][0].get("VarCharValue")}


def count_commercial_in_polygon(geojson_coords):
    """Return count of VOA commercial entries whose postcode centroid falls inside the polygon."""
    from geo import wgs84_to_osgb
    postcode_areas = _postcode_areas_for_polygon(geojson_coords)
    if not postcode_areas:
        return 0

    areas_list = ", ".join(f"'{a}'" for a in postcode_areas)
    osgb_pts = [wgs84_to_osgb(lon, lat) for lon, lat in geojson_coords[0]]
    min_e = min(p[0] for p in osgb_pts)
    max_e = max(p[0] for p in osgb_pts)
    min_n = min(p[1] for p in osgb_pts)
    max_n = max(p[1] for p in osgb_pts)

    sql = f"""
SELECT c.eastings, c.northings
FROM {ATHENA_DB}.{VOA_TABLE} v
JOIN {ATHENA_DB}.{CODEPOINT_TABLE} c
    ON c.postcode = v.postcode
   AND c.postcode_area = v.postcode_area
WHERE v.postcode_area IN ({areas_list})
  AND c.eastings  BETWEEN {min_e:.0f} AND {max_e:.0f}
  AND c.northings BETWEEN {min_n:.0f} AND {max_n:.0f}
""".strip()

    client = _client()
    resp = client.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": ATHENA_DB},
        ResultConfiguration={"OutputLocation": RESULTS_BUCKET},
    )
    eid = resp["QueryExecutionId"]
    while True:
        s = client.get_query_execution(QueryExecutionId=eid)
        state = s["QueryExecution"]["Status"]["State"]
        if state == "SUCCEEDED":
            break
        if state in ("FAILED", "CANCELLED"):
            raise RuntimeError(f"Athena query {state}: {s['QueryExecution']['Status'].get('StateChangeReason', '')}")
        time.sleep(1)

    rows = _fetch_all_rows(client, eid)
    poly = polygon_osgb(geojson_coords)
    count = 0
    for row in rows[1:]:
        try:
            e = float(row["Data"][0]["VarCharValue"])
            n = float(row["Data"][1]["VarCharValue"])
        except (KeyError, ValueError):
            continue
        if poly.contains(Point(e, n)):
            count += 1
    return count


def fetch_all_counts_for_polygon(geojson_coords):
    """Return (address_count, commercial_count, residential_count) for the polygon.

    Runs both UPRN and VOA queries. residential = address - commercial.
    """
    address_count = count_uprns_in_polygon(geojson_coords)
    commercial_count = count_commercial_in_polygon(geojson_coords)
    residential_count = max(0, address_count - commercial_count)
    return address_count, commercial_count, residential_count
