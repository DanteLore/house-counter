# House Counter

A geospatial analysis tool for counting residential addresses and measuring housing density within user-drawn map areas. Built for urban planning research and housing analysis in Great Britain.

## What it does

Draw polygons on an interactive map, then query a database of ~41.5 million addressable locations (OS Open UPRN) to count how many properties fall inside each area. The tool calculates area and density metrics used in UK planning assessments:

- **Dwellings per hectare (DPH)** — the standard UK planning density metric
- **m² per address** — land use intensity
- **Total area** in m² and hectares

Multiple polygons can be managed simultaneously, named, colour-coded, and exported to a self-contained HTML report.

## Screenshot

Run the app and draw a polygon on the map to get started.

## Requirements

- Python 3.x
- AWS credentials configured for profile `dantelore` with access to Athena and S3 (`eu-west-1`)

## Getting started

```bash
bash run.sh
```

This creates a virtual environment, installs dependencies, and launches the Streamlit app. Open the URL shown in the terminal (usually `http://localhost:8501`).

## Usage

1. **Draw a polygon** using the rectangle or polygon tools on the map toolbar
2. **Name it** in the sidebar panel that appears
3. Click **Count** to query how many addresses fall within the polygon
4. Click **Show** to fetch and display all address locations as clustered map markers
5. Use **Export HTML** to generate a shareable static report (`output.html`)

Polygons are saved automatically to `polygons.geojson` between sessions.

## Data sources

### OS Open UPRN

Every addressable location in Great Britain has a Unique Property Reference Number (UPRN). This dataset contains coordinates for all ~41.5 million locations across England, Scotland, and Wales.

See [UPRN.md](UPRN.md) for the full schema, partitioning strategy, and example Athena queries.

| Detail | Value |
|--------|-------|
| Source | Ordnance Survey, Open Government Licence |
| Coverage | Great Britain (not Northern Ireland) |
| Update frequency | Every six weeks |
| Athena table | `incoming.os_open_uprn_uprn` |
| S3 location | `s3://dantelore.data.incoming/os_open_uprn/uprn/` |
| Partitioned by | 100km National Grid tiles (`grid_e`, `grid_n`) |

### Land Registry Price Paid Data

Every residential property sale in England & Wales registered with HM Land Registry since 1995.

See [PRICE-PAID.md](PRICE-PAID.md) for the full schema, partitioning strategy, and example Athena queries.

| Detail | Value |
|--------|-------|
| Source | HM Land Registry, Open Government Licence |
| Coverage | England and Wales only |
| Time range | 1995 – present (updated monthly) |
| Athena table | `incoming.house_prices_ppd` |
| S3 location | `s3://dantelore.data.incoming/house_prices/ppd/` |
| Partitioned by | `year` |

> **Note:** Price Paid Data is documented and available in Athena but is not currently used by the app. It can be joined to UPRN data on the `uprn` column for spatial price analysis.

## Architecture

```
Streamlit UI (app.py)
    │
    ├── Polygon drawing → polygons.geojson (session persistence)
    │
    ├── Geospatial processing (geo.py)
    │       WGS84 ↔ OSGB36 transforms, area calculation, grid tile lookup
    │
    ├── AWS Athena query (athena.py)
    │       Filters by National Grid partition, then bounding box, then point-in-polygon
    │
    ├── Density metrics (area_analysis.py)
    │       DPH, m² per address
    │
    └── HTML export (package.py)
            Self-contained Leaflet map + summary table → output.html
```

Queries use a two-stage spatial filter to avoid full-table scans on the 41M-row UPRN dataset: Athena filters by National Grid tile partition and bounding box, then Shapely performs the exact point-in-polygon test in Python.

## Project structure

| File | Purpose |
|------|---------|
| `app.py` | Main Streamlit application |
| `athena.py` | AWS Athena queries for UPRN data |
| `area_analysis.py` | `PolygonAnalysis` dataclass — area and density calculations |
| `geo.py` | Coordinate transforms, polygon area, partition tile lookup |
| `package.py` | HTML report generator |
| `test_area_analysis.py` | Unit tests for area and density calculations |
| `requirements.txt` | Python dependencies |
| `polygons.geojson` | Saved polygons (auto-created at runtime) |
| `UPRN.md` | OS Open UPRN data source documentation |
| `PRICE-PAID.md` | Land Registry Price Paid data source documentation |

## Running tests

```bash
python -m pytest test_area_analysis.py
```

## Dependencies

Core libraries: `streamlit`, `streamlit-folium`, `folium`, `shapely`, `pyproj`, `boto3`.

See `requirements.txt` for pinned versions.
