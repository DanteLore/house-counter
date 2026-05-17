"""Stacked bar chart for property mix (type, tenure, new/established) + section renderer."""

import plotly.graph_objects as go
import streamlit as st

from price_paid.charts.common import (
    PROPERTY_TYPE_LABELS,
    PROPERTY_TYPE_COLORS,
    DURATION_LABELS,
    OLD_NEW_LABELS,
    show_data_table,
)


def mix_stacked_bar_chart(mix, dimension_key, labels, title, colors=None):
    years_set   = sorted({r["year"] for r in mix})
    totals      = {}
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
        kwargs = {"marker_color": colors[code]} if colors and code in colors else {}
        fig.add_trace(go.Bar(x=years_set, y=pcts, name=label,
                             hovertemplate="%{x}: %{y:.1f}%<extra>" + label + "</extra>",
                             **kwargs))
    fig.update_layout(
        barmode="stack", title=title,
        yaxis=dict(ticksuffix="%", range=[0, 100]),
        xaxis_title="Year",
        legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
        margin=dict(t=40, b=40), hovermode="x unified", height=300,
    )
    return fig


def render_property_mix(loaded, poly_name_fn, poly_mix_fn, filter_fn, year_range_selector_fn):
    st.subheader("Property mix")
    from_year, to_year = year_range_selector_fn("mix")
    st.markdown(
        "Breakdown of sales by property type, tenure, and new/established build  -  "
        "shown as a percentage of all sales in each year. "
        "Shifts over time reflect new development, estate regeneration, or changing demand."
    )

    for feat in loaded:
        name = poly_name_fn(feat)
        mix  = filter_fn(poly_mix_fn(feat), from_year, to_year)
        if not mix:
            st.caption(f"No mix data for {name}  -  re-fetch to load.")
            continue
        st.markdown(f"**{name}**")
        c1, c2, c3 = st.columns(3)
        c1.plotly_chart(mix_stacked_bar_chart(mix, "property_type", PROPERTY_TYPE_LABELS, "Property type", PROPERTY_TYPE_COLORS), width="stretch")
        c2.plotly_chart(mix_stacked_bar_chart(mix, "duration",      DURATION_LABELS,       "Tenure"),                              width="stretch")
        c3.plotly_chart(mix_stacked_bar_chart(mix, "old_new",       OLD_NEW_LABELS,        "New / established"),                   width="stretch")

        mix_rows  = []
        for year in sorted({r["year"] for r in mix}):
            year_rows = [r for r in mix if r["year"] == year]
            total     = sum(r["count"] for r in year_rows)
            by_type   = {}
            for r in year_rows:
                pt = PROPERTY_TYPE_LABELS.get(r.get("property_type"), r.get("property_type", "?"))
                by_type[pt] = by_type.get(pt, 0) + r["count"]
            new_builds = sum(r["count"] for r in year_rows if r.get("old_new") == "Y")
            row = {"Year": year, "Total sales": total,
                   "New build %": f"{new_builds / total * 100:.1f}%" if total else " - "}
            for code, label in PROPERTY_TYPE_LABELS.items():
                cnt = by_type.get(label, 0)
                row[label] = f"{cnt / total * 100:.1f}%" if total else " - "
            mix_rows.append(row)
        show_data_table(mix_rows, f"{name}  -  property mix")

    st.divider()
