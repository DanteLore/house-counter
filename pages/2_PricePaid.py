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
# Load polygons and select which to analyse
# ---------------------------------------------------------------------------

polygons = load_polygons()

if not polygons:
    st.info("No polygons saved yet. Draw some on the House Counter page first.")
    st.stop()

poly_names = [f["properties"].get("name", f"Polygon {i+1}") for i, f in enumerate(polygons)]

if "pp_selected_names" not in st.session_state:
    preferred = [n for n in poly_names if n in ("Newbury", "Thatcham")]
    st.session_state.pp_selected_names = preferred if preferred else poly_names[:1]
else:
    # Drop any names that no longer exist (polygon may have been deleted)
    st.session_state.pp_selected_names = [n for n in st.session_state.pp_selected_names if n in poly_names]

selected_names = st.multiselect(
    "Select polygons to analyse",
    poly_names,
    key="pp_selected_names",
)

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

all_lons = [lon for feat in selected for lon, lat in feat["geometry"]["coordinates"][0]]
all_lats = [lat for feat in selected for lon, lat in feat["geometry"]["coordinates"][0]]
map_centre = ((min(all_lats) + max(all_lats)) / 2, (min(all_lons) + max(all_lons)) / 2)

m = folium.Map(location=map_centre, zoom_start=13, tiles="OpenStreetMap")

for feat in selected:
    color = feat["properties"].get("color", DEFAULT_COLOR)
    name  = feat["properties"].get("name", "")
    folium.GeoJson(feat,
        style_function=lambda _, c=color: {"color": c, "fillColor": c, "fillOpacity": 0.25, "weight": 2},
        tooltip=folium.Tooltip(name),
    ).add_to(m)

for feat in polygons:
    if feat["properties"].get("name") not in selected_names:
        folium.GeoJson(feat,
            style_function=lambda _: {"color": "#aaaaaa", "fillColor": "#aaaaaa",
                                      "fillOpacity": 0.08, "weight": 1, "dashArray": "4 4"},
        ).add_to(m)

st_folium(m, width="stretch", height=400, returned_objects=[])
st.divider()


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

NATIONAL_CACHE_FILE = "national_price_stats.json"


def load_national_cache():
    if os.path.exists(NATIONAL_CACHE_FILE):
        with open(NATIONAL_CACHE_FILE) as f:
            data = json.load(f)
        if isinstance(data, list):
            return {"stats": data, "cpi": None}
        return data
    return None


def save_national_cache(stats, cpi):
    with open(NATIONAL_CACHE_FILE, "w") as f:
        json.dump({"stats": stats, "cpi": cpi}, f)


# ---------------------------------------------------------------------------
# Session state — seed from disk on first load
# ---------------------------------------------------------------------------

if "pp_results" not in st.session_state:
    st.session_state.pp_results = {}
if "pp_national" not in st.session_state or "pp_cpi" not in st.session_state:
    cached = load_national_cache() or {}
    st.session_state.pp_national = cached.get("stats")
    st.session_state.pp_cpi      = cached.get("cpi")

for feat in polygons:
    poly_id = feat["properties"].get("id", feat["properties"].get("name"))
    if poly_id not in st.session_state.pp_results:
        stored_stats  = feat["properties"].get("pp_stats")
        stored_prices = feat["properties"].get("pp_prices")
        if stored_stats is not None:
            st.session_state.pp_results[poly_id] = {
                "stats":  stored_stats,
                "prices": [tuple(p) for p in (stored_prices or [])],
                "mix":    feat["properties"].get("pp_mix", []),
            }


# ---------------------------------------------------------------------------
# Fetch controls
# ---------------------------------------------------------------------------

def fetch_polygon_data(feat):
    poly_id = feat["properties"].get("id", feat["properties"].get("name"))
    name    = feat["properties"].get("name", poly_id)
    coords  = feat["geometry"]["coordinates"]
    with st.spinner(f"Fetching prices for {name}…"):
        poly_stats, all_prices = fetch_price_stats_for_polygon(coords)
    with st.spinner(f"Fetching property mix for {name}…"):
        mix = fetch_mix_for_polygon(coords)
    st.session_state.pp_results[poly_id] = {"stats": poly_stats, "prices": all_prices, "mix": mix}
    for i, f in enumerate(polygons):
        if f["properties"].get("id", f["properties"].get("name")) == poly_id:
            polygons[i]["properties"]["pp_stats"]  = poly_stats
            polygons[i]["properties"]["pp_prices"] = [list(p) for p in all_prices]
            polygons[i]["properties"]["pp_mix"]    = mix
            break
    save_polygons(polygons)


def ensure_national_data():
    if st.session_state.pp_national is None:
        with st.spinner("Fetching national price data…"):
            st.session_state.pp_national = fetch_price_stats_national()
        with st.spinner("Fetching CPI inflation data…"):
            st.session_state.pp_cpi = fetch_cpi_by_year()
        save_national_cache(st.session_state.pp_national, st.session_state.pp_cpi)


with st.container():
    btn_cols = st.columns(2 + len(selected))
    if btn_cols[0].button("Fetch all", type="primary", use_container_width=True):
        ensure_national_data()
        for feat in selected:
            fetch_polygon_data(feat)
        st.rerun()

    if btn_cols[1].button("Fetch missing", use_container_width=True):
        ensure_national_data()
        for feat in selected:
            poly_id = feat["properties"].get("id", feat["properties"].get("name"))
            if poly_id not in st.session_state.pp_results:
                fetch_polygon_data(feat)
        st.rerun()

    for idx, feat in enumerate(selected):
        poly_id = feat["properties"].get("id", feat["properties"].get("name"))
        name    = feat["properties"].get("name", poly_id)
        if btn_cols[2 + idx].button(f"↺ {name}", key=f"refresh_{poly_id}", use_container_width=True):
            ensure_national_data()
            fetch_polygon_data(feat)
            st.rerun()


