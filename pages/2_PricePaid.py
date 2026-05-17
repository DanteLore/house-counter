import folium
import streamlit as st
from streamlit_folium import st_folium

import utils.nav as nav
from price_paid.cache import save_county_cache
from price_paid.charts.market_summary import render_market_summary
from price_paid.charts.price_by_type import render_price_by_type
from price_paid.charts.price_distribution import render_price_distribution_table, render_price_histogram
from price_paid.charts.price_trends import render_median_trends, render_indexed_performance
from price_paid.charts.property_mix import render_property_mix
from price_paid.charts.turnover import EW_DWELLING_STOCK, render_annual_turnover, render_volume_by_type
from price_paid.filters import (
    compute_latest_year,
    exclude_incomplete_year,
    filter_to_year_range,
    get_all_years,
    year_range_selector,
)
from price_paid.inflation import (
    comparison_stats_in_real_terms,
    get_cpi_state,
    price_axis_label,
    prices_in_real_terms,
    stats_in_real_terms,
    warn_if_cpi_missing,
)
from price_paid.session import (
    ensure_county_names,
    ensure_national_data,
    fetch_county_stats,
    fetch_polygon_data,
    init_session,
    poly_color,
    poly_id,
    poly_mix,
    poly_name,
    poly_price_by_type,
    poly_prices,
    poly_stats,
    poly_uprn_count,
)
from utils.polygons import DEFAULT_COLOR, load_polygons

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
# Polygon selection
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
    st.session_state.pp_selected_names = [n for n in st.session_state.pp_selected_names if n in poly_names]

selected_names = st.multiselect("Select polygons to analyse", poly_names, key="pp_selected_names")
if not selected_names:
    st.info("Select at least one polygon above.")
    st.stop()

selected = [f for f in polygons if f["properties"].get("name") in selected_names]

missing_count = [f["properties"].get("name") for f in selected if f["properties"].get("uprn_count") is None]
if missing_count:
    st.warning(
        f"These polygons have no address count  -  turnover % will be unavailable: "
        f"{', '.join(missing_count)}. Use the House Counter page to count addresses first."
    )


# ---------------------------------------------------------------------------
# Map
# ---------------------------------------------------------------------------

