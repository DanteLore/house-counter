"""Session state initialisation, polygon accessors, and data-fetch helpers."""

import streamlit as st

from price_paid.cache import (
    load_national_cache,
    load_county_cache,
    save_national_cache,
    save_county_cache,
)
from queries.price_paid_queries import (
    fetch_price_stats_for_polygon,
    fetch_price_stats_national,
    fetch_price_by_type_national,
    fetch_price_stats_for_county,
    fetch_price_by_type_for_county,
    fetch_address_count_for_county,
    fetch_all_county_names,
    fetch_mix_for_polygon,
    fetch_price_by_type_for_polygon,
    fetch_cpi_by_year,
)
from utils.polygons import save_polygons


# ---------------------------------------------------------------------------
# Session state initialisation  -  call once at page startup
# ---------------------------------------------------------------------------

def init_session(polygons):
    """Seed all pp_* session state keys from disk/polygon cache on first load."""
    if "pp_results" not in st.session_state:
        st.session_state.pp_results = {}

    if "pp_national" not in st.session_state or "pp_cpi" not in st.session_state:
        cached = load_national_cache() or {}
        st.session_state.pp_national         = cached.get("stats")
        st.session_state.pp_cpi              = cached.get("cpi")
        st.session_state.pp_national_by_type = cached.get("price_by_type")

    if "pp_county_cache" not in st.session_state:
        disk = load_county_cache()
        st.session_state.pp_county_cache          = disk["stats"]
        st.session_state.pp_county_by_type_cache  = disk.get("by_type", {})
        st.session_state.pp_county_address_counts = disk.get("address_counts", {})
        st.session_state.pp_county_names          = disk["names"]
        st.session_state.pp_comparison_selection  = (
            disk.get("comparison") or "National (England & Wales)"
        )

    if "pp_comparison_selection" not in st.session_state:
        st.session_state.pp_comparison_selection = (
            load_county_cache().get("comparison") or "National (England & Wales)"
        )

    # Restore per-polygon data from polygon properties (persisted across page reloads)
    for feat in polygons:
        pid = _feat_id(feat)
        if pid not in st.session_state.pp_results:
            stored_stats  = feat["properties"].get("pp_stats")
            stored_prices = feat["properties"].get("pp_prices")
            if stored_stats is not None:
                st.session_state.pp_results[pid] = {
                    "stats":         stored_stats,
                    "prices":        [tuple(p) for p in (stored_prices or [])],
                    "mix":           feat["properties"].get("pp_mix", []),
                    "price_by_type": feat["properties"].get("pp_price_by_type", []),
                }


# ---------------------------------------------------------------------------
# Polygon accessors
# ---------------------------------------------------------------------------

def _feat_id(feat):
    return feat["properties"].get("id", feat["properties"].get("name"))


def poly_id(feat):
    return _feat_id(feat)

def poly_name(feat):
    return feat["properties"].get("name", _feat_id(feat))

def poly_color(feat):
    from utils.polygons import DEFAULT_COLOR
    return feat["properties"].get("color", DEFAULT_COLOR)

def poly_uprn_count(feat):
    return feat["properties"].get("uprn_count")

def poly_prices(feat):
    return st.session_state.pp_results[_feat_id(feat)].get("prices", [])

def poly_stats(feat):
    return st.session_state.pp_results[_feat_id(feat)]["stats"]

def poly_mix(feat):
    return st.session_state.pp_results[_feat_id(feat)].get("mix", [])

def poly_price_by_type(feat):
    return st.session_state.pp_results[_feat_id(feat)].get("price_by_type", [])


# ---------------------------------------------------------------------------
# Data-fetch helpers
# ---------------------------------------------------------------------------

def fetch_polygon_data(feat, polygons):
    pid    = _feat_id(feat)
    name   = poly_name(feat)
    coords = feat["geometry"]["coordinates"]

    with st.spinner(f"Fetching prices for {name}…"):
        poly_stats_data, all_prices = fetch_price_stats_for_polygon(coords)
    with st.spinner(f"Fetching property mix for {name}…"):
        mix = fetch_mix_for_polygon(coords)
    with st.spinner(f"Fetching price by type for {name}…"):
        price_by_type = fetch_price_by_type_for_polygon(coords)

    st.session_state.pp_results[pid] = {
        "stats": poly_stats_data, "prices": all_prices,
        "mix": mix, "price_by_type": price_by_type,
    }

    for i, f in enumerate(polygons):
        if _feat_id(f) == pid:
            polygons[i]["properties"]["pp_stats"]         = poly_stats_data
            polygons[i]["properties"]["pp_prices"]        = [list(p) for p in all_prices]
            polygons[i]["properties"]["pp_mix"]           = mix
            polygons[i]["properties"]["pp_price_by_type"] = price_by_type
            break
    save_polygons(polygons)


def ensure_national_data():
    if st.session_state.pp_national is None:
        with st.spinner("Fetching national price data…"):
            st.session_state.pp_national = fetch_price_stats_national()
        with st.spinner("Fetching national price by type…"):
            st.session_state.pp_national_by_type = fetch_price_by_type_national()
        with st.spinner("Fetching CPI inflation data…"):
            st.session_state.pp_cpi = fetch_cpi_by_year()
        save_national_cache(
            st.session_state.pp_national,
            st.session_state.pp_cpi,
            st.session_state.pp_national_by_type,
        )


def ensure_county_names():
    if st.session_state.pp_county_names is None:
        with st.spinner("Loading county list…"):
            st.session_state.pp_county_names = fetch_all_county_names()
        save_county_cache(
            st.session_state.pp_county_names,
            st.session_state.pp_county_cache,
            st.session_state.pp_comparison_selection,
            st.session_state.pp_county_by_type_cache,
        )


def fetch_county_stats(county_name):
    with st.spinner(f"Fetching price data for {county_name}…"):
        stats = fetch_price_stats_for_county(county_name)
    with st.spinner(f"Fetching price by type for {county_name}…"):
        by_type = fetch_price_by_type_for_county(county_name)
    with st.spinner(f"Counting addresses in {county_name}…"):
        address_count = fetch_address_count_for_county(county_name)

    st.session_state.pp_county_cache[county_name]          = stats
    st.session_state.pp_county_by_type_cache[county_name]  = by_type
    st.session_state.pp_county_address_counts[county_name] = address_count

    save_county_cache(
        st.session_state.pp_county_names,
        st.session_state.pp_county_cache,
        st.session_state.pp_comparison_selection,
        st.session_state.pp_county_by_type_cache,
        st.session_state.pp_county_address_counts,
    )