# ---------------------------------------------------------------------------
# Guard — stop if no polygon data loaded yet
# ---------------------------------------------------------------------------

loaded = [f for f in selected
          if f["properties"].get("id", f["properties"].get("name")) in st.session_state.pp_results]

if not loaded:
    st.caption("Click 'Fetch missing' to load results.")
    st.stop()


# ---------------------------------------------------------------------------
# Polygon property accessors  (avoid repeating .get() chains everywhere)
# ---------------------------------------------------------------------------

def poly_id(feat):
    return feat["properties"].get("id", feat["properties"].get("name"))

def poly_name(feat):
    return feat["properties"].get("name", poly_id(feat))

def poly_color(feat):
    return feat["properties"].get("color", DEFAULT_COLOR)

def poly_uprn_count(feat):
    return feat["properties"].get("uprn_count")

def poly_prices(feat):
    return st.session_state.pp_results[poly_id(feat)].get("prices", [])

def poly_stats(feat):
    return st.session_state.pp_results[poly_id(feat)]["stats"]

def poly_mix(feat):
    return st.session_state.pp_results[poly_id(feat)].get("mix", [])


# ---------------------------------------------------------------------------
# National data and year filtering
# ---------------------------------------------------------------------------

national    = st.session_state.pp_national or []
latest_year = max((r["year"] for r in national), default=None)

def exclude_incomplete_year(rows):
    """Drop the latest year — it almost always has incomplete data."""
    return [r for r in rows if r["year"] != latest_year]

national    = exclude_incomplete_year(national)
national_by_year = {r["year"]: r for r in national}


def filter_to_year_range(rows, from_year=None, to_year=None):
    """Filter year-keyed dicts to a range, always excluding the latest incomplete year."""
    return [r for r in rows
            if r["year"] != latest_year
            and (from_year is None or r["year"] >= from_year)
            and (to_year   is None or r["year"] <= to_year)]


# ---------------------------------------------------------------------------
# CPI / inflation helpers
# ---------------------------------------------------------------------------

cpi           = st.session_state.pp_cpi or {}
cpi_base_year = max(cpi.keys()) if cpi else None


def warn_if_cpi_missing():
    if not cpi:
        st.warning("CPI data not loaded — click **Fetch all** or **Fetch missing** to enable inflation adjustment.")


def prices_in_real_terms(year_prices, adjust):
    return deflate_prices(year_prices, cpi, cpi_base_year) if adjust else year_prices


def stats_in_real_terms(feat, adjust):
    """Yearly stats for a polygon, derived from real prices when adjust=True."""
    year_prices = poly_prices(feat)
    if adjust:
        return real_stats_from_prices(year_prices, cpi, cpi_base_year)
    return poly_stats(feat)


def national_stats_in_real_terms(adjust):
    """National stats deflated to current £.

    National data has no raw prices (it comes from Athena aggregates), so we
    deflate the pre-computed stats directly. This is valid because CPI deflation
    is a linear per-year transform: deflate(median) == median(deflate(prices)).
    """
    rows = st.session_state.pp_national or []
    if not adjust:
        return rows

    def deflate_field(row, field):
        return deflate_prices([(row["year"], row[field])], cpi, cpi_base_year)[0][1]

    return [{**r,
             "min_price":    deflate_field(r, "min_price"),
             "max_price":    deflate_field(r, "max_price"),
             "mean_price":   deflate_field(r, "mean_price"),
             "median_price": deflate_field(r, "median_price"),
             "p25_price":    deflate_field(r, "p25_price"),
             "p75_price":    deflate_field(r, "p75_price"),
             } for r in rows]


def price_axis_label(adjust):
    return f"Sale price ({cpi_base_year} £)" if adjust else "Sale price (£)"


# ---------------------------------------------------------------------------
# Shared year-range selector widget
# ---------------------------------------------------------------------------

all_years = sorted({
    year
    for feat in loaded
    for year, _ in poly_prices(feat)
    if year != latest_year
})


_DEFAULT_FROM_YEAR = "2001"


def _default_from_index():
    """Index of the first year >= 2001, or 0 if all years are before 2001."""
    for i, y in enumerate(all_years):
        if y >= _DEFAULT_FROM_YEAR:
            return i
    return 0


def year_range_selector(key_prefix):
    """Render From/To year dropdowns and return (from_year, to_year)."""
    if not all_years:
        return None, None
    c1, c2, c3 = st.columns([2, 1, 1])
    with c2:
        from_yr = st.selectbox("From year", all_years, index=_default_from_index(), key=f"{key_prefix}_from")
    with c3:
        to_yr = st.selectbox("To year", all_years, index=len(all_years) - 1, key=f"{key_prefix}_to")
    return from_yr, to_yr


# ---------------------------------------------------------------------------
# Chart colour helpers
# ---------------------------------------------------------------------------

def hex_to_rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def chart_layout(**kwargs):
    return dict(
        legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
        margin=dict(t=20, b=40),
        hovermode="x unified",
        **kwargs,
    )


def add_baseline_bars(fig, years, vals, name, color, baseline=100, hover_suffix="", show_legend=True):
    """Add grouped bars coloured by whether they are above or below a baseline."""
    above = [v - baseline if v >= baseline else 0 for v in vals]
    below = [v - baseline if v <  baseline else 0 for v in vals]
    hover = f"%{{x}}: %{{base:.1f}}{hover_suffix}<extra>{name}</extra>"
    fig.add_trace(go.Bar(x=years, y=above, name=name, marker_color=color, opacity=0.8,
                         legendgroup=name, showlegend=show_legend, base=baseline, hovertemplate=hover))
    fig.add_trace(go.Bar(x=years, y=below, name=name, marker_color=color, opacity=0.4,
                         legendgroup=name, showlegend=False,     base=baseline, hovertemplate=hover))


