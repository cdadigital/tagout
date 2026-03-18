"""
Tagout API — hunting success prediction for Idaho Panhandle.

Endpoints:
  POST /v1/predict          — predict success for species + unit (upcoming season)
  GET  /v1/predict/map      — all units ranked for choropleth
  GET  /v1/harvest/stats    — historical stats per unit
  GET  /v1/gmu              — GMU list with boundaries
  GET  /v1/species          — species reference
"""

import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import duckdb
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

DATA_DIR = Path(__file__).parents[2] / "data"
DB_PATH = DATA_DIR / "tagout.duckdb"
MODEL_PATH = DATA_DIR / "models" / "xgb_success.pkl"
META_PATH = DATA_DIR / "models" / "model_meta.json"
GEOJSON_PATH = DATA_DIR / "shapefiles" / "hunt_units.geojson"

CURRENT_SEASON = 2025

app = FastAPI(title="Tagout API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)
with open(META_PATH) as f:
    model_meta = json.load(f)

PANHANDLE_UNITS = ["1", "2", "3", "4", "4A", "5", "6", "7", "9"]
SPECIES_LIST = ["Deer", "Elk"]
WEAPON_TYPES = ["All Weapons Combined", "Any Weapon", "Archery", "Muzzleloader"]
WEAPON_LABELS = {
    "All Weapons Combined": "All",
    "Any Weapon": "Rifle",
    "Archery": "Archery",
    "Muzzleloader": "Muzzleloader",
}


def get_db():
    return duckdb.connect(str(DB_PATH), read_only=True)


def doy_to_date(doy: int) -> str:
    """Convert day-of-year to readable date like 'Oct 15'."""
    try:
        return datetime.strptime(str(int(doy)), "%j").strftime("%b %d")
    except Exception:
        return "N/A"


# ── Schemas ──────────────────────────────────────────────────────────────────


class PredictRequest(BaseModel):
    species: str = "Elk"
    hunt_unit: str = "5"


class PressureInfo(BaseModel):
    level: str
    avg_hunters: Optional[int] = None
    avg_days_per_hunter: Optional[float] = None
    total_hunter_days: Optional[int] = None
    hunters_trend: Optional[str] = None
    panhandle_rank: Optional[int] = None
    panhandle_total_units: int = 9


class WeatherProfile(BaseModel):
    avg_temp: Optional[float] = None
    avg_high: Optional[float] = None
    avg_low: Optional[float] = None
    first_snow_date: Optional[str] = None
    total_snow_days: Optional[int] = None
    total_precip_days: Optional[int] = None
    max_snow_depth: Optional[float] = None
    snow_total_in: Optional[float] = None
    precip_total_in: Optional[float] = None


class AntlerQuality(BaseModel):
    antlered_pct: Optional[float] = None
    spike_pct: Optional[float] = None
    six_plus_pt_pct: Optional[float] = None
    four_pt_pct: Optional[float] = None
    five_plus_pt_pct: Optional[float] = None
    whitetail_pct: Optional[float] = None
    quality_label: str = "Unknown"


class WeaponBreakdown(BaseModel):
    weapon_type: str
    weapon_label: str
    success_pct_3yr: Optional[float] = None
    success_pct_5yr: Optional[float] = None
    avg_hunters: Optional[int] = None
    avg_days_per_hunter: Optional[float] = None


class PredictResponse(BaseModel):
    species: str
    hunt_unit: str
    season: int
    predicted_success_pct: float
    historical_3yr_avg: Optional[float] = None
    historical_5yr_avg: Optional[float] = None
    trend: str
    pressure: Optional[PressureInfo] = None
    weather_profile: Optional[WeatherProfile] = None
    antler_quality: Optional[AntlerQuality] = None
    weapon_breakdown: Optional[List[WeaponBreakdown]] = None
    confidence_note: str
    recommendation: str


class UnitScore(BaseModel):
    hunt_unit: str
    species: str
    predicted_success_pct: float
    historical_avg: Optional[float] = None
    rank: int
    trend: str


# ── Helpers ──────────────────────────────────────────────────────────────────


def get_historical_stats(con, hunt_unit: str, species: str):
    return con.execute(f"""
        SELECT season_year, success_pct, kills, hunter_count, hunter_days
        FROM harvest
        WHERE hunt_unit = '{hunt_unit}'
          AND species = '{species}'
          AND weapon_type = 'All Weapons Combined'
          AND success_pct IS NOT NULL
        ORDER BY season_year
    """).df()


def compute_trend(rows: pd.DataFrame) -> str:
    if len(rows) < 4:
        return "stable"
    recent_3 = rows.tail(3)["success_pct"].mean()
    prior_3 = rows.iloc[-6:-3]["success_pct"].mean() if len(rows) >= 6 else rows.head(3)["success_pct"].mean()
    delta = recent_3 - prior_3
    if delta > 2:
        return "improving"
    elif delta < -2:
        return "declining"
    return "stable"


def classify_pressure(avg_hunters: float) -> str:
    if avg_hunters < 500:
        return "low"
    elif avg_hunters < 2000:
        return "moderate"
    return "high"


def get_weather_profile(con, hunt_unit: str) -> WeatherProfile:
    """Aggregate weather across all years to get climate normals for a unit."""
    row = con.execute(f"""
        SELECT
            ROUND(AVG(avg_temp), 1),
            ROUND(AVG(avg_high), 1),
            ROUND(AVG(avg_low), 1),
            ROUND(AVG(first_snow), 0),
            ROUND(AVG(snow_days), 0),
            ROUND(AVG(precip_days), 0),
            ROUND(AVG(max_depth), 1),
            ROUND(AVG(snow_total), 1),
            ROUND(AVG(precip_total), 1)
        FROM (
            SELECT
                season_year,
                AVG(temperature_2m_mean) AS avg_temp,
                AVG(temperature_2m_max) AS avg_high,
                AVG(temperature_2m_min) AS avg_low,
                MIN(CASE WHEN snowfall_sum > 0 THEN EXTRACT(DOY FROM CAST(date AS DATE)) END) AS first_snow,
                COUNT(CASE WHEN snowfall_sum > 0 THEN 1 END) AS snow_days,
                COUNT(CASE WHEN precipitation_sum > 0.1 THEN 1 END) AS precip_days,
                MAX(snow_depth_max) AS max_depth,
                SUM(snowfall_sum) AS snow_total,
                SUM(precipitation_sum) AS precip_total
            FROM weather
            WHERE hunt_unit = '{hunt_unit}'
            GROUP BY season_year
        ) yearly
    """).fetchone()

    if not row or row[0] is None:
        return WeatherProfile()

    first_snow_doy = row[3]
    return WeatherProfile(
        avg_temp=row[0],
        avg_high=row[1],
        avg_low=row[2],
        first_snow_date=doy_to_date(first_snow_doy) if first_snow_doy else None,
        total_snow_days=int(row[4]) if row[4] else None,
        total_precip_days=int(row[5]) if row[5] else None,
        max_snow_depth=row[6],
        snow_total_in=row[7],
        precip_total_in=row[8],
    )


def get_antler_quality(con, hunt_unit: str, species: str) -> AntlerQuality:
    """Get antler quality stats from recent 5 years of harvest data."""
    if species == "Elk":
        row = con.execute(f"""
            SELECT
                ROUND(AVG(CAST(antlered_count AS FLOAT) / NULLIF(antlered_count + antlerless_count, 0) * 100), 0),
                ROUND(AVG(spike_pct), 0),
                ROUND(AVG(six_plus_pt_pct), 0)
            FROM harvest
            WHERE hunt_unit = '{hunt_unit}' AND species = 'Elk'
              AND weapon_type = 'All Weapons Combined'
              AND season_year >= {CURRENT_SEASON - 5}
              AND spike_pct IS NOT NULL
        """).fetchone()
        if not row or row[1] is None:
            return AntlerQuality(quality_label="No data")
        six_pt = row[2] or 0
        label = "Good Trophy Potential" if six_pt >= 30 else ("Average" if six_pt >= 20 else "Below Average")
        return AntlerQuality(
            antlered_pct=row[0],
            spike_pct=row[1],
            six_plus_pt_pct=row[2],
            quality_label=label,
        )
    else:  # Deer
        row = con.execute(f"""
            SELECT
                ROUND(AVG(CAST(antlered_count AS FLOAT) / NULLIF(antlered_count + antlerless_count, 0) * 100), 0),
                ROUND(AVG("4_pts"), 0),
                ROUND(AVG("5_pts"), 0),
                ROUND(AVG(whitetail), 0)
            FROM harvest
            WHERE hunt_unit = '{hunt_unit}' AND species = 'Deer'
              AND weapon_type = 'All Weapons Combined'
              AND season_year >= {CURRENT_SEASON - 5}
        """).fetchone()
        if not row or row[0] is None:
            return AntlerQuality(quality_label="No data")
        five_pt = row[2] or 0
        label = "Good Trophy Potential" if five_pt >= 25 else ("Average" if five_pt >= 15 else "Below Average")
        return AntlerQuality(
            antlered_pct=row[0],
            four_pt_pct=row[1],
            five_plus_pt_pct=row[2],
            whitetail_pct=row[3],
            quality_label=label,
        )


def get_weapon_breakdown(con, hunt_unit: str, species: str) -> List[WeaponBreakdown]:
    """Get success stats broken down by weapon type."""
    results = []
    for wt in ["Any Weapon", "Archery", "Muzzleloader"]:
        row = con.execute(f"""
            SELECT
                ROUND(AVG(CASE WHEN season_year >= {CURRENT_SEASON - 3} THEN success_pct END), 1),
                ROUND(AVG(success_pct), 1),
                ROUND(AVG(hunter_count), 0),
                ROUND(AVG(CAST(hunter_days AS FLOAT) / NULLIF(hunter_count, 0)), 1)
            FROM harvest
            WHERE hunt_unit = '{hunt_unit}' AND species = '{species}'
              AND weapon_type = '{wt}'
              AND season_year >= {CURRENT_SEASON - 5}
              AND success_pct IS NOT NULL
        """).fetchone()
        if row and row[0] is not None:
            results.append(WeaponBreakdown(
                weapon_type=wt,
                weapon_label=WEAPON_LABELS[wt],
                success_pct_3yr=row[0],
                success_pct_5yr=row[1],
                avg_hunters=int(row[2]) if row[2] else None,
                avg_days_per_hunter=row[3],
            ))
    return results


def get_unit_features(con, hunt_unit: str, species: str) -> dict:
    """Build ML feature dict using climate normals for weather."""
    hist = con.execute(f"""
        SELECT AVG(success_pct) AS avg_success,
               AVG(CAST(hunter_days AS FLOAT) / NULLIF(hunter_count, 0)) AS avg_dphr
        FROM harvest
        WHERE hunt_unit = '{hunt_unit}' AND species = '{species}'
          AND weapon_type = 'All Weapons Combined'
          AND season_year >= {CURRENT_SEASON - 3}
    """).fetchone()

    success_3yr_avg = hist[0] if hist[0] is not None else 10.0
    days_per_hunter = hist[1] if hist[1] is not None else 6.0

    weather = con.execute(f"""
        SELECT
            ROUND(AVG(temperature_2m_mean), 1), ROUND(AVG(min_temp), 1),
            ROUND(AVG(max_temp), 1), ROUND(AVG(temp_std), 1),
            ROUND(AVG(early_late_delta), 1), ROUND(AVG(precip_total), 2),
            ROUND(AVG(precip_days), 0), ROUND(AVG(snow_total), 2),
            ROUND(AVG(snow_days), 0), ROUND(AVG(max_snow_depth), 1),
            ROUND(AVG(first_snow), 0), ROUND(AVG(wind_max), 1),
            ROUND(AVG(gust_max), 1), ROUND(AVG(high_wind), 0),
            ROUND(AVG(pressure), 1), ROUND(AVG(pressure_sd), 2),
            ROUND(AVG(daylight), 2)
        FROM (
            SELECT season_year,
                AVG(temperature_2m_mean) AS temperature_2m_mean,
                MIN(temperature_2m_min) AS min_temp, MAX(temperature_2m_max) AS max_temp,
                STDDEV(temperature_2m_mean) AS temp_std,
                AVG(CASE WHEN EXTRACT(MONTH FROM CAST(date AS DATE)) <= 9 THEN temperature_2m_mean END) -
                AVG(CASE WHEN EXTRACT(MONTH FROM CAST(date AS DATE)) >= 11 THEN temperature_2m_mean END) AS early_late_delta,
                SUM(precipitation_sum) AS precip_total,
                COUNT(CASE WHEN precipitation_sum > 0.1 THEN 1 END) AS precip_days,
                SUM(snowfall_sum) AS snow_total,
                COUNT(CASE WHEN snowfall_sum > 0 THEN 1 END) AS snow_days,
                MAX(snow_depth_max) AS max_snow_depth,
                MIN(CASE WHEN snowfall_sum > 0 THEN EXTRACT(DOY FROM CAST(date AS DATE)) END) AS first_snow,
                AVG(wind_speed_10m_max) AS wind_max, MAX(wind_gusts_10m_max) AS gust_max,
                COUNT(CASE WHEN wind_speed_10m_max > 20 THEN 1 END) AS high_wind,
                AVG(pressure_msl_mean) AS pressure, STDDEV(pressure_msl_mean) AS pressure_sd,
                AVG(daylight_duration) / 3600 AS daylight
            FROM weather WHERE hunt_unit = '{hunt_unit}' GROUP BY season_year
        ) yearly_aggs
    """).fetchone()

    col_names = [
        "temp_mean", "temp_min_season", "temp_max_season", "temp_std",
        "temp_early_late_delta", "precip_total_in", "precip_days",
        "snow_total_in", "snow_days", "snow_depth_max", "first_snow_doy",
        "wind_avg_max", "wind_gust_max", "high_wind_days",
        "pressure_mean", "pressure_std", "daylight_avg_hrs",
    ]
    features = {}
    if weather:
        for name, val in zip(col_names, weather):
            features[name] = val if val is not None else -999
    else:
        for name in col_names:
            features[name] = -999

    features["success_3yr_avg"] = round(success_3yr_avg, 1)
    features["days_per_hunter"] = round(days_per_hunter, 1)
    features["year_offset"] = CURRENT_SEASON - 2003
    for u in PANHANDLE_UNITS:
        features[f"hunt_unit_{u}"] = 1.0 if u == hunt_unit else 0.0
    for s in SPECIES_LIST:
        features[f"species_{s}"] = 1.0 if s == species else 0.0
    return features, success_3yr_avg


def get_pressure_info(con, hunt_unit: str, species: str, hist_rows) -> PressureInfo:
    """Compute pressure stats from historical data."""
    avg_hunters = None
    avg_dphr = None
    total_hdays = None
    hunters_trend = None

    if not hist_rows.empty:
        recent_5 = hist_rows.tail(5)
        avg_hunters = int(recent_5["hunter_count"].mean())
        avg_dphr = round(recent_5.apply(
            lambda r: r["hunter_days"] / r["hunter_count"] if r["hunter_count"] > 0 else 0, axis=1
        ).mean(), 1)
        total_hdays = int(recent_5["hunter_days"].mean())
        if len(hist_rows) >= 6:
            rec_h = hist_rows.tail(3)["hunter_count"].mean()
            pri_h = hist_rows.iloc[-6:-3]["hunter_count"].mean()
            hdelta = (rec_h - pri_h) / pri_h * 100 if pri_h > 0 else 0
            hunters_trend = "increasing" if hdelta > 10 else ("decreasing" if hdelta < -10 else "steady")

    level = classify_pressure(avg_hunters) if avg_hunters else "moderate"

    pressure_rank = None
    ranked = con.execute(f"""
        SELECT hunt_unit, AVG(hunter_count) AS avg_hc
        FROM harvest
        WHERE species = '{species}' AND weapon_type = 'All Weapons Combined'
          AND season_year >= {CURRENT_SEASON - 5}
        GROUP BY hunt_unit ORDER BY avg_hc DESC
    """).df()
    if not ranked.empty:
        match = ranked[ranked["hunt_unit"] == hunt_unit]
        if not match.empty:
            pressure_rank = int(match.index[0]) + 1

    return PressureInfo(
        level=level, avg_hunters=avg_hunters, avg_days_per_hunter=avg_dphr,
        total_hunter_days=total_hdays, hunters_trend=hunters_trend,
        panhandle_rank=pressure_rank,
    )


def make_recommendation(pct: float, trend: str, pressure: str) -> str:
    quality = {True: "This is one of the best units in the Panhandle"}.get(pct >= 20) or \
              {True: "Above-average unit with solid opportunity"}.get(pct >= 15) or \
              {True: "Average success rate — typical for this region"}.get(pct >= 10) or \
              "Below-average success rate — challenging hunting"
    trend_text = {
        "improving": "Success rates have been trending upward recently.",
        "declining": "Success rates have been declining — herd or conditions may be shifting.",
        "stable": "Success rates have been consistent over recent years.",
    }[trend]
    pressure_text = {
        "low": "Low hunter pressure means less competition.",
        "moderate": "Moderate hunter pressure.",
        "high": "High hunter pressure — consider hunting midweek or deeper backcountry.",
    }[pressure]
    return f"{quality}. {trend_text} {pressure_text}"


# ── Endpoints ────────────────────────────────────────────────────────────────


@app.get("/")
def root():
    return {"app": "Tagout", "version": "0.3.0", "season": CURRENT_SEASON}


@app.post("/v1/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    if req.species not in SPECIES_LIST:
        raise HTTPException(400, f"Species must be one of {SPECIES_LIST}")
    if req.hunt_unit not in PANHANDLE_UNITS:
        raise HTTPException(400, f"Hunt unit must be one of {PANHANDLE_UNITS}")

    con = get_db()
    features, hist_3yr = get_unit_features(con, req.hunt_unit, req.species)
    hist_rows = get_historical_stats(con, req.hunt_unit, req.species)
    trend = compute_trend(hist_rows)

    hist_5yr = round(hist_rows.tail(5)["success_pct"].mean(), 1) if not hist_rows.empty else None
    pressure = get_pressure_info(con, req.hunt_unit, req.species, hist_rows)
    weather = get_weather_profile(con, req.hunt_unit)
    antlers = get_antler_quality(con, req.hunt_unit, req.species)
    weapons = get_weapon_breakdown(con, req.hunt_unit, req.species)
    con.close()

    # Model prediction
    feature_names = model_meta["features"]
    X = pd.DataFrame([{f: features.get(f, -999) for f in feature_names}])
    pred = max(0, min(100, round(float(model.predict(X)[0]), 1)))

    rec = make_recommendation(pred, trend, pressure.level)

    return PredictResponse(
        species=req.species,
        hunt_unit=req.hunt_unit,
        season=CURRENT_SEASON,
        predicted_success_pct=pred,
        historical_3yr_avg=round(hist_3yr, 1) if hist_3yr else None,
        historical_5yr_avg=hist_5yr,
        trend=trend,
        pressure=pressure,
        weather_profile=weather,
        antler_quality=antlers,
        weapon_breakdown=weapons,
        confidence_note="Based on 22 years of IDFG harvest data and historical weather patterns.",
        recommendation=rec,
    )


@app.get("/v1/predict/map")
def predict_map(
    species: str = Query("Elk"),
    weapon_type: str = Query("All Weapons Combined"),
):
    if species not in SPECIES_LIST:
        raise HTTPException(400, f"Species must be one of {SPECIES_LIST}")

    con = get_db()
    results = []

    if weapon_type == "All Weapons Combined":
        # Use model predictions
        for unit in PANHANDLE_UNITS:
            features, hist_avg = get_unit_features(con, unit, species)
            hist_rows = get_historical_stats(con, unit, species)
            trend = compute_trend(hist_rows)
            X = pd.DataFrame([{f: features.get(f, -999) for f in model_meta["features"]}])
            pred = max(0, min(100, round(float(model.predict(X)[0]), 1)))
            results.append({
                "hunt_unit": unit, "species": species,
                "predicted_success_pct": pred,
                "historical_avg": round(hist_avg, 1) if hist_avg else None,
                "trend": trend,
            })
    else:
        # Use historical averages for specific weapon type
        for unit in PANHANDLE_UNITS:
            row = con.execute(f"""
                SELECT
                    ROUND(AVG(CASE WHEN season_year >= {CURRENT_SEASON - 3} THEN success_pct END), 1),
                    ROUND(AVG(success_pct), 1)
                FROM harvest
                WHERE hunt_unit = '{unit}' AND species = '{species}'
                  AND weapon_type = '{weapon_type}'
                  AND season_year >= {CURRENT_SEASON - 5}
                  AND success_pct IS NOT NULL
            """).fetchone()
            hist_rows = get_historical_stats(con, unit, species)
            trend = compute_trend(hist_rows)
            pct_3yr = row[0] if row and row[0] else 0
            pct_5yr = row[1] if row and row[1] else 0
            results.append({
                "hunt_unit": unit, "species": species,
                "predicted_success_pct": round(pct_3yr, 1),
                "historical_avg": round(pct_5yr, 1) if pct_5yr else None,
                "trend": trend,
            })
    con.close()

    results.sort(key=lambda x: x["predicted_success_pct"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1
    return [UnitScore(**r) for r in results]


@app.get("/v1/harvest/stats")
def harvest_stats(
    species: str = Query("Elk"),
    hunt_unit: Optional[str] = Query(None),
    weapon_type: str = Query("All Weapons Combined"),
):
    con = get_db()
    where = f"WHERE species = '{species}' AND weapon_type = '{weapon_type}'"
    if hunt_unit:
        where += f" AND hunt_unit = '{hunt_unit}'"
    rows = con.execute(f"""
        SELECT hunt_unit, species, season_year, success_pct, kills,
               hunter_count, hunter_days
        FROM harvest {where}
        ORDER BY hunt_unit, season_year
    """).df().to_dict(orient="records")
    con.close()
    return rows


@app.get("/v1/gmu")
def gmu_list():
    if not GEOJSON_PATH.exists():
        raise HTTPException(500, "GeoJSON not found")
    with open(GEOJSON_PATH) as f:
        geojson = json.load(f)
    features = [f for f in geojson["features"] if f["properties"].get("NAME") in PANHANDLE_UNITS]
    return {"type": "FeatureCollection", "features": features}


@app.get("/v1/species")
def species_list():
    return [
        {"name": "Elk", "slug": "elk", "description": "Rocky Mountain Elk"},
        {"name": "Deer", "slug": "deer", "description": "White-tailed & Mule Deer"},
    ]
