"""
Feature engineering: join harvest success rates with season weather aggregates.

Granularity: one row per (hunt_unit, species, weapon_type, season_year)
Target: success_pct

Weather features are aggregated over hunting season (Aug 15 - Dec 31) per unit-year.
"""

import duckdb
import pandas as pd
from pathlib import Path

DB_PATH = Path(__file__).parents[2] / "data" / "tagout.duckdb"


def build_weather_features(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """
    Aggregate daily weather into season-level features per unit-year.
    """
    return con.execute("""
        WITH daily AS (
            SELECT *,
                CAST(date AS DATE) AS dt,
                EXTRACT(MONTH FROM CAST(date AS DATE)) AS month
            FROM weather
        )
        SELECT
            hunt_unit,
            season_year,

            -- Temperature
            ROUND(AVG(temperature_2m_mean), 1)  AS temp_mean,
            ROUND(MIN(temperature_2m_min), 1)   AS temp_min_season,
            ROUND(MAX(temperature_2m_max), 1)   AS temp_max_season,
            ROUND(STDDEV(temperature_2m_mean), 1) AS temp_std,

            -- Early season (Aug-Sep) vs late season (Nov-Dec) temp delta
            ROUND(
                AVG(CASE WHEN month <= 9 THEN temperature_2m_mean END) -
                AVG(CASE WHEN month >= 11 THEN temperature_2m_mean END),
            1) AS temp_early_late_delta,

            -- Precipitation
            ROUND(SUM(precipitation_sum), 2)    AS precip_total_in,
            ROUND(AVG(precipitation_sum), 3)    AS precip_daily_avg,
            COUNT(CASE WHEN precipitation_sum > 0.1 THEN 1 END) AS precip_days,

            -- Snow
            ROUND(SUM(snowfall_sum), 2)         AS snow_total_in,
            COUNT(CASE WHEN snowfall_sum > 0 THEN 1 END) AS snow_days,
            ROUND(MAX(snow_depth_max), 1)       AS snow_depth_max,
            -- First snow date as day-of-season offset
            MIN(CASE WHEN snowfall_sum > 0 THEN
                EXTRACT(DOY FROM CAST(date AS DATE)) END) AS first_snow_doy,

            -- Wind
            ROUND(AVG(wind_speed_10m_max), 1)   AS wind_avg_max,
            ROUND(MAX(wind_gusts_10m_max), 1)   AS wind_gust_max,
            COUNT(CASE WHEN wind_speed_10m_max > 20 THEN 1 END) AS high_wind_days,

            -- Pressure (frontal activity proxy)
            ROUND(AVG(pressure_msl_mean), 1)    AS pressure_mean,
            ROUND(STDDEV(pressure_msl_mean), 2) AS pressure_std,

            -- Daylight
            ROUND(AVG(daylight_duration) / 3600, 2) AS daylight_avg_hrs,

            -- Count for sanity check
            COUNT(*) AS weather_days

        FROM daily
        GROUP BY hunt_unit, season_year
        ORDER BY hunt_unit, season_year
    """).df()


def build_training_data(weapon_filter: str = "All Weapons Combined") -> pd.DataFrame:
    """
    Join harvest targets with weather features.
    Returns one row per (unit, species, year) ready for modeling.
    """
    con = duckdb.connect(str(DB_PATH), read_only=True)

    # Harvest data (target + historical features)
    harvest = con.execute(f"""
        SELECT
            hunt_unit,
            species,
            season_year,
            success_pct,
            kills,
            hunter_count,
            hunter_days,
            ROUND(CAST(hunter_days AS FLOAT) / NULLIF(hunter_count, 0), 1) AS days_per_hunter,
            antlered_count,
            antlerless_count
        FROM harvest
        WHERE weapon_type = '{weapon_filter}'
          AND success_pct IS NOT NULL
    """).df()

    weather = build_weather_features(con)
    con.close()

    # Merge
    df = harvest.merge(weather, on=["hunt_unit", "season_year"], how="inner")

    # Derived features
    df["kill_rate_per_day"] = (df["kills"] / df["hunter_days"].replace(0, float("nan"))).round(4)

    # 3-year rolling average success for this unit+species (lag to avoid leakage)
    df = df.sort_values(["hunt_unit", "species", "season_year"])
    df["success_3yr_avg"] = (
        df.groupby(["hunt_unit", "species"])["success_pct"]
        .transform(lambda x: x.shift(1).rolling(3, min_periods=1).mean())
        .round(1)
    )

    # Year trend
    df["year_offset"] = df["season_year"] - df["season_year"].min()

    return df


def main():
    print("Building training dataset...")
    df = build_training_data()
    print(f"Shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print(f"\nSpecies counts:")
    print(df.groupby("species").size().to_string())
    print(f"\nYear range: {df['season_year'].min()} - {df['season_year'].max()}")
    print(f"\nSample:")
    print(df.head(5).to_string())

    out_path = Path(__file__).parents[2] / "data" / "training.csv"
    df.to_csv(out_path, index=False)
    print(f"\nSaved: {out_path}")

    return df


if __name__ == "__main__":
    main()
