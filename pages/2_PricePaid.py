import json
import os
import statistics

import folium
import numpy as np
from scipy.stats import gaussian_kde
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

import utils.nav as nav
from queries.price_paid_queries import (
    fetch_price_stats_for_polygon,
    fetch_price_stats_national,
    fetch_mix_for_polygon,
    fetch_cpi_by_year,
    deflate_prices,
    real_stats_from_prices,
)
from utils.polygons import DEFAULT_COLOR, load_polygons, save_polygons

st.set_page_config(page_title="Price Paid Analysis", layout="wide")

st.markdown("""
<style>
[data-testid="stSidebar"] { display: none; }
[data-testid="collapsedControl"] { display: none; }
.main .block-container { padding-top: 0.75rem; }
</style>
""", unsafe_allow_html=True)

nav.render()
st.title("Price Paid Analysis")


# ---------------------------------------------------------------------------
# Load polygons
# ---------------------------------------------------------------------------




polygons = load_polygons()

if not polygons:
    st.info("No polygons saved yet. Draw some on the House Counter page first.")
    st.stop()


# ---------------------------------------------------------------------------
# Polygon selector
# ---------------------------------------------------------------------------

poly_names = [f["properties"].get("name", f"Polygon {i+1}") for i, f in enumerate(polygons)]
preferred = [n for n in poly_names if n in ("Newbury", "Thatcham")]
default_selection = preferred if preferred else poly_names[:1]
selected_names = st.multiselect("Select polygons to analyse", poly_names, default=default_selection)

if not selected_names:
    st.info("Select at least one polygon above.")
    st.stop()

selected = [f for f in polygons if f["properties"].get("name") in selected_names]

missing_count = [f["properties"].get("name") for f in selected if f["properties"].get("uprn_count") is None]
if missing_count:
    st.warning(
        f"These polygons have no address count — turnover % will be unavailable: "
        f"{', '.join(missing_count)}. Use the House Counter page to count addresses first."
    )


# ---------------------------------------------------------------------------
# Map
# ---------------------------------------------------------------------------

all_lons, all_lats = [], []
for feat in selected:
    for lon, lat in feat["geometry"]["coordinates"][0]:
        all_lons.append(lon)
        all_lats.append(lat)

map_centre = (
    (min(all_lats) + max(all_lats)) / 2,
    (min(all_lons) + max(all_lons)) / 2,
)

m = folium.Map(location=map_centre, zoom_start=13, tiles="OpenStreetMap")

for feat in selected:
    color = feat["properties"].get("color", DEFAULT_COLOR)
    name = feat["properties"].get("name", "")
    folium.GeoJson(
        feat,
        style_function=lambda _, c=color: {
            "color": c,
            "fillColor": c,
            "fillOpacity": 0.25,
            "weight": 2,
        },
        tooltip=folium.Tooltip(name),
    ).add_to(m)

for feat in polygons:
    if feat["properties"].get("name") not in selected_names:
        folium.GeoJson(
            feat,
            style_function=lambda _: {
                "color": "#aaaaaa",
                "fillColor": "#aaaaaa",
                "fillOpacity": 0.08,
                "weight": 1,
                "dashArray": "4 4",
            },
        ).add_to(m)

st_folium(m, width="stretch", height=400, returned_objects=[])

st.divider()


NATIONAL_CACHE_FILE = "national_price_stats.json"


def _load_national_cache():
    if os.path.exists(NATIONAL_CACHE_FILE):
        with open(NATIONAL_CACHE_FILE) as f:
            data = json.load(f)
        # Old format was a bare list; new format is {"stats": [...], "cpi": {...}}
        if isinstance(data, list):
            return {"stats": data, "cpi": None}
        return data
    return None


def _save_national_cache(stats, cpi):
    with open(NATIONAL_CACHE_FILE, "w") as f:
        json.dump({"stats": stats, "cpi": cpi}, f)


# ---------------------------------------------------------------------------
# Session state — seed from stored data on first load
# ---------------------------------------------------------------------------

if "pp_results" not in st.session_state:
    st.session_state.pp_results = {}
if "pp_national" not in st.session_state or "pp_cpi" not in st.session_state:
    _cached = _load_national_cache() or {}
    st.session_state.pp_national = _cached.get("stats")
    st.session_state.pp_cpi = _cached.get("cpi")

