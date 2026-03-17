"""
Fetch historical daily weather for Panhandle GMU centroids via Open-Meteo Archive API.

Open-Meteo provides free historical weather data (no API key required).
Archive endpoint: https://archive-api.open-meteo.com/v1/archive

We pull daily data for each GMU centroid during hunting season months (Aug-Dec)
for all years in our harvest dataset (2003-2024).

Variables fetched:
  - temperature_2m_max, temperature_2m_min, temperature_2m_mean
  - precipitation_sum, snowfall_sum, snow_depth_max (ERA5 reanalysis)
  - wind_speed_10m_max, wind_gusts_10m_max
  - pressure_msl_mean (mean sea level pressure)
  - sunrise, sunset (for day length)

Usage:
    python -m src.ingest.fetch_weather
"""

import time
from pathlib import Path
from typing import Dict, List, Tuple

import geopandas as gpd
import pandas as pd
import requests

from src.ingest.config import PANHANDLE_UNITS, YEAR_END, YEAR_START

OUTPUT_DIR = Path(__file__).parents[2] / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Daily weather variables to fetch
DAILY_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "precipitation_sum",
    "snowfall_sum",
    "snow_depth_max",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
    "pressure_msl_mean",
    "daylight_duration",
]

# Hunting season months (Aug 30 - Dec 31 covers all Idaho general seasons)
SEASON_START_MONTH = 8
SEASON_START_DAY = 15
SEASON_END_MONTH = 12
SEASON_END_DAY = 31

HEADERS = {
    "User-Agent": "Tagout/1.0 (hunting prediction research)",
}


def get_gmu_centroids() -> Dict[str, Tuple[float, float]]:
    """
    Compute centroids for Panhandle GMUs from the GeoJSON file.
    Returns {unit_name: (lat, lon)}.
    """
    geojson_path = Path(__file__).parents[2] / "data" / "shapefiles" / "hunt_units.geojson"
    if not geojson_path.exists():
        raise FileNotFoundError(
            f"No hunt_units.geojson at {geojson_path}. Run fetch_units.py first."
        )

    gdf = gpd.read_file(geojson_path)
    panhandle = gdf[gdf["NAME"].isin(PANHANDLE_UNITS)].copy()
    panhandle = panhandle.to_crs(epsg=4326)
    panhandle["centroid"] = panhandle.geometry.centroid

    centroids = {}
    for _, row in panhandle.iterrows():
        c = row["centroid"]
        centroids[row["NAME"]] = (round(c.y, 4), round(c.x, 4))

    return centroids


def fetch_weather_for_unit(
    session: requests.Session,
    unit: str,
    lat: float,
    lon: float,
    start_year: int,
    end_year: int,
) -> pd.DataFrame:
    """
    Fetch hunting-season weather for one GMU centroid across all years.
    Open-Meteo allows large date ranges in a single request.
    """
    start_date = f"{start_year}-{SEASON_START_MONTH:02d}-{SEASON_START_DAY:02d}"
    end_date = f"{end_year}-{SEASON_END_MONTH:02d}-{SEASON_END_DAY:02d}"

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": ",".join(DAILY_VARS),
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "America/Boise",
    }

    resp = session.get(ARCHIVE_URL, params=params, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    if "daily" not in data:
        print(f"    No daily data returned for unit {unit}")
        return pd.DataFrame()

    daily = data["daily"]
    df = pd.DataFrame(daily)
    df["date"] = pd.to_datetime(df["time"])
    df = df.drop(columns=["time"])

    # Filter to hunting season months only (Aug 15 - Dec 31 each year)
    df["month"] = df["date"].dt.month
    df["day"] = df["date"].dt.day
    mask = (
        ((df["month"] == SEASON_START_MONTH) & (df["day"] >= SEASON_START_DAY))
        | (df["month"] > SEASON_START_MONTH)
    ) & (df["month"] <= SEASON_END_MONTH)
    df = df[mask].copy()
    df = df.drop(columns=["month", "day"])

    df["hunt_unit"] = unit
    df["season_year"] = df["date"].dt.year

    return df


def main(
    start_year: int = YEAR_START,
    end_year: int = YEAR_END,
):
    # Clamp to data availability (Open-Meteo ERA5 starts ~1940, but 2003 is our harvest start)
    start_year = max(start_year, 2003)

    print("Computing GMU centroids...")
    centroids = get_gmu_centroids()
    print(f"  {len(centroids)} Panhandle units: {sorted(centroids.keys())}")
    for unit, (lat, lon) in sorted(centroids.items()):
        print(f"    Unit {unit:>3s}: {lat:.4f}°N, {lon:.4f}°W")

    # Load existing data to skip already-fetched units
    out_path = OUTPUT_DIR / "weather_panhandle.csv"
    existing_units = set()
    all_frames = []
    if out_path.exists():
        existing = pd.read_csv(out_path)
        existing_units = set(existing["hunt_unit"].astype(str).unique())
        all_frames.append(existing)
        print(f"  Already have data for units: {sorted(existing_units)}")

    session = requests.Session()

    for unit, (lat, lon) in sorted(centroids.items()):
        if unit in existing_units:
            print(f"\nSkipping Unit {unit} (already fetched)")
            continue
        print(f"\nFetching weather for Unit {unit} ({lat}, {lon})...")
        for attempt in range(3):
            try:
                df = fetch_weather_for_unit(session, unit, lat, lon, start_year, end_year)
                if not df.empty:
                    all_frames.append(df)
                    print(f"  {len(df)} daily records")
                else:
                    print(f"  No data returned")
                break
            except requests.HTTPError as e:
                if "429" in str(e) and attempt < 2:
                    wait = 10 * (attempt + 1)
                    print(f"  Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                print(f"  HTTP error: {e}")
            except Exception as e:
                print(f"  Failed: {e}")
                break
        time.sleep(2)  # polite rate limit between units

    if not all_frames:
        print("\nNo weather data collected.")
        return

    weather = pd.concat(all_frames, ignore_index=True)
    weather["date"] = pd.to_datetime(weather["date"])
    print(f"\nTotal weather records: {len(weather):,}")
    print(f"Date range: {weather['date'].min()} to {weather['date'].max()}")
    print(f"Columns: {list(weather.columns)}")

    # Save
    out_path = OUTPUT_DIR / "weather_panhandle.csv"
    weather.to_csv(out_path, index=False)
    print(f"Saved: {out_path}")

    # Quick stats
    print("\nAvg temps by unit (°F):")
    summary = (
        weather.groupby("hunt_unit")["temperature_2m_mean"]
        .agg(["mean", "min", "max"])
        .round(1)
    )
    print(summary.to_string())

    return weather


if __name__ == "__main__":
    main()
