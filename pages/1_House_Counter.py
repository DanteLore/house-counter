import folium
import streamlit as st
from folium import JsCode
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

import utils.nav as nav
from utils.area_analysis import PolygonAnalysis
from queries.uprn_queries import fetch_all_counts_for_polygon, fetch_uprns_in_polygon
from utils.polygons import DEFAULT_COLOR, load_polygons, save_polygons

THATCHAM = (51.4035, -1.2614)

st.set_page_config(page_title="House Counter", layout="wide")

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
st.title("House Counter")

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "polygons" not in st.session_state:
    st.session_state.polygons = load_polygons()

if "show_addresses" not in st.session_state:
    st.session_state.show_addresses = set()

if not st.session_state.polygons:
    st.info("No polygons saved yet. Add some on the Manage Polygons page first.")
    st.stop()

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

all_lons, all_lats = [], []
for feat in st.session_state.polygons:
    for lon, lat in feat["geometry"]["coordinates"][0]:
        all_lons.append(lon)
        all_lats.append(lat)

map_centre = (
    (min(all_lats) + max(all_lats)) / 2,
    (min(all_lons) + max(all_lons)) / 2,
) if all_lons else THATCHAM

m = folium.Map(location=map_centre, zoom_start=13, tiles="OpenStreetMap")

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

st_folium(m, width="stretch", height=600, returned_objects=[])

# ---------------------------------------------------------------------------
# Polygon table — Count / Show only
# ---------------------------------------------------------------------------

with st.container(border=True):
    h0, h1, h2, h3, h4, h5, h6, h7, h8, h9, h10 = st.columns([1, 3, 2, 2, 2, 2, 2, 2, 2, 2, 4])
    h0.markdown("**Colour**")
    h1.markdown("**Name**")
    h2.markdown("**Area (m²)**")
    h3.markdown("**Area (ha)**")
    h4.markdown("**Residential**")
    h5.markdown("**Commercial**")
    h6.markdown("**Res:Com**")
    h7.markdown("**m² / dwelling**")
    h8.markdown("**DPH**")
    h9.markdown("**All addresses**")
    h10.markdown("**Actions**")

    st.divider()

    for i, feat in enumerate(st.session_state.polygons):
        props = feat["properties"]
        color = props.get("color", DEFAULT_COLOR)
        name = props.get("name", "Unnamed")
        area = props.get("area_m2")
        residential = props.get("uprn_count")
        commercial = props.get("commercial_count")
        address_count = props.get("address_count")
        points = props.get("uprn_points")
        poly_id = props.get("id", str(i))
        showing = poly_id in st.session_state.show_addresses
        analysis = PolygonAnalysis(feat["geometry"]["coordinates"], uprn_count=residential)

        c0, c1, c2, c3, c4, c5, c6, c7, c8, c9, c10 = st.columns([1, 3, 2, 2, 2, 2, 2, 2, 2, 2, 4])

        c0.color_picker("Colour", value=color, key=f"color_{i}",
                        label_visibility="collapsed", disabled=True)
        c1.markdown(name)
        c2.markdown(f"{area:,.0f}" if area is not None else "—")
        c3.markdown(f"{analysis.area_ha:,.2f}")
        c4.markdown(f"{residential:,}" if residential is not None else "—")
        c5.markdown(f"{commercial:,}" if commercial is not None else "—")
        if residential is not None and commercial is not None and commercial > 0:
            c6.markdown(f"{residential / commercial:.1f}")
        else:
            c6.markdown("—")
        density = analysis.density_m2_per_address
        c7.markdown(f"{density:,.0f}" if density is not None else "—")
        dph = analysis.dwellings_per_hectare
        c8.markdown(f"{dph:.1f}" if dph is not None else "—")
        c9.markdown(f"{address_count:,}" if address_count is not None else "—")

        with c10:
            b1, b2 = st.columns(2)
            if b1.button("🔢 Count", key=f"count_{i}", use_container_width=True):
                with st.spinner("Querying Athena…"):
                    addr, comm, resid = fetch_all_counts_for_polygon(feat["geometry"]["coordinates"])
                st.session_state.polygons[i]["properties"]["address_count"] = addr
                st.session_state.polygons[i]["properties"]["commercial_count"] = comm
                st.session_state.polygons[i]["properties"]["uprn_count"] = resid
                save_polygons(st.session_state.polygons)
                st.rerun()

            if points is None:
                show_label = "📍 Show"
            else:
                show_label = "📍 Hide" if showing else "📍 Show"
            if b2.button(show_label, key=f"show_{i}", use_container_width=True,
                         disabled=residential is None):
                if points is None:
                    pa = PolygonAnalysis(feat["geometry"]["coordinates"])
                    with st.spinner("Fetching address locations…"):
                        pa.fetch_points(fetch_uprns_in_polygon)
                    st.session_state.polygons[i]["properties"]["uprn_points"] = pa.uprn_points
                    if address_count is None:
                        st.session_state.polygons[i]["properties"]["address_count"] = pa.uprn_count
                    st.session_state.show_addresses.add(poly_id)
                    save_polygons(st.session_state.polygons)
                elif showing:
                    st.session_state.show_addresses.discard(poly_id)
                else:
                    st.session_state.show_addresses.add(poly_id)
                st.rerun()

        st.divider()

nav.render_attributions()
