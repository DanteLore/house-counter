import json
import os
import uuid

import folium
import streamlit as st
from folium.plugins import Draw
from streamlit_folium import st_folium

from athena import count_uprns_in_polygon
from geo import polygon_area_m2

POLYGONS_FILE = "polygons.geojson"
THATCHAM = (51.4035, -1.2614)
DEFAULT_COLOR = "#3388ff"

st.set_page_config(page_title="House Counter", layout="wide")


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def load_polygons():
    if not os.path.exists(POLYGONS_FILE):
        return []
    with open(POLYGONS_FILE) as f:
        fc = json.load(f)
    return fc.get("features", [])


def save_polygons(features):
    fc = {"type": "FeatureCollection", "features": features}
    with open(POLYGONS_FILE, "w") as f:
        json.dump(fc, f, indent=2)


# ---------------------------------------------------------------------------
# Session state bootstrap
# ---------------------------------------------------------------------------

if "polygons" not in st.session_state:
    st.session_state.polygons = load_polygons()

if "pending" not in st.session_state:
    st.session_state.pending = None  # GeoJSON Feature dict


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("House Counter")

    # --- Pending drawn polygon ---
    if st.session_state.pending:
        st.subheader("New polygon")
        coords = st.session_state.pending["geometry"]["coordinates"]
        area = polygon_area_m2(coords)
        st.caption(f"Area: {area:,.0f} m²")

        name = st.text_input("Name", value="New Area", key="pending_name")
        color = st.color_picker("Colour", value=DEFAULT_COLOR, key="pending_color")

        col_save, col_discard = st.columns(2)
        with col_save:
            if st.button("Save", use_container_width=True):
                feature = {
                    "type": "Feature",
                    "properties": {
                        "id": str(uuid.uuid4()),
                        "name": name,
                        "color": color,
                        "area_m2": area,
                        "uprn_count": None,
                    },
                    "geometry": st.session_state.pending["geometry"],
                }
                st.session_state.polygons.append(feature)
                save_polygons(st.session_state.polygons)
                st.session_state.pending = None
                st.rerun()
        with col_discard:
            if st.button("Discard", use_container_width=True):
                st.session_state.pending = None
                st.rerun()

        st.divider()

    # --- Saved polygons ---
    st.subheader("Saved areas")
    if not st.session_state.polygons:
        st.caption("Draw a polygon on the map to get started.")
    else:
        for i, feat in enumerate(st.session_state.polygons):
            props = feat["properties"]
            color = props.get("color", DEFAULT_COLOR)
            name = props.get("name", "Unnamed")
            area = props.get("area_m2")
            count = props.get("uprn_count")

            with st.expander(f"{'⬛' } {name}", expanded=False):
                # colour swatch via markdown
                st.markdown(
                    f'<div style="display:inline-block;width:16px;height:16px;'
                    f'background:{color};border-radius:3px;margin-right:6px;'
                    f'vertical-align:middle"></div> <b>{name}</b>',
                    unsafe_allow_html=True,
                )
                if area is not None:
                    st.caption(f"Area: {area:,.0f} m²")
                if count is not None:
                    col_a, col_b = st.columns(2)
                    col_a.metric("Addresses", f"{count:,}")
                    if count > 0 and area:
                        col_b.metric("m² per address", f"{area / count:,.0f}")
                else:
                    st.caption("Address count not yet queried.")

                new_name = st.text_input("Rename", value=name, key=f"name_{i}")
                new_color = st.color_picker("Colour", value=color, key=f"color_{i}")

                col_update, col_count, col_delete = st.columns(3)
                with col_update:
                    if st.button("Update", key=f"update_{i}", use_container_width=True):
                        st.session_state.polygons[i]["properties"]["name"] = new_name
                        st.session_state.polygons[i]["properties"]["color"] = new_color
                        save_polygons(st.session_state.polygons)
                        st.rerun()
                with col_count:
                    if st.button("Count", key=f"count_{i}", use_container_width=True):
                        coords = feat["geometry"]["coordinates"]
                        with st.spinner("Querying Athena…"):
                            n = count_uprns_in_polygon(coords)
                        st.session_state.polygons[i]["properties"]["uprn_count"] = n
                        save_polygons(st.session_state.polygons)
                        st.rerun()
                with col_delete:
                    if st.button("Delete", key=f"delete_{i}", use_container_width=True):
                        st.session_state.polygons.pop(i)
                        save_polygons(st.session_state.polygons)
                        st.rerun()


# ---------------------------------------------------------------------------
# Map
# ---------------------------------------------------------------------------

m = folium.Map(location=THATCHAM, zoom_start=13, tiles="OpenStreetMap")

Draw(
    export=False,
    draw_options={
        "polygon": True,
        "polyline": False,
        "rectangle": True,
        "circle": False,
        "marker": False,
        "circlemarker": False,
    },
    edit_options={"edit": False},
).add_to(m)

for feat in st.session_state.polygons:
    color = feat["properties"].get("color", DEFAULT_COLOR)
    folium.GeoJson(
        feat,
        style_function=lambda _, c=color: {
            "color": c,
            "fillColor": c,
            "fillOpacity": 0.2,
            "weight": 2,
        },
        tooltip=feat["properties"].get("name", ""),
    ).add_to(m)

output = st_folium(m, use_container_width=True, height=750, returned_objects=["last_active_drawing"])

# Capture newly drawn polygon
drawn = output.get("last_active_drawing")
if drawn and drawn.get("geometry", {}).get("type") in ("Polygon", "Rectangle"):
    existing_coords = (
        st.session_state.pending["geometry"]["coordinates"]
        if st.session_state.pending
        else None
    )
    if drawn["geometry"]["coordinates"] != existing_coords:
        st.session_state.pending = drawn
        st.rerun()
