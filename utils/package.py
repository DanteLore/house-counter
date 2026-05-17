"""Read polygons.geojson and write a self-contained output.html."""
import json
import sys
from pathlib import Path

from utils.area_analysis import PolygonAnalysis

POLYGONS_FILE = Path("polygons.geojson")
OUTPUT_FILE = Path("output.html")

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

if not POLYGONS_FILE.exists():
    sys.exit(f"ERROR: {POLYGONS_FILE} not found")

features = json.loads(POLYGONS_FILE.read_text(encoding="utf-8")).get("features", [])
if not features:
    sys.exit("ERROR: no features in polygons.geojson")

# ---------------------------------------------------------------------------
# Compute metrics and build per-polygon data
# ---------------------------------------------------------------------------

polygons = []
all_lons, all_lats = [], []

for feat in features:
    props = feat["properties"]
    coords = feat["geometry"]["coordinates"]
    ring = coords[0]

    for lon, lat in ring:
        all_lons.append(lon)
        all_lats.append(lat)

    analysis = PolygonAnalysis(coords, uprn_count=props.get("uprn_count"))

    count = props.get("uprn_count")
    area_m2 = props.get("area_m2") or analysis.area_m2
    density = analysis.density_m2_per_address
    dph = analysis.dwellings_per_hectare

    polygons.append({
        "name": props.get("name", "Unnamed"),
        "color": props.get("color", "#3388ff"),
        "coords": ring,
        "area_m2": area_m2,
        "area_ha": analysis.area_ha,
        "count": count,
        "density": density,
        "dph": dph,
    })

center_lat = (min(all_lats) + max(all_lats)) / 2
center_lon = (min(all_lons) + max(all_lons)) / 2

# ---------------------------------------------------------------------------
# Build Leaflet JS for polygons
# ---------------------------------------------------------------------------

def fmt(value, decimals=0):
    if value is None:
        return " - "
    return f"{value:,.{decimals}f}"

polygon_js_blocks = []
for p in polygons:
    latlngs = [[lat, lon] for lon, lat in p["coords"]]
    polygon_js_blocks.append(f"""
    L.polygon({json.dumps(latlngs)}, {{
        color: {json.dumps(p["color"])},
        fillColor: {json.dumps(p["color"])},
        fillOpacity: 0.2,
        weight: 2,
        interactive: false
    }}).addTo(map);
""")

polygon_js = "\n".join(polygon_js_blocks)

# ---------------------------------------------------------------------------
# Build table rows
# ---------------------------------------------------------------------------

table_rows = []
for p in polygons:
    swatch = (
        f'<span style="display:inline-block;width:14px;height:14px;'
        f'background:{p["color"]};border-radius:3px;'
        f'vertical-align:middle;border:1px solid #0003"></span>'
    )
    table_rows.append(f"""
        <tr>
            <td>{swatch}</td>
            <td>{p["name"]}</td>
            <td>{fmt(p["area_m2"])}</td>
            <td>{fmt(p["area_ha"], 2)}</td>
            <td>{fmt(p["count"])}</td>
            <td>{fmt(p["density"])}</td>
            <td>{fmt(p["dph"], 1)}</td>
        </tr>""")

table_html = "\n".join(table_rows)

# ---------------------------------------------------------------------------
# Render HTML
# ---------------------------------------------------------------------------

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>House Counter</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: sans-serif; }}
  .container {{ width: 800px; }}
  h1 {{ padding: 0.5rem 1rem; font-size: 1.1rem; background: #f5f5f5; border-bottom: 1px solid #ddd; }}
  #map {{ width: 800px; height: 400px; }}
  .table-wrap {{ padding: 1rem; overflow-x: auto; border-top: 1px solid #ddd; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 0.85rem; }}
  th, td {{ padding: 0.4rem 0.75rem; text-align: left; border: 1px solid #e0e0e0; }}
  th {{ background: #f5f5f5; font-weight: 600; }}
  tr:nth-child(even) {{ background: #fafafa; }}
  .attribution {{ padding: 0.4rem 1rem; font-size: 0.75rem; color: #666; border-top: 1px solid #ddd; background: #fafafa; }}
  .attribution a {{ color: #444; }}
</style>
</head>
<body>
<div class="container">
<h1>House Counter</h1>
<div id="map"></div>
<div class="attribution">
  Address data: <a href="https://www.ordnancesurvey.co.uk/products/os-open-uprn" target="_blank">OS Open UPRN</a>
  &copy; Crown copyright and database rights 2025 Ordnance Survey.
  Licensed under the <a href="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/" target="_blank">Open Government Licence v3.0</a>.
</div>
<div class="table-wrap">
  <table>
    <thead>
      <tr>
        <th>Colour</th>
        <th>Name</th>
        <th>Area (m²)</th>
        <th>Area (ha)</th>
        <th>Addresses</th>
        <th>m² / address</th>
        <th>DPH</th>
      </tr>
    </thead>
    <tbody>
{table_html}
    </tbody>
  </table>
</div>
</div>
<script>
  var map = L.map('map').setView([{center_lat}, {center_lon}], 14);
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }}).addTo(map);
{polygon_js}
</script>
</body>
</html>
"""

OUTPUT_FILE.write_text(html, encoding="utf-8")
print(f"Written {OUTPUT_FILE} ({len(features)} polygon(s))")
