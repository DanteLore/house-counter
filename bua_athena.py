import time
import boto3
from shapely import wkt as shapely_wkt
from shapely.geometry import MultiPolygon, mapping

AWS_PROFILE = "dantelore"
AWS_REGION = "eu-west-1"
ATHENA_DB = "incoming"
BUA_TABLE = "ons_bua_boundaries_bua"
RESULTS_BUCKET = "s3://dantelore.queryresults/"


def _client():
    session = boto3.Session(profile_name=AWS_PROFILE)
    return session.client("athena", region_name=AWS_REGION)


def _run_query(sql):
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


def _rows_to_dicts(rows):
    if not rows:
        return []
    headers = [c["VarCharValue"] for c in rows[0]["Data"]]
    return [
        {headers[i]: col.get("VarCharValue", "") for i, col in enumerate(row["Data"])}
        for row in rows[1:]
    ]


def search_buas(name):
    """
    Return list of {bua24cd, bua24nm, centre_e, centre_n} whose name contains
    the search string (case-insensitive). Limited to 50 results.
    """
    safe = name.replace("'", "''")
    sql = f"""
SELECT bua24cd, bua24nm, centre_e, centre_n
FROM {ATHENA_DB}.{BUA_TABLE}
WHERE LOWER(bua24nm) LIKE LOWER('%{safe}%')
ORDER BY bua24nm
LIMIT 50
""".strip()
    return _rows_to_dicts(_run_query(sql))


def fetch_bua_as_geojson_coords(bua24cd):
    """
    Fetch the WGS84 WKT geometry for a single BUA and return it as a GeoJSON
    coordinate ring suitable for storing as a simple Polygon feature.

    For MultiPolygons, returns the ring of the largest part by area.
    Holes (interior rings) are discarded.
    """
    safe = bua24cd.replace("'", "''")
    sql = f"""
SELECT geometry_wgs84_wkt
FROM {ATHENA_DB}.{BUA_TABLE}
WHERE bua24cd = '{safe}'
LIMIT 1
""".strip()

    rows = _rows_to_dicts(_run_query(sql))
    if not rows:
        return None

    wkt_str = rows[0].get("geometry_wgs84_wkt", "")
    if not wkt_str:
        return None

    geom = shapely_wkt.loads(wkt_str)

    # Normalise to a list of simple polygons, pick the largest
    if isinstance(geom, MultiPolygon):
        parts = list(geom.geoms)
    else:
        parts = [geom]

    largest = max(parts, key=lambda p: p.area)

    # Return only the exterior ring as a GeoJSON coordinate list [[lon, lat], ...]
    # wrapped in the outer array that GeoJSON Polygon coordinates expect.
    exterior = [[lon, lat] for lon, lat in largest.exterior.coords]
    return [exterior]