# ---------------------------------------------------------------------------
# Market summary calculations
# ---------------------------------------------------------------------------
# All functions accept from_year/to_year (year strings or None) and adjust (bool).
# When adjust=True, CAGR and volatility use CPI-deflated prices; premium vs national
# uses nominal prices on both sides (CPI cancels within a year).

def _filtered_real_stats(feat, from_year, to_year):
    """CPI-deflated yearly stats for a polygon, filtered to the year range."""
    return filter_to_year_range(
        real_stats_from_prices(poly_prices(feat), cpi, cpi_base_year),
        from_year, to_year,
    )


def _filtered_nominal_stats(feat, from_year, to_year):
    """Nominal yearly stats for a polygon, filtered to the year range."""
    return filter_to_year_range(poly_stats(feat), from_year, to_year)


def _filtered_stats(feat, from_year, to_year, adjust):
    """Yearly stats filtered to range, real or nominal depending on adjust."""
    return _filtered_real_stats(feat, from_year, to_year) if adjust else _filtered_nominal_stats(feat, from_year, to_year)


def price_growth_cagr(feat, from_year=None, to_year=None, adjust=True):
    """Compound annual growth rate of median price, first to last year.

    Returns (cagr_pct, from_year, to_year) or None if insufficient data.
    """
    stats = _filtered_stats(feat, from_year, to_year, adjust)
    years = sorted(r["year"] for r in stats)
    if len(years) < 2:
        return None
    by_yr  = {r["year"]: r for r in stats}
    y0, yn = years[0], years[-1]
    v0 = _safe_float(by_yr[y0]["median_price"])
    vn = _safe_float(by_yr[yn]["median_price"])
    n_years = int(yn) - int(y0)
    if not (v0 and vn and n_years > 0):
        return None
    return ((vn / v0) ** (1 / n_years) - 1) * 100, y0, yn


def price_volatility(feat, from_year=None, to_year=None, adjust=True):
    """Coefficient of variation of annual median prices (%).

    Higher = less predictable year-to-year. Returns None if fewer than 3 years.
    """
    stats   = _filtered_stats(feat, from_year, to_year, adjust)
    medians = [_safe_float(r["median_price"]) for r in stats if _safe_float(r["median_price"])]
    if len(medians) < 3:
        return None
    return (statistics.stdev(medians) / statistics.mean(medians)) * 100


def annual_turnover_rate(feat, from_year=None, to_year=None):
    """Mean annual sales as % of residential address stock.

    Proxy for market liquidity / demand. Returns (rate_pct, uprn_count) or None.
    """
    uprn_count = poly_uprn_count(feat)
    if not uprn_count:
        return None
    stats  = _filtered_nominal_stats(feat, from_year, to_year)
    counts = [int(r["count"]) for r in stats if r.get("count")]
    if not counts:
        return None
    return statistics.mean(counts) / uprn_count * 100, uprn_count


def average_new_build_share(feat, from_year=None, to_year=None):
    """Mean annual % of sales that are new builds.

    High values can inflate turnover and skew prices upward.
    """
    mix = filter_to_year_range(poly_mix(feat), from_year, to_year)
    if not mix:
        return None
    totals_by_year = {}
    new_by_year    = {}
    for r in mix:
        y = r["year"]
        totals_by_year[y] = totals_by_year.get(y, 0) + r["count"]
        if r.get("old_new") == "Y":
            new_by_year[y] = new_by_year.get(y, 0) + r["count"]
    annual_pcts = [
        new_by_year.get(y, 0) / total * 100
        for y, total in totals_by_year.items() if total > 0
    ]
    return statistics.mean(annual_pcts) if annual_pcts else None


def average_premium_vs_national(feat, from_year=None, to_year=None):
    """Mean ratio of polygon median price to national median, across all years (%).

    100 = at national median; 120 = 20% premium; 80 = 20% discount.
    Uses nominal prices for both sides so the ratio is consistent (CPI cancels within a year).
    """
    stats = _filtered_nominal_stats(feat, from_year, to_year)
    ratios = []
    for r in stats:
        nat      = national_by_year.get(r["year"])
        poly_med = _safe_float(r["median_price"])
        nat_med  = _safe_float(nat["median_price"]) if nat else None
        if poly_med and nat_med:
            ratios.append(poly_med / nat_med * 100)
    return statistics.mean(ratios) if ratios else None


def _safe_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def rank_polygons(summaries, key, higher_is_better=True):
    """Return {name: rank} dict, 1 = best. Polygons missing the key are omitted."""
    eligible = sorted(
        [(s[key], s["name"]) for s in summaries if key in s],
        reverse=higher_is_better,
    )
    return {name: i + 1 for i, (_, name) in enumerate(eligible)}


