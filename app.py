import json
import os
import uuid

import folium
import streamlit as st
from folium.plugins import Draw
from streamlit_folium import st_folium

from athena import count_uprns_in_polygon
from area_analysis import PolygonAnalysis

POLYGONS_FILE = "polygons.geojson"
THATCHAM = (51.4035, -1.2614)
DEFAULT_COLOR = "#3388ff"

st.set_page_config(page_title="House Counter", layout="wide")

st.markdown("""
<style>
section[data-testid="stSidebar"] button[data-testid="baseButton-secondary"] p,
section[data-testid="stSidebar"] button[data-testid="baseButton-secondary"] ol,
section[data-testid="stSidebar"] button[data-testid="baseButton-secondary"] ul,
section[data-testid="stSidebar"] button[data-testid="baseButton-secondary"] dl {
    font-size: 0.65rem !important;
    white-space: nowrap !important;
    margin: 0 !important;
    line-height: 1 !important;
}
</style>
""", unsafe_allow_html=True)


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
        analysis = PolygonAnalysis(coords)
        st.caption(f"Area: {analysis.area_m2:,.0f} m²")

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
                        "area_m2": analysis.area_m2,
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

            expander_index = i + 1
            st.markdown(
                f"""<style>
                section[data-testid="stSidebar"]
                details:nth-of-type({expander_index}) summary span p::before {{
                    content: "⬛";
                    color: {color};
                    margin-right: 4px;
                    font-size: 0.7em;
                    vertical-align: middle;
                }}
                </style>""",
                unsafe_allow_html=True,
            )
            col_exp, col_x = st.columns([0.85, 0.15])
            with col_x:
                if st.button("✕", key=f"delete_{i}", help=f"Delete {name}"):
                    st.session_state.polygons.pop(i)
                    save_polygons(st.session_state.polygons)
                    st.rerun()
            with col_exp:
                with st.expander(name, expanded=False):
                    st.markdown(
                        f'<span style="display:inline-block;width:12px;height:12px;'
                        f'background:{color};border-radius:2px;margin-right:6px;'
                        f'vertical-align:middle"></span><b>{name}</b>',
                        unsafe_allow_html=True,
                    )
                    analysis = PolygonAnalysis(feat["geometry"]["coordinates"], uprn_count=count)
                    if area is not None:
                        st.caption(f"Area: {area:,.0f} m²")
                    if count is not None:
                        col_a, col_b = st.columns(2)
                        col_a.metric("Addresses", f"{count:,}")
                        density = analysis.density_m2_per_address
                        if density is not None:
                            col_b.metric("m² per address", f"{density:,.0f}")
                    else:
                        st.caption("Address count not yet queried.")

                    def make_save_callback(idx, name_key, color_key):
                        def callback():
                            st.session_state.polygons[idx]["properties"]["name"] = st.session_state[name_key]
                            st.session_state.polygons[idx]["properties"]["color"] = st.session_state[color_key]
                            save_polygons(st.session_state.polygons)
                        return callback

                    st.text_input("Name", value=name, key=f"name_{i}",
                                  on_change=make_save_callback(i, f"name_{i}", f"color_{i}"))
                    st.color_picker("Colour", value=color, key=f"color_{i}",
                                    on_change=make_save_callback(i, f"name_{i}", f"color_{i}"))

                    if st.button("🔢 Count addresses", key=f"count_{i}", use_container_width=True):
                        pa = PolygonAnalysis(feat["geometry"]["coordinates"])
                        with st.spinner("Querying Athena…"):
                            pa.fetch_count(count_uprns_in_polygon)
                        st.session_state.polygons[i]["properties"]["uprn_count"] = pa.uprn_count
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