all_lons   = [c[0] for feat in selected for c in feat["geometry"]["coordinates"][0]]
all_lats   = [c[1] for feat in selected for c in feat["geometry"]["coordinates"][0]]
map_centre = ((min(all_lats) + max(all_lats)) / 2, (min(all_lons) + max(all_lons)) / 2)
m = folium.Map(location=map_centre, zoom_start=13, tiles="OpenStreetMap")
for feat in selected:
    color = feat["properties"].get("color", DEFAULT_COLOR)
    folium.GeoJson(feat,
        style_function=lambda _, c=color: {"color": c, "fillColor": c, "fillOpacity": 0.25, "weight": 2},
        tooltip=folium.Tooltip(feat["properties"].get("name", "")),
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
# Session + fetch controls
# ---------------------------------------------------------------------------

init_session(polygons)

with st.container():
    btn_cols = st.columns(2 + len(selected))
    if btn_cols[0].button("Fetch all", type="primary", use_container_width=True):
        ensure_national_data()
        for feat in selected:
            fetch_polygon_data(feat, polygons)
        st.rerun()
    if btn_cols[1].button("Fetch missing", use_container_width=True):
        ensure_national_data()
        for feat in selected:
            if poly_id(feat) not in st.session_state.pp_results:
                fetch_polygon_data(feat, polygons)
        st.rerun()
    for idx, feat in enumerate(selected):
        pid = poly_id(feat)
        if btn_cols[2 + idx].button(f"↺ {poly_name(feat)}", key=f"refresh_{pid}", use_container_width=True):
            ensure_national_data()
            fetch_polygon_data(feat, polygons)
            st.rerun()


# ---------------------------------------------------------------------------
# Comparison baseline selector
# ---------------------------------------------------------------------------

st.markdown("**Comparison baseline**")
ensure_county_names()
county_names = st.session_state.pp_county_names or []
c_sel, c_btn = st.columns([4, 1])
with c_sel:
    county_options = ["National (England & Wales)"] + county_names
    if st.session_state.pp_comparison_selection not in county_options:
        st.session_state.pp_comparison_selection = "National (England & Wales)"

    def _save_comparison():
        save_county_cache(st.session_state.pp_county_names, st.session_state.pp_county_cache,
                          st.session_state.pp_comparison_selection)

    comparison_choice = st.selectbox("Compare polygons against", county_options,
                                     key="pp_comparison_selection", on_change=_save_comparison)

selected_county = None if comparison_choice == "National (England & Wales)" else comparison_choice
with c_btn:
    st.markdown("&nbsp;", unsafe_allow_html=True)
    if selected_county and selected_county not in st.session_state.pp_county_cache:
        if st.button("Fetch", key="fetch_county", use_container_width=True):
            fetch_county_stats(selected_county)
            st.rerun()
    elif selected_county:
        if st.button("↺ Refresh", key="refresh_county", use_container_width=True):
            fetch_county_stats(selected_county)
            st.rerun()
st.divider()


# ---------------------------------------------------------------------------
# Guard + shared derived state
# ---------------------------------------------------------------------------

loaded = [f for f in selected if poly_id(f) in st.session_state.pp_results]
if not loaded:
    st.caption("Click 'Fetch missing' to load results.")
    st.stop()

national_raw = st.session_state.pp_national or []
latest_year  = compute_latest_year(
    national_raw,
    st.session_state.pp_county_cache.get(selected_county) or [],
    st.session_state.pp_results,
)
national = exclude_incomplete_year(national_raw, latest_year)

if selected_county and selected_county in st.session_state.pp_county_cache:
    comparison               = exclude_incomplete_year(st.session_state.pp_county_cache[selected_county], latest_year)
    comparison_label         = selected_county
    _cmp_by_type_raw         = st.session_state.pp_county_by_type_cache.get(selected_county, [])
    comparison_address_count = st.session_state.pp_county_address_counts.get(selected_county)
else:
    comparison               = national
    comparison_label         = "National"
    _cmp_by_type_raw         = st.session_state.get("pp_national_by_type") or []
    comparison_address_count = EW_DWELLING_STOCK

comparison_by_year = {r["year"]: r for r in comparison}
comparison_by_type = {
    (r["year"], r["property_type"]): r
    for r in _cmp_by_type_raw if r["year"] != latest_year
}
cpi, cpi_base_year = get_cpi_state()
all_years = get_all_years(loaded, poly_prices, latest_year)

# Short wrappers so render_* calls don't need latest_year/cpi/comparison threaded through every argument
def _filter(rows, from_year=None, to_year=None):
    return filter_to_year_range(rows, latest_year, from_year, to_year)

def _yr_sel(prefix):
    return year_range_selector(prefix, all_years)

def _stats_real(feat, adjust):
    return stats_in_real_terms(poly_stats(feat), poly_prices(feat), adjust)

def _cmp_real(adjust):
    return comparison_stats_in_real_terms(comparison, adjust)

def _prices_real(year_prices, adjust):
    return prices_in_real_terms(year_prices, adjust)

def _price_label(adjust):
    return price_axis_label(adjust)


# ---------------------------------------------------------------------------
# Page note + sections
# ---------------------------------------------------------------------------

if latest_year:
    st.caption(
        f"**Note:** {latest_year} data is excluded from all charts and calculations. "
        f"Land Registry registration typically lags completions by 6–8 weeks, so the current year "
        f"is always a partial sample  -  transaction counts are low and mix is unrepresentative."
    )

# Market summary
st.subheader("Market summary")
adj_summary = st.toggle(
    f"Adjust prices for inflation ({cpi_base_year} £)" if cpi_base_year else "Adjust prices for inflation",
    key="adj_summary", value=bool(cpi),
)
if adj_summary:
    warn_if_cpi_missing()
summary_from, summary_to = _yr_sel("summary")
render_market_summary(
    loaded, poly_name, poly_stats, poly_prices, poly_uprn_count, poly_mix,
    comparison_by_year, latest_year, cpi, cpi_base_year,
    summary_from, summary_to, adj_summary, comparison_label,
)

render_price_distribution_table(
    loaded, poly_name, poly_prices, latest_year, _prices_real,
    all_years, warn_if_cpi_missing, _yr_sel,
)
render_price_histogram(
    loaded, poly_name, poly_color, poly_prices, latest_year, _prices_real,
    _price_label, all_years, warn_if_cpi_missing, _yr_sel,
)
render_median_trends(
    loaded, poly_name, poly_color, poly_stats, poly_prices,
    _stats_real, comparison, comparison_label, latest_year, cpi_base_year,
    _filter, _cmp_real, warn_if_cpi_missing, _yr_sel, _price_label,
)
render_indexed_performance(
    loaded, poly_name, poly_color, poly_stats,
    comparison, comparison_by_year, comparison_label, latest_year, _filter,
)
render_property_mix(loaded, poly_name, poly_mix, _filter, _yr_sel)
render_price_by_type(
    loaded, poly_name, poly_price_by_type,
    comparison_by_type, comparison_label,
    cpi, cpi_base_year, _filter, warn_if_cpi_missing, _yr_sel, _price_label,
)
render_annual_turnover(
    loaded, poly_name, poly_color, poly_stats, poly_uprn_count,
    national, latest_year, _filter,
)
render_volume_by_type(
    loaded, poly_name, poly_price_by_type, poly_uprn_count,
    comparison_by_type, comparison_label, comparison_address_count,
    _filter, _yr_sel,
)

nav.render_attributions()
