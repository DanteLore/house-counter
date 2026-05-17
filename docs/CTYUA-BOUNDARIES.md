# ONS Counties and Unitary Authorities Boundaries 2025

ONS-defined polygon boundaries for 205 Counties and Unitary Authorities (CTYUAs) covering
England, Wales and Scotland, April 2019 vintage (Ultra Generalised Clipped Boundaries).
Area codes are stable and match current ONS codes — e.g. West Berkshire (`E06000037`),
Cornwall (`E06000052`), Highland (`S12000017`). Boundaries are generalised (~20m tolerance)
and suitable for spatial filtering, bbox lookups and display, not precise measurements.

CTYUAs are upper-tier administrative areas sitting above districts and wards. They are
useful for grouping data at a regional/county level when BUA boundaries (which follow
urban form) are too granular.

## Schema

**Glue table:** `incoming.ons_ctyua_boundaries_ctyua`
**S3 location:** `s3://dantelore.data.incoming/ons_ctyua_boundaries/ctyua/ctyua_2025.parquet`

| Column | Type | Description |
|---|---|---|
| `ctyua25cd` | string | Stable ONS area code (primary key, e.g. `E06000037`) |
| `ctyua25nm` | string | Area name in English (e.g. `West Berkshire`) |
| `ctyua25nmw` | string | Area name in Welsh (Wales only, null elsewhere) |
| `geometry_wgs84_wkt` | string | Polygon/MultiPolygon in WGS84 (EPSG:4326, lng/lat) as WKT |
| `geometry_osgb_wkt` | string | Polygon/MultiPolygon in British National Grid (EPSG:27700, metres) as WKT |
| `centre_e` | int | Centroid easting (OSGB metres) |
| `centre_n` | int | Centroid northing (OSGB metres) |
| `bbox_min_e` | int | Bounding rectangle min easting (OSGB metres) |
| `bbox_min_n` | int | Bounding rectangle min northing (OSGB metres) |
| `bbox_max_e` | int | Bounding rectangle max easting (OSGB metres) |
| `bbox_max_n` | int | Bounding rectangle max northing (OSGB metres) |

All coordinates are in metres for OSGB columns. WKT geometry strings can be large — avoid
`SELECT *` over many rows.

## Common queries

### Look up a single area by name

```sql
SELECT ctyua25cd, ctyua25nm, centre_e, centre_n
FROM ons_ctyua_boundaries_ctyua
WHERE ctyua25nm = 'West Berkshire'
```

### List all areas

```sql
SELECT ctyua25cd, ctyua25nm, centre_e, centre_n
FROM ons_ctyua_boundaries_ctyua
ORDER BY ctyua25nm
```

### Find areas by approximate location (bounding box)

```sql
-- CTYUAs whose centroid falls within ~50km of central London (531000, 181000)
SELECT ctyua25cd, ctyua25nm, centre_e, centre_n
FROM ons_ctyua_boundaries_ctyua
WHERE centre_e BETWEEN 481000 AND 581000
  AND centre_n BETWEEN 131000 AND 231000
```

### Aggregate house prices by CTYUA

Join on area name — note that `town_city` in house price data won't always match a CTYUA
name. For accurate spatial joining, use the postcode → CTYUA lookup via OS Code Point Open
(the `admin_district_code` field references the local authority, not CTYUA directly).

```sql
SELECT
    c.ctyua25nm,
    COUNT(*) AS sales,
    ROUND(AVG(p.price)) AS avg_price
FROM house_prices_ppd p
JOIN ons_ctyua_boundaries_ctyua c
    ON p.county = c.ctyua25nm
WHERE p.year = '2023'
GROUP BY c.ctyua25nm
ORDER BY avg_price DESC
LIMIT 20
```

### Area sizes (bounding rectangle)

```sql
SELECT
    ctyua25nm,
    (bbox_max_e - bbox_min_e)                                        AS width_m,
    (bbox_max_n - bbox_min_n)                                        AS height_m,
    (bbox_max_e - bbox_min_e) * (bbox_max_n - bbox_min_n) / 1000000 AS bbox_area_km2
FROM ons_ctyua_boundaries_ctyua
ORDER BY bbox_area_km2 DESC
LIMIT 20
```

## Working with WKT geometry

Athena has no native spatial functions. Use the bbox columns for fast rectangular
pre-filtering in Athena, then apply exact geometry tests in Python with Shapely:

```python
from shapely import wkt
from shapely.geometry import Point

polygon = wkt.loads(row["geometry_osgb_wkt"])
point = Point(easting, northing)
if polygon.contains(point):
    ...
```

Use `geometry_wgs84_wkt` when passing to tools that expect latitude/longitude (e.g. Leaflet,
Google Maps); use `geometry_osgb_wkt` for distance calculations and joins against OSGB
coordinates (Code Point Open, UPRN).

## Source and update cadence

**Source:** ONS Open Geography Portal —
[CTYUA_Apr_2019_UGCB_Great_Britain_2022](https://services1.arcgis.com/ESMARspQHYMw9BZ9/ArcGIS/rest/services/CTYUA_Apr_2019_UGCB_Great_Britain_2022/FeatureServer/0)
(Ultra Generalised Clipped Boundaries)

Note: The full-resolution `_NC` services exceed the ArcGIS per-feature transfer limit and
cannot be paged with geometry. The UGCB variant is used instead. If a newer UGCB vintage
is published on the ONS Open Geography Portal, update `ARCGIS_URL` in the loader and re-run.

**Reload:**
```bash
python ons_ctyua_boundaries/ons_ctyua_boundaries_load.py
```
