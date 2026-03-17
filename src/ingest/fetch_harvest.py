"""
Scrape Idaho F&G harvest statistics via the Hunt Planner stats page.

Direct URL pattern (no form postback needed):
  General season:    /ifwis/huntplanner/stats/?season=general&game={species}&yr={year}
  Controlled hunts:  /ifwis/huntplanner/stats/?season=controlled&game={species}&yr={year}

Both return plain HTML tables — no ASP.NET ViewState required.

Usage:
    python -m src.ingest.fetch_harvest
"""

import re
import time
from pathlib import Path
from typing import List, Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.ingest.config import PANHANDLE_UNITS, YEAR_END, YEAR_START

OUTPUT_DIR = Path(__file__).parents[2] / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

STATS_BASE_URL = "https://fishandgame.idaho.gov/ifwis/huntplanner/stats/"

# game= parameter values for the stats URL
SPECIES_SLUGS = {
    "Deer":      "deer",
    "Elk":       "elk",
    "Antelope":  "antelope",
    "Moose":     "moose",
    "Sheep":     "sheep",
    "Goat":      "goat",
    "Bear":      "bear",
}

AVAILABLE_YEARS = list(range(2024, 2002, -1))  # 2024 down to 2003

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}


def fetch_stats_page(
    session: requests.Session,
    season: str,
    species_slug: str,
    year: int,
) -> Optional[pd.DataFrame]:
    """
    Fetch one stats page and return a DataFrame.

    season: "general" or "controlled"
    """
    url = STATS_BASE_URL
    params = {"season": season, "game": species_slug, "yr": str(year)}
    resp = session.get(url, params=params, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")

    # Find the main data table
    tables = soup.find_all("table")
    if not tables:
        print(f"    No tables found for {season} {species_slug} {year}")
        return None

    try:
        dfs = pd.read_html(str(tables[0]))
    except Exception as e:
        print(f"    Table parse error for {season} {species_slug} {year}: {e}")
        return None

    if not dfs:
        return None

    df = dfs[0]

    # Drop summary rows (last row often has statewide totals)
    df = df.dropna(how="all")

    df["season_year"] = year
    df["season_type"] = season
    return df


def scrape_species(
    species: str,
    years: List[int],
    season: str = "general",
    delay: float = 0.3,
) -> pd.DataFrame:
    """Scrape all years for one species."""
    slug = SPECIES_SLUGS.get(species)
    if not slug:
        raise ValueError(f"Unknown species: {species}. Options: {list(SPECIES_SLUGS.keys())}")

    session = requests.Session()
    frames = []

    for year in years:
        print(f"  Fetching {species} {season} {year}...")
        try:
            df = fetch_stats_page(session, season, slug, year)
            if df is not None and not df.empty:
                frames.append(df)
                print(f"    {len(df)} rows")
            else:
                print(f"    No data")
        except requests.HTTPError as e:
            print(f"    HTTP error: {e}")
        except Exception as e:
            print(f"    Failed: {e}")
        time.sleep(delay)

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)


def normalize_columns(df: pd.DataFrame, species: str) -> pd.DataFrame:
    """Standardize column names to a consistent schema."""
    df = df.copy()
    df.columns = [
        re.sub(r"[^a-z0-9]+", "_", str(col).lower().strip()).strip("_")
        for col in df.columns
    ]

    renames = {
        "unit":             "hunt_unit",
        "area":             "hunt_unit",
        "take_method":      "weapon_type",
        "takemethod":       "weapon_type",
        "success":          "success_pct",
        "success_":         "success_pct",
        "harvest":          "kills",
        "hunters":          "hunter_count",
        "days":             "hunter_days",
        "antlered":         "antlered_count",
        "antlerless":       "antlerless_count",
        "spike":            "spike_pct",
        "spike_pct":        "spike_pct",
        "6_pts":            "six_plus_pt_pct",
        "6_pt":             "six_plus_pt_pct",
    }
    for old, new in renames.items():
        if old in df.columns and old != new:
            df = df.rename(columns={old: new})

    # Strip "%" from success column values if present
    if "success_pct" in df.columns:
        df["success_pct"] = (
            df["success_pct"]
            .astype(str)
            .str.replace("%", "", regex=False)
            .str.strip()
        )
        df["success_pct"] = pd.to_numeric(df["success_pct"], errors="coerce")

    df["species"] = species
    return df


def filter_panhandle(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to Panhandle hunt units."""
    if "hunt_unit" not in df.columns:
        unit_cols = [c for c in df.columns if "unit" in c.lower()]
        if unit_cols:
            df = df.rename(columns={unit_cols[0]: "hunt_unit"})
        else:
            print("  Warning: no hunt_unit column — returning all rows")
            return df
    df["hunt_unit"] = df["hunt_unit"].astype(str).str.strip()
    mask = df["hunt_unit"].isin(PANHANDLE_UNITS)
    filtered = df[mask].copy()
    print(f"  Panhandle filter: {len(df)} total → {len(filtered)} rows")
    return filtered


def main(
    species: str = "Elk",
    years: Optional[List[int]] = None,
    season: str = "general",
    panhandle_only: bool = True,
):
    year_list = years or [y for y in AVAILABLE_YEARS if YEAR_START <= y <= YEAR_END]
    print(f"Scraping {species} | {season} season | {len(year_list)} years | panhandle_only={panhandle_only}")

    raw = scrape_species(species, year_list, season=season)

    if raw.empty:
        print("No data collected.")
        return

    print(f"\nRaw columns: {list(raw.columns)}")
    print(f"Raw rows: {len(raw)}")

    df = normalize_columns(raw, species)

    raw_path = OUTPUT_DIR / f"harvest_{species.lower()}_{season}_raw.csv"
    raw.to_csv(raw_path, index=False)
    print(f"Saved raw: {raw_path}")

    if panhandle_only:
        df = filter_panhandle(df)
        out_path = OUTPUT_DIR / f"harvest_{species.lower()}_{season}_panhandle.csv"
        df.to_csv(out_path, index=False)
        print(f"Saved panhandle: {out_path}")

    if "season_year" in df.columns and "success_pct" in df.columns:
        print("\nAvg success rate by year:")
        print(df.groupby("season_year")["success_pct"].mean().round(1).to_string())

    return df


if __name__ == "__main__":
    main(species="Elk", season="general", panhandle_only=True)
