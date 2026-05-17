"""CPI inflation helpers for real-terms price conversion."""

import streamlit as st

from queries.price_paid_queries import deflate_prices, real_stats_from_prices


def get_cpi_state():
    """Return (cpi_dict, cpi_base_year) from session state."""
    cpi = st.session_state.pp_cpi or {}
    base = max(cpi.keys()) if cpi else None
    return cpi, base


def warn_if_cpi_missing():
    cpi, _ = get_cpi_state()
    if not cpi:
        st.warning("CPI data not loaded  -  click **Fetch all** or **Fetch missing** to enable inflation adjustment.")


def prices_in_real_terms(year_prices, adjust):
    cpi, base = get_cpi_state()
    return deflate_prices(year_prices, cpi, base) if adjust else year_prices


def stats_in_real_terms(poly_stats_rows, poly_prices_rows, adjust):
    """Return yearly stats, optionally re-derived from deflated raw prices."""
    if not adjust:
        return poly_stats_rows
    cpi, base = get_cpi_state()
    return real_stats_from_prices(poly_prices_rows, cpi, base)


def comparison_stats_in_real_terms(comparison_rows, adjust):
    """Deflate pre-computed comparison stats row-by-row (no raw prices available)."""
    if not adjust:
        return comparison_rows
    cpi, base = get_cpi_state()

    def deflate_field(row, field):
        return deflate_prices([(row["year"], row[field])], cpi, base)[0][1]

    return [{**r,
             "min_price":    deflate_field(r, "min_price"),
             "max_price":    deflate_field(r, "max_price"),
             "mean_price":   deflate_field(r, "mean_price"),
             "median_price": deflate_field(r, "median_price"),
             "p25_price":    deflate_field(r, "p25_price"),
             "p75_price":    deflate_field(r, "p75_price"),
             } for r in comparison_rows]


def price_axis_label(adjust):
    _, base = get_cpi_state()
    return f"Sale price ({base} £)" if adjust else "Sale price (£)"
