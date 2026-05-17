import json
import os

NATIONAL_CACHE_FILE = "national_price_stats.json"
COUNTY_CACHE_FILE   = "county_price_stats.json"


def load_national_cache():
    if os.path.exists(NATIONAL_CACHE_FILE):
        with open(NATIONAL_CACHE_FILE) as f:
            data = json.load(f)
        if isinstance(data, list):
            return {"stats": data, "cpi": None, "price_by_type": None}
        return data
    return None


def save_national_cache(stats, cpi, price_by_type=None):
    with open(NATIONAL_CACHE_FILE, "w") as f:
        json.dump({"stats": stats, "cpi": cpi, "price_by_type": price_by_type}, f)


def load_county_cache():
    """Return {"names", "stats", "by_type", "address_counts", "comparison"} from disk."""
    if os.path.exists(COUNTY_CACHE_FILE):
        with open(COUNTY_CACHE_FILE) as f:
            data = json.load(f)
        if isinstance(data, dict) and "names" in data:
            return data
        return {"names": None, "stats": data, "by_type": {}, "address_counts": {}, "comparison": None}
    return {"names": None, "stats": {}, "by_type": {}, "address_counts": {}, "comparison": None}


def save_county_cache(names, stats, comparison=None, by_type=None, address_counts=None):
    with open(COUNTY_CACHE_FILE, "w") as f:
        json.dump({
            "names":          names,
            "stats":          stats,
            "by_type":        by_type or {},
            "address_counts": address_counts or {},
            "comparison":     comparison,
        }, f)