for feat in polygons:
    poly_id = feat["properties"].get("id", feat["properties"].get("name"))
    if poly_id not in st.session_state.pp_results:
        stored_stats = feat["properties"].get("pp_stats")
        stored_prices = feat["properties"].get("pp_prices")
        if stored_stats is not None:
            prices_tuples = [tuple(p) for p in (stored_prices or [])]
            st.session_state.pp_results[poly_id] = {
                "stats": stored_stats,
                "prices": prices_tuples,
                "mix": feat["properties"].get("pp_mix", []),
            }


# ---------------------------------------------------------------------------
# Fetch controls
# ---------------------------------------------------------------------------

def _fetch_polygon(feat):
    poly_id = feat["properties"].get("id", feat["properties"].get("name"))
    name = feat["properties"].get("name", poly_id)
    coords = feat["geometry"]["coordinates"]
    with st.spinner(f"Fetching prices for {name}…"):
        poly_stats, all_prices = fetch_price_stats_for_polygon(coords)
    with st.spinner(f"Fetching property mix for {name}…"):
        mix = fetch_mix_for_polygon(coords)
    st.session_state.pp_results[poly_id] = {"stats": poly_stats, "prices": all_prices, "mix": mix}
    for i, f in enumerate(polygons):
        if f["properties"].get("id", f["properties"].get("name")) == poly_id:
            polygons[i]["properties"]["pp_stats"] = poly_stats
            polygons[i]["properties"]["pp_prices"] = [list(p) for p in all_prices]
            polygons[i]["properties"]["pp_mix"] = mix
            break
    save_polygons(polygons)


def _ensure_national():
    if st.session_state.pp_national is None:
        with st.spinner("Fetching national price data…"):
            st.session_state.pp_national = fetch_price_stats_national()
        with st.spinner("Fetching CPI inflation data…"):
            st.session_state.pp_cpi = fetch_cpi_by_year()
        _save_national_cache(st.session_state.pp_national, st.session_state.pp_cpi)


with st.container():
    btn_cols = st.columns(2 + len(selected))
    if btn_cols[0].button("Fetch all", type="primary", use_container_width=True):
        _ensure_national()
        for feat in selected:
            _fetch_polygon(feat)
        st.rerun()

    if btn_cols[1].button("Fetch missing", use_container_width=True):
        _ensure_national()
        already = st.session_state.pp_results
        for feat in selected:
            poly_id = feat["properties"].get("id", feat["properties"].get("name"))
            if poly_id not in already:
                _fetch_polygon(feat)
        st.rerun()

    for idx, feat in enumerate(selected):
        poly_id = feat["properties"].get("id", feat["properties"].get("name"))
        name = feat["properties"].get("name", poly_id)
        if btn_cols[2 + idx].button(f"↺ {name}", key=f"refresh_{poly_id}",
                                    use_container_width=True):
            _ensure_national()
            _fetch_polygon(feat)
            st.rerun()


# ---------------------------------------------------------------------------
# Check we have data to display
# ---------------------------------------------------------------------------

loaded = [
    f for f in selected
    if f["properties"].get("id", f["properties"].get("name")) in st.session_state.pp_results
]

if not loaded:
    st.caption("Click 'Fetch missing' to load results.")
    st.stop()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _by_year(stats):
    return {r["year"]: r for r in stats}


def _float(val, fallback=None):
    try:
        return float(val)
    except (TypeError, ValueError):
        return fallback


def _hex_to_rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _bar_vs_baseline(fig, years, vals, name, color, baseline=100,
                     hover_suffix="", show_legend=True):
    """Add grouped bars coloured by whether they are above or below baseline."""
    above_y = [v - baseline if v >= baseline else 0 for v in vals]
    below_y = [v - baseline if v < baseline else 0 for v in vals]

    fig.add_trace(go.Bar(
        x=years, y=above_y,
        name=name,
        marker_color=color,
        opacity=0.8,
        legendgroup=name,
        showlegend=show_legend,
        base=baseline,
        hovertemplate="%{x}: %{base:.1f}" + hover_suffix + "<extra>" + name + "</extra>",
    ))
    fig.add_trace(go.Bar(
        x=years, y=below_y,
        name=name,
        marker_color=color,
        opacity=0.4,
        legendgroup=name,
        showlegend=False,
        base=baseline,
        hovertemplate="%{x}: %{base:.1f}" + hover_suffix + "<extra>" + name + "</extra>",
    ))


national = st.session_state.pp_national or []

