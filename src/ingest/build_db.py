"""
Load harvest CSVs into a DuckDB database for analysis.
Creates a single normalized `harvest` table.

Run after fetch_harvest.py has downloaded raw CSVs.

Usage:
    python -m src.ingest.build_db
"""
import duckdb
import pandas as pd
from pathlib import Path

RAW_DIR = Path(__file__).parents[2] / "data" / "raw"
DB_PATH = Path(__file__).parents[2] / "data" / "tagout.duckdb"


def load_panhandle_csvs() -> pd.DataFrame:
    """Load all *_panhandle.csv files from the raw data directory."""
    csvs = sorted(RAW_DIR.glob("harvest_*_panhandle.csv"))
    if not csvs:
        raise FileNotFoundError(
            f"No panhandle CSVs found in {RAW_DIR}. Run fetch_harvest.py first."
        )

    frames = []
    for path in csvs:
        print(f"  Loading {path.name}...")
        df = pd.read_csv(path)
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)
    return combined


def load_weather() -> pd.DataFrame:
    """Load weather CSV."""
    path = RAW_DIR / "weather_panhandle.csv"
    if not path.exists():
        raise FileNotFoundError(f"No weather CSV at {path}. Run fetch_weather.py first.")
    print(f"  Loading {path.name}...")
    return pd.read_csv(path)


def build_db(harvest_df: pd.DataFrame, weather_df: pd.DataFrame):
    """Write DataFrames to DuckDB."""
    con = duckdb.connect(str(DB_PATH))

    con.execute("DROP TABLE IF EXISTS harvest")
    con.execute("CREATE TABLE harvest AS SELECT * FROM harvest_df")
    h_count = con.execute("SELECT COUNT(*) FROM harvest").fetchone()[0]
    print(f"Built harvest table: {h_count:,} rows")

    con.execute("DROP TABLE IF EXISTS weather")
    con.execute("CREATE TABLE weather AS SELECT * FROM weather_df")
    w_count = con.execute("SELECT COUNT(*) FROM weather").fetchone()[0]
    print(f"Built weather table: {w_count:,} rows")

    print(f"Database: {DB_PATH}")
    con.close()


def main():
    print("Loading panhandle harvest CSVs...")
    harvest_df = load_panhandle_csvs()
    print(f"Harvest rows: {len(harvest_df):,}")

    print("Loading weather data...")
    weather_df = load_weather()
    print(f"Weather rows: {len(weather_df):,}")

    print("\nBuilding DuckDB...")
    build_db(harvest_df, weather_df)


if __name__ == "__main__":
    main()
