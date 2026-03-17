"""
Load all raw CSVs into a DuckDB database for analysis.
Creates a single normalized `harvest` table.

Run after fetch_harvest.py has downloaded raw CSVs.
"""
import duckdb
import pandas as pd
from pathlib import Path
import json

RAW_DIR = Path(__file__).parents[2] / "data" / "raw"
DB_PATH = Path(__file__).parents[2] / "data" / "tagout.duckdb"


COLUMN_ALIASES = {
    # Normalize whatever IDFG exports to consistent names
    # These will be updated once we see actual CSV headers
    "unit": "hunt_unit",
    "Unit": "hunt_unit",
    "HuntUnit": "hunt_unit",
    "species": "species",
    "Species": "species",
    "year": "season_year",
    "Year": "season_year",
    "Season": "season_year",
    "success": "success_pct",
    "Success": "success_pct",
    "SuccessRate": "success_pct",
    "hunters": "hunter_count",
    "Hunters": "hunter_count",
    "kills": "kills",
    "Kills": "kills",
    "Harvest": "kills",
    "hunter_days": "hunter_days",
    "HunterDays": "hunter_days",
    "weapon": "weapon_type",
    "Weapon": "weapon_type",
    "WeaponType": "weapon_type",
}


def load_csvs() -> pd.DataFrame:
    """Load all raw harvest CSVs and combine into a single DataFrame."""
    manifest_path = RAW_DIR / "scrape_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError("No scrape_manifest.json found. Run fetch_harvest.py first.")

    with open(manifest_path) as f:
        manifest = json.load(f)

    frames = []
    for entry in manifest:
        path = Path(entry["path"])
        if not path or not Path(path).exists():
            continue
        df = pd.read_csv(path)
        # Tag with species/year in case columns are missing
        df["_species_raw"] = entry["species"]
        df["_year_raw"] = entry["year"]
        frames.append(df)

    if not frames:
        raise ValueError("No CSV files loaded. Check raw data directory.")

    combined = pd.concat(frames, ignore_index=True)
    return combined


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns to consistent schema."""
    df = df.rename(columns={k: v for k, v in COLUMN_ALIASES.items() if k in df.columns})
    return df


def build_db(df: pd.DataFrame):
    """Write normalized DataFrame to DuckDB."""
    con = duckdb.connect(str(DB_PATH))

    con.execute("DROP TABLE IF EXISTS harvest")
    con.execute("""
        CREATE TABLE harvest AS SELECT * FROM df
    """)

    count = con.execute("SELECT COUNT(*) FROM harvest").fetchone()[0]
    print(f"Built harvest table: {count:,} rows")
    print(f"Database: {DB_PATH}")

    # Show sample
    print("\nSample:")
    print(con.execute("SELECT * FROM harvest LIMIT 5").df())

    con.close()


def main():
    print("Loading CSVs...")
    df = load_csvs()
    print(f"Raw rows: {len(df):,}")

    print("Normalizing columns...")
    df = normalize(df)
    print(f"Columns: {list(df.columns)}")

    print("Building DuckDB...")
    build_db(df)


if __name__ == "__main__":
    main()
