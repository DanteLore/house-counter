import time
import boto3
from geo import bbox_partition_tiles, polygon_wkt_ring, bbox_wgs84

AWS_PROFILE = "dantelore"
AWS_REGION = "eu-west-1"
ATHENA_DB = "incoming"
ATHENA_TABLE = "os_open_uprn_uprn"
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

    results = client.get_query_results(QueryExecutionId=execution_id)
    return results


def count_uprns_in_polygon(geojson_coords):
    """Query Athena for the number of distinct UPRNs within a GeoJSON polygon."""
    tiles = bbox_partition_tiles(geojson_coords)
    grid_e_vals = ", ".join(str(e) for e, _ in tiles)
    grid_n_vals = ", ".join(str(n) for _, n in tiles)
    min_lat, max_lat, min_lon, max_lon = bbox_wgs84(geojson_coords)
    wkt_ring = polygon_wkt_ring(geojson_coords)

    sql = f"""
SELECT COUNT(DISTINCT uprn) AS cnt
FROM {ATHENA_DB}.{ATHENA_TABLE}
WHERE grid_e IN ({grid_e_vals})
  AND grid_n IN ({grid_n_vals})
  AND latitude  BETWEEN {min_lat} AND {max_lat}
  AND longitude BETWEEN {min_lon} AND {max_lon}
  AND ST_Contains(
        ST_GeomFromText('POLYGON(({wkt_ring}))'),
        ST_Point(longitude, latitude)
      )
""".strip()

    results = _run_query(sql)
    rows = results["ResultSet"]["Rows"]
    # rows[0] is header, rows[1] is data
    if len(rows) < 2:
        return 0
    return int(rows[1]["Data"][0].get("VarCharValue", "0"))
