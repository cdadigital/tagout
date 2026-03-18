"""
Tagout API — hunting success prediction for Idaho Panhandle.

Endpoints:
  POST /v1/predict          — predict success for species + unit (upcoming season)
  GET  /v1/predict/map      — all units ranked for choropleth
  GET  /v1/predict/compare  — side-by-side unit comparison
  GET  /v1/harvest/stats    — historical stats per unit
  GET  /v1/gmu              — GMU list with boundaries
  GET  /v1/species          — species reference
"""

import json
import pickle
from pathlib import Path
from typing import Optional

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

CURRENT_SEASON = 2025  # upcoming season

app = FastAPI(
    title="Tagout API",
    description="Hunting success prediction for Idaho Panhandle",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load model + metadata at startup
with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)

with open(META_PATH) as f:
    model_meta = json.load(f)

PANHANDLE_UNITS = ["1", "2", "3", "4", "4A", "5", "6", "7", "9"]
SPECIES_LIST = ["Deer", "Elk"]


def get_db():
    return duckdb.connect(str(DB_PATH), read_only=True)


# ── Schemas ──────────────────────────────────────────────────────────────────


class PredictRequest(BaseModel):
    species: str = "Elk"
    hunt_unit: str = "5"


class PressureInfo(BaseModel):
    level: str  # "low", "moderate", "high"
    avg_hunters: Optional[int]
    avg_days_per_hunter: Optional[float]
    total_hunter_days: Optional[int]
    hunters_trend: Optional[str]  # "increasing", "decreasing", "steady"
    panhandle_rank: Optional[int]  # 1 = most crowded
    panhandle_total_units: int = 9


class PredictResponse(BaseModel):
    species: str
    hunt_unit: str
    season: int
    predicted_success_pct: float
    historical_3yr_avg: Optional[float]
    historical_5yr_avg: Optional[float]
    trend: str
    pressure: Optional[PressureInfo]
    confidence_note: str
    top_factors: dict
    recommendation: str


class UnitScore(BaseModel):
    hunt_unit: str
    species: str
    predicted_success_pct: float
    historical_avg: Optional[float]
    rank: int
    trend: str


class CompareUnit(BaseModel):
    hunt_unit: str
    predicted_success_pct: float
    historical_avg: Optional[float]
    avg_hunters: Optional[int]
    avg_days_per_hunter: Optional[float]
    trend: str
    pros: list
    cons: list


# ── Helpers ──────────────────────────────────────────────────────────────────


def get_historical_stats(con, hunt_unit: str, species: str):
    """Get historical stats for a unit-species combo."""
    rows = con.execute(f"""
        SELECT season_year, success_pct, kills, hunter_count, hunter_days
        FROM harvest
        WHERE hunt_unit = '{hunt_unit}'
          AND species = '{species}'
          AND weapon_type = 'All Weapons Combined'
          AND success_pct IS NOT NULL
        ORDER BY season_year
    """).df()
    return rows


def compute_trend(rows: pd.DataFrame) -> str:
    """Determine if success rate is trending up, down, or flat."""
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
    """Classify hunter pressure based on avg hunter count."""
    if avg_hunters < 500:
        return "low"
    elif avg_hunters < 2000:
        return "moderate"
    return "high"