# Exclude the latest year across all charts — it is almost always incomplete.
# Derived from national data (largest dataset); polygon stats use the same cutoff.
_latest_year = max((r["year"] for r in national), default=None)

def _complete(rows):
    """Exclude the latest (incomplete) year from a list of year-keyed dicts."""
    return [r for r in rows if r["year"] != _latest_year]

national = _complete(national)
_nat_by_yr = _by_year(national)

_cpi = st.session_state.pp_cpi or {}
_cpi_available = bool(_cpi)
_cpi_base_year = max(_cpi.keys()) if _cpi else None


def _cpi_warning():
    if not _cpi_available:
        st.warning("CPI data not loaded — click **Fetch all** or **Fetch missing** to enable inflation adjustment.")


def _deflate_prices(year_prices, adjust):
    return deflate_prices(year_prices, _cpi, _cpi_base_year) if adjust else year_prices


def _real_stats(poly_id, adjust):
    """Return yearly stats for a polygon, deflating source prices first when adjust=True."""
    year_prices = st.session_state.pp_results[poly_id].get("prices", [])
    if adjust:
        return real_stats_from_prices(year_prices, _cpi, _cpi_base_year)
    return st.session_state.pp_results[poly_id]["stats"]


def _real_national_stats(adjust):
    """Return national yearly stats deflated to current £.

    National stats come from Athena aggregates (no raw prices stored), so we
    deflate the pre-computed stats directly — valid because CPI deflation is a
    linear per-year transform, making deflate(median) == median(deflate(prices)).
    """
    rows = st.session_state.pp_national or []
    if not adjust:
        return rows
    return [
        {**r,
         "min_price":    deflate_prices([(r["year"], r["min_price"])],    _cpi, _cpi_base_year)[0][1],
         "max_price":    deflate_prices([(r["year"], r["max_price"])],    _cpi, _cpi_base_year)[0][1],
         "mean_price":   deflate_prices([(r["year"], r["mean_price"])],   _cpi, _cpi_base_year)[0][1],
         "median_price": deflate_prices([(r["year"], r["median_price"])], _cpi, _cpi_base_year)[0][1],
         "p25_price":    deflate_prices([(r["year"], r["p25_price"])],    _cpi, _cpi_base_year)[0][1],
         "p75_price":    deflate_prices([(r["year"], r["p75_price"])],    _cpi, _cpi_base_year)[0][1],
         }
        for r in rows
    ]


def _price_label(adjust):
    return f"Sale price ({_cpi_base_year} £)" if adjust else "Sale price (£)"


_all_years = sorted({
    year
    for feat in loaded
    for year, _ in st.session_state.pp_results[
        feat["properties"].get("id", feat["properties"].get("name"))
    ].get("prices", [])
    if year != _latest_year
})


def _year_range_selector(key_prefix):
    """Render from/to year selectors and return (from_year, to_year) or (None, None)."""
    if not _all_years:
        return None, None
    c1, c2, c3 = st.columns([2, 1, 1])
    with c2:
        from_yr = st.selectbox("From year", _all_years, index=0,
                               key=f"{key_prefix}_from")
    with c3:
        to_yr = st.selectbox("To year", _all_years, index=len(_all_years) - 1,
                             key=f"{key_prefix}_to")
    return from_yr, to_yr


def _filter(rows, from_year=None, to_year=None):
    """Filter year-keyed dicts to a year range, excluding the latest incomplete year."""
    return [r for r in rows
            if r["year"] != _latest_year
            and (from_year is None or r["year"] >= from_year)
            and (to_year   is None or r["year"] <= to_year)]



st.divider()


# ---------------------------------------------------------------------------
# Section 1: Price distribution summary table
# ---------------------------------------------------------------------------

st.subheader("Price distribution")
_adj_table = st.toggle("Adjust for inflation (current £)", key="adj_table", value=False)
if _adj_table:
    _cpi_warning()
_table_from, _table_to = _year_range_selector("table")
st.markdown(
    "Overall price spread across the selected years of sales data. "
    "The median is the middle sale price — half of all sales were above and half below. "
    "P25 and P75 show the middle 50% range. "
    "P5 and P95 show the 90% range: 90% of all sales fell between these two values."
)

col_headers = st.columns([3, 2, 2, 2, 2, 2, 2, 2])
col_headers[0].markdown("**Polygon**")
col_headers[1].markdown("**P5**")
col_headers[2].markdown("**Lower quartile (P25)**")
col_headers[3].markdown("**Median**")
col_headers[4].markdown("**Upper quartile (P75)**")
col_headers[5].markdown("**P95**")
col_headers[6].markdown("**Min ever**")
col_headers[7].markdown("**Max ever**")

