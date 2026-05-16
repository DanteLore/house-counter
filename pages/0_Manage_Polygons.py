import uuid

import folium
import streamlit as st
from folium.plugins import Draw
from streamlit_folium import st_folium

import utils.nav as nav
from utils.area_analysis import PolygonAnalysis
from queries.bua_queries import fetch_bua_as_geojson_coords, search_buas
from utils.polygons import DEFAULT_COLOR, load_polygons, make_feature, save_polygons

THATCHAM = (51.4035, -1.2614)

st.set_page_config(page_title="Manage Polygons", layout="wide")

st.markdown("""
<style>
[data-testid="stSidebar"] { display: none; }
[data-testid="collapsedControl"] { display: none; }
div[data-testid="column"] button { padding: 0.2rem 0.4rem; }
.main .block-container { padding-top: 0.75rem; }
div[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    padding: 0.5rem 0.75rem;
    margin: 0.75rem 0;
}
</style>
""", unsafe_allow_html=True)

nav.render()
st.title("Manage Polygons")

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "polygons" not in st.session_state:
    st.session_state.polygons = load_polygons()

if "pending" not in st.session_state:
    st.session_state.pending = None

if "bua_results" not in st.session_state:
    st.session_state.bua_results = []


# ---------------------------------------------------------------------------
# Map
# ---------------------------------------------------------------------------

if st.session_state.polygons:
    all_lons, all_lats = [], []
    for feat in st.session_state.polygons:
        for lon, lat in feat["geometry"]["coordinates"][0]:
            all_lons.append(lon)
            all_lats.append(lat)
    map_centre = (
        (min(all_lats) + max(all_lats)) / 2,
        (min(all_lons) + max(all_lons)) / 2,
    )
else:
    map_centre = THATCHAM

m = folium.Map(location=map_centre, zoom_start=13, tiles="OpenStreetMap")

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
    props = feat["properties"]
    color = props.get("color", DEFAULT_COLOR)
    folium.GeoJson(
        feat,
        style_function=lambda _, c=color: {
            "color": c,
            "fillColor": c,
            "fillOpacity": 0.2,
            "weight": 2,
        },
        tooltip=folium.Tooltip(props.get("name", "")),
    ).add_to(m)

output = st_folium(
    m,
    width="stretch",
    height=500,
    returned_objects=["last_active_drawing"],
)

# ---------------------------------------------------------------------------
# Capture newly drawn polygon
# ---------------------------------------------------------------------------

