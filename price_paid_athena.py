import time
import boto3
from shapely.geometry import Point

from geo import polygon_osgb

AWS_PROFILE = "dantelore"
AWS_REGION = "eu-west-1"
ATHENA_DB = "incoming"
RESULTS_BUCKET = "s3://dantelore.queryresults/"

PPD_TABLE = "house_prices_ppd"
CODEPOINT_TABLE = "os_code_point_open_codepo"

START_YEAR = 1995


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
    result = []
    for row in rows[1:]:
        result.append({
            headers[i]: col.get("VarCharValue", "")
            for i, col in enumerate(row["Data"])
        })
    return result


def _postcode_areas_for_polygon(geojson_coords):
    """
    Derive the set of postcode area prefixes (e.g. 'rg', 'ox') that overlap
    the polygon by querying Code-Point within the OSGB bounding box.
    """
    poly = polygon_osgb(geojson_coords)
    bounds = poly.bounds  # (min_e, min_n, max_e, max_n)

    sql = f"""
SELECT DISTINCT postcode_area
FROM {ATHENA_DB}.{CODEPOINT_TABLE}
WHERE eastings  BETWEEN {bounds[0]} AND {bounds[2]}
  AND northings BETWEEN {bounds[1]} AND {bounds[3]}
""".strip()

    rows = _run_query(sql)
    areas = set()
    for row in rows[1:]:
        val = row["Data"][0].get("VarCharValue", "").strip()
        if val:
            areas.add(val)
    return areas


def fetch_price_stats_for_polygon(geojson_coords):
    """
    Return a list of dicts, one per year, with price stats for sales whose
    postcode centroid falls inside the polygon.

    Each dict: {year, count, min_price, max_price, mean_price,
                median_price, p25_price, p75_price}
    """
    poly = polygon_osgb(geojson_coords)
    bounds = poly.bounds  # (min_e, min_n, max_e, max_n)
    postcode_areas = _postcode_areas_for_polygon(geojson_coords)

    if not postcode_areas:
        return []

    area_list = ", ".join(f"'{a}'" for a in postcode_areas)

    # Pull raw transactions with Code-Point coordinates, bbox-filtered
    sql = f"""
SELECT
    p.year,
    CAST(p.price AS double) AS price,
    c.eastings,
    c.northings
FROM {ATHENA_DB}.{PPD_TABLE} p
JOIN {ATHENA_DB}.{CODEPOINT_TABLE} c
  ON c.postcode = p.postcode
 AND c.postcode_area = LOWER(REGEXP_EXTRACT(p.postcode, '^([A-Z]{{1,2}})', 1))
WHERE p.record_status != 'D'
  AND c.postcode_area IN ({area_list})
  AND c.eastings  BETWEEN {bounds[0]} AND {bounds[2]}
  AND c.northings BETWEEN {bounds[1]} AND {bounds[3]}
""".strip()

    rows = _run_query(sql)
    records = _rows_to_dicts(rows)

    # Exact point-in-polygon filter in OSGB space, then aggregate by year
    by_year = {}
    all_prices = []
    for r in records:
        try:
            e = float(r["eastings"])
            n = float(r["northings"])
            price = float(r["price"])
        except (ValueError, KeyError):
            continue
        if not poly.contains(Point(e, n)):
            continue
        year = r["year"]
        by_year.setdefault(year, []).append(price)
        all_prices.append((year, price))

    return _aggregate_by_year(by_year), all_prices


def fetch_price_stats_national():
    """
    Return yearly price stats aggregated across all of England & Wales.
    Each dict: {year, count, min_price, max_price, mean_price,
                median_price, p25_price, p75_price}
    """
    sql = f"""
SELECT
    year,
    COUNT(*) AS count,
    MIN(CAST(price AS double)) AS min_price,
    MAX(CAST(price AS double)) AS max_price,
    AVG(CAST(price AS double)) AS mean_price,
    approx_percentile(CAST(price AS double), 0.25) AS p25_price,
    approx_percentile(CAST(price AS double), 0.5)  AS median_price,
    approx_percentile(CAST(price AS double), 0.75) AS p75_price
FROM {ATHENA_DB}.{PPD_TABLE}
WHERE record_status != 'D'
  AND ppd_category_type = 'A'
GROUP BY year
ORDER BY year
""".strip()

    rows = _run_query(sql)
    return _rows_to_dicts(rows)


def fetch_price_stats_county(county):
    """
    Return yearly price stats for a given county name (as it appears in PPD).
    """
    safe_county = county.replace("'", "''")
    sql = f"""
SELECT
    year,
    COUNT(*) AS count,
    MIN(CAST(price AS double)) AS min_price,
    MAX(CAST(price AS double)) AS max_price,
    AVG(CAST(price AS double)) AS mean_price,
    approx_percentile(CAST(price AS double), 0.25) AS p25_price,
    approx_percentile(CAST(price AS double), 0.5)  AS median_price,
    approx_percentile(CAST(price AS double), 0.75) AS p75_price
FROM {ATHENA_DB}.{PPD_TABLE}
WHERE record_status != 'D'
  AND ppd_category_type = 'A'
  AND UPPER(county) = UPPER('{safe_county}')
GROUP BY year
ORDER BY year
""".strip()

    rows = _run_query(sql)
    return _rows_to_dicts(rows)


def fetch_county_for_polygon(geojson_coords):
    """
    Return the most common county name from PPD sales whose postcode centroid
    falls inside the polygon — used to pick the county baseline.
    """
    poly = polygon_osgb(geojson_coords)
    bounds = poly.bounds
    postcode_areas = _postcode_areas_for_polygon(geojson_coords)

    if not postcode_areas:
        return None

    area_list = ", ".join(f"'{a}'" for a in postcode_areas)

    sql = f"""
SELECT p.county, c.eastings, c.northings
FROM {ATHENA_DB}.{PPD_TABLE} p
JOIN {ATHENA_DB}.{CODEPOINT_TABLE} c
  ON c.postcode = p.postcode
 AND c.postcode_area = LOWER(REGEXP_EXTRACT(p.postcode, '^([A-Z]{{1,2}})', 1))
WHERE p.record_status != 'D'
  AND p.year >= '2015'
  AND c.postcode_area IN ({area_list})
  AND c.eastings  BETWEEN {bounds[0]} AND {bounds[2]}
  AND c.northings BETWEEN {bounds[1]} AND {bounds[3]}
""".strip()

    rows = _run_query(sql)
    records = _rows_to_dicts(rows)

    county_counts = {}
    for r in records:
        try:
            e = float(r["eastings"])
            n = float(r["northings"])
        except (ValueError, KeyError):
            continue
        if not poly.contains(Point(e, n)):
            continue
        county = r.get("county", "").strip()
        if county:
            county_counts[county] = county_counts.get(county, 0) + 1

    if not county_counts:
        return None
    return max(county_counts, key=county_counts.get)


def _aggregate_by_year(by_year):
    """Convert {year: [prices]} dict to list of stat dicts, sorted by year."""
    import statistics
    result = []
    for year in sorted(by_year):
        prices = sorted(by_year[year])
        n = len(prices)
        if n == 0:
            continue
        result.append({
            "year": year,
            "count": n,
            "min_price": min(prices),
            "max_price": max(prices),
            "mean_price": statistics.mean(prices),
            "median_price": statistics.median(prices),
            "p25_price": prices[max(0, int(n * 0.25) - 1)],
            "p75_price": prices[min(n - 1, int(n * 0.75))],
        })
    return result