for feat in loaded:
    poly_id = feat["properties"].get("id", feat["properties"].get("name"))
    name = feat["properties"].get("name", poly_id)
    year_prices = [(y, p) for y, p in st.session_state.pp_results[poly_id].get("prices", [])
                   if y != _latest_year
                   and (_table_from is None or y >= _table_from)
                   and (_table_to   is None or y <= _table_to)]
    if not year_prices:
        continue
    prices = sorted(p for _, p in _deflate_prices(year_prices, _adj_table))
    n = len(prices)
    p5  = prices[max(0, int(n * 0.05) - 1)]
    p25 = prices[max(0, int(n * 0.25) - 1)]
    p75 = prices[min(n - 1, int(n * 0.75))]
    p95 = prices[min(n - 1, int(n * 0.95))]

    cols = st.columns([3, 2, 2, 2, 2, 2, 2, 2])
    cols[0].markdown(name)
    cols[1].markdown(f"£{p5:,.0f}")
    cols[2].markdown(f"£{p25:,.0f}")
    cols[3].markdown(f"£{statistics.median(prices):,.0f}")
    cols[4].markdown(f"£{p75:,.0f}")
    cols[5].markdown(f"£{p95:,.0f}")
    cols[6].markdown(f"£{min(prices):,.0f}")
    cols[7].markdown(f"£{max(prices):,.0f}")
    cols[5].markdown(f"£{max(prices):,.0f}")

st.divider()


# ---------------------------------------------------------------------------
# Section 2: Price distribution histogram
# ---------------------------------------------------------------------------

st.subheader("Price distribution histogram")
_adj_hist = st.toggle("Adjust for inflation (current £)", key="adj_hist", value=False)
if _adj_hist:
    _cpi_warning()
st.markdown(
    "Distribution of sale prices for each polygon, normalised so shapes are comparable "
    "regardless of total transaction count. Bottom and top 1% are excluded as outliers. "
    "The shape reveals whether the market is broad or tightly clustered, "
    "and whether there are distinct sub-markets (e.g. a concentration of flats at one end "
    "and detached houses at the other)."
)

_hist_from, _hist_to = _year_range_selector("hist")
if _all_years:
    hcol1, hcol2 = st.columns([2, 1])
    with hcol1:
        price_min = st.number_input("Min price (£)", value=75_000, step=5_000, key="hist_price_min")
    with hcol2:
        price_max = st.number_input("Max price (£)", value=1_000_000, step=25_000, key="hist_price_max")
else:
    price_min, price_max = 75_000, 1_000_000

fig_hist = go.Figure()
for feat in loaded:
    poly_id = feat["properties"].get("id", feat["properties"].get("name"))
    name = feat["properties"].get("name", poly_id)
    color = feat["properties"].get("color", DEFAULT_COLOR)
    year_prices = st.session_state.pp_results[poly_id].get("prices", [])
    if not year_prices:
        continue

    filtered = [(y, p) for y, p in year_prices
                if y != _latest_year
                and (_hist_from is None or y >= _hist_from)
                and (_hist_to   is None or y <= _hist_to)]
    prices = [p for _, p in _deflate_prices(filtered, _adj_hist)]

    prices = [p for p in prices if price_min <= p <= price_max]

    kde = gaussian_kde(prices)
    x_range = np.linspace(min(prices), max(prices), 500)
    y_kde = kde(x_range)

    fig_hist.add_trace(go.Scatter(
        x=x_range, y=y_kde,
        mode="lines",
        name=name,
        fill="tozeroy",
        fillcolor=_hex_to_rgba(color, 0.2),
        line=dict(color=color, width=2),
        hovertemplate="£%{x:,.0f}: %{y:.6f}<extra>" + name + "</extra>",
    ))

fig_hist.update_layout(
    xaxis_title=_price_label(_adj_hist),
    yaxis_title="Probability density",
    xaxis=dict(tickprefix="£", tickformat=","),
    legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
    margin=dict(t=20, b=40),
    hovermode="x unified",
)
st.plotly_chart(fig_hist, width="stretch")

st.divider()


# ---------------------------------------------------------------------------
# Section 3: Price trends over time
# ---------------------------------------------------------------------------

