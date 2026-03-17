"""
Fetch Idaho hunt unit boundaries from the IDFG ArcGIS Open Data Portal.
Saves shapefiles and a simplified GeoJSON to data/shapefiles/.
"""
import json
import requests
import geopandas as gpd
from pathlib import Path

OUTPUT_DIR = Path(__file__).parents[2] / "data" / "shapefiles"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ArcGIS REST endpoint for Game Management Units
GMU_FEATURE_URL = (
    "https://services.arcgis.com/qnjIrwR8z5Izc0ij/arcgis/rest/services"
    "/Idaho_Hunt_Units/FeatureServer/0/query"
)

# Fallback: direct download from IDFG open data portal
GMU_DOWNLOAD_URL = (
    "https://data-idfggis.opendata.arcgis.com/datasets"
    "/893e7c1df7c14e1c9744a6beadc3b3f8_0.geojson"
)


def fetch_via_arcgis_rest() -> gpd.GeoDataFrame:
    """Query ArcGIS REST service for all hunt unit features."""
    params = {
        "where": "1=1",
        "outFields": "*",
        "f": "geojson",
        "resultRecordCount": 1000,
    }
    print("Fetching hunt units from ArcGIS REST...")
    resp = requests.get(GMU_FEATURE_URL, params=params, timeout=30)
    resp.raise_for_status()
    return gpd.read_file(resp.text)


def fetch_via_direct_download() -> gpd.GeoDataFrame:
    """Fallback: download GeoJSON directly from open data portal."""
    print("Fetching hunt units via direct download...")
    resp = requests.get(GMU_DOWNLOAD_URL, timeout=60)
    resp.raise_for_status()
    return gpd.read_file(resp.text)


def main():
    try:
        gdf = fetch_via_arcgis_rest()
    except Exception as e:
        print(f"ArcGIS REST failed ({e}), trying direct download...")
        gdf = fetch_via_direct_download()

    print(f"Fetched {len(gdf)} hunt units")
    print(f"Columns: {list(gdf.columns)}")

    # Save GeoJSON
    geojson_path = OUTPUT_DIR / "hunt_units.geojson"
    gdf.to_file(geojson_path, driver="GeoJSON")
    print(f"Saved: {geojson_path}")

    # Save simplified unit summary (no geometry) for easy inspection
    summary = gdf.drop(columns=["geometry"]).copy()
    summary_path = OUTPUT_DIR / "hunt_units_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"Saved: {summary_path}")

    return gdf


if __name__ == "__main__":
    main()
