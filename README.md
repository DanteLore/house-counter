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
- Data loaded to the lake via [DanteLore/gov-etl](https://github.com/DanteLore/gov-etl) — see that repo for ETL scripts covering all datasets listed above

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

The app is structured in three layers, each with a single responsibility:

**Pages** (`pages/`) — display only. No SQL, no spatial logic, no business calculations. Pages call query functions and render the results.

**Queries** (`queries/`) — one file per data source. Each file owns the SQL for that source, the partition/bbox strategy, and any post-query filtering (e.g. exact point-in-polygon tests). No boto3 here.

**Plumbing** (`queries/athena.py`) — the only file that touches boto3. Executes SQL, polls for completion, handles errors, and returns results as plain Python dicts. No SQL, no domain logic.

Supporting modules at the root handle geometry (`geo.py`), density metrics (`area_analysis.py`), and polygon persistence (`polygons.py`).

Queries use a two-stage spatial filter to avoid full-table scans on large datasets: Athena filters by partition key and bounding box, then Shapely performs the exact point-in-polygon test in Python.

## Project structure

```
house-counter/
├── app.py                      # Entry point — redirects to Manage Polygons
├── nav.py                      # Shared navigation bar and data attributions
├── geo.py                      # WGS84 ↔ OSGB36 transforms, area, partition tile lookup
├── area_analysis.py            # PolygonAnalysis — DPH, m² per address, density metrics
├── polygons.py                 # Load/save polygons.geojson, make_feature()
├── package.py                  # HTML report export
│
├── queries/                    # All data access — one file per data source
│   ├── athena.py               # boto3 plumbing only: run_query(), run_query_rows()
│   ├── uprn_queries.py         # OS Open UPRN + VOA rating list queries
│   ├── price_paid_queries.py   # Land Registry Price Paid queries
│   └── bua_queries.py          # ONS Built-up Area boundary queries
│
├── pages/                      # Streamlit pages — display only, no business logic
│   ├── 0_Manage_Polygons.py    # Draw, import, edit and delete polygons
│   ├── 1_House_Counter.py      # Count residential/commercial addresses per polygon
│   └── 2_Price_Paid.py         # House price analysis and trends
│
├── docs/                       # Data source reference documentation
│   ├── UPRN.md
│   ├── PRICE-PAID.md
│   ├── CODE-POINT.md
│   ├── BUA-BOUNDARIES.md
│   └── VOA.md
│
├── test_area_analysis.py       # Unit tests for area and density calculations
├── requirements.txt            # Python dependencies
└── polygons.geojson            # Saved polygons (auto-created at runtime)
```

## Running tests

```bash
python -m pytest test_area_analysis.py
```

## Dependencies

Core libraries: `streamlit`, `streamlit-folium`, `folium`, `shapely`, `pyproj`, `boto3`.

See `requirements.txt` for pinned versions.