drawn = output.get("last_active_drawing")
if drawn and drawn.get("geometry", {}).get("type") in ("Polygon", "Rectangle"):
    existing_coords = (
        st.session_state.pending["geometry"]["coordinates"]
        if st.session_state.pending else None
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
        name_val = pc1.text_input("Name", value="New Area", key="pending_name",
                                  label_visibility="collapsed")
        color_val = pc2.color_picker("Colour", value=DEFAULT_COLOR, key="pending_color",
                                     label_visibility="collapsed")
        if pc3.button("Save", use_container_width=True):
            feat = make_feature(name_val, color_val, coords, analysis.area_m2)
            st.session_state.polygons.append(feat)
            save_polygons(st.session_state.polygons)
            st.session_state.pending = None
            st.rerun()
        if pc4.button("Discard", use_container_width=True):
            st.session_state.pending = None
            st.rerun()

st.divider()

# ---------------------------------------------------------------------------
# BUA search
# ---------------------------------------------------------------------------

st.subheader("Import from Built-up Area boundaries")
st.markdown(
    "Search the ONS Built-up Area (BUA) dataset to import an official boundary as a polygon. "
    "Where a BUA has multiple parts, the largest is used."
)

sc1, sc2 = st.columns([4, 1])
bua_query = sc1.text_input("Search by name", placeholder="e.g. Newbury",
                            label_visibility="collapsed")
if sc2.button("Search", use_container_width=True):
    if bua_query.strip():
        with st.spinner("Searching…"):
            st.session_state.bua_results = search_buas(bua_query.strip())
    else:
        st.session_state.bua_results = []

if st.session_state.bua_results:
    existing_names = {f["properties"].get("name") for f in st.session_state.polygons}

    rh0, rh1, rh2, rh3 = st.columns([3, 2, 2, 2])
    rh0.markdown("**Name**")
    rh1.markdown("**Code**")
    rh2.markdown("**Colour**")
    rh3.markdown("**Action**")

    for row in st.session_state.bua_results:
        code = row["bua24cd"]
        name = row["bua24nm"]
        rc0, rc1, rc2, rc3 = st.columns([3, 2, 2, 2])
        rc0.markdown(name)
        rc1.markdown(f"`{code}`")
        color_pick = rc2.color_picker(
            "Colour", value=DEFAULT_COLOR, key=f"bua_color_{code}",
            label_visibility="collapsed",
        )
        already_saved = name in existing_names
        if rc3.button(
            "✓ Added" if already_saved else "＋ Add",
            key=f"bua_add_{code}",
            use_container_width=True,
            disabled=already_saved,
        ):
            with st.spinner(f"Fetching boundary for {name}…"):
                coords = fetch_bua_as_geojson_coords(code)
            if coords:
                analysis = PolygonAnalysis(coords)
                feat = make_feature(name, color_pick, coords, analysis.area_m2)
                st.session_state.polygons.append(feat)
                save_polygons(st.session_state.polygons)
                st.rerun()
            else:
                st.error(f"Could not fetch geometry for {name}.")

elif bua_query and not st.session_state.bua_results:
    st.caption("No results.")

st.divider()

# ---------------------------------------------------------------------------
# Saved polygon table
# ---------------------------------------------------------------------------

st.subheader("Saved polygons")

if not st.session_state.polygons:
    st.caption("No polygons saved yet. Draw one on the map or import a BUA above.")
else:
    with st.container(border=True):
        h0, h1, h2, h3, h4, h5 = st.columns([1, 3, 2, 2, 2, 2])
        h0.markdown("**Colour**")
        h1.markdown("**Name**")
        h2.markdown("**Area (m²)**")
        h3.markdown("**Area (ha)**")
        h4.markdown("**Residential**")
        h5.markdown("**Actions**")

        st.divider()

        for i, feat in enumerate(st.session_state.polygons):
            props = feat["properties"]
            color = props.get("color", DEFAULT_COLOR)
            name = props.get("name", "Unnamed")
            area = props.get("area_m2")
            count = props.get("uprn_count")
            poly_id = props.get("id", str(i))
            analysis = PolygonAnalysis(feat["geometry"]["coordinates"], uprn_count=count)

            c0, c1, c2, c3, c4, c5 = st.columns([1, 3, 2, 2, 2, 2])

            with c0:
                new_color = st.color_picker(
                    "Colour", value=color, key=f"color_{poly_id}",
                    label_visibility="collapsed",
                )
                if new_color != color:
                    st.session_state.polygons[i]["properties"]["color"] = new_color
                    save_polygons(st.session_state.polygons)
                    st.rerun()

            with c1:
                new_name = st.text_input(
                    "Name", value=name, key=f"name_{poly_id}",
                    label_visibility="collapsed",
                )
                if new_name != name:
                    st.session_state.polygons[i]["properties"]["name"] = new_name
                    save_polygons(st.session_state.polygons)
                    st.rerun()

            c2.markdown(f"{area:,.0f}" if area is not None else "—")
            c3.markdown(f"{analysis.area_ha:,.2f}")
            c4.markdown(f"{count:,}" if count is not None else "—")

            with c5:
                if st.button("✕ Delete", key=f"delete_{i}", use_container_width=True):
                    st.session_state.polygons.pop(i)
                    save_polygons(st.session_state.polygons)
                    st.rerun()

            st.divider()

nav.render_attributions()
