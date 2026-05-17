"""Annual turnover and sales-volume-by-type charts + section renderers."""

import statistics

import plotly.graph_objects as go
import streamlit as st

from price_paid.charts.common import (
    PROPERTY_TYPE_LABELS,
    PROPERTY_TYPE_COLORS,
    chart_layout,
    show_data_table,
)

EW_DWELLING_STOCK = 25_400_000


# ---------------------------------------------------------------------------
# Chart builders (pure Plotly)
# ---------------------------------------------------------------------------

def turnover_chart(loaded, poly_name_fn, poly_color_fn, poly_stats_fn,
                   poly_uprn_count_fn, national_rows, latest_year):
    fig = go.Figure()
    for feat in loaded:
        uprn = poly_uprn_count_fn(feat)
        if not uprn:
            continue
        name  = poly_name_fn(feat)
        color = poly_color_fn(feat)
        stats = [r for r in poly_stats_fn(feat) if r["year"] != latest_year]
        fig.add_trace(go.Scatter(
            x=[r["year"] for r in stats],
            y=[int(r["count"]) / uprn * 100 for r in stats],
            mode="lines+markers", name=name,
            line=dict(color=color, width=2),
            hovertemplate="%{x}: %{y:.2f}%<extra>" + name + "</extra>",
        ))
    if national_rows:
        fig.add_trace(go.Scatter(
            x=[r["year"] for r in national_rows],
            y=[int(r["count"]) / EW_DWELLING_STOCK * 100 for r in national_rows],
            mode="lines", name="National (E&W)",
            line=dict(color="#888888", width=1, dash="dot"),
            hovertemplate="%{x}: %{y:.2f}%<extra>National (E&W)</extra>",
        ))
    fig.update_layout(**chart_layout(xaxis_title="Year", yaxis_title="% of address stock sold"))
    fig.update_yaxes(tickformat=".1f", ticksuffix="%")
    return fig


def volume_by_type_chart(pbt_rows, uprn, comparison_by_type, comparison_label,
                          comparison_address_count, from_year, to_year):
    rows = [
        r for r in pbt_rows
        if (from_year is None or r["year"] >= from_year)
        and (to_year   is None or r["year"] <= to_year)
    ]
    if not rows or not uprn:
        return None
    fig   = go.Figure()
    for pt in sorted({r["property_type"] for r in rows}):
        label     = PROPERTY_TYPE_LABELS.get(pt, pt)
        type_rows = sorted([r for r in rows if r["property_type"] == pt], key=lambda r: r["year"])
        pt_color  = PROPERTY_TYPE_COLORS.get(pt, "#888888")
        fig.add_trace(go.Scatter(
            x=[r["year"] for r in type_rows],
            y=[r["count"] / uprn * 100 for r in type_rows],
            mode="lines+markers", name=label, legendgroup=label,
            line=dict(color=pt_color, width=2), marker=dict(color=pt_color),
            hovertemplate="%{x}: %{y:.2f}%<extra>" + label + "</extra>",
        ))
        if comparison_address_count:
            cmp_rows = sorted(
                [(year, r) for (year, t), r in comparison_by_type.items()
                 if t == pt
                 and (from_year is None or year >= from_year)
                 and (to_year   is None or year <= to_year)],
                key=lambda x: x[0],
            )
            if cmp_rows:
                fig.add_trace(go.Scatter(
                    x=[y for y, _ in cmp_rows],
                    y=[int(r["count"]) / comparison_address_count * 100 for _, r in cmp_rows],
                    mode="lines",
                    name=f"{comparison_label}  -  {label}",
                    legendgroup=label, showlegend=False,
                    line=dict(color=pt_color, width=1, dash="dash"),
                    hovertemplate="%{x}: %{y:.2f}%<extra>" + f"{comparison_label}  -  {label}" + "</extra>",
                ))
    fig.update_layout(**chart_layout(xaxis_title="Year", yaxis_title="% of address stock sold"))
    fig.update_yaxes(tickformat=".2f", ticksuffix="%")
    return fig


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def render_annual_turnover(loaded, poly_name_fn, poly_color_fn, poly_stats_fn,
                            poly_uprn_count_fn, national_rows, latest_year, filter_fn):
    st.subheader("Annual turnover")

    notes = []
    for feat in loaded:
        uprn = poly_uprn_count_fn(feat)
        if not uprn:
            continue
        name   = poly_name_fn(feat)
        recent = [r for r in filter_fn(poly_stats_fn(feat)) if int(r["year"]) >= 2015]
        if recent:
            avg = statistics.mean(int(r["count"]) / uprn * 100 for r in recent)
            notes.append(f"**{name}** averaged **{avg:.1f}% of addresses** selling per year since 2015.")
    if national_rows:
        nat_recent = [r for r in national_rows if int(r["year"]) >= 2015]
        if nat_recent:
            avg_nat = statistics.mean(int(r["count"]) / EW_DWELLING_STOCK * 100 for r in nat_recent)
            notes.append(f"The national average was **{avg_nat:.1f}%** over the same period.")

    st.markdown(
        "Annual sales as a percentage of total address stock, compared to the national turnover rate. "
        "Low turnover may indicate high owner-occupancy or low mobility; spikes often reflect "
        "new-build completions or estate regeneration. "
        + " ".join(notes)
    )
    st.plotly_chart(
        turnover_chart(loaded, poly_name_fn, poly_color_fn, poly_stats_fn,
                       poly_uprn_count_fn, national_rows, latest_year),
        width="stretch",
    )

    rows = []
    for feat in loaded:
        uprn = poly_uprn_count_fn(feat)
        if not uprn:
            continue
        name = poly_name_fn(feat)
        for r in filter_fn(poly_stats_fn(feat)):
            pct = int(r["count"]) / uprn * 100
            rows.append({"Area": name, "Year": r["year"],
                         "Sales": r["count"], "Addresses": f"{uprn:,}",
                         "Turnover %": f"{pct:.2f}%"})
    for r in national_rows:
        pct = int(r["count"]) / EW_DWELLING_STOCK * 100
        rows.append({"Area": "National (E&W)", "Year": r["year"],
                     "Sales": r["count"], "Addresses": f"{EW_DWELLING_STOCK:,}",
                     "Turnover %": f"{pct:.2f}%"})
    show_data_table(sorted(rows, key=lambda r: (r["Year"], r["Area"])), "Annual turnover data")
    st.divider()