st.subheader("Median price trends")
_adj_trend = st.toggle("Adjust for inflation (current £)", key="adj_trend", value=False)
if _adj_trend:
    _cpi_warning()
_trend_from, _trend_to = _year_range_selector("trend")

_nat_trend = _filter(_real_national_stats(_adj_trend), _trend_from, _trend_to)
_nat_trend_by_yr = _by_year(_nat_trend)

narrative_parts = []
for feat in loaded:
    poly_id = feat["properties"].get("id", feat["properties"].get("name"))
    name = feat["properties"].get("name", poly_id)
    stats = _filter(_real_stats(poly_id, _adj_trend), _trend_from, _trend_to)
    if not stats:
        continue
    latest = stats[-1]
    latest_median = _float(latest["median_price"])
    nat_latest_raw = _nat_trend_by_yr.get(latest["year"])
    nat_latest = _float(nat_latest_raw["median_price"]) if nat_latest_raw else None
    if latest_median and nat_latest:
        pct_vs_national = (latest_median / nat_latest - 1) * 100
        direction = "above" if pct_vs_national >= 0 else "below"
        narrative_parts.append(
            f"**{name}** had a median sale price of **£{latest_median:,.0f}** in {latest['year']}, "
            f"{abs(pct_vs_national):.0f}% {direction} the national median of £{nat_latest:,.0f}."
        )

_inflation_note = f" Prices adjusted to {_cpi_base_year} £ using annual average CPI." if _adj_trend else ""
st.markdown(
    "Median sale price per year for each selected area alongside the national median (dotted line)."
    + _inflation_note + " "
    + " ".join(narrative_parts)
)

fig_trend = go.Figure()

for feat in loaded:
    poly_id = feat["properties"].get("id", feat["properties"].get("name"))
    name = feat["properties"].get("name", poly_id)
    color = feat["properties"].get("color", DEFAULT_COLOR)
    stats = _filter(_real_stats(poly_id, _adj_trend), _trend_from, _trend_to)

    years = [r["year"] for r in stats]

    # P25 lower bound — no fill, invisible line, just sets the base for tonexty
    fig_trend.add_trace(go.Scatter(
        x=years,
        y=[_float(r["p25_price"]) for r in stats],
        mode="lines",
        name=name,
        legendgroup=name,
        showlegend=False,
        line=dict(color=color, width=0),
        hovertemplate="%{x}: £%{y:,.0f} (P25)<extra>" + name + "</extra>",
    ))
    # P75 upper bound — filled back to P25
    fig_trend.add_trace(go.Scatter(
        x=years,
        y=[_float(r["p75_price"]) for r in stats],
        mode="lines",
        name=f"{name} (P25–P75)",
        legendgroup=name,
        showlegend=True,
        fill="tonexty",
        fillcolor=_hex_to_rgba(color, 0.15),
        line=dict(color=color, width=0),
        hovertemplate="%{x}: £%{y:,.0f} (P75)<extra>" + name + "</extra>",
    ))
    # Median line on top
    fig_trend.add_trace(go.Scatter(
        x=years,
        y=[_float(r["median_price"]) for r in stats],
        mode="lines+markers",
        name=name,
        legendgroup=name,
        showlegend=True,
        line=dict(color=color, width=2),
        hovertemplate="%{x}: £%{y:,.0f} (median)<extra>" + name + "</extra>",
    ))

if _nat_trend:
    fig_trend.add_trace(go.Scatter(
        x=[r["year"] for r in _nat_trend],
        y=[_float(r["median_price"]) for r in _nat_trend],
        mode="lines",
        name="National",
        line=dict(color="#888888", width=1, dash="dot"),
        hovertemplate="%{x}: £%{y:,.0f}<extra>National</extra>",
    ))

fig_trend.update_layout(
    yaxis_title=_price_label(_adj_trend),
    xaxis_title="Year",
    legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
    margin=dict(t=20, b=40),
    hovermode="x unified",
)
st.plotly_chart(fig_trend, width="stretch")

# --- Premium / discount to national ---

