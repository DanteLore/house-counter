import json
import os
import uuid

POLYGONS_FILE = "polygons.geojson"
DEFAULT_COLOR = "#3388ff"


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


def make_feature(name, color, coords, area_m2):
    """Create a new GeoJSON feature dict with standard properties."""
    return {
        "type": "Feature",
        "properties": {
            "id": str(uuid.uuid4()),
            "name": name,
            "color": color,
            "area_m2": area_m2,
            "address_count": None,
            "commercial_count": None,
            "uprn_count": None,
            "uprn_points": None,
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": coords,
        },
    }
