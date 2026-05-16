# ONS Built-up Area Boundaries 2024

ONS-defined polygon boundaries for all 7,775 Built-up Areas (BUAs) in England and Wales,
April 2024 vintage. A Built-up Area is a contiguous area of urban development — towns,
cities and suburbs — defined by the ONS from OS MasterMap Topography data. BUA boundaries
are stable reference geographies useful for grouping and spatially filtering other datasets
(house prices, traffic census, UPRN, etc.).

## Schema

**Glue table:** `incoming.ons_bua_boundaries_bua`
**S3 location:** `s3://dantelore.data.incoming/ons_bua_boundaries/bua/bua_2024.parquet`

| Column | Type | Description |
|---|---|---|
| `bua24cd` | string | Stable ONS area code (primary key, e.g. `E63012319`) |
| `bua24nm` | string | Area name (e.g. `Newbury`) |
| `geometry_wgs84_wkt` | string | Polygon/MultiPolygon in WGS84 (EPSG:4326, lng/lat) as WKT |
| `geometry_osgb_wkt` | string | Polygon/MultiPolygon in British National Grid (EPSG:27700, metres) as WKT |
| `centre_e` | int | Centroid easting in OSGB metres |
| `centre_n` | int | Centroid northing in OSGB metres |
| `bbox_min_e` | int | Bounding rectangle min easting (OSGB metres) |
| `bbox_min_n` | int | Bounding rectangle min northing (OSGB metres) |
| `bbox_max_e` | int | Bounding rectangle max easting (OSGB metres) |
| `bbox_max_n` | int | Bounding rectangle max northing (OSGB metres) |

All coordinates are in metres for OSGB columns. WKT geometry strings can be large
(tens to hundreds of KB per feature) — avoid `SELECT *` over many rows.

## Common queries

### Look up a single area by name

```sql
SELECT bua24cd, bua24nm, centre_e, centre_n
FROM incoming.ons_bua_boundaries_bua
WHERE bua24nm = 'Newbury'
```

### Find all areas within a bounding box

The bbox columns allow fast rectangular pre-filtering without parsing WKT geometry.
For example, to find all BUAs whose centroid falls within a 20km radius of a point:

```sql
-- Areas with centroid within ~20km of Newbury town centre (448000, 167000)
SELECT bua24cd, bua24nm, centre_e, centre_n
FROM incoming.ons_bua_boundaries_bua
WHERE centre_e BETWEEN 428000 AND 468000
  AND centre_n BETWEEN 147000 AND 187000
```

Use the bounding rectangle columns to find areas that could overlap a region of interest
(useful before doing exact geometry work elsewhere):

```sql
-- BUAs whose bounding rectangle overlaps a query rectangle
SELECT bua24cd, bua24nm
FROM incoming.ons_bua_boundaries_bua
WHERE bbox_max_e >= 440000
  AND bbox_min_e <= 460000
  AND bbox_max_n >= 160000
  AND bbox_min_n <= 175000
```

### Join to house price data by area name

```sql
SELECT
    b.bua24nm,
    COUNT(*) AS sales,
    ROUND(AVG(p.price)) AS avg_price
FROM incoming.house_prices_ppd p
JOIN incoming.ons_bua_boundaries_bua b
    ON p.town_city = b.bua24nm
WHERE p.year = '2023'
GROUP BY b.bua24nm
ORDER BY avg_price DESC
```

Note: `town_city` in the house price data is free text and won't always match `bua24nm`
exactly — consider normalising case or using a postcode-to-BUA lookup via OS Code Point Open.

### List all areas sorted by size of bounding rectangle (largest first)

```sql
SELECT
    bua24nm,
    (bbox_max_e - bbox_min_e) AS width_m,
    (bbox_max_n - bbox_min_n) AS height_m,
    (bbox_max_e - bbox_min_e) * (bbox_max_n - bbox_min_n) / 1000000 AS bbox_area_km2
FROM incoming.ons_bua_boundaries_bua
ORDER BY bbox_area_km2 DESC
LIMIT 20
```

## Working with WKT geometry

Athena does not have native spatial functions, so the WKT columns are most useful when:

- Exporting results to a GIS tool (QGIS, GeoPandas) for exact point-in-polygon tests
- Passing geometries to another system that accepts WKT (e.g. PostGIS, Spark)
- Visual inspection via a WKT viewer

For point-in-polygon filtering in the pipeline itself, the recommended approach is to use
the bbox columns in Athena for a fast coarse filter, then apply exact geometry tests in
Python with Shapely:

```python
from shapely import wkt

# After querying Athena for candidate rows...
polygon = wkt.loads(row["geometry_osgb_wkt"])
point = Point(easting, northing)
if polygon.contains(point):
    ...
```

## Source and update cadence

**Source:** ONS Open Geography Portal
([main_ONS_BUA_2024_EW_V2](https://services1.arcgis.com/ESMARspQHYMw9BZ9/ArcGIS/rest/services/main_ONS_BUA_2024_EW_V2/FeatureServer/0))

BUA boundaries are updated infrequently — the current vintage is April 2024. Check the
[ONS Open Geography Portal](https://geoportal.statistics.gov.uk/) for new releases and
re-run the loader when a new vintage is published.

**Reload:**
```bash
python ons_bua_boundaries/ons_bua_boundaries_load.py
```
