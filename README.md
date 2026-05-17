# House Counter

A geospatial analysis tool for counting residential addresses, measuring housing density, and analysing house price trends within user-drawn map areas. Built for urban planning research and housing analysis in Great Britain.

## What it does

Draw polygons on an interactive map, then query a database of ~41.5 million addressable locations (OS Open UPRN) and 30 years of Land Registry price paid records to analyse each area:

- **Dwellings per hectare (DPH)**  -  the standard UK planning density metric
- **m² per address**  -  land use intensity
- **House price trends**  -  median price, P25–P75 band, inflation-adjusted, vs national/county baseline
- **Property mix**  -  breakdown by type, tenure, and new/established build over time
- **Market metrics**  -  CAGR, price volatility (CV), annual turnover rate, premium vs baseline
- **Sales volume**  -  annual sales as % of address stock, by property type

Multiple polygons can be managed simultaneously, named, colour-coded, and exported to a self-contained HTML report.

## Requirements

- Python 3.x
- AWS credentials configured for profile `dantelore` with access to Athena and S3 (`eu-west-1`)
- Data loaded to the lake via [DanteLore/gov-etl](https://github.com/DanteLore/gov-etl)  -  see that repo for ETL scripts covering all datasets listed below

## Getting started

```bash
bash run.sh
```

This creates a virtual environment, installs dependencies, and launches the Streamlit app. Open the URL shown in the terminal (usually `http://localhost:8501`).

## Data sources

### OS Open UPRN

Every addressable location in Great Britain has a Unique Property Reference Number (UPRN). This dataset contains coordinates for all ~41.5 million locations across England, Scotland, and Wales.

| Detail | Value |
|--------|-------|
| Source | Ordnance Survey, Open Government Licence |
| Coverage | Great Britain (not Northern Ireland) |
| Athena table | `incoming.os_open_uprn_uprn` |
| Coordinates | `x_coordinate`, `y_coordinate`  -  OSGB36 metres (not tile indices) |
| Partitioned by | 100km National Grid tiles (`grid_e`, `grid_n`) |

### Land Registry Price Paid Data

Every residential property sale in England & Wales registered with HM Land Registry since 1995.

| Detail | Value |
|--------|-------|
| Source | HM Land Registry, Open Government Licence |
| Coverage | England and Wales only |
| Time range | 1995 – present (updated monthly) |
| Athena table | `incoming.house_prices_ppd` |
| Partitioned by | `year` |
| Property type O | Excluded from all queries  -  non-standard types (park homes, houseboats) distort statistics |
| Latest year | Always excluded from charts  -  Land Registry registration lags completions by 6–8 weeks |

### ONS/OS Built-up Area Boundaries

CTYUA (County/Unitary Authority) boundaries used for county-level comparison baselines.

### ONS CPI

Annual average CPI index used for inflation adjustment (real-terms price analysis).

## Architecture

The app is structured in four layers, each with a single responsibility:

**Pages** (`pages/`)  -  display only. No SQL, no spatial logic, no business calculations. Each page is a thin shell that calls module functions and renders results. Target: ~300 lines per page.

**Feature modules** (`price_paid/`)  -  self-contained logic for a feature area, organised into sub-modules. No cross-module state. See [Price Paid page pattern](#price-paid-page-pattern) below.

**Queries** (`queries/`)  -  one file per data source. Owns the SQL, partition/bbox strategy, and any post-query filtering (e.g. exact point-in-polygon via Shapely). No boto3.

**Plumbing** (`queries/athena.py`)  -  the only file that touches boto3. Executes SQL, polls for completion, handles errors, and returns plain Python dicts.

Queries use a two-stage spatial filter to avoid full-table scans: Athena filters by partition key and bounding box, then Shapely performs the exact point-in-polygon test in Python.

## Price Paid page pattern

`pages/2_PricePaid.py` was refactored from a 1,869-line monolith into a modular structure. The pattern used is documented here for consistency when adding new sections.

### Module structure

```
price_paid/
├── __init__.py
├── cache.py          # JSON disk cache  -  load/save national and county data
├── session.py        # Session state init, polygon accessors, Athena fetch helpers
├── filters.py        # Year-range filtering, latest_year computation, selector widget
├── inflation.py      # CPI deflation helpers (prices_in_real_terms, stats_in_real_terms)
├── calculations.py   # Pure-Python market metrics  -  no Streamlit, fully unit-testable
└── charts/
    ├── __init__.py
    ├── common.py           # Shared constants (PROPERTY_TYPE_LABELS/COLORS) and utilities
    ├── market_summary.py   # render_market_summary()  -  metrics cards and narrative
    ├── price_distribution.py  # render_price_distribution_table(), render_price_histogram()
    ├── price_trends.py     # render_median_trends(), render_indexed_performance()
    ├── property_mix.py     # render_property_mix()
    ├── price_by_type.py    # render_price_by_type()
    └── turnover.py         # render_annual_turnover(), render_volume_by_type()
```

### Design rules

1. **Each `charts/*.py` file owns one page section end-to-end.** It contains both the pure Plotly chart builder function(s) and a `render_*()` function that handles the Streamlit widgets, narrative text, chart, and data table for that section. The page just calls `render_*()`.

2. **`calculations.py` has no Streamlit imports.** All market metric functions accept plain data (lists of dicts) and return plain Python values. This makes them fully unit-testable without mocking Streamlit.

3. **No shared mutable module-level state.** Every function receives its data as arguments. The page computes shared derived state (e.g. `latest_year`, `comparison_by_year`, `cpi`) once at the top and passes it in via short wrapper functions.

4. **Short wrapper functions (`_filter`, `_yr_sel`, `_stats_real`, etc.) close over derived state** in the page's run-scope, so `render_*` calls stay clean without threading the same variables through every argument.

5. **`session.py` is the only place that touches `st.session_state`.** It initialises all `pp_*` keys on first load and provides the `poly_*` accessors (`poly_name`, `poly_stats`, `poly_prices`, etc.) that the rest of the code uses.

6. **Property type O is excluded everywhere, permanently.** The exclusion is in the SQL (`AND p.property_type != 'O'`), not in Python post-filtering. Non-standard residential types (park homes, houseboats, converted structures) distort medians and should never appear in any chart or table.

7. **Latest year is always excluded.** Land Registry registration lags completions by 6–8 weeks, making the current year a partial sample with low counts and unrepresentative mix. `compute_latest_year()` derives this from the maximum year seen across all data sources.

### Adding a new section

1. Create (or add to) a file in `price_paid/charts/`.
2. Write a pure Plotly chart builder function  -  accepts data, returns a `go.Figure`.
3. Write a `render_*()` function that renders the subheader, description, widgets, chart, and data table. It should call the chart builder and `show_data_table()` from `common.py`.
4. Add the call to `render_*()` at the bottom of `pages/2_PricePaid.py`, passing the bound wrappers.
5. If the section involves new calculations, add them to `calculations.py` and write tests in `tests/test_calculations.py`.

### Statistical methods

| Metric | Formula | Notes |
|--------|---------|-------|
| CAGR | `(Vn/V0)^(1/n) - 1` | Compound Annual Growth Rate of median price, first to last year in range |
| CV (volatility) | `stdev(medians) / mean(medians)` | Coefficient of Variation  -  requires ≥ 3 years |
| Turnover | `mean(annual_sales) / address_stock` | Mean across years, denominator is UPRN count |
| Premium | `mean(poly_median / baseline_median)` | Per-year ratio then averaged  -  prevents high-volume years dominating |
| New-build share | `mean(new_builds/total per year)` | Per-year average  -  prevents high-volume years dominating |
| Inflation adjustment | `price × (CPI_base / CPI_year)` | Annual average CPI; base year = most recent year in CPI data |

All these are tested in `tests/test_calculations.py` with hand-verified examples.

## Project structure

```
house-counter/
├── app.py                       # Entry point  -  redirects to Manage Polygons
├── run.sh                       # Bootstrap: venv, pip install, streamlit run
│
├── pages/                       # Streamlit pages  -  display only, ~300 lines each
│   ├── 0_Manage_Polygons.py     # Draw, import, edit and delete polygons
│   ├── 1_House_Counter.py       # Count addresses, density metrics, HTML export
│   └── 2_PricePaid.py           # House price analysis and trends
│
├── price_paid/                  # Feature modules for the Price Paid page
│   ├── cache.py                 # Disk cache (national + county JSON files)
│   ├── session.py               # Session state, polygon accessors, fetch helpers
│   ├── filters.py               # Year-range filtering and selector widget
│   ├── inflation.py             # CPI deflation helpers
│   ├── calculations.py          # Pure-Python market metrics (no Streamlit)
│   └── charts/                  # One file per page section
│       ├── common.py            # Shared constants and chart utilities
│       ├── market_summary.py
│       ├── price_distribution.py
│       ├── price_trends.py
│       ├── property_mix.py
│       ├── price_by_type.py
│       └── turnover.py
│
├── queries/                     # All data access  -  one file per data source
│   ├── athena.py                # boto3 plumbing only: run_query()
│   ├── uprn_queries.py          # OS Open UPRN + VOA rating list queries
│   ├── price_paid_queries.py    # Land Registry Price Paid + CPI queries
│   └── bua_queries.py           # ONS Built-up Area boundary queries
│
├── utils/                       # Shared utilities
│   ├── nav.py                   # Navigation bar and data attributions
│   ├── polygons.py              # Load/save polygons.geojson
│   └── geo.py                   # WGS84 ↔ OSGB36 transforms, area, tile lookup
│
├── tests/                       # Unit tests
│   ├── test_calculations.py     # Market metric functions (58 tests)
│   ├── test_inflation.py        # CPI deflation functions
│   ├── test_area_analysis.py    # Density metric calculations
│   ├── test_price_paid_queries.py
│   ├── test_uprn_queries.py
│   └── test_bua_queries.py
│
├── docs/                        # Data source reference documentation
│   ├── UPRN.md
│   ├── PRICE-PAID.md
│   ├── CODE-POINT.md
│   ├── BUA-BOUNDARIES.md
│   └── VOA.md
│
├── requirements.txt             # Python dependencies
└── polygons.geojson             # Saved polygons (auto-created at runtime)
```

## Running tests

```bash
venv/Scripts/python -m pytest tests/ -v
```

## Dependencies

Core libraries: `streamlit`, `streamlit-folium`, `folium`, `shapely`, `pyproj`, `boto3`, `plotly`, `scipy`, `numpy`.

See `requirements.txt` for pinned versions.