def render_volume_by_type(loaded, poly_name_fn, poly_price_by_type_fn, poly_uprn_count_fn,
                           comparison_by_type, comparison_label, comparison_address_count,
                           filter_fn, year_range_selector_fn):
    st.subheader("Sales volume by property type")
    from_year, to_year = year_range_selector_fn("vol")
    st.markdown(
        "Annual sales per property type expressed as a percentage of total address stock  -  "
        "normalised so polygons and the comparison baseline are directly comparable regardless of size. "
        f"Dashed lines show the {comparison_label} baseline. "
        "Requires address count from the House Counter tab."
    )

    any_data = False
    for feat in loaded:
        name = poly_name_fn(feat)
        uprn = poly_uprn_count_fn(feat)
        rows = filter_fn(poly_price_by_type_fn(feat), from_year, to_year)
        if not rows:
            st.caption(f"No volume data for **{name}**  -  re-fetch to load.")
            continue
        if not uprn:
            st.caption(f"No address count for **{name}**  -  run House Counter first.")
            continue
        any_data = True
        st.markdown(f"**{name}**")

        fig = volume_by_type_chart(rows, uprn, comparison_by_type, comparison_label,
                                    comparison_address_count, from_year, to_year)
        if fig:
            st.plotly_chart(fig, width="stretch")

        vol_rows = []
        for r in sorted(rows, key=lambda r: (r["year"], r["property_type"])):
            vol_rows.append({
                "Area": name, "Year": r["year"],
                "Type":          PROPERTY_TYPE_LABELS.get(r["property_type"], r["property_type"]),
                "Sales":         r["count"],
                "Address stock": f"{uprn:,}",
                "% of stock":    f"{r['count'] / uprn * 100:.2f}%",
            })
        if comparison_address_count:
            for (year, pt), r in sorted(comparison_by_type.items()):
                if pt not in PROPERTY_TYPE_LABELS:
                    continue
                if from_year and year < from_year:
                    continue
                if to_year and year > to_year:
                    continue
                cnt = int(r["count"])
                vol_rows.append({
                    "Area": comparison_label, "Year": year,
                    "Type":          PROPERTY_TYPE_LABELS[pt],
                    "Sales":         cnt,
                    "Address stock": f"{comparison_address_count:,}",
                    "% of stock":    f"{cnt / comparison_address_count * 100:.2f}%",
                })
        show_data_table(
            sorted(vol_rows, key=lambda r: (r["Year"], r["Type"], r["Area"])),
            f"{name}  -  sales volume by type",
        )

    if not any_data:
        st.caption("Re-fetch polygon data to load volume-by-type breakdown.")