if national:
    nat_by_yr_price = {r["year"]: _float(r["median_price"]) for r in national}

    st.markdown(
        "The chart below shows the same data normalised to the national median each year — "
        "so the national line is always 100 and each area's value shows its percentage premium "
        "or discount relative to the country as a whole. "
        "A rising line means the area is becoming *more* expensive relative to the rest of England & Wales; "
        "a falling line means it is becoming *cheaper* in relative terms."
    )

    fig_vs_nat = go.Figure()

    for feat in loaded:
        poly_id = feat["properties"].get("id", feat["properties"].get("name"))
        name = feat["properties"].get("name", poly_id)
        color = feat["properties"].get("color", DEFAULT_COLOR)
        stats = _filter(st.session_state.pp_results[poly_id]["stats"])

        years, vals = [], []
        for r in stats:
            nat_val = nat_by_yr_price.get(r["year"])
            poly_val = _float(r["median_price"])
            if nat_val and poly_val:
                years.append(r["year"])
                vals.append(poly_val / nat_val * 100)

        _bar_vs_baseline(fig_vs_nat, years, vals, name, color,
                         baseline=100, hover_suffix="% of national")

    fig_vs_nat.add_hline(y=100, line_dash="dot", line_color="#888888",
                         annotation_text="National", annotation_position="right")
    fig_vs_nat.update_layout(
        yaxis_title="Median price as % of national median",
        xaxis_title="Year",
        barmode="group",
        legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
        margin=dict(t=20, b=40),
        hovermode="x unified",
    )
    st.plotly_chart(fig_vs_nat, width="stretch")

st.divider()


# ---------------------------------------------------------------------------
# Section 3: Relative performance (indexed to first common year)
# ---------------------------------------------------------------------------

st.subheader("Relative price performance")

all_year_sets = [{r["year"] for r in st.session_state.pp_results[
    f["properties"].get("id", f["properties"].get("name"))]["stats"]} for f in loaded]
if national:
    all_year_sets.append({r["year"] for r in national})

common_years = sorted(set.intersection(*all_year_sets)) if all_year_sets else []
base_year = common_years[0] if common_years else None

index_narrative_parts = []
if base_year:
    for feat in loaded:
        poly_id = feat["properties"].get("id", feat["properties"].get("name"))
        name = feat["properties"].get("name", poly_id)
        stats = _filter(st.session_state.pp_results[poly_id]["stats"])
        by_yr = _by_year(stats)
        base_val = _float(by_yr.get(base_year, {}).get("median_price"))
        latest_val = _float(stats[-1]["median_price"]) if stats else None
        if base_val and latest_val:
            growth = (latest_val / base_val - 1) * 100
            nat_base = _float(_nat_by_yr.get(base_year, {}).get("median_price"))
            nat_latest_val = _float(_nat_by_yr.get(stats[-1]["year"], {}).get("median_price"))
            if nat_base and nat_latest_val:
                nat_growth = (nat_latest_val / nat_base - 1) * 100
                diff = growth - nat_growth
                faster_slower = "faster" if diff >= 0 else "slower"
                index_narrative_parts.append(
                    f"**{name}** has grown **{growth:.0f}%** since {base_year}, "
                    f"{abs(diff):.0f} percentage points {faster_slower} than the national average of {nat_growth:.0f}%."
                )

st.markdown(
    f"All series indexed to 100 in {base_year} (the earliest year with data across all selected areas). "
    "Values above 100 mean prices have risen more than the baseline; below 100 means they have risen less "
    "(or fallen). This removes absolute price differences and focuses purely on growth rates. "
    + (" ".join(index_narrative_parts) if index_narrative_parts else "")
)

fig_index = go.Figure()

