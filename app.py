import json
import os
import uuid

import folium
import streamlit as st
from folium import JsCode
from folium.plugins import Draw, MarkerCluster
from streamlit_folium import st_folium

from athena import count_uprns_in_polygon, fetch_uprns_in_polygon
from area_analysis import PolygonAnalysis
import nav

POLYGONS_FILE = "polygons.geojson"
THATCHAM = (51.4035, -1.2614)
DEFAULT_COLOR = "#3388ff"

st.set_page_config(page_title="House Counter", layout="wide")

st.markdown("""
<style>
/* Hide the sidebar toggle and sidebar entirely */
[data-testid="stSidebar"] { display: none; }
[data-testid="collapsedControl"] { display: none; }
/* Tighten up table row buttons */
div[data-testid="column"] button { padding: 0.2rem 0.4rem; }
/* Remove top padding so map sits high */
.main .block-container { padding-top: 0.75rem; }
/* Table border and margin */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    padding: 0.5rem 0.75rem;
    margin: 0.75rem 0;
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
    st.session_state.pending = None

if "show_addresses" not in st.session_state:
    st.session_state.show_addresses = set()


# ---------------------------------------------------------------------------
# Map helpers
# ---------------------------------------------------------------------------


def _cluster_icon_js(color: str) -> JsCode:
    return JsCode(f"""
function(cluster) {{
    var count = cluster.getChildCount();
    var size = count < 10 ? 30 : count < 100 ? 38 : 46;
    return new L.DivIcon({{
        html: '<div style="background:{color};opacity:0.85;border-radius:50%;'
            + 'width:' + size + 'px;height:' + size + 'px;'
            + 'display:flex;align-items:center;justify-content:center;'
            + 'color:#fff;font-weight:bold;font-size:12px;border:2px solid #fff;">'
            + count + '</div>',
        className: '',
        iconSize: [size, size],
        iconAnchor: [size/2, size/2]
    }});
}}
""")


# ---------------------------------------------------------------------------
# Map
# ---------------------------------------------------------------------------

nav.render()
st.title("House Counter")

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
    props_display = feat["properties"]
    color_display = props_display.get("color", DEFAULT_COLOR)
    folium.GeoJson(
        feat,
        style_function=lambda _, c=color_display: {
            "color": c,
            "fillColor": c,
            "fillOpacity": 0.2,
            "weight": 2,
        },
        tooltip=folium.Tooltip(props_display.get("name", "")),
    ).add_to(m)

for feat in st.session_state.polygons:
    props = feat["properties"]
    poly_id = props.get("id", "")
    color = props.get("color", DEFAULT_COLOR)

    if poly_id in st.session_state.show_addresses:
        points = props.get("uprn_points") or []
        cluster = MarkerCluster(
            options={
                "maxClusterRadius": 20,
                "disableClusteringAtZoom": 17,
                "iconCreateFunction": _cluster_icon_js(color),
            }
        ).add_to(m)
        for pt in points:
            folium.CircleMarker(
                location=[pt["lat"], pt["lon"]],
                radius=4,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.8,
                weight=0,
            ).add_to(cluster)

output = st_folium(
    m,
    width="stretch",
    height=600,
    returned_objects=["last_active_drawing"],
)

# ---------------------------------------------------------------------------
# Capture newly drawn polygon
# ---------------------------------------------------------------------------
drawn = output.get("last_active_drawing")
if drawn and drawn.get("geometry", {}).get("type") in ("Polygon", "Rectangle"):
    existing_coords = (
        st.session_state.pending["geometry"]["coordinates"]
        if st.session_state.pending
        else None
    )
    if drawn["geometry"]["coordinates"] != existing_coords:
        saved_coords = [f["geometry"]["coordinates"] for f in st.session_state.polygons]
        if drawn["geometry"]["coordinates"] not in saved_coords:
            st.session_state.pending = drawn
            st.rerun()


# ---------------------------------------------------------------------------
# Pending new polygon banner
# ---------------------------------------------------------------------------
if st.session_state.pending:
    coords = st.session_state.pending["geometry"]["coordinates"]
    analysis = PolygonAnalysis(coords)
    with st.container(border=True):
        st.caption(f"New polygon — area: {analysis.area_m2:,.0f} m²")
        pc1, pc2, pc3, pc4 = st.columns([3, 2, 1, 1])
        name_val = pc1.text_input("Name", value="New Area", key="pending_name", label_visibility="collapsed")
        color_val = pc2.color_picker("Colour", value=DEFAULT_COLOR, key="pending_color", label_visibility="collapsed")
        if pc3.button("Save", use_container_width=True):
            feature = {
                "type": "Feature",
                "properties": {
                    "id": str(uuid.uuid4()),
                    "name": name_val,
                    "color": color_val,
                    "area_m2": analysis.area_m2,
                    "uprn_count": None,
                    "uprn_points": None,
                },
                "geometry": st.session_state.pending["geometry"],
            }
            st.session_state.polygons.append(feature)
            save_polygons(st.session_state.polygons)
            st.session_state.pending = None
            st.rerun()
        if pc4.button("Discard", use_container_width=True):
            st.session_state.pending = None
            st.rerun()


# ---------------------------------------------------------------------------
# Polygon table
# ---------------------------------------------------------------------------
if not st.session_state.polygons:
    st.caption("Draw a polygon on the map to get started.")
else:
    with st.container(border=True):
        # Header row
        h0, h1, h2, h3, h4, h5, h6, h7 = st.columns([1, 3, 2, 2, 2, 2, 2, 5])
        h0.markdown("**Colour**")
        h1.markdown("**Name**")
        h2.markdown("**Area (m²)**")
        h3.markdown("**Area (ha)**")
        h4.markdown("**Addresses**")
        h5.markdown("**m² / address**")
        h6.markdown("**DPH**")
        h7.markdown("**Actions**")

        st.divider()

        for i, feat in enumerate(st.session_state.polygons):
            props = feat["properties"]
            color = props.get("color", DEFAULT_COLOR)
            name = props.get("name", "Unnamed")
            area = props.get("area_m2")
            count = props.get("uprn_count")
            points = props.get("uprn_points")
            poly_id = props.get("id", str(i))
            showing = poly_id in st.session_state.show_addresses
            analysis = PolygonAnalysis(feat["geometry"]["coordinates"], uprn_count=count)

            c0, c1, c2, c3, c4, c5, c6, c7 = st.columns([1, 3, 2, 2, 2, 2, 2, 5])

            with c0:
                new_color = st.color_picker("Colour", value=color, key=f"color_{i}", label_visibility="collapsed")
                if new_color != color:
                    st.session_state.polygons[i]["properties"]["color"] = new_color
                    save_polygons(st.session_state.polygons)
                    st.rerun()

            with c1:
                new_name = st.text_input("Name", value=name, key=f"name_{i}", label_visibility="collapsed")
                if new_name != name:
                    st.session_state.polygons[i]["properties"]["name"] = new_name
                    save_polygons(st.session_state.polygons)
                    st.rerun()

            c2.markdown(f"{area:,.0f}" if area is not None else "—")
            c3.markdown(f"{analysis.area_ha:,.2f}")
            c4.markdown(f"{count:,}" if count is not None else "—")
            density = analysis.density_m2_per_address
            c5.markdown(f"{density:,.0f}" if density is not None else "—")
            dph = analysis.dwellings_per_hectare
            c6.markdown(f"{dph:.1f}" if dph is not None else "—")

            with c7:
                b1, b2, b3 = st.columns(3)
                if b1.button("🔢 Count", key=f"count_{i}", use_container_width=True):
                    pa = PolygonAnalysis(feat["geometry"]["coordinates"])
                    with st.spinner("Querying Athena…"):
                        pa.fetch_count(count_uprns_in_polygon)
                    st.session_state.polygons[i]["properties"]["uprn_count"] = pa.uprn_count
                    save_polygons(st.session_state.polygons)
                    st.rerun()

                if points is None:
                    show_label = "📍 Show"
                else:
                    show_label = "📍 Hide" if showing else "📍 Show"
                if b2.button(show_label, key=f"show_{i}", use_container_width=True):
                    if points is None:
                        pa = PolygonAnalysis(feat["geometry"]["coordinates"])
                        with st.spinner("Fetching address locations…"):
                            pa.fetch_points(fetch_uprns_in_polygon)
                        st.session_state.polygons[i]["properties"]["uprn_points"] = pa.uprn_points
                        st.session_state.polygons[i]["properties"]["uprn_count"] = pa.uprn_count
                        st.session_state.show_addresses.add(poly_id)
                        save_polygons(st.session_state.polygons)
                    elif showing:
                        st.session_state.show_addresses.discard(poly_id)
                    else:
                        st.session_state.show_addresses.add(poly_id)
                    st.rerun()

                if b3.button("✕ Delete", key=f"delete_{i}", use_container_width=True):
                    st.session_state.polygons.pop(i)
                    st.session_state.show_addresses.discard(poly_id)
                    save_polygons(st.session_state.polygons)
                    st.rerun()

            st.divider()
