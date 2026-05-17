"""Price trend by property type chart + section renderer."""

import plotly.graph_objects as go
import streamlit as st

from price_paid.charts.common import (
    PROPERTY_TYPE_LABELS,
    PROPERTY_TYPE_COLORS,
    chart_layout,
    hex_to_rgba,
    show_data_table,
)
from queries.price_paid_queries import deflate_prices


def _sf(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def price_by_type_chart(pbt_rows, comparison_by_type, comparison_label,
                        from_year, to_year, adjust, cpi, cpi_base_year, price_axis_label):
    """Median price trend per property type with P25-P75 band and comparison dashes."""
    rows = [
        r for r in pbt_rows
        if (from_year is None or r["year"] >= from_year)
        and (to_year   is None or r["year"] <= to_year)
    ]
    if not rows:
        return None

    types = sorted({r["property_type"] for r in rows})
    fig   = go.Figure()

    for pt in types:
        label   = PROPERTY_TYPE_LABELS.get(pt, pt)
        pt_rows = sorted([r for r in rows if r["property_type"] == pt], key=lambda r: r["year"])
        if not pt_rows:
            continue
        years  = [r["year"] for r in pt_rows]
        counts = [r["count"] for r in pt_rows]
        color  = PROPERTY_TYPE_COLORS.get(pt, "#888888")

        if adjust and cpi:
            medians = [deflate_prices([(r["year"], r["median_price"])], cpi, cpi_base_year)[0][1] for r in pt_rows]
            p25s    = [deflate_prices([(r["year"], r["p25_price"])],    cpi, cpi_base_year)[0][1] for r in pt_rows]
            p75s    = [deflate_prices([(r["year"], r["p75_price"])],    cpi, cpi_base_year)[0][1] for r in pt_rows]
        else:
            medians = [_sf(r["median_price"]) for r in pt_rows]
            p25s    = [_sf(r["p25_price"])    for r in pt_rows]
            p75s    = [_sf(r["p75_price"])    for r in pt_rows]

        fig.add_trace(go.Scatter(
            x=years, y=p25s, mode="lines", name=label, legendgroup=label, showlegend=False,
            line=dict(color=color, width=0),
            hovertemplate="%{x}: £%{y:,.0f} (P25)<extra>" + label + "</extra>",
        ))
        fig.add_trace(go.Scatter(
            x=years, y=p75s, mode="lines", name=f"{label} (P25–P75)", legendgroup=label, showlegend=True,
            fill="tonexty", fillcolor=hex_to_rgba(color, 0.15), line=dict(color=color, width=0),
            hovertemplate="%{x}: £%{y:,.0f} (P75)<extra>" + label + "</extra>",
        ))
        fig.add_trace(go.Scatter(
            x=years, y=medians, mode="lines+markers", name=label, legendgroup=label, showlegend=True,
            line=dict(color=color, width=2), customdata=counts,
            hovertemplate="%{x}: £%{y:,.0f} median (%{customdata} sales)<extra>" + label + "</extra>",
        ))

        cmp_pt_rows = sorted(
            [r for (y, t), r in comparison_by_type.items()
             if t == pt
             and (from_year is None or y >= from_year)
             and (to_year   is None or y <= to_year)],
            key=lambda r: r["year"],
        )
        if cmp_pt_rows:
            if adjust and cpi:
                cmp_medians = [deflate_prices([(r["year"], r["median_price"])], cpi, cpi_base_year)[0][1]
                               for r in cmp_pt_rows]
            else:
                cmp_medians = [_sf(r["median_price"]) for r in cmp_pt_rows]
            fig.add_trace(go.Scatter(
                x=[r["year"] for r in cmp_pt_rows], y=cmp_medians,
                mode="lines",
                name=f"{comparison_label} {label}",
                legendgroup=label, showlegend=False,
                line=dict(color=color, width=1, dash="dash"),
                hovertemplate="%{x}: £%{y:,.0f}<extra>" + f"{comparison_label} {label}" + "</extra>",
            ))

    fig.update_layout(**chart_layout(yaxis_title=price_axis_label, xaxis_title="Year"))
    return fig


def render_price_by_type(loaded, poly_name_fn, poly_price_by_type_fn,
                          comparison_by_type, comparison_label,
                          cpi, cpi_base_year, filter_fn,
                          warn_if_cpi_missing_fn, year_range_selector_fn,
                          price_axis_label_fn):
    st.subheader("Price by property type")
    adjust = st.toggle("Adjust for inflation (current £)", key="adj_type", value=False)
    if adjust:
        warn_if_cpi_missing_fn()
    from_year, to_year = year_range_selector_fn("type")
    st.markdown(
        "Median sale price over time, split by property type. "
        "This separates the mix effect from genuine price movements  -  "
        "if flats become a larger share of sales, the overall median can fall even if every property type is rising. "
        "The shaded band shows the P25–P75 range (middle 50% of sales for that type in that year)."
    )

    any_data = False
    for feat in loaded:
        name = poly_name_fn(feat)
        pbt  = filter_fn(poly_price_by_type_fn(feat), from_year, to_year)
        if not pbt:
            need_fetch = not poly_price_by_type_fn(feat)
            st.caption(f"No price-by-type data for **{name}**  -  {'re-fetch to load' if need_fetch else 'no data in range'}.")
            continue
        any_data = True
        st.markdown(f"**{name}**")

        types_in_data = sorted({r["property_type"] for r in pbt if r["property_type"] in PROPERTY_TYPE_LABELS})
        latest_yr     = max((r["year"] for r in pbt), default=None)
        if latest_yr:
            latest_by_type = {r["property_type"]: r for r in pbt
                              if r["year"] == latest_yr and r["property_type"] in types_in_data}
            if latest_by_type:
                parts = [
                    f"{PROPERTY_TYPE_LABELS.get(pt, pt)}: £{row['median_price']:,.0f} ({row['count']} sales)"
                    for pt, row in sorted(latest_by_type.items(), key=lambda kv: kv[1]["median_price"], reverse=True)
                ]
                st.caption(f"Median prices in {latest_yr}: " + " · ".join(parts))
                det_row  = latest_by_type.get("D")
                flat_row = latest_by_type.get("F")
                if det_row and flat_row:
                    ratio = det_row["median_price"] / flat_row["median_price"]
                    st.caption(
                        f"Detached homes sell for **{ratio:.1f}×** the median flat price in {latest_yr}. "
                        f"Years with more detached sales (and fewer flats) will have a higher overall median, "
                        f"even if no individual type has changed."
                    )

        fig = price_by_type_chart(pbt, comparison_by_type, comparison_label,
                                   from_year, to_year, adjust, cpi, cpi_base_year,
                                   price_axis_label_fn(adjust))
        if fig:
            st.plotly_chart(fig, width="stretch")

        table_rows = []
        for r in sorted(pbt, key=lambda r: (r["year"], r["property_type"])):
            table_rows.append({
                "Area": name, "Year": r["year"],
                "Type":   PROPERTY_TYPE_LABELS.get(r["property_type"], r["property_type"]),
                "Sales":  r["count"],
                "Median": f"£{r['median_price']:,.0f}",
                "P25":    f"£{r['p25_price']:,.0f}",
                "P75":    f"£{r['p75_price']:,.0f}",
            })
        for (year, pt), r in sorted(comparison_by_type.items()):
            if pt not in PROPERTY_TYPE_LABELS:
                continue
            if from_year and year < from_year:
                continue
            if to_year and year > to_year:
                continue
            table_rows.append({
                "Area": comparison_label, "Year": year,
                "Type":   PROPERTY_TYPE_LABELS[pt],
                "Sales":  r["count"],
                "Median": f"£{_sf(r['median_price']):,.0f}",
                "P25":    f"£{_sf(r['p25_price']):,.0f}",
                "P75":    f"£{_sf(r['p75_price']):,.0f}",
            })
        show_data_table(
            sorted(table_rows, key=lambda r: (r["Year"], r["Type"], r["Area"])),
            f"{name}  -  price by type vs {comparison_label}",
        )

    if not any_data:
        st.caption("Re-fetch polygon data to load price-by-type breakdown.")
    st.divider()