def build_cross_polygon_narrative(summaries):
    """Generate comparative sentences across polygons for metrics where comparison adds insight.

    Returns a list of markdown strings, one sentence per observation.
    Only emits a sentence when there are at least 2 polygons with data for that metric.
    """
    sentences = []
    n = len(summaries)
    if n < 2:
        return sentences

    def best(key, higher_is_better=True):
        eligible = [s for s in summaries if key in s]
        if len(eligible) < 2:
            return None, None, None
        ranked = sorted(eligible, key=lambda s: s[key], reverse=higher_is_better)
        return ranked[0]["name"], ranked[0][key], ranked[-1]["name"], ranked[-1][key]

    # Price growth spread — only report if polygons differ by at least 0.5pp/yr
    r = best("cagr")
    if r[0]:
        top_name, top_val, bot_name, bot_val = r
        gap = top_val - bot_val
        if gap >= 0.5:
            sentences.append(
                f"**Price growth**: {top_name} had the highest growth at **{top_val:+.1f}%/yr**, "
                f"{bot_name} the lowest at **{bot_val:+.1f}%/yr** — a spread of {gap:.1f} percentage points."
            )
        else:
            sentences.append(
                f"**Price growth**: all areas grew at a similar rate (~{top_val:+.1f}%/yr), "
                f"suggesting the markets move in lockstep."
            )

    # Volatility comparison — only flag if spread exceeds 2pp CV
    r = best("volatility", higher_is_better=False)
    if r[0]:
        stable_name, stable_val, unstable_name, unstable_val = r
        spread = unstable_val - stable_val
        if spread >= 2:
            sentences.append(
                f"**Price stability**: {stable_name} was the most stable market (CV {stable_val:.1f}%), "
                f"{unstable_name} the most volatile (CV {unstable_val:.1f}%) — "
                f"{'a modest' if spread < 5 else 'a notable'} difference."
            )
        else:
            sentences.append(
                f"**Price stability**: similar volatility across all areas (CV {stable_val:.1f}%–{unstable_val:.1f}%)."
            )

    # Liquidity spread — only highlight if one area has meaningfully higher turnover (>0.3pp)
    r = best("turnover")
    if r[0]:
        high_name, high_val, low_name, low_val = r
        spread = high_val - low_val
        if spread >= 0.3:
            ratio = high_val / low_val if low_val else None
            ratio_note = f" ({ratio:.1f}× higher)" if ratio else ""
            sentences.append(
                f"**Liquidity**: {high_name} had higher annual turnover (**{high_val:.1f}%**{ratio_note}) "
                f"than {low_name} ({low_val:.1f}%). "
                f"Higher turnover indicates a more liquid, demand-driven market."
            )
        else:
            sentences.append(
                f"**Liquidity**: similar turnover across all areas (~{high_val:.1f}%/yr)."
            )

    # Premium vs national — only contrast if spread between polygons exceeds 5pp
    r = best("vs_national")
    if r[0]:
        top_name, top_val, bot_name, bot_val = r
        spread   = top_val - bot_val
        top_diff = top_val - 100
        bot_diff = bot_val - 100
        top_dir  = "above" if top_diff >= 0 else "below"
        bot_dir  = "above" if bot_diff >= 0 else "below"
        if spread >= 5:
            sentences.append(
                f"**National premium**: {top_name} commands a larger premium "
                f"(**{abs(top_diff):.0f}% {top_dir}** national median) "
                f"than {bot_name} ({abs(bot_diff):.0f}% {bot_dir})."
            )
        else:
            sentences.append(
                f"**National premium**: both areas sit at a similar premium "
                f"(~{abs(top_diff):.0f}% {top_dir} national median)."
            )

    # New-build share — only flag if spread is meaningful (>5pp)
    nb_eligible = [s for s in summaries if "new_build_pct" in s]
    if len(nb_eligible) >= 2:
        nb_sorted = sorted(nb_eligible, key=lambda s: s["new_build_pct"], reverse=True)
        hi, lo    = nb_sorted[0], nb_sorted[-1]
        spread    = hi["new_build_pct"] - lo["new_build_pct"]
        if spread > 5:
            sentences.append(
                f"**New-build mix**: {hi['name']} had the highest new-build share "
                f"(**{hi['new_build_pct']:.1f}%** of sales) vs {lo['name']} "
                f"({lo['new_build_pct']:.1f}%). A high new-build share can inflate "
                f"turnover figures and push median prices upward."
            )

    return sentences


def build_market_summaries(feats, from_year=None, to_year=None, adjust=True):
    rows = []
    for feat in feats:
        name = poly_name(feat)
        row  = {"name": name}

        cagr_result = price_growth_cagr(feat, from_year, to_year, adjust)
        if cagr_result:
            row["cagr"], row["cagr_from"], row["cagr_to"] = cagr_result

        vol = price_volatility(feat, from_year, to_year, adjust)
        if vol is not None:
            row["volatility"] = vol

        turnover_result = annual_turnover_rate(feat, from_year, to_year)
        if turnover_result:
            row["turnover"], row["uprn_count"] = turnover_result

        new_build = average_new_build_share(feat, from_year, to_year)
        if new_build is not None:
            row["new_build_pct"] = new_build

        vs_nat = average_premium_vs_national(feat, from_year, to_year)
        if vs_nat is not None:
            row["vs_national"] = vs_nat

        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------

def price_histogram_chart(from_year, to_year, adjust, price_min, price_max):
    fig = go.Figure()
    for feat in loaded:
        name  = poly_name(feat)
        color = poly_color(feat)
        year_prices = [(y, p) for y, p in poly_prices(feat)
                       if y != latest_year
                       and (from_year is None or y >= from_year)
                       and (to_year   is None or y <= to_year)]
        if not year_prices:
            continue
        prices = [p for _, p in prices_in_real_terms(year_prices, adjust)]
        prices = [p for p in prices if price_min <= p <= price_max]
        if len(prices) < 2:
            continue
        kde     = gaussian_kde(prices)
        x_range = np.linspace(min(prices), max(prices), 500)
        fig.add_trace(go.Scatter(
            x=x_range, y=kde(x_range),
            mode="lines", name=name,
            fill="tozeroy",
            fillcolor=hex_to_rgba(color, 0.2),
            line=dict(color=color, width=2),
            hovertemplate="£%{x:,.0f}: %{y:.6f}<extra>" + name + "</extra>",
        ))
    fig.update_layout(**chart_layout(
        xaxis_title=price_axis_label(adjust),
        yaxis_title="Probability density",
        xaxis=dict(tickprefix="£", tickformat=","),
    ))
    return fig


