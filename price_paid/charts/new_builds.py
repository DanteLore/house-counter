"""New build sales charts + section renderer."""

import plotly.graph_objects as go
import streamlit as st

from price_paid.charts.common import (
    PROPERTY_TYPE_LABELS,
    PROPERTY_TYPE_COLORS,
    chart_layout,
    show_data_table,
)


def _build_new_build_series(mix_rows, latest_year, from_year, to_year):
    """Return {year: new_count} and {year: total_count} dicts, filtered to range."""
    new_by_year   = {}
    total_by_year = {}
    for r in mix_rows:
        y = r["year"]
        if y == latest_year:
            continue
        if from_year and y < from_year:
            continue
        if to_year and y > to_year:
            continue
        total_by_year[y] = total_by_year.get(y, 0) + r["count"]
        if r.get("old_new") == "Y":
            new_by_year[y] = new_by_year.get(y, 0) + r["count"]
    return new_by_year, total_by_year


def new_builds_absolute_chart(loaded, poly_name_fn, poly_color_fn, poly_mix_fn,
                               latest_year, from_year, to_year):
    """Annual new build sales count per polygon."""
    fig = go.Figure()
    for feat in loaded:
        name  = poly_name_fn(feat)
        color = poly_color_fn(feat)
        new_by_year, total_by_year = _build_new_build_series(poly_mix_fn(feat), latest_year, from_year, to_year)
        if not total_by_year:
            continue
        years = sorted(total_by_year)
        fig.add_trace(go.Scatter(
            x=years, y=[new_by_year.get(y, 0) for y in years],
            mode="lines+markers", name=name,
            line=dict(color=color, width=2),
            hovertemplate="%{x}: %{y:,} new build sales<extra>" + name + "</extra>",
        ))
    fig.update_layout(**chart_layout(xaxis_title="Year", yaxis_title="New build sales"))
    return fig


def new_builds_pct_chart(loaded, poly_name_fn, poly_color_fn, poly_mix_fn,
                          poly_uprn_count_fn, latest_year, from_year, to_year):
    """Annual new build sales as % of total address stock."""
    fig = go.Figure()
    for feat in loaded:
        uprn = poly_uprn_count_fn(feat)
        if not uprn:
            continue
        name  = poly_name_fn(feat)
        color = poly_color_fn(feat)
        new_by_year, total_by_year = _build_new_build_series(poly_mix_fn(feat), latest_year, from_year, to_year)
        if not total_by_year:
            continue
        years = sorted(total_by_year)
        fig.add_trace(go.Scatter(
            x=years, y=[new_by_year.get(y, 0) / uprn * 100 for y in years],
            mode="lines+markers", name=name,
            line=dict(color=color, width=2),
            hovertemplate="%{x}: %{y:.2f}% of stock<extra>" + name + "</extra>",
        ))
    fig.update_layout(**chart_layout(xaxis_title="Year", yaxis_title="New build sales as % of address stock"))
    fig.update_yaxes(tickformat=".2f", ticksuffix="%")
    return fig


def new_builds_by_type_chart(mix_rows, name, latest_year, from_year, to_year, all_years=None):
    """Per-polygon stacked bar: new build sales broken down by property type."""
    # Collect new build counts by (year, property_type)
    by_year_type = {}
    for r in mix_rows:
        y = r["year"]
        if y == latest_year:
            continue
        if from_year and y < from_year:
            continue
        if to_year and y > to_year:
            continue
        if r.get("old_new") != "Y":
            continue
        pt = r.get("property_type", "?")
        if pt not in PROPERTY_TYPE_LABELS:
            continue
        key = (y, pt)
        by_year_type[key] = by_year_type.get(key, 0) + r["count"]

    if not by_year_type:
        return None

    years = sorted(all_years if all_years else {y for y, _ in by_year_type})
    fig   = go.Figure()
    for pt, label in PROPERTY_TYPE_LABELS.items():
        counts = [by_year_type.get((y, pt), 0) for y in years]
        if not any(counts):
            continue
        color = PROPERTY_TYPE_COLORS.get(pt, "#888888")
        fig.add_trace(go.Bar(
            x=years, y=counts, name=label,
            marker_color=color,
            hovertemplate="%{x}: %{y:,} new build sales<extra>" + label + "</extra>",
        ))
    fig.update_layout(**chart_layout(
        xaxis_title="Year", yaxis_title="New build sales",
        barmode="stack", title=name,
    ))
    return fig


