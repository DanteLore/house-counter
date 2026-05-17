"""Render market summary metrics and narrative to Streamlit."""

import streamlit as st

from price_paid.calculations import (
    build_market_summaries,
    build_cross_polygon_narrative,
    rank_polygons,
)


def render_market_summary(loaded, poly_name_fn, poly_stats_fn, poly_prices_fn,
                          poly_uprn_count_fn, poly_mix_fn,
                          comparison_by_year, latest_year, cpi, cpi_base_year,
                          from_year, to_year, adjust, comparison_label):
    market_summaries = build_market_summaries(
        loaded,
        poly_name_fn, poly_stats_fn, poly_prices_fn,
        poly_uprn_count_fn, poly_mix_fn,
        comparison_by_year, latest_year,
        cpi, cpi_base_year,
        from_year, to_year, adjust,
    )
    if not market_summaries:
        return

    inflation_note = (
        f" Price growth and volatility are computed from inflation-adjusted prices ({cpi_base_year} £, annual CPI)."
        if adjust and cpi else
        " Price growth and volatility use nominal prices  -  enable inflation adjustment for real-terms comparison."
    )
    st.markdown(
        "Key metrics for each polygon across the selected year range. "
        "Rankings are relative to the other selected polygons."
        + inflation_note
    )

    with st.expander("ℹ️ How to read these metrics"):
        st.markdown("""
**Price growth (CAGR)**  -  Compound Annual Growth Rate: the steady yearly growth rate that would take
the median price from the first year to the last. Reported in real terms (inflation-adjusted) when the
toggle is on, so it reflects genuine purchasing-power change rather than general price rises.

**Price stability (CV)**  -  Coefficient of Variation: the standard deviation of annual median prices
divided by their mean, expressed as a percentage. A low CV means prices moved smoothly year to year;
a high CV means there were larger swings. Useful for gauging predictability and risk.

**Liquidity (turnover %)**  -  The mean number of sales per year as a percentage of the total address
stock. A higher rate suggests more people are choosing to move, which indicates strong demand and a
liquid market. The implied hold period is simply 100 ÷ turnover rate.

**National premium**  -  The polygon's median sale price expressed as a percentage of the England &
Wales median for the same year, averaged across all years in the range.
100% = at the national median; 120% = 20% above; 80% = 20% below.

**New-build share**  -  The percentage of sales that were newly built properties, averaged annually.
A high share can inflate turnover figures (new builds sell once on completion) and push median prices
upward, so it is worth considering alongside the other metrics.
""")

    narrative = build_cross_polygon_narrative(market_summaries)
    for sentence in narrative:
        st.markdown(f"> {sentence}")
    if narrative:
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
                f"**{s['cagr']:+.1f}%/yr**  -  ranked {rank_cagr[name]} of {n_poly}"
            )
        if "volatility" in s:
            lines.append(
                f"Price stability (lower = more stable): "
                f"**{s['volatility']:.1f}% CV**  -  ranked {rank_volatility[name]} of {n_poly}"
            )
        if "turnover" in s:
            implied_hold = f", implying ~{100 / s['turnover']:.0f}-year average hold"
            lines.append(
                f"Liquidity ({s['uprn_count']:,} addresses): "
                f"**{s['turnover']:.1f}%/yr**{implied_hold}  -  ranked {rank_turnover[name]} of {n_poly}"
            )
        if "new_build_pct" in s:
            lines.append(
                f"New-build share: **{s['new_build_pct']:.1f}%** of sales "
                f" -  ranked {rank_new_build[name]} of {n_poly}"
            )
        if "vs_national" in s:
            diff      = s["vs_national"] - 100
            direction = "above" if diff >= 0 else "below"
            lines.append(
                f"Premium vs {comparison_label}: **{abs(diff):.0f}% {direction}** "
                f"median on average  -  ranked {rank_vs_nat[name]} of {n_poly}"
            )
        if lines:
            st.markdown(f"**{name}**")
            for line in lines:
                st.markdown(f"- {line}")