def median_trend_chart(from_year, to_year, adjust, nat_trend):
    fig = go.Figure()
    for feat in loaded:
        name  = poly_name(feat)
        color = poly_color(feat)
        stats = filter_to_year_range(stats_in_real_terms(feat, adjust), from_year, to_year)
        years = [r["year"] for r in stats]
        fig.add_trace(go.Scatter(
            x=years, y=[_safe_float(r["p25_price"]) for r in stats],
            mode="lines", name=name, legendgroup=name, showlegend=False,
            line=dict(color=color, width=0),
            hovertemplate="%{x}: £%{y:,.0f} (P25)<extra>" + name + "</extra>",
        ))
        fig.add_trace(go.Scatter(
            x=years, y=[_safe_float(r["p75_price"]) for r in stats],
            mode="lines", name=f"{name} (P25–P75)", legendgroup=name, showlegend=True,
            fill="tonexty", fillcolor=hex_to_rgba(color, 0.15), line=dict(color=color, width=0),
            hovertemplate="%{x}: £%{y:,.0f} (P75)<extra>" + name + "</extra>",
        ))
        fig.add_trace(go.Scatter(
            x=years, y=[_safe_float(r["median_price"]) for r in stats],
            mode="lines+markers", name=name, legendgroup=name, showlegend=True,
            line=dict(color=color, width=2),
            hovertemplate="%{x}: £%{y:,.0f} (median)<extra>" + name + "</extra>",
        ))
    if nat_trend:
        fig.add_trace(go.Scatter(
            x=[r["year"] for r in nat_trend],
            y=[_safe_float(r["median_price"]) for r in nat_trend],
            mode="lines", name="National",
            line=dict(color="#888888", width=1, dash="dot"),
            hovertemplate="%{x}: £%{y:,.0f}<extra>National</extra>",
        ))
    fig.update_layout(**chart_layout(yaxis_title=price_axis_label(adjust), xaxis_title="Year"))
    return fig


def premium_vs_national_chart():
    nat_median_by_year = {r["year"]: _safe_float(r["median_price"]) for r in national}
    fig = go.Figure()
    for feat in loaded:
        name  = poly_name(feat)
        color = poly_color(feat)
        stats = filter_to_year_range(poly_stats(feat))
        years, vals = [], []
        for r in stats:
            nat_val  = nat_median_by_year.get(r["year"])
            poly_val = _safe_float(r["median_price"])
            if nat_val and poly_val:
                years.append(r["year"])
                vals.append(poly_val / nat_val * 100)
        add_baseline_bars(fig, years, vals, name, color, baseline=100, hover_suffix="% of national")
    fig.add_hline(y=100, line_dash="dot", line_color="#888888",
                  annotation_text="National", annotation_position="right")
    fig.update_layout(**chart_layout(
        yaxis_title="Median price as % of national median",
        xaxis_title="Year", barmode="group",
    ))
    return fig


def indexed_performance_chart(base_year):
    fig = go.Figure()
    for feat in loaded:
        name  = poly_name(feat)
        color = poly_color(feat)
        stats = filter_to_year_range(poly_stats(feat))
        by_yr = {r["year"]: r for r in stats}
        base_val = _safe_float(by_yr.get(base_year, {}).get("median_price"))
        if not base_val:
            continue
        years   = sorted(by_yr)
        indexed = [(_safe_float(by_yr[y]["median_price"]) or 0) / base_val * 100 for y in years]
        fig.add_trace(go.Scatter(
            x=years, y=indexed, mode="lines+markers", name=name,
            line=dict(color=color, width=2),
            hovertemplate="%{x}: %{y:.1f}<extra>" + name + "</extra>",
        ))
    if national:
        nat_by_yr = {r["year"]: r for r in national}
        base_n    = _safe_float(nat_by_yr.get(base_year, {}).get("median_price"))
        if base_n:
            ny = sorted(nat_by_yr)
            ni = [(_safe_float(nat_by_yr[y]["median_price"]) or 0) / base_n * 100 for y in ny]
            fig.add_trace(go.Scatter(
                x=ny, y=ni, mode="lines", name="National",
                line=dict(color="#888888", width=1, dash="dot"),
                hovertemplate="%{x}: %{y:.1f}<extra>National</extra>",
            ))
    fig.add_hline(y=100, line_dash="dash", line_color="#cccccc")
    fig.update_layout(**chart_layout(yaxis_title=f"Index ({base_year} = 100)", xaxis_title="Year"))
    return fig


def relative_growth_chart(base_year, nat_indexed_by_year):
    fig = go.Figure()
    for feat in loaded:
        name  = poly_name(feat)
        color = poly_color(feat)
        stats = filter_to_year_range(poly_stats(feat))
        by_yr = {r["year"]: r for r in stats}
        base_val = _safe_float(by_yr.get(base_year, {}).get("median_price"))
        if not base_val:
            continue
        years, vals = [], []
        for y in sorted(by_yr):
            nat_idx  = nat_indexed_by_year.get(y)
            poly_val = _safe_float(by_yr[y]["median_price"])
            if nat_idx and poly_val:
                years.append(y)
                vals.append((poly_val / base_val * 100) / nat_idx * 100)
        add_baseline_bars(fig, years, vals, name, color, baseline=100)
    fig.add_hline(y=100, line_dash="dot", line_color="#888888",
                  annotation_text="National", annotation_position="right")
    fig.update_layout(**chart_layout(
        yaxis_title=f"Growth relative to national ({base_year} = 100)",
        xaxis_title="Year", barmode="group",
    ))
    return fig


def mix_stacked_bar_chart(mix, dimension_key, labels, title):
    years_set  = sorted({r["year"] for r in mix})
    totals     = {}
    by_category = {}
    for r in mix:
        y, cat, cnt = r["year"], r.get(dimension_key, "?"), r["count"]
        totals[y] = totals.get(y, 0) + cnt
        by_category.setdefault(cat, {})[y] = by_category.get(cat, {}).get(y, 0) + cnt
    fig = go.Figure()
    for code, label in labels.items():
        pcts = [
            by_category.get(code, {}).get(y, 0) / totals[y] * 100 if totals.get(y) else 0
            for y in years_set
        ]
        fig.add_trace(go.Bar(x=years_set, y=pcts, name=label,
                             hovertemplate="%{x}: %{y:.1f}%<extra>" + label + "</extra>"))
    fig.update_layout(
        barmode="stack", title=title,
        yaxis=dict(ticksuffix="%", range=[0, 100]),
        xaxis_title="Year",
        legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
        margin=dict(t=40, b=40), hovermode="x unified", height=300,
    )
    return fig