if base_year:
    for feat in loaded:
        poly_id = feat["properties"].get("id", feat["properties"].get("name"))
        name = feat["properties"].get("name", poly_id)
        color = feat["properties"].get("color", DEFAULT_COLOR)
        stats = _filter(st.session_state.pp_results[poly_id]["stats"])
        by_yr = _by_year(stats)

        base_val = _float(by_yr.get(base_year, {}).get("median_price"))
        if not base_val:
            continue

        years   = sorted(by_yr)
        indexed = [(_float(by_yr[y]["median_price"]) or 0) / base_val * 100 for y in years]

        fig_index.add_trace(go.Scatter(
            x=years, y=indexed,
            mode="lines+markers",
            name=name,
            line=dict(color=color, width=2),
            hovertemplate="%{x}: %{y:.1f}<extra>" + name + "</extra>",
        ))

    if national:
        nat_by_yr = _by_year(national)
        base_n = _float(nat_by_yr.get(base_year, {}).get("median_price"))
        if base_n:
            ny = sorted(nat_by_yr)
            ni = [(_float(nat_by_yr[y]["median_price"]) or 0) / base_n * 100 for y in ny]
            fig_index.add_trace(go.Scatter(
                x=ny, y=ni,
                mode="lines",
                name="National",
                line=dict(color="#888888", width=1, dash="dot"),
                hovertemplate="%{x}: %{y:.1f}<extra>National</extra>",
            ))

    fig_index.add_hline(y=100, line_dash="dash", line_color="#cccccc")
    fig_index.update_layout(
        yaxis_title=f"Index ({base_year} = 100)",
        xaxis_title="Year",
        legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
        margin=dict(t=20, b=40),
        hovermode="x unified",
    )
    st.plotly_chart(fig_index, width="stretch")

    # --- Growth relative to national (national clamped to 100) ---

    if national:
        nat_by_yr = _by_year(national)
        base_n = _float(nat_by_yr.get(base_year, {}).get("median_price"))

        if base_n:
            nat_indexed_by_yr = {
                y: (_float(nat_by_yr[y]["median_price"]) or 0) / base_n * 100
                for y in nat_by_yr
            }

            st.markdown(
                f"The same indexed data with the national growth line clamped to 100 each year. "
                f"A value above 100 means prices in that area have grown *faster* than the national "
                f"average since {base_year}; below 100 means they have grown slower. "
                f"Unlike the chart above, this removes the national trend entirely so you can focus "
                f"purely on whether each area is outpacing or lagging the country."
            )

            fig_rel_growth = go.Figure()

            for feat in loaded:
                poly_id = feat["properties"].get("id", feat["properties"].get("name"))
                name = feat["properties"].get("name", poly_id)
                color = feat["properties"].get("color", DEFAULT_COLOR)
                stats = _filter(st.session_state.pp_results[poly_id]["stats"])
                by_yr = _by_year(stats)

                base_val = _float(by_yr.get(base_year, {}).get("median_price"))
                if not base_val:
                    continue

                years, vals = [], []
                for y in sorted(by_yr):
                    nat_idx = nat_indexed_by_yr.get(y)
                    poly_price = _float(by_yr[y]["median_price"])
                    if nat_idx and poly_price:
                        poly_idx = poly_price / base_val * 100
                        years.append(y)
                        vals.append(poly_idx / nat_idx * 100)

                _bar_vs_baseline(fig_rel_growth, years, vals, name, color, baseline=100)

            fig_rel_growth.add_hline(y=100, line_dash="dot", line_color="#888888",
                                     annotation_text="National", annotation_position="right")
            fig_rel_growth.update_layout(
                yaxis_title=f"Growth relative to national ({base_year} = 100)",
                xaxis_title="Year",
                barmode="group",
                legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
                margin=dict(t=20, b=40),
                hovermode="x unified",
            )
            st.plotly_chart(fig_rel_growth, width="stretch")

else:
    st.caption("Not enough overlapping data to build an index chart.")

st.divider()


# ---------------------------------------------------------------------------
# Section 4: Property mix
# ---------------------------------------------------------------------------

PROPERTY_TYPE_LABELS = {"D": "Detached", "S": "Semi-detached", "T": "Terraced", "F": "Flat", "O": "Other"}
DURATION_LABELS      = {"F": "Freehold", "L": "Leasehold", "U": "Unknown"}
OLD_NEW_LABELS       = {"Y": "New build", "N": "Established"}

st.subheader("Property mix")
_mix_from, _mix_to = _year_range_selector("mix")
st.markdown(
    "Breakdown of sales by property type, tenure, and new/established build — "
    "shown as a percentage of all sales in each year. "
    "Shifts over time reflect new development, estate regeneration, or changing demand."
)

