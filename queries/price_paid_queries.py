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


def fetch_mix_for_polygon(geojson_coords):
    """
    Return yearly counts broken down by property_type, duration, and old_new
    for sales within the polygon.

    Returns a list of dicts:
      {year, property_type, duration, old_new, count}
    """
    poly = polygon_osgb(geojson_coords)
    bounds = poly.bounds
    postcode_areas = _postcode_areas_for_polygon(geojson_coords)

    if not postcode_areas:
        return []

    area_list = ", ".join(f"'{a}'" for a in postcode_areas)

    sql = f"""
SELECT
    p.year,
    p.property_type,
    p.duration,
    p.old_new,
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

    # Exact point-in-polygon filter then aggregate
    by_key = {}
    for r in records:
        try:
            e = float(r["eastings"])
            n = float(r["northings"])
        except (ValueError, KeyError):
            continue
        if not poly.contains(Point(e, n)):
            continue
        key = (r["year"], r["property_type"], r["duration"], r["old_new"])
        by_key[key] = by_key.get(key, 0) + 1

    return [
        {"year": y, "property_type": pt, "duration": dur, "old_new": on, "count": cnt}
        for (y, pt, dur, on), cnt in sorted(by_key.items())
    ]


_CPI_BASE = 100.0  # CPI index is normalised to 2015 = 100


def deflate_price(price, year, cpi_by_year, base_year=None):
    """
    Convert a nominal price to real £ in base_year using annual average CPI.

    base_year: year string to rebase to (e.g. "2024"). Defaults to 2015 (CPI index = 100).
    cpi_by_year: dict of {year_str: cpi_index_float} as returned by fetch_cpi_by_year().
    Returns the nominal price unchanged if CPI data is missing for either year.
    """
    idx = cpi_by_year.get(str(year))
    if not idx:
        return price
    if base_year is not None:
        base_idx = cpi_by_year.get(str(base_year))
        if not base_idx:
            return price
        return float(price) / idx * base_idx
    return float(price) / idx * _CPI_BASE


def deflate_prices(year_prices, cpi_by_year, base_year=None):
    """
    Deflate a list of (year, price) tuples to real £ in base_year.

    year_prices: list of (year_str, nominal_price) tuples.
    Returns a new list of (year_str, real_price) tuples.
    """
    return [(year, deflate_price(price, year, cpi_by_year, base_year)) for year, price in year_prices]


def real_stats_from_prices(year_prices, cpi_by_year, base_year=None):
    """
    Derive yearly stats from raw (year, price) tuples after deflating each price to real £.

    This is the correct order of operations: deflate individual prices first, then aggregate.
    Deflating derived stats (e.g. the nominal median) gives the same answer for single-year
    aggregates (deflation is a linear transform within a year) but deflating first is clearer
    and correct by construction for any cross-year summary.

    Returns a list of per-year stat dicts in the same shape as _aggregate_by_year.
    """
    real_prices = deflate_prices(year_prices, cpi_by_year, base_year)
    by_year = {}
    for year, price in real_prices:
        by_year.setdefault(year, []).append(price)
    return _aggregate_by_year(by_year)


def fetch_cpi_by_year():
    """Return annual average CPI index (2015=100) keyed by year string, from 1988 onwards."""
    sql = """
SELECT year, AVG(cpi_index) AS avg_cpi
FROM incoming.ons_inflation_inflation
WHERE cpi_index IS NOT NULL
GROUP BY year
ORDER BY year
""".strip()
    rows = run_query(sql)
    return {str(int(r["year"])): float(r["avg_cpi"]) for r in rows if r.get("avg_cpi")}


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
