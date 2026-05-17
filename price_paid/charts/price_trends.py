"""Median price trend, premium vs baseline, and indexed performance charts + render functions."""

import plotly.graph_objects as go
import streamlit as st

from price_paid.charts.common import chart_layout, hex_to_rgba, add_baseline_bars, show_data_table


def _sf(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Chart builders (pure Plotly, no Streamlit)
# ---------------------------------------------------------------------------

def median_trend_chart(loaded, poly_name_fn, poly_color_fn, stats_rows_fn,
                       comparison_rows, comparison_label, price_axis_label):
    fig = go.Figure()
    for feat in loaded:
        name  = poly_name_fn(feat)
        color = poly_color_fn(feat)
        stats = stats_rows_fn(feat)
        years = [r["year"] for r in stats]
        fig.add_trace(go.Scatter(
            x=years, y=[_sf(r["p25_price"]) for r in stats],
            mode="lines", name=name, legendgroup=name, showlegend=False,
            line=dict(color=color, width=0),
            hovertemplate="%{x}: £%{y:,.0f} (P25)<extra>" + name + "</extra>",
        ))
        fig.add_trace(go.Scatter(
            x=years, y=[_sf(r["p75_price"]) for r in stats],
            mode="lines", name=f"{name} (P25–P75)", legendgroup=name, showlegend=True,
            fill="tonexty", fillcolor=hex_to_rgba(color, 0.15), line=dict(color=color, width=0),
            hovertemplate="%{x}: £%{y:,.0f} (P75)<extra>" + name + "</extra>",
        ))
        fig.add_trace(go.Scatter(
            x=years, y=[_sf(r["median_price"]) for r in stats],
            mode="lines+markers", name=name, legendgroup=name, showlegend=True,
            line=dict(color=color, width=2),
            hovertemplate="%{x}: £%{y:,.0f} (median)<extra>" + name + "</extra>",
        ))
    if comparison_rows:
        fig.add_trace(go.Scatter(
            x=[r["year"] for r in comparison_rows],
            y=[_sf(r["median_price"]) for r in comparison_rows],
            mode="lines", name=comparison_label,
            line=dict(color="#888888", width=1, dash="dot"),
            hovertemplate="%{x}: £%{y:,.0f}<extra>" + comparison_label + "</extra>",
        ))
    fig.update_layout(**chart_layout(yaxis_title=price_axis_label, xaxis_title="Year"))
    return fig


def premium_vs_national_chart(loaded, poly_name_fn, poly_color_fn, poly_stats_fn,
                               comparison_rows, comparison_label, latest_year,
                               from_year, to_year):
    cmp_median_by_year = {r["year"]: _sf(r["median_price"]) for r in comparison_rows}
    fig = go.Figure()
    for feat in loaded:
        name  = poly_name_fn(feat)
        color = poly_color_fn(feat)
        stats = [r for r in poly_stats_fn(feat)
                 if r["year"] != latest_year
                 and (from_year is None or r["year"] >= from_year)
                 and (to_year   is None or r["year"] <= to_year)]
        years, vals = [], []
        for r in stats:
            cmp_val  = cmp_median_by_year.get(r["year"])
            poly_val = _sf(r["median_price"])
            if cmp_val and poly_val:
                years.append(r["year"])
                vals.append(poly_val / cmp_val * 100)
        add_baseline_bars(fig, years, vals, name, color, baseline=100,
                          hover_suffix=f"% of {comparison_label} median")
    fig.add_hline(y=100, line_dash="dot", line_color="#888888",
                  annotation_text=comparison_label, annotation_position="right")
    fig.update_layout(**chart_layout(
        yaxis_title=f"Median price as % of {comparison_label} median",
        xaxis_title="Year", barmode="group",
    ))
    return fig


def indexed_performance_chart(loaded, poly_name_fn, poly_color_fn, poly_stats_fn,
                               comparison_rows, comparison_label, latest_year, base_year):
    fig = go.Figure()
    for feat in loaded:
        name  = poly_name_fn(feat)
        color = poly_color_fn(feat)
        stats = [r for r in poly_stats_fn(feat) if r["year"] != latest_year]
        by_yr = {r["year"]: r for r in stats}
        base_val = _sf(by_yr.get(base_year, {}).get("median_price"))
        if not base_val:
            continue
        years   = sorted(by_yr)
        indexed = [(_sf(by_yr[y]["median_price"]) or 0) / base_val * 100 for y in years]
        fig.add_trace(go.Scatter(
            x=years, y=indexed, mode="lines+markers", name=name,
            line=dict(color=color, width=2),
            hovertemplate="%{x}: %{y:.1f}<extra>" + name + "</extra>",
        ))
    if comparison_rows:
        cmp_by_yr = {r["year"]: r for r in comparison_rows}
        base_n    = _sf(cmp_by_yr.get(base_year, {}).get("median_price"))
        if base_n:
            cy = sorted(cmp_by_yr)
            ci = [(_sf(cmp_by_yr[y]["median_price"]) or 0) / base_n * 100 for y in cy]
            fig.add_trace(go.Scatter(
                x=cy, y=ci, mode="lines", name=comparison_label,
                line=dict(color="#888888", width=1, dash="dot"),
                hovertemplate="%{x}: %{y:.1f}<extra>" + comparison_label + "</extra>",
            ))
    fig.add_hline(y=100, line_dash="dash", line_color="#cccccc")
    fig.update_layout(**chart_layout(yaxis_title=f"Index ({base_year} = 100)", xaxis_title="Year"))
    return fig


def relative_growth_chart(loaded, poly_name_fn, poly_color_fn, poly_stats_fn,
                           comparison_label, latest_year, base_year, cmp_indexed_by_year):
    fig = go.Figure()
    for feat in loaded:
        name  = poly_name_fn(feat)
        color = poly_color_fn(feat)
        stats = [r for r in poly_stats_fn(feat) if r["year"] != latest_year]
        by_yr = {r["year"]: r for r in stats}
        base_val = _sf(by_yr.get(base_year, {}).get("median_price"))
        if not base_val:
            continue
        years, vals = [], []
        for y in sorted(by_yr):
            nat_idx  = cmp_indexed_by_year.get(y)
            poly_val = _sf(by_yr[y]["median_price"])
            if nat_idx and poly_val:
                years.append(y)
                vals.append((poly_val / base_val * 100) / nat_idx * 100)
        add_baseline_bars(fig, years, vals, name, color, baseline=100)
    fig.add_hline(y=100, line_dash="dot", line_color="#888888",
                  annotation_text=comparison_label, annotation_position="right")
    fig.update_layout(**chart_layout(
        yaxis_title=f"Growth relative to {comparison_label} ({base_year} = 100)",
        xaxis_title="Year", barmode="group",
    ))
    return fig


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def render_median_trends(loaded, poly_name_fn, poly_color_fn, poly_stats_fn,
                          poly_prices_fn, stats_in_real_terms_fn, comparison_rows,
                          comparison_label, latest_year, cpi_base_year,
                          filter_fn, comparison_stats_real_fn,
                          warn_if_cpi_missing_fn, year_range_selector_fn,
                          price_axis_label_fn):
    st.subheader("Median price trends")
    adjust = st.toggle("Adjust for inflation (current £)", key="adj_trend", value=False)
    if adjust:
        warn_if_cpi_missing_fn()
    from_year, to_year = year_range_selector_fn("trend")

    cmp_trend         = filter_fn(comparison_stats_real_fn(adjust), from_year, to_year)
    cmp_trend_by_year = {r["year"]: r for r in cmp_trend}

    narrative_parts = []
    for feat in loaded:
        name  = poly_name_fn(feat)
        stats = filter_fn(stats_in_real_terms_fn(feat, adjust), from_year, to_year)
        if not stats:
            continue
        last        = stats[-1]
        last_med    = _sf(last["median_price"])
        cmp_row     = cmp_trend_by_year.get(last["year"])
        cmp_med     = _sf(cmp_row["median_price"]) if cmp_row else None
        if last_med and cmp_med:
            pct = (last_med / cmp_med - 1) * 100
            dir = "above" if pct >= 0 else "below"
            narrative_parts.append(
                f"**{name}** had a median sale price of **£{last_med:,.0f}** in {last['year']}, "
                f"{abs(pct):.0f}% {dir} the {comparison_label} median of £{cmp_med:,.0f}."
            )

    inflation_note = f" Prices adjusted to {cpi_base_year} £ using annual average CPI." if adjust else ""
    st.markdown(
        "Median sale price per year for each selected area alongside the comparison median (dotted line)."
        + inflation_note + " " + " ".join(narrative_parts)
    )
    st.plotly_chart(
        median_trend_chart(
            loaded, poly_name_fn, poly_color_fn,
            lambda feat: filter_fn(stats_in_real_terms_fn(feat, adjust), from_year, to_year),
            cmp_trend, comparison_label, price_axis_label_fn(adjust),
        ),
        width="stretch",
    )

    table_rows = []
    for feat in loaded:
        name  = poly_name_fn(feat)
        for r in filter_fn(stats_in_real_terms_fn(feat, adjust), from_year, to_year):
            table_rows.append({"Area": name, "Year": r["year"],
                               "Median": f"£{_sf(r['median_price']):,.0f}",
                               "P25": f"£{_sf(r['p25_price']):,.0f}",
                               "P75": f"£{_sf(r['p75_price']):,.0f}",
                               "Sales": r["count"]})
    for r in cmp_trend:
        table_rows.append({"Area": comparison_label, "Year": r["year"],
                           "Median": f"£{_sf(r['median_price']):,.0f}",
                           "P25": f"£{_sf(r['p25_price']):,.0f}",
                           "P75": f"£{_sf(r['p75_price']):,.0f}",
                           "Sales": r.get("count", " - ")})
    show_data_table(sorted(table_rows, key=lambda r: (r["Year"], r["Area"])), "Median price data")

    if comparison_rows:
        st.markdown(
            f"The chart below shows the same data normalised to the {comparison_label} median each year  -  "
            f"so the {comparison_label} line is always 100 and each area's value shows its percentage premium "
            f"or discount relative to {comparison_label}. "
            "A rising line means the area is becoming *more* expensive in relative terms; "
            "a falling line means it is becoming *cheaper*."
        )
        st.plotly_chart(
            premium_vs_national_chart(loaded, poly_name_fn, poly_color_fn, poly_stats_fn,
                                      comparison_rows, comparison_label, latest_year,
                                      from_year, to_year),
            width="stretch",
        )
        cmp_med_by_yr = {r["year"]: _sf(r["median_price"]) for r in comparison_rows}
        premium_rows  = []
        for feat in loaded:
            name  = poly_name_fn(feat)
            for r in filter_fn(poly_stats_fn(feat), from_year, to_year):
                cmp_val  = cmp_med_by_yr.get(r["year"])
                poly_val = _sf(r["median_price"])
                if cmp_val and poly_val:
                    premium_rows.append({
                        "Area": name, "Year": r["year"],
                        "Polygon median": f"£{poly_val:,.0f}",
                        f"{comparison_label} median": f"£{cmp_val:,.0f}",
                        f"% of {comparison_label}": f"{poly_val / cmp_val * 100:.1f}%",
                    })
        show_data_table(sorted(premium_rows, key=lambda r: (r["Year"], r["Area"])),
                        f"Premium vs {comparison_label}")
    st.divider()


def render_indexed_performance(loaded, poly_name_fn, poly_color_fn, poly_stats_fn,
                                comparison_rows, comparison_by_year, comparison_label,
                                latest_year, filter_fn):
    st.subheader("Relative price performance")

    all_year_sets = [{r["year"] for r in poly_stats_fn(f)} for f in loaded]
    if comparison_rows:
        all_year_sets.append({r["year"] for r in comparison_rows})
    common_years = sorted(set.intersection(*all_year_sets)) if all_year_sets else []
    base_year    = common_years[0] if common_years else None

    narrative_parts = []
    if base_year:
        for feat in loaded:
            name  = poly_name_fn(feat)
            stats = filter_fn(poly_stats_fn(feat))
            by_yr = {r["year"]: r for r in stats}
            base_v = _sf(by_yr.get(base_year, {}).get("median_price"))
            last_v = _sf(stats[-1]["median_price"]) if stats else None
            cmp_b  = _sf(comparison_by_year.get(base_year, {}).get("median_price"))
            last_yr = stats[-1]["year"] if stats else ""
            cmp_l   = _sf(comparison_by_year.get(last_yr, {}).get("median_price"))
            if base_v and last_v and cmp_b and cmp_l:
                growth     = (last_v / base_v - 1) * 100
                cmp_growth = (cmp_l / cmp_b - 1) * 100
                diff       = growth - cmp_growth
                fs         = "faster" if diff >= 0 else "slower"
                narrative_parts.append(
                    f"**{name}** has grown **{growth:.0f}%** since {base_year}, "
                    f"{abs(diff):.0f} percentage points {fs} than "
                    f"the {comparison_label} average of {cmp_growth:.0f}%."
                )

    st.markdown(
        f"All series indexed to 100 in {base_year} (the earliest year with data across all selected areas). "
        "Values above 100 mean prices have risen more than the baseline; below 100 means less (or fallen). "
        + (" ".join(narrative_parts) if narrative_parts else "")
    )

    if not base_year:
        st.caption("Not enough overlapping data to build an index chart.")
        st.divider()
        return

    st.plotly_chart(
        indexed_performance_chart(loaded, poly_name_fn, poly_color_fn, poly_stats_fn,
                                  comparison_rows, comparison_label, latest_year, base_year),
        width="stretch",
    )

    index_rows = []
    for feat in loaded:
        name   = poly_name_fn(feat)
        stats  = filter_fn(poly_stats_fn(feat))
        by_yr  = {r["year"]: r for r in stats}
        base_v = _sf(by_yr.get(base_year, {}).get("median_price"))
        if not base_v:
            continue
        for y in sorted(by_yr):
            val = _sf(by_yr[y]["median_price"])
            if val:
                index_rows.append({"Area": name, "Year": y,
                                   "Median": f"£{val:,.0f}",
                                   f"Index ({base_year}=100)": f"{val / base_v * 100:.1f}"})
    if comparison_rows:
        cmp_by_yr = {r["year"]: r for r in comparison_rows}
        base_n    = _sf(cmp_by_yr.get(base_year, {}).get("median_price"))
        if base_n:
            for y in sorted(cmp_by_yr):
                val = _sf(cmp_by_yr[y]["median_price"])
                if val:
                    index_rows.append({"Area": comparison_label, "Year": y,
                                       "Median": f"£{val:,.0f}",
                                       f"Index ({base_year}=100)": f"{val / base_n * 100:.1f}"})
    show_data_table(sorted(index_rows, key=lambda r: (r["Year"], r["Area"])),
                    f"Indexed prices ({base_year} = 100)")

    if comparison_rows:
        cmp_by_yr = {r["year"]: r for r in comparison_rows}
        base_n    = _sf(cmp_by_yr.get(base_year, {}).get("median_price"))
        if base_n:
            cmp_indexed = {
                y: (_sf(cmp_by_yr[y]["median_price"]) or 0) / base_n * 100
                for y in cmp_by_yr
            }
            st.markdown(
                f"The same indexed data with the {comparison_label} growth line clamped to 100 each year. "
                f"A value above 100 means prices have grown *faster* than {comparison_label} since {base_year}; "
                f"below 100 means slower."
            )
            st.plotly_chart(
                relative_growth_chart(loaded, poly_name_fn, poly_color_fn, poly_stats_fn,
                                      comparison_label, latest_year, base_year, cmp_indexed),
                width="stretch",
            )
            rel_rows = []
            for feat in loaded:
                name  = poly_name_fn(feat)
                stats = filter_fn(poly_stats_fn(feat))
                by_yr = {r["year"]: r for r in stats}
                base_v = _sf(by_yr.get(base_year, {}).get("median_price"))
                if not base_v:
                    continue
                for y in sorted(by_yr):
                    cmp_idx  = cmp_indexed.get(y)
                    poly_val = _sf(by_yr[y]["median_price"])
                    if cmp_idx and poly_val:
                        rel_rows.append({
                            "Area": name, "Year": y,
                            f"Relative to {comparison_label}": f"{(poly_val / base_v * 100) / cmp_idx * 100:.1f}",
                        })
            show_data_table(sorted(rel_rows, key=lambda r: (r["Year"], r["Area"])),
                            f"Growth relative to {comparison_label}")
    st.divider()