def render_new_builds(loaded, poly_name_fn, poly_color_fn, poly_mix_fn, poly_uprn_count_fn,
                       latest_year, filter_fn, year_range_selector_fn):
    st.subheader("New build sales")
    from_year, to_year = year_range_selector_fn("nb")
    st.markdown(
        "Annual sales of newly built properties. "
        "The absolute chart shows raw transaction counts; the second chart normalises by total address "
        "stock so areas of different sizes are directly comparable. "
        "Spikes typically indicate a new estate completing. "
        "A persistently high new-build share can inflate overall turnover figures and push the median "
        "price upward, so it is worth reading alongside the property mix and turnover sections."
    )

    missing = [poly_name_fn(f) for f in loaded if not poly_mix_fn(f)]
    if missing:
        st.caption(f"No mix data for: {', '.join(missing)} - re-fetch to load.")

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(
            new_builds_absolute_chart(loaded, poly_name_fn, poly_color_fn, poly_mix_fn,
                                       latest_year, from_year, to_year),
            width="stretch",
        )
    with c2:
        no_stock = [poly_name_fn(f) for f in loaded if not poly_uprn_count_fn(f)]
        if no_stock:
            st.caption(f"No address count for: {', '.join(no_stock)} - run House Counter first.")
        st.plotly_chart(
            new_builds_pct_chart(loaded, poly_name_fn, poly_color_fn, poly_mix_fn,
                                  poly_uprn_count_fn, latest_year, from_year, to_year),
            width="stretch",
        )

    # Data table for the two comparison charts above
    overview_rows = []
    for feat in loaded:
        name = poly_name_fn(feat)
        uprn = poly_uprn_count_fn(feat)
        new_by_year, total_by_year = _build_new_build_series(
            poly_mix_fn(feat), latest_year, from_year, to_year
        )
        for y in sorted(total_by_year):
            new_cnt   = new_by_year.get(y, 0)
            total_cnt = total_by_year.get(y, 0)
            row = {
                "Area":            name,
                "Year":            y,
                "New build sales": new_cnt,
                "Total sales":     total_cnt,
                "New build %":     f"{new_cnt / total_cnt * 100:.1f}%" if total_cnt else "-",
            }
            if uprn:
                row["Address stock"] = f"{uprn:,}"
                row["% of stock"]    = f"{new_cnt / uprn * 100:.2f}%"
            overview_rows.append(row)
    show_data_table(
        sorted(overview_rows, key=lambda r: (r["Year"], r["Area"])),
        "New build sales data",
    )

    # Per-polygon breakdown by property type
    # Compute shared year range across all polygons so x-axes are aligned
    shared_years = set()
    for feat in loaded:
        for r in poly_mix_fn(feat) or []:
            y = r["year"]
            if y == latest_year:
                continue
            if from_year and y < from_year:
                continue
            if to_year and y > to_year:
                continue
            if r.get("old_new") == "Y" and r.get("property_type") in PROPERTY_TYPE_LABELS:
                shared_years.add(y)

    st.markdown("**New build sales by property type**")
    for feat in loaded:
        name = poly_name_fn(feat)
        mix  = poly_mix_fn(feat)
        if not mix:
            continue
        fig = new_builds_by_type_chart(mix, name, latest_year, from_year, to_year, shared_years)
        if not fig:
            continue
        st.markdown(f"**{name}**")
        st.plotly_chart(fig, width="stretch")

        # Per-polygon table: new build sales by year and property type
        by_year_type = {}
        for r in mix:
            y = r["year"]
            if y == latest_year:
                continue
            if from_year and y < from_year:
                continue
            if to_year and y > to_year:
                continue
            if r.get("old_new") != "Y":
                continue
            pt = r.get("property_type")
            if pt not in PROPERTY_TYPE_LABELS:
                continue
            by_year_type[(y, pt)] = by_year_type.get((y, pt), 0) + r["count"]

        type_rows = []
        for y in sorted(shared_years):
            for pt, label in PROPERTY_TYPE_LABELS.items():
                cnt = by_year_type.get((y, pt), 0)
                type_rows.append({"Year": y, "Type": label, "New build sales": cnt})
        show_data_table(type_rows, f"{name} - new build sales by type")

    st.divider()