def turnover_chart():
    EW_DWELLING_STOCK = 25_000_000
    fig = go.Figure()
    for feat in loaded:
        uprn_count = poly_uprn_count(feat)
        if not uprn_count:
            continue
        name  = poly_name(feat)
        color = poly_color(feat)
        stats = filter_to_year_range(poly_stats(feat))
        years = [r["year"] for r in stats]
        pcts  = [int(r["count"]) / uprn_count * 100 for r in stats]
        fig.add_trace(go.Scatter(
            x=years, y=pcts, mode="lines+markers", name=name,
            line=dict(color=color, width=2),
            hovertemplate="%{x}: %{y:.2f}%<extra>" + name + "</extra>",
        ))
    if national:
        ny   = [r["year"] for r in national]
        npct = [int(r["count"]) / EW_DWELLING_STOCK * 100 for r in national]
        fig.add_trace(go.Scatter(
            x=ny, y=npct, mode="lines", name="National",
            line=dict(color="#888888", width=1, dash="dot"),
            hovertemplate="%{x}: %{y:.2f}%<extra>National</extra>",
        ))
    fig.update_layout(**chart_layout(xaxis_title="Year", yaxis_title="% of address stock sold"))
    fig.update_yaxes(tickformat=".1f", ticksuffix="%")
    return fig


# ===========================================================================
# PAGE RENDERING
# ===========================================================================

# ---------------------------------------------------------------------------
# Market summary
# ---------------------------------------------------------------------------
# Metrics defined in the calculation functions above. Rankings are relative to
# the other selected polygons so the comparison is always meaningful.

st.subheader("Market summary")
adj_summary = st.toggle(
    f"Adjust prices for inflation ({cpi_base_year} £)" if cpi_base_year else "Adjust prices for inflation",
    key="adj_summary", value=bool(cpi),
)
if adj_summary:
    warn_if_cpi_missing()
summary_from, summary_to = year_range_selector("summary")
market_summaries = build_market_summaries(loaded, summary_from, summary_to, adj_summary)

if market_summaries:
    inflation_note = (
        f" Price growth and volatility are computed from inflation-adjusted prices ({cpi_base_year} £, annual CPI)."
        if adj_summary and cpi else
        " Price growth and volatility use nominal prices — enable inflation adjustment for real-terms comparison."
    )
    st.markdown(
        "Key metrics for each polygon across the selected year range. "
        "Rankings are relative to the other selected polygons."
        + inflation_note
    )

    with st.expander("ℹ️ How to read these metrics"):
        st.markdown("""
**Price growth (CAGR)** — Compound Annual Growth Rate: the steady yearly growth rate that would take
the median price from the first year to the last. Reported in real terms (inflation-adjusted) when the
toggle is on, so it reflects genuine purchasing-power change rather than general price rises.

**Price stability (CV)** — Coefficient of Variation: the standard deviation of annual median prices
divided by their mean, expressed as a percentage. A low CV means prices moved smoothly year to year;
a high CV means there were larger swings. Useful for gauging predictability and risk.

**Liquidity (turnover %)** — The mean number of sales per year as a percentage of the total address
stock. A higher rate suggests more people are choosing to move, which indicates strong demand and a
liquid market. The implied hold period is simply 100 ÷ turnover rate.

**National premium** — The polygon's median sale price expressed as a percentage of the England &
Wales median for the same year, averaged across all years in the range.
100% = at the national median; 120% = 20% above; 80% = 20% below.

**New-build share** — The percentage of sales that were newly built properties, averaged annually.
A high share can inflate turnover figures (new builds sell once on completion) and push median prices
upward, so it is worth considering alongside the other metrics.
""")

    # Cross-polygon comparative narrative
    narrative = build_cross_polygon_narrative(market_summaries)
    if narrative:
        for sentence in narrative:
            st.markdown(f"> {sentence}")
        st.markdown("")

    n_poly          = len(market_summaries)
    rank_cagr       = rank_polygons(market_summaries, "cagr")
    rank_volatility = rank_polygons(market_summaries, "volatility", higher_is_better=False)
    rank_turnover   = rank_polygons(market_summaries, "turnover")
    rank_new_build  = rank_polygons(market_summaries, "new_build_pct", higher_is_better=False)
    rank_vs_nat     = rank_polygons(market_summaries, "vs_national")

    for s in market_summaries:
        name  = s["name"]
        lines = []

        if "cagr" in s:
            lines.append(
                f"Real price growth ({s['cagr_from']}–{s['cagr_to']}): "
                f"**{s['cagr']:+.1f}%/yr** — ranked {rank_cagr[name]} of {n_poly}"
            )
        if "volatility" in s:
            lines.append(
                f"Price stability (lower = more stable): "
                f"**{s['volatility']:.1f}% CV** — ranked {rank_volatility[name]} of {n_poly}"
            )
        if "turnover" in s:
            implied_hold = f", implying ~{100 / s['turnover']:.0f}-year average hold"
            lines.append(
                f"Liquidity ({s['uprn_count']:,} addresses): "
                f"**{s['turnover']:.1f}%/yr**{implied_hold} — ranked {rank_turnover[name]} of {n_poly}"
            )
        if "new_build_pct" in s:
            lines.append(
                f"New-build share: **{s['new_build_pct']:.1f}%** of sales "
                f"— ranked {rank_new_build[name]} of {n_poly}"
            )
        if "vs_national" in s:
            diff      = s["vs_national"] - 100
            direction = "above" if diff >= 0 else "below"
            lines.append(
                f"Premium vs national: **{abs(diff):.0f}% {direction}** national median on average "
                f"— ranked {rank_vs_nat[name]} of {n_poly}"
            )
        if lines:
            st.markdown(f"**{name}**")
            for line in lines:
                st.markdown(f"- {line}")


# ---------------------------------------------------------------------------
# Section 1: Price distribution summary table
# ---------------------------------------------------------------------------

