"""New build sales map: clustered markers at postcode centroids, coloured by polygon."""

import folium
import streamlit as st
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

from price_paid.charts.common import PROPERTY_TYPE_LABELS


def render_new_build_map(loaded, poly_name_fn, poly_color_fn, poly_new_build_locations_fn,
                          latest_year):
    st.markdown("**New build sales map**")
    st.markdown(
        "Each marker represents a postcode centroid where at least one new build was sold. "
        "Markers are coloured by polygon and cluster automatically at lower zoom levels. "
        "Re-fetch polygon data to populate locations."
    )

    # Collect all location rows across all polygons
    all_rows = []
    for feat in loaded:
        name  = poly_name_fn(feat)
        color = poly_color_fn(feat)
        for r in poly_new_build_locations_fn(feat) or []:
            all_rows.append({**r, "_name": name, "_color": color})

    if not all_rows:
        st.caption("No new build location data - re-fetch polygons to load.")
        return

    # Year range
    years = sorted({r["year"] for r in all_rows if r["year"] != latest_year})
    if not years:
        st.caption("No new build location data for completed years.")
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        from_year = st.selectbox("From year", years, index=0, key="nb_map_from")
    with c2:
        to_year   = st.selectbox("To year",   years, index=len(years) - 1, key="nb_map_to")
    with c3:
        type_options = ["All types"] + list(PROPERTY_TYPE_LABELS.values())
        type_filter  = st.selectbox("Property type", type_options, key="nb_map_type")

    selected_type_code = None
    if type_filter != "All types":
        selected_type_code = next(
            (k for k, v in PROPERTY_TYPE_LABELS.items() if v == type_filter), None
        )

    filtered = [
        r for r in all_rows
        if r["year"] != latest_year
        and from_year <= r["year"] <= to_year
        and (selected_type_code is None or r["property_type"] == selected_type_code)
    ]

    if not filtered:
        st.caption("No data matches the selected filters.")
        return

    centre_lat = sum(r["lat"] for r in filtered) / len(filtered)
    centre_lon = sum(r["lon"] for r in filtered) / len(filtered)

    m = folium.Map(location=(centre_lat, centre_lon), zoom_start=13, tiles="OpenStreetMap")
    cluster = MarkerCluster().add_to(m)

    for r in filtered:
        label = PROPERTY_TYPE_LABELS.get(r["property_type"], r["property_type"])
        popup  = f"{r['postcode']}<br>{r['year']} - {label}<br>{r['count']} sale{'s' if r['count'] != 1 else ''}"
        folium.CircleMarker(
            location=(r["lat"], r["lon"]),
            radius=6,
            color=r["_color"],
            fill=True,
            fill_color=r["_color"],
            fill_opacity=0.8,
            tooltip=f"{r['_name']} - {r['postcode']} ({r['year']})",
            popup=folium.Popup(popup, max_width=200),
        ).add_to(cluster)

    st_folium(m, width="stretch", height=500, returned_objects=[])
