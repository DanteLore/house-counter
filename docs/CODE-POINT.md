# OS Code Point Open

Ordnance Survey postcode-to-coordinate lookup for ~1.7 million Great Britain postcodes.
Updated quarterly by OS. No API key required.

**Source:** https://osdatahub.os.uk/downloads/open/CodePointOpen  
**Current release cadence:** Quarterly (release `2026.2.0` as of April 2026)  
**Coverage:** England, Scotland, Wales (not Northern Ireland)

---

## Coordinate system

Coordinates are **OSGB36 / British National Grid (EPSG:27700)** — integer metres east and
north of the BNG false origin. This is the same system used in `os_open_uprn`.

To convert to WGS84 (latitude/longitude) in Athena you will need a projection library or
a pre-joined table; there is no built-in Athena function for OSGB→WGS84.

---

## Athena table

| Detail | Value |
|--------|-------|
| Database | `incoming` |
| Table | `os_code_point_open_codepo` |
| S3 location | `s3://dantelore.data.incoming/os_code_point_open/codepo/` |
| Format | Parquet / SNAPPY |
| Partition key | `postcode_area` (string, e.g. `sw`) |

---

## Schema

| Column | Type | Description |
|--------|------|-------------|
| `postcode` | string | Full postcode, e.g. `SW10 0AA` |
| `positional_quality_indicator` | int | Quality score for the coordinate (see below) |
| `eastings` | int | OSGB36 easting in metres (BNG, EPSG:27700) |
| `northings` | int | OSGB36 northing in metres (BNG, EPSG:27700) |
| `country_code` | string | ONS GSS country code, e.g. `E92000001` |
| `nhs_regional_ha_code` | string | NHS Regional Health Authority code (may be empty) |
| `nhs_ha_code` | string | NHS Health Authority / CCG code |
| `admin_county_code` | string | Administrative county GSS code (may be empty) |
| `admin_district_code` | string | Administrative district GSS code |
| `admin_ward_code` | string | Administrative ward GSS code |
| `postcode_area` | string | **Partition key** — two-letter area prefix, e.g. `sw` |

### Positional Quality Indicator (PQI)

| Value | Meaning |
|-------|---------|
| 10 | Within address building |
| 20 | Within postcode sector |
| 30 | Sector centroid |
| 40 | District centroid |
| 50 | Area centroid |
| 60 | Centroid of 1 km grid square |
| 90 | Postcode not geocoded |

---

## Partitioning

Data is split into 120 files, one per postcode area. The partition key `postcode_area` is the
lowercase two-letter area prefix (e.g. `sw`, `ec`, `b`).

Always filter on `postcode_area` when you know the area — it avoids a full table scan:

```sql
WHERE postcode_area = 'sw'
```

Single-letter areas (`b`, `e`, `g`, `l`, `m`, `n`, `s`, `w`) are stored as single characters.

---

## Example queries

### Look up a single postcode
```sql
SELECT postcode, eastings, northings, admin_district_code
FROM incoming.os_code_point_open_codepo
WHERE postcode_area = 'sw'
  AND postcode = 'SW10 0AA';
```

### All postcodes in a district
```sql
SELECT postcode, eastings, northings
FROM incoming.os_code_point_open_codepo
WHERE postcode_area = 'sw'
  AND admin_district_code = 'E09000020'   -- Kensington & Chelsea
ORDER BY postcode;
```

### Join postcodes to house price data
```sql
SELECT p.price, p.postcode, c.eastings, c.northings
FROM incoming.house_prices_ppd p
JOIN incoming.os_code_point_open_codepo c
  ON c.postcode = p.postcode
 AND c.postcode_area = LOWER(REGEXP_EXTRACT(p.postcode, '^([A-Z]+)', 1))
WHERE p.year = '2024'
  AND c.admin_district_code = 'E09000020';
```

### Count postcodes per country
```sql
SELECT country_code, COUNT(*) AS postcode_count
FROM incoming.os_code_point_open_codepo
GROUP BY country_code
ORDER BY postcode_count DESC;
```