st.subheader("Price distribution")
adj_table   = st.toggle("Adjust for inflation (current £)", key="adj_table", value=False)
if adj_table:
    warn_if_cpi_missing()
table_from, table_to = year_range_selector("table")
st.markdown(
    "Overall price spread across the selected years of sales data. "
    "The median is the middle sale price — half of all sales were above and half below. "
    "P25 and P75 show the middle 50% range. "
    "P5 and P95 show the 90% range: 90% of all sales fell between these two values."
)

table_rows = []
for feat in loaded:
    year_prices = [(y, p) for y, p in poly_prices(feat)
                   if y != latest_year
                   and (table_from is None or y >= table_from)
                   and (table_to   is None or y <= table_to)]
    if not year_prices:
        continue
    prices = sorted(p for _, p in prices_in_real_terms(year_prices, adj_table))
    n      = len(prices)
    years  = sorted({y for y, _ in year_prices})
    table_rows.append({
        "name":       poly_name(feat),
        "year_from":  years[0],
        "year_to":    years[-1],
        "year_count": len(years),
        "min":  min(prices),
        "p5":   prices[max(0, int(n * 0.05) - 1)],
        "p25":  prices[max(0, int(n * 0.25) - 1)],
        "med":  statistics.median(prices),
        "p75":  prices[min(n - 1, int(n * 0.75))],
        "p95":  prices[min(n - 1, int(n * 0.95))],
        "max":  max(prices),
        "n":    n,
    })

headers = st.columns([3, 2, 2, 2, 2, 2, 2, 2, 2])
for col, label in zip(headers, ["**Polygon**", "**Min**", "**P5**", "**P25**",
                                  "**Median**", "**P75**", "**P95**", "**Max**", "**Count**"]):
    col.markdown(label)

for r in table_rows:
    cols = st.columns([3, 2, 2, 2, 2, 2, 2, 2, 2])
    for col, val in zip(cols, [r["name"], f"£{r['min']:,.0f}", f"£{r['p5']:,.0f}",
                                f"£{r['p25']:,.0f}", f"£{r['med']:,.0f}", f"£{r['p75']:,.0f}",
                                f"£{r['p95']:,.0f}", f"£{r['max']:,.0f}", f"{r['n']:,}"]):
        col.markdown(val)

for r in table_rows:
    st.markdown(
        f"**{r['name']}**: in the {r['year_count']} years between {r['year_from']} and {r['year_to']}, "
        f"90% of sales were between **£{r['p5']:,.0f}** and **£{r['p95']:,.0f}**; "
        f"half were between £{r['p25']:,.0f} and £{r['p75']:,.0f}; "
        f"the median was £{r['med']:,.0f} from {r['n']:,} transactions."
    )

st.divider()


# ---------------------------------------------------------------------------
# Section 2: Price distribution histogram
# ---------------------------------------------------------------------------

st.subheader("Price distribution histogram")
adj_hist = st.toggle("Adjust for inflation (current £)", key="adj_hist", value=False)
if adj_hist:
    warn_if_cpi_missing()
st.markdown(
    "Distribution of sale prices for each polygon, normalised so shapes are comparable "
    "regardless of total transaction count. "
    "The shape reveals whether the market is broad or tightly clustered, "
    "and whether there are distinct sub-markets (e.g. a concentration of flats at one end "
    "and detached houses at the other)."
)

hist_from, hist_to = year_range_selector("hist")
if all_years:
    hcol1, hcol2 = st.columns([2, 1])
    with hcol1:
        price_min = st.number_input("Min price (£)", value=75_000,     step=5_000,  key="hist_price_min")
    with hcol2:
        price_max = st.number_input("Max price (£)", value=1_000_000,  step=25_000, key="hist_price_max")
else:
    price_min, price_max = 75_000, 1_000_000

st.plotly_chart(
    price_histogram_chart(hist_from, hist_to, adj_hist, price_min, price_max),
    width="stretch",
)
st.divider()


# ---------------------------------------------------------------------------
# Section 3: Median price trends
# ---------------------------------------------------------------------------

st.subheader("Median price trends")
adj_trend = st.toggle("Adjust for inflation (current £)", key="adj_trend", value=False)
if adj_trend:
    warn_if_cpi_missing()
trend_from, trend_to = year_range_selector("trend")

nat_trend        = filter_to_year_range(national_stats_in_real_terms(adj_trend), trend_from, trend_to)
nat_trend_by_year = {r["year"]: r for r in nat_trend}

narrative_parts = []
for feat in loaded:
    name   = poly_name(feat)
    stats  = filter_to_year_range(stats_in_real_terms(feat, adj_trend), trend_from, trend_to)
    if not stats:
        continue
    latest        = stats[-1]
    latest_median = _safe_float(latest["median_price"])
    nat_row       = nat_trend_by_year.get(latest["year"])
    nat_median    = _safe_float(nat_row["median_price"]) if nat_row else None
    if latest_median and nat_median:
        pct       = (latest_median / nat_median - 1) * 100
        direction = "above" if pct >= 0 else "below"
        narrative_parts.append(
            f"**{name}** had a median sale price of **£{latest_median:,.0f}** in {latest['year']}, "
            f"{abs(pct):.0f}% {direction} the national median of £{nat_median:,.0f}."
        )

inflation_note = f" Prices adjusted to {cpi_base_year} £ using annual average CPI." if adj_trend else ""
st.markdown(
    "Median sale price per year for each selected area alongside the national median (dotted line)."
    + inflation_note + " " + " ".join(narrative_parts)
)
st.plotly_chart(median_trend_chart(trend_from, trend_to, adj_trend, nat_trend), width="stretch")

if national:
    st.markdown(
        "The chart below shows the same data normalised to the national median each year — "
        "so the national line is always 100 and each area's value shows its percentage premium "
        "or discount relative to the country as a whole. "
        "A rising line means the area is becoming *more* expensive relative to the rest of England & Wales; "
        "a falling line means it is becoming *cheaper* in relative terms."
    )
    st.plotly_chart(premium_vs_national_chart(), width="stretch")