for feat in loaded:
    poly_id = feat["properties"].get("id", feat["properties"].get("name"))
    name    = feat["properties"].get("name", poly_id)
    mix     = st.session_state.pp_results[poly_id].get("mix", [])

    if not mix:
        st.caption(f"No mix data for {name} — re-fetch to load.")
        continue

    mix = _filter(mix, _mix_from, _mix_to)
    st.markdown(f"**{name}**")

    # Build {year: {category: count}} for each dimension
    def _mix_chart(mix, key, labels, title):
        years_set = sorted({r["year"] for r in mix})
        totals = {}
        by_cat = {}
        for r in mix:
            y, cat, cnt = r["year"], r.get(key, "?"), r["count"]
            totals[y] = totals.get(y, 0) + cnt
            by_cat.setdefault(cat, {})[y] = by_cat.get(cat, {}).get(y, 0) + cnt

        fig = go.Figure()
        for code, label in labels.items():
            pcts = [
                by_cat.get(code, {}).get(y, 0) / totals[y] * 100
                if totals.get(y) else 0
                for y in years_set
            ]
            fig.add_trace(go.Bar(
                x=years_set, y=pcts, name=label,
                hovertemplate="%{x}: %{y:.1f}%<extra>" + label + "</extra>",
            ))
        fig.update_layout(
            barmode="stack",
            title=title,
            yaxis=dict(ticksuffix="%", range=[0, 100]),
            xaxis_title="Year",
            legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
            margin=dict(t=40, b=40),
            hovermode="x unified",
            height=300,
        )
        return fig

    col1, col2, col3 = st.columns(3)
    col1.plotly_chart(_mix_chart(mix, "property_type", PROPERTY_TYPE_LABELS, "Property type"), width="stretch")
    col2.plotly_chart(_mix_chart(mix, "duration",      DURATION_LABELS,      "Tenure"),        width="stretch")
    col3.plotly_chart(_mix_chart(mix, "old_new",       OLD_NEW_LABELS,       "New / established"), width="stretch")

st.divider()


# ---------------------------------------------------------------------------
# Section 5: Turnover
# ---------------------------------------------------------------------------

st.subheader("Annual turnover")

# England & Wales dwelling stock (ONS estimate) used to convert national sale
# counts to a comparable turnover % rate.
EW_DWELLING_STOCK = 25_000_000

turnover_parts = []
for feat in loaded:
    poly_id = feat["properties"].get("id", feat["properties"].get("name"))
    name = feat["properties"].get("name", poly_id)
    uprn_count = feat["properties"].get("uprn_count")
    stats = _filter(st.session_state.pp_results[poly_id]["stats"])
    if not stats or not uprn_count:
        continue
    recent = [r for r in stats if int(r["year"]) >= 2015]
    if recent:
        avg_pct = statistics.mean(int(r["count"]) / uprn_count * 100 for r in recent)
        turnover_parts.append(
            f"**{name}** averaged **{avg_pct:.1f}% of addresses** selling per year since 2015."
        )

if national:
    nat_recent = [r for r in national if int(r["year"]) >= 2015]
    if nat_recent:
        avg_nat_pct = statistics.mean(int(r["count"]) / EW_DWELLING_STOCK * 100 for r in nat_recent)
        turnover_parts.append(
            f"The national average was **{avg_nat_pct:.1f}%** over the same period."
        )

st.markdown(
    "Annual sales as a percentage of total address stock, compared to the national turnover rate. "
    "Low turnover may indicate high owner-occupancy or low mobility; spikes often reflect "
    "new-build completions or estate regeneration. "
    "The national rate is estimated using ONS dwelling stock figures. "
    + " ".join(turnover_parts)
)

fig_turnover = go.Figure()

for feat in loaded:
    poly_id = feat["properties"].get("id", feat["properties"].get("name"))
    name = feat["properties"].get("name", poly_id)
    color = feat["properties"].get("color", DEFAULT_COLOR)
    uprn_count = feat["properties"].get("uprn_count")
    stats = _filter(st.session_state.pp_results[poly_id]["stats"])

    if not uprn_count:
        continue

    years = [r["year"] for r in stats]
    pct   = [int(r["count"]) / uprn_count * 100 for r in stats]
    fig_turnover.add_trace(go.Scatter(
        x=years, y=pct,
        mode="lines+markers",
        name=name,
        line=dict(color=color, width=2),
        hovertemplate="%{x}: %{y:.2f}%<extra>" + name + "</extra>",
    ))

if national:
    ny   = [r["year"] for r in national]
    npct = [int(r["count"]) / EW_DWELLING_STOCK * 100 for r in national]
    fig_turnover.add_trace(go.Scatter(
        x=ny, y=npct,
        mode="lines",
        name="National",
        line=dict(color="#888888", width=1, dash="dot"),
        hovertemplate="%{x}: %{y:.2f}%<extra>National</extra>",
    ))

fig_turnover.update_layout(
    xaxis_title="Year",
    yaxis_title="% of address stock sold",
    legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
    margin=dict(t=20, b=40),
    hovermode="x unified",
)
fig_turnover.update_yaxes(tickformat=".1f", ticksuffix="%")
st.plotly_chart(fig_turnover, width="stretch")

nav.render_attributions()