def get_unit_features(con, hunt_unit: str, species: str) -> dict:
    """
    Build feature dict for predicting the upcoming season.
    Uses most recent 3 years for historical features.
    For weather, uses climate normals (average of all available years)
    since we don't have future weather data.
    """
    # Historical success (most recent 3 years)
    hist = con.execute(f"""
        SELECT AVG(success_pct) AS avg_success,
               AVG(CAST(hunter_days AS FLOAT) / NULLIF(hunter_count, 0)) AS avg_days_per_hunter
        FROM harvest
        WHERE hunt_unit = '{hunt_unit}'
          AND species = '{species}'
          AND weapon_type = 'All Weapons Combined'
          AND season_year >= {CURRENT_SEASON - 3}
    """).fetchone()

    success_3yr_avg = hist[0] if hist[0] is not None else 10.0
    days_per_hunter = hist[1] if hist[1] is not None else 6.0

    # Weather: use climate normals (average across all available years)
    # This is the best estimate for a future season
    weather = con.execute(f"""
        SELECT
            ROUND(AVG(temperature_2m_mean), 1)  AS temp_mean,
            ROUND(AVG(min_temp), 1)             AS temp_min_season,
            ROUND(AVG(max_temp), 1)             AS temp_max_season,
            ROUND(AVG(temp_std), 1)             AS temp_std,
            ROUND(AVG(early_late_delta), 1)     AS temp_early_late_delta,
            ROUND(AVG(precip_total), 2)         AS precip_total_in,
            ROUND(AVG(precip_days), 0)          AS precip_days,
            ROUND(AVG(snow_total), 2)           AS snow_total_in,
            ROUND(AVG(snow_days), 0)            AS snow_days,
            ROUND(AVG(max_snow_depth), 1)       AS snow_depth_max,
            ROUND(AVG(first_snow), 0)           AS first_snow_doy,
            ROUND(AVG(wind_max), 1)             AS wind_avg_max,
            ROUND(AVG(gust_max), 1)             AS wind_gust_max,
            ROUND(AVG(high_wind), 0)            AS high_wind_days,
            ROUND(AVG(pressure), 1)             AS pressure_mean,
            ROUND(AVG(pressure_sd), 2)          AS pressure_std,
            ROUND(AVG(daylight), 2)             AS daylight_avg_hrs
        FROM (
            SELECT
                season_year,
                AVG(temperature_2m_mean) AS temperature_2m_mean,
                MIN(temperature_2m_min) AS min_temp,
                MAX(temperature_2m_max) AS max_temp,
                STDDEV(temperature_2m_mean) AS temp_std,
                AVG(CASE WHEN EXTRACT(MONTH FROM CAST(date AS DATE)) <= 9 THEN temperature_2m_mean END) -
                AVG(CASE WHEN EXTRACT(MONTH FROM CAST(date AS DATE)) >= 11 THEN temperature_2m_mean END) AS early_late_delta,
                SUM(precipitation_sum) AS precip_total,
                COUNT(CASE WHEN precipitation_sum > 0.1 THEN 1 END) AS precip_days,
                SUM(snowfall_sum) AS snow_total,
                COUNT(CASE WHEN snowfall_sum > 0 THEN 1 END) AS snow_days,
                MAX(snow_depth_max) AS max_snow_depth,
                MIN(CASE WHEN snowfall_sum > 0 THEN EXTRACT(DOY FROM CAST(date AS DATE)) END) AS first_snow,
                AVG(wind_speed_10m_max) AS wind_max,
                MAX(wind_gusts_10m_max) AS gust_max,
                COUNT(CASE WHEN wind_speed_10m_max > 20 THEN 1 END) AS high_wind,
                AVG(pressure_msl_mean) AS pressure,
                STDDEV(pressure_msl_mean) AS pressure_sd,
                AVG(daylight_duration) / 3600 AS daylight
            FROM weather
            WHERE hunt_unit = '{hunt_unit}'
            GROUP BY season_year
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

    # One-hot encode unit + species
    for u in PANHANDLE_UNITS:
        features[f"hunt_unit_{u}"] = 1.0 if u == hunt_unit else 0.0
    for s in SPECIES_LIST:
        features[f"species_{s}"] = 1.0 if s == species else 0.0

    return features, success_3yr_avg


def make_recommendation(pct: float, trend: str, pressure: str) -> str:
    """Generate a plain-English recommendation."""
    if pct >= 20:
        quality = "This is one of the best units in the Panhandle"
    elif pct >= 15:
        quality = "Above-average unit with solid opportunity"
    elif pct >= 10:
        quality = "Average success rate — typical for this region"
    else:
        quality = "Below-average success rate — challenging hunting"

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
    return {
        "app": "Tagout",
        "version": "0.2.0",
        "description": "Idaho Panhandle hunting success prediction",
        "season": CURRENT_SEASON,
    }


@app.post("/v1/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    if req.species not in SPECIES_LIST:
        raise HTTPException(400, f"Species must be one of {SPECIES_LIST}")
    if req.hunt_unit not in PANHANDLE_UNITS:
        raise HTTPException(400, f"Hunt unit must be one of {PANHANDLE_UNITS}")

    con = get_db()
    features, hist_3yr = get_unit_features(con, req.hunt_unit, req.species)

    # Historical analysis
    hist_rows = get_historical_stats(con, req.hunt_unit, req.species)
    trend = compute_trend(hist_rows)

    hist_5yr = None
    avg_hunters = None
    avg_dphr = None
    total_hdays = None
    hunters_trend = None
    if not hist_rows.empty:
        recent_5 = hist_rows.tail(5)
        hist_5yr = round(recent_5["success_pct"].mean(), 1)
        avg_hunters = int(recent_5["hunter_count"].mean())
        avg_dphr = round(
            recent_5.apply(
                lambda r: r["hunter_days"] / r["hunter_count"] if r["hunter_count"] > 0 else 0,
                axis=1,
            ).mean(), 1
        )
        total_hdays = int(recent_5["hunter_days"].mean())

        # Hunter count trend (recent 3 vs prior 3)
        if len(hist_rows) >= 6:
            recent_hunters = hist_rows.tail(3)["hunter_count"].mean()
            prior_hunters = hist_rows.iloc[-6:-3]["hunter_count"].mean()
            hdelta = (recent_hunters - prior_hunters) / prior_hunters * 100 if prior_hunters > 0 else 0
            if hdelta > 10:
                hunters_trend = "increasing"
            elif hdelta < -10:
                hunters_trend = "decreasing"
            else:
                hunters_trend = "steady"

    pressure_level = classify_pressure(avg_hunters) if avg_hunters else "moderate"

    # Rank this unit by hunter count among all panhandle units for same species
    pressure_rank = None
    all_units_hunters = con.execute(f"""
        SELECT hunt_unit, AVG(hunter_count) AS avg_hc
        FROM harvest
        WHERE species = '{req.species}'
          AND weapon_type = 'All Weapons Combined'
          AND season_year >= {CURRENT_SEASON - 5}
        GROUP BY hunt_unit
        ORDER BY avg_hc DESC
    """).df()
    if not all_units_hunters.empty:
        ranked = all_units_hunters.reset_index(drop=True)
        match = ranked[ranked["hunt_unit"] == req.hunt_unit]
        if not match.empty:
            pressure_rank = int(match.index[0]) + 1

    pressure_info = PressureInfo(
        level=pressure_level,
        avg_hunters=avg_hunters,
        avg_days_per_hunter=avg_dphr,
        total_hunter_days=total_hdays,
        hunters_trend=hunters_trend,
        panhandle_rank=pressure_rank,
    )
    con.close()

    # Predict
    feature_names = model_meta["features"]
    X = pd.DataFrame([{f: features.get(f, -999) for f in feature_names}])
    pred = float(model.predict(X)[0])
    pred = max(0, min(100, round(pred, 1)))

    # Top factors with readable names
    importance = model_meta.get("feature_importance", {})
    readable = {
        "success_3yr_avg": "Historical success rate",
        "snow_days": "Snow days",
        "precip_total_in": "Precipitation",
        "temp_mean": "Temperature",
        "wind_avg_max": "Wind",
        "pressure_std": "Weather variability",
        "daylight_avg_hrs": "Daylight hours",
        "days_per_hunter": "Hunter effort",
        "year_offset": "Long-term trend",
    }
    top = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]
    top_factors = {}
    for k, v in top:
        label = readable.get(k, k.replace("_", " ").replace("hunt unit", "Unit").replace("species ", ""))
        top_factors[label] = round(v, 3)

    rec = make_recommendation(pred, trend, pressure_level)

    return PredictResponse(
        species=req.species,
        hunt_unit=req.hunt_unit,
        season=CURRENT_SEASON,
        predicted_success_pct=pred,
        historical_3yr_avg=round(hist_3yr, 1) if hist_3yr else None,
        historical_5yr_avg=hist_5yr,
        trend=trend,
        pressure=pressure_info,
        confidence_note="Based on 22 years of IDFG harvest data and historical weather patterns. Uses climate normals for upcoming season weather.",
        top_factors=top_factors,
        recommendation=rec,
    )


@app.get("/v1/predict/map")
def predict_map(species: str = Query("Elk")):
    """Rank all units for the upcoming season."""
    if species not in SPECIES_LIST:
        raise HTTPException(400, f"Species must be one of {SPECIES_LIST}")

    con = get_db()
    results = []
    for unit in PANHANDLE_UNITS:
        features, hist_avg = get_unit_features(con, unit, species)
        hist_rows = get_historical_stats(con, unit, species)
        trend = compute_trend(hist_rows)

        feature_names = model_meta["features"]
        X = pd.DataFrame([{f: features.get(f, -999) for f in feature_names}])
        pred = float(model.predict(X)[0])
        pred = max(0, min(100, round(pred, 1)))
        results.append({
            "hunt_unit": unit,
            "species": species,
            "predicted_success_pct": pred,
            "historical_avg": round(hist_avg, 1) if hist_avg else None,
            "trend": trend,
        })
    con.close()

    # Rank by predicted success
    results.sort(key=lambda x: x["predicted_success_pct"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1

    return [UnitScore(**r) for r in results]


@app.get("/v1/predict/compare")
def compare_units(
    species: str = Query("Elk"),
    units: str = Query("5,6", description="Comma-separated unit IDs"),
):
    """Side-by-side comparison of specific units."""
    unit_list = [u.strip() for u in units.split(",")]
    for u in unit_list:
        if u not in PANHANDLE_UNITS:
            raise HTTPException(400, f"Invalid unit: {u}")

    con = get_db()
    results = []
    for unit in unit_list:
        features, hist_avg = get_unit_features(con, unit, species)
        hist_rows = get_historical_stats(con, unit, species)
        trend = compute_trend(hist_rows)

        feature_names = model_meta["features"]
        X = pd.DataFrame([{f: features.get(f, -999) for f in feature_names}])
        pred = float(model.predict(X)[0])
        pred = max(0, min(100, round(pred, 1)))

        # Compute stats for pros/cons
        avg_hunters = int(hist_rows.tail(5)["hunter_count"].mean()) if not hist_rows.empty else None
        avg_dphr = round(hist_rows.tail(5).apply(
            lambda r: r["hunter_days"] / r["hunter_count"] if r["hunter_count"] > 0 else 0, axis=1
        ).mean(), 1) if not hist_rows.empty else None

        pros = []
        cons = []
        if pred >= 15:
            pros.append("Above-average success rate")
        elif pred < 9:
            cons.append("Below-average success rate")
        if trend == "improving":
            pros.append("Trending upward")
        elif trend == "declining":
            cons.append("Trending downward")
        if avg_hunters and avg_hunters < 1000:
            pros.append("Lower hunter pressure")
        elif avg_hunters and avg_hunters > 3000:
            cons.append("High hunter pressure")

        results.append(CompareUnit(
            hunt_unit=unit,
            predicted_success_pct=pred,
            historical_avg=round(hist_avg, 1) if hist_avg else None,
            avg_hunters=avg_hunters,
            avg_days_per_hunter=avg_dphr,
            trend=trend,
            pros=pros,
            cons=cons,
        ))
    con.close()
    return results


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
        FROM harvest
        {where}
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
    features = [
        feat for feat in geojson["features"]
        if feat["properties"].get("NAME") in PANHANDLE_UNITS
    ]
    return {"type": "FeatureCollection", "features": features}


@app.get("/v1/species")
def species_list():
    return [
        {"name": "Elk", "slug": "elk", "description": "Rocky Mountain Elk"},
        {"name": "Deer", "slug": "deer", "description": "White-tailed & Mule Deer"},
    ]