st.divider()


# ---------------------------------------------------------------------------
# Section 4: Relative price performance (indexed)
# ---------------------------------------------------------------------------

st.subheader("Relative price performance")

all_year_sets = [{r["year"] for r in poly_stats(f)} for f in loaded]
if national:
    all_year_sets.append({r["year"] for r in national})
common_years = sorted(set.intersection(*all_year_sets)) if all_year_sets else []
base_year    = common_years[0] if common_years else None

index_narrative_parts = []
if base_year:
    for feat in loaded:
        name   = poly_name(feat)
        stats  = filter_to_year_range(poly_stats(feat))
        by_yr  = {r["year"]: r for r in stats}
        base_val   = _safe_float(by_yr.get(base_year, {}).get("median_price"))
        latest_val = _safe_float(stats[-1]["median_price"]) if stats else None
        nat_base   = _safe_float(national_by_year.get(base_year, {}).get("median_price"))
        nat_latest = _safe_float(national_by_year.get(stats[-1]["year"] if stats else "", {}).get("median_price"))
        if base_val and latest_val and nat_base and nat_latest:
            growth       = (latest_val / base_val - 1) * 100
            nat_growth   = (nat_latest / nat_base - 1) * 100
            diff         = growth - nat_growth
            faster_slower = "faster" if diff >= 0 else "slower"
            index_narrative_parts.append(
                f"**{name}** has grown **{growth:.0f}%** since {base_year}, "
                f"{abs(diff):.0f} percentage points {faster_slower} than "
                f"the national average of {nat_growth:.0f}%."
            )

st.markdown(
    f"All series indexed to 100 in {base_year} (the earliest year with data across all selected areas). "
    "Values above 100 mean prices have risen more than the baseline; below 100 means less (or fallen). "
    "This removes absolute price differences and focuses purely on growth rates. "
    + (" ".join(index_narrative_parts) if index_narrative_parts else "")
)

if base_year:
    st.plotly_chart(indexed_performance_chart(base_year), width="stretch")

    if national:
        nat_by_yr  = {r["year"]: r for r in national}
        base_n     = _safe_float(nat_by_yr.get(base_year, {}).get("median_price"))
        if base_n:
            nat_indexed_by_year = {
                y: (_safe_float(nat_by_yr[y]["median_price"]) or 0) / base_n * 100
                for y in nat_by_yr
            }
            st.markdown(
                f"The same indexed data with the national growth line clamped to 100 each year. "
                f"A value above 100 means prices have grown *faster* than the national average since {base_year}; "
                f"below 100 means slower. This removes the national trend so you can focus purely on "
                f"whether each area is outpacing or lagging the country."
            )
            st.plotly_chart(relative_growth_chart(base_year, nat_indexed_by_year), width="stretch")
else:
    st.caption("Not enough overlapping data to build an index chart.")

st.divider()


# ---------------------------------------------------------------------------
# Section 5: Property mix
# ---------------------------------------------------------------------------

PROPERTY_TYPE_LABELS = {"D": "Detached", "S": "Semi-detached", "T": "Terraced", "F": "Flat", "O": "Other"}
DURATION_LABELS      = {"F": "Freehold", "L": "Leasehold", "U": "Unknown"}
OLD_NEW_LABELS       = {"Y": "New build", "N": "Established"}

st.subheader("Property mix")
mix_from, mix_to = year_range_selector("mix")
st.markdown(
    "Breakdown of sales by property type, tenure, and new/established build — "
    "shown as a percentage of all sales in each year. "
    "Shifts over time reflect new development, estate regeneration, or changing demand."
)

for feat in loaded:
    name = poly_name(feat)
    mix  = filter_to_year_range(poly_mix(feat), mix_from, mix_to)
    if not mix:
        st.caption(f"No mix data for {name} — re-fetch to load.")
        continue
    st.markdown(f"**{name}**")
    col1, col2, col3 = st.columns(3)
    col1.plotly_chart(mix_stacked_bar_chart(mix, "property_type", PROPERTY_TYPE_LABELS, "Property type"), width="stretch")
    col2.plotly_chart(mix_stacked_bar_chart(mix, "duration",      DURATION_LABELS,      "Tenure"),        width="stretch")
    col3.plotly_chart(mix_stacked_bar_chart(mix, "old_new",       OLD_NEW_LABELS,       "New / established"), width="stretch")

st.divider()


# ---------------------------------------------------------------------------
# Section 6: Annual turnover
# ---------------------------------------------------------------------------

EW_DWELLING_STOCK = 25_000_000

st.subheader("Annual turnover")

turnover_notes = []
for feat in loaded:
    uprn_count = poly_uprn_count(feat)
    if not uprn_count:
        continue
    name   = poly_name(feat)
    stats  = filter_to_year_range(poly_stats(feat))
    recent = [r for r in stats if int(r["year"]) >= 2015]
    if recent:
        avg_pct = statistics.mean(int(r["count"]) / uprn_count * 100 for r in recent)
        turnover_notes.append(f"**{name}** averaged **{avg_pct:.1f}% of addresses** selling per year since 2015.")

if national:
    nat_recent = [r for r in national if int(r["year"]) >= 2015]
    if nat_recent:
        avg_nat_pct = statistics.mean(int(r["count"]) / EW_DWELLING_STOCK * 100 for r in nat_recent)
        turnover_notes.append(f"The national average was **{avg_nat_pct:.1f}%** over the same period.")

st.markdown(
    "Annual sales as a percentage of total address stock, compared to the national turnover rate. "
    "Low turnover may indicate high owner-occupancy or low mobility; spikes often reflect "
    "new-build completions or estate regeneration. "
    "The national rate is estimated using ONS dwelling stock figures. "
    + " ".join(turnover_notes)
)
st.plotly_chart(turnover_chart(), width="stretch")

nav.render_attributions()
