"""Year-range filtering and selector widget."""

import streamlit as st

_DEFAULT_FROM_YEAR = "2001"


def compute_latest_year(national, county_rows, pp_results):
    """Return the most recent year seen across all data sources."""
    years = (
        [r["year"] for r in national]
        + [r["year"] for r in (county_rows or [])]
        + [r["year"] for pid in pp_results for r in pp_results[pid].get("stats", [])]
    )
    return max(years, default=None)


def exclude_incomplete_year(rows, latest_year):
    return [r for r in rows if r["year"] != latest_year]


def filter_to_year_range(rows, latest_year, from_year=None, to_year=None):
    return [
        r for r in rows
        if r["year"] != latest_year
        and (from_year is None or r["year"] >= from_year)
        and (to_year   is None or r["year"] <= to_year)
    ]


def get_all_years(loaded_feats, poly_prices_fn, latest_year):
    return sorted({
        year
        for feat in loaded_feats
        for year, _ in poly_prices_fn(feat)
        if year != latest_year
    })


def _default_from_index(all_years):
    for i, y in enumerate(all_years):
        if y >= _DEFAULT_FROM_YEAR:
            return i
    return 0


def year_range_selector(key_prefix, all_years):
    """Render From/To year dropdowns and return (from_year, to_year)."""
    if not all_years:
        return None, None
    _, c2, c3 = st.columns([2, 1, 1])
    with c2:
        from_yr = st.selectbox("From year", all_years, index=_default_from_index(all_years), key=f"{key_prefix}_from")
    with c3:
        to_yr = st.selectbox("To year", all_years, index=len(all_years) - 1, key=f"{key_prefix}_to")
    return from_yr, to_yr
