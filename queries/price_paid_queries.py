import statistics

from shapely.geometry import Point

from queries.athena import run_query, ATHENA_DB
from utils.geo import polygon_osgb

PPD_TABLE = "house_prices_ppd"
CODEPOINT_TABLE = "os_code_point_open_codepo"


def _postcode_areas_for_polygon(geojson_coords):
    """Return set of lowercase postcode area prefixes overlapping the polygon bbox."""
    poly = polygon_osgb(geojson_coords)
    bounds = poly.bounds  # (min_e, min_n, max_e, max_n)

    sql = f"""
SELECT DISTINCT postcode_area
FROM {ATHENA_DB}.{CODEPOINT_TABLE}
WHERE eastings  BETWEEN {bounds[0]:.0f} AND {bounds[2]:.0f}
  AND northings BETWEEN {bounds[1]:.0f} AND {bounds[3]:.0f}
""".strip()

    rows = run_query(sql)
    return {r["postcode_area"] for r in rows if r.get("postcode_area")}


def _aggregate_by_year(by_year):
    """Convert {year: [prices]} to a list of per-year stat dicts, sorted by year."""
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


def fetch_price_stats_for_polygon(geojson_coords):
    """
    Return (yearly_stats, all_prices) for sales within the polygon.

    yearly_stats: list of {year, count, min/max/mean/median/p25/p75_price}
    all_prices:   list of (year, price) tuples
    """
    poly = polygon_osgb(geojson_coords)
    bounds = poly.bounds
    postcode_areas = _postcode_areas_for_polygon(geojson_coords)

    if not postcode_areas:
        return [], []

    area_list = ", ".join(f"'{a}'" for a in postcode_areas)

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
  AND c.eastings  BETWEEN {bounds[0]:.0f} AND {bounds[2]:.0f}
  AND c.northings BETWEEN {bounds[1]:.0f} AND {bounds[3]:.0f}
""".strip()

    records = run_query(sql)

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
    """Return yearly price stats aggregated across all of England & Wales."""
    sql = f"""
SELECT
    year,
    COUNT(*) AS count,
    MIN(CAST(price AS double))                        AS min_price,
    MAX(CAST(price AS double))                        AS max_price,
    AVG(CAST(price AS double))                        AS mean_price,
    approx_percentile(CAST(price AS double), 0.25)   AS p25_price,
    approx_percentile(CAST(price AS double), 0.5)    AS median_price,
    approx_percentile(CAST(price AS double), 0.75)   AS p75_price
FROM {ATHENA_DB}.{PPD_TABLE}
WHERE record_status != 'D'
  AND ppd_category_type = 'A'
GROUP BY year
ORDER BY year
""".strip()

    return run_query(sql)
