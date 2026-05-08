import time
import boto3
from shapely.geometry import Polygon, Point
from geo import bbox_partition_tiles, bbox_wgs84

AWS_PROFILE = "dantelore"
AWS_REGION = "eu-west-1"
ATHENA_DB = "incoming"
ATHENA_TABLE = "os_open_uprn_uprn"
RESULTS_BUCKET = "s3://dantelore.queryresults/"


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


def count_uprns_in_polygon(geojson_coords):
    """Fetch candidate UPRNs from Athena (bbox + partition filter) then test exact containment in Python."""
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

    # rows[0] is the header row
    poly = Polygon(geojson_coords[0])
    count = 0
    for row in rows[1:]:
        vals = row["Data"]
        try:
            lat = float(vals[1]["VarCharValue"])
            lon = float(vals[2]["VarCharValue"])
        except (KeyError, ValueError):
            continue
        if poly.contains(Point(lon, lat)):
            count += 1
    return count
