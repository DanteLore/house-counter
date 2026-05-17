# OS Open UPRN

Every addressable location in Great Britain has a Unique Property Reference Number (UPRN)  -  a
persistent numeric identifier assigned by the local authority and maintained by Ordnance Survey.
This dataset contains the UPRN and OSGB/WGS84 coordinates for all ~41.5 million locations,
including residential and commercial properties and features without postal addresses.

**Source:** OS Open UPRN, published under the Open Government Licence.  
**Update frequency:** Every six weeks.  
**Coverage:** Great Britain (England, Scotland, Wales). Does not include Northern Ireland.

---

## Athena table

```
database : incoming
table    : os_open_uprn_uprn
location : s3://dantelore.data.incoming/os_open_uprn/uprn/
```

---

## Schema

| Column | Type | Description |
|--------|------|-------------|
| `uprn` | bigint | Unique Property Reference Number  -  persistent identifier for the address |
| `x_coordinate` | double | OSGB36 easting in metres (British National Grid) |
| `y_coordinate` | double | OSGB36 northing in metres (British National Grid) |
| `latitude` | double | WGS84 latitude (decimal degrees) |
| `longitude` | double | WGS84 longitude (decimal degrees) |
| `grid_e` | int | **Partition key**  -  100km easting tile index: `floor(x_coordinate / 100000)` |
| `grid_n` | int | **Partition key**  -  100km northing tile index: `floor(y_coordinate / 100000)` |

---

## Partitioning

The data is partitioned by 100km National Grid tile. Each tile is identified by two integers:

```
grid_e = floor(x_coordinate / 100000)   -- 0 to 6  (west to east)
grid_n = floor(y_coordinate / 100000)   -- 0 to 12 (south to north)
```

There are 57 non-empty tiles across GB. Always filter on `grid_e` and/or `grid_n` in queries
that cover a known geographic area  -  this tells Athena which S3 prefixes to scan and avoids
reading the full 41M-row dataset.

### Tile reference

Approximate coverage of commonly queried areas:

| Area | grid_e | grid_n |
|------|--------|--------|
| London / SE England | 5 | 1 |
| East Anglia | 6 | 2 |
| South Coast (Southampton, Brighton) | 4 | 1 |
| South West (Bristol, Exeter) | 3 | 1 |
| Wales | 2–3 | 2–3 |
| Midlands (Birmingham, Coventry) | 4 | 2–3 |
| East Midlands (Nottingham, Leicester) | 4–5 | 3 |
| North West (Manchester, Liverpool) | 3–4 | 3–4 |
| Yorkshire (Leeds, Sheffield) | 4–5 | 4 |
| North East (Newcastle) | 4 | 5 |
| Scotland (Central Belt, Glasgow/Edinburgh) | 2–3 | 6 |
| Highlands | 2–3 | 7–9 |
| Shetland | 4 | 11–12 |

To find the tile for any OSGB coordinate pair:

```sql
-- Which tile is easting 530000, northing 180000 (central London)?
SELECT floor(530000 / 100000) AS grid_e,   -- 5
       floor(180000 / 100000) AS grid_n    -- 1
```

To find the tile for a known lat/lon, convert to OSGB first (e.g. via a GIS tool or the OS
Coordinates API), then apply the formula above.

---

## Example queries

**Look up a single UPRN:**
```sql
SELECT *
FROM os_open_uprn_uprn
WHERE grid_e = 5 AND grid_n = 1
  AND uprn = 10008314978
```

**All UPRNs within a bounding box (OSGB coordinates):**
```sql
SELECT uprn, x_coordinate, y_coordinate
FROM os_open_uprn_uprn
WHERE grid_e = 5 AND grid_n = 1
  AND x_coordinate BETWEEN 525000 AND 535000
  AND y_coordinate BETWEEN 178000 AND 182000
```

**Count UPRNs per tile (full table scan  -  use sparingly):**
```sql
SELECT grid_e, grid_n, COUNT(*) AS uprn_count
FROM os_open_uprn_uprn
GROUP BY grid_e, grid_n
ORDER BY grid_e, grid_n
```

**Join to another dataset on UPRN:**
```sql
SELECT h.price, h.date_of_transfer, u.latitude, u.longitude
FROM house_prices_ppd h
JOIN os_open_uprn_uprn u
  ON CAST(h.uprn AS bigint) = u.uprn
WHERE u.grid_e = 5 AND u.grid_n = 1
  AND h.year = '2024'
```

---

## Refreshing the data

The script overwrites all tiles with the current OS release:

```bash
python os_open_uprn/os_open_uprn_load.py
```

Downloads ~600MB, processes ~41.5M rows, and uploads ~57 Parquet files to S3. Takes several
minutes. Re-run whenever OS publish a new release (approximately every six weeks).
