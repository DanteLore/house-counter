"""Price distribution summary table + histogram (KDE) chart."""

import statistics

import numpy as np
import plotly.graph_objects as go
import streamlit as st
from scipy.stats import gaussian_kde

from price_paid.charts.common import chart_layout, hex_to_rgba, show_data_table


def price_histogram_chart(loaded, poly_name_fn, poly_color_fn, poly_prices_fn,
                          latest_year, prices_in_real_terms_fn,
                          from_year, to_year, adjust, price_min, price_max,
                          price_axis_label):
    fig = go.Figure()
    for feat in loaded:
        name  = poly_name_fn(feat)
        color = poly_color_fn(feat)
        year_prices = [
            (y, p) for y, p in poly_prices_fn(feat)
            if y != latest_year
            and (from_year is None or y >= from_year)
            and (to_year   is None or y <= to_year)
        ]
        if not year_prices:
            continue
        prices = [p for _, p in prices_in_real_terms_fn(year_prices, adjust)]
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
        xaxis_title=price_axis_label,
        yaxis_title="Probability density",
        xaxis=dict(tickprefix="£", tickformat=","),
    ))
    return fig


def render_price_distribution_table(loaded, poly_name_fn, poly_prices_fn,
                                     latest_year, prices_in_real_terms_fn,
                                     all_years, warn_if_cpi_missing_fn,
                                     year_range_selector_fn):
    st.subheader("Price distribution")
    adjust = st.toggle("Adjust for inflation (current £)", key="adj_table", value=False)
    if adjust:
        warn_if_cpi_missing_fn()
    from_year, to_year = year_range_selector_fn("table")
    st.markdown(
        "Overall price spread across the selected years of sales data. "
        "The median is the middle sale price  -  half of all sales were above and half below. "
        "P25 and P75 show the middle 50% range. "
        "P5 and P95 show the 90% range: 90% of all sales fell between these two values."
    )

    rows = []
    for feat in loaded:
        year_prices = [(y, p) for y, p in poly_prices_fn(feat)
                       if y != latest_year
                       and (from_year is None or y >= from_year)
                       and (to_year   is None or y <= to_year)]
        if not year_prices:
            continue
        prices = sorted(p for _, p in prices_in_real_terms_fn(year_prices, adjust))
        n      = len(prices)
        yrs    = sorted({y for y, _ in year_prices})
        rows.append({
            "name": poly_name_fn(feat), "year_from": yrs[0], "year_to": yrs[-1],
            "year_count": len(yrs), "min": min(prices),
            "p5":  prices[max(0, int(n * 0.05) - 1)],
            "p25": prices[max(0, int(n * 0.25) - 1)],
            "med": statistics.median(prices),
            "p75": prices[min(n - 1, int(n * 0.75))],
            "p95": prices[min(n - 1, int(n * 0.95))],
            "max": max(prices), "n": n,
        })

    headers = st.columns([3, 2, 2, 2, 2, 2, 2, 2, 2])
    for col, label in zip(headers, ["**Polygon**", "**Min**", "**P5**", "**P25**",
                                      "**Median**", "**P75**", "**P95**", "**Max**", "**Count**"]):
        col.markdown(label)
    for r in rows:
        cols = st.columns([3, 2, 2, 2, 2, 2, 2, 2, 2])
        for col, val in zip(cols, [r["name"], f"£{r['min']:,.0f}", f"£{r['p5']:,.0f}",
                                    f"£{r['p25']:,.0f}", f"£{r['med']:,.0f}", f"£{r['p75']:,.0f}",
                                    f"£{r['p95']:,.0f}", f"£{r['max']:,.0f}", f"{r['n']:,}"]):
            col.markdown(val)
    for r in rows:
        st.markdown(
            f"**{r['name']}**: in the {r['year_count']} years between {r['year_from']} and {r['year_to']}, "
            f"90% of sales were between **£{r['p5']:,.0f}** and **£{r['p95']:,.0f}**; "
            f"half were between £{r['p25']:,.0f} and £{r['p75']:,.0f}; "
            f"the median was £{r['med']:,.0f} from {r['n']:,} transactions."
        )

    table_rows = [{
        "Area":    r["name"],
        "Years":   f"{r['year_from']}-{r['year_to']}",
        "Count":   r["n"],
        "Min":     f"£{r['min']:,.0f}",
        "P5":      f"£{r['p5']:,.0f}",
        "P25":     f"£{r['p25']:,.0f}",
        "Median":  f"£{r['med']:,.0f}",
        "P75":     f"£{r['p75']:,.0f}",
        "P95":     f"£{r['p95']:,.0f}",
        "Max":     f"£{r['max']:,.0f}",
    } for r in rows]
    show_data_table(table_rows, "Price distribution summary data")
    st.divider()


def render_price_histogram(loaded, poly_name_fn, poly_color_fn, poly_prices_fn,
                            latest_year, prices_in_real_terms_fn, price_axis_label_fn,
                            all_years, warn_if_cpi_missing_fn, year_range_selector_fn):
    st.subheader("Price distribution histogram")
    adjust = st.toggle("Adjust for inflation (current £)", key="adj_hist", value=False)
    if adjust:
        warn_if_cpi_missing_fn()
    st.markdown(
        "Distribution of sale prices for each polygon, normalised so shapes are comparable "
        "regardless of total transaction count."
    )
    from_year, to_year = year_range_selector_fn("hist")
    if all_years:
        c1, c2 = st.columns([2, 1])
        with c1:
            price_min = st.number_input("Min price (£)", value=75_000,    step=5_000,  key="hist_price_min")
        with c2:
            price_max = st.number_input("Max price (£)", value=1_000_000, step=25_000, key="hist_price_max")
    else:
        price_min, price_max = 75_000, 1_000_000
    st.plotly_chart(
        price_histogram_chart(loaded, poly_name_fn, poly_color_fn, poly_prices_fn,
                              latest_year, prices_in_real_terms_fn,
                              from_year, to_year, adjust, price_min, price_max,
                              price_axis_label_fn(adjust)),
        width="stretch",
    )

    hist_rows = []
    for feat in loaded:
        year_prices = [
            (y, p) for y, p in poly_prices_fn(feat)
            if y != latest_year
            and (from_year is None or y >= from_year)
            and (to_year   is None or y <= to_year)
        ]
        if not year_prices:
            continue
        prices = sorted(p for _, p in prices_in_real_terms_fn(year_prices, adjust))
        n = len(prices)
        hist_rows.append({
            "Area":    poly_name_fn(feat),
            "Count":   n,
            "Min":     f"£{min(prices):,.0f}",
            "P5":      f"£{prices[max(0, int(n * 0.05) - 1)]:,.0f}",
            "P25":     f"£{prices[max(0, int(n * 0.25) - 1)]:,.0f}",
            "Median":  f"£{prices[n // 2]:,.0f}",
            "P75":     f"£{prices[min(n - 1, int(n * 0.75))]:,.0f}",
            "P95":     f"£{prices[min(n - 1, int(n * 0.95))]:,.0f}",
            "Max":     f"£{max(prices):,.0f}",
        })
    show_data_table(hist_rows, "Price distribution data")
    st.divider()
