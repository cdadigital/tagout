"""
Tagout API — hunting success prediction for Idaho Panhandle.

Endpoints:
  POST /v1/predict          — predict success for species + unit + date range
  GET  /v1/predict/map      — all units scored for choropleth
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

app = FastAPI(
    title="Tagout API",
    description="Hunting success prediction for Idaho Panhandle",
    version="0.1.0",
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
    species: str
    hunt_unit: str
    year: Optional[int] = 2024


class PredictResponse(BaseModel):
    species: str
    hunt_unit: str
    year: int
    predicted_success_pct: float
    historical_avg: Optional[float]
    confidence_note: str
    top_factors: dict


class UnitScore(BaseModel):
    hunt_unit: str
    species: str
    predicted_success_pct: float
    historical_avg: Optional[float]


class HarvestStats(BaseModel):
    hunt_unit: str
    species: str
    season_year: int
    success_pct: Optional[float]
    kills: Optional[float]
    hunter_count: Optional[float]
    hunter_days: Optional[float]


# ── Helpers ──────────────────────────────────────────────────────────────────


def get_unit_features(con, hunt_unit: str, species: str, year: int) -> dict:
    """Build feature dict for a single prediction."""
    # Historical success (3yr avg from years before target)
    hist = con.execute(f"""
        SELECT AVG(success_pct) AS avg_success,
               AVG(CAST(hunter_days AS FLOAT) / NULLIF(hunter_count, 0)) AS avg_days_per_hunter
        FROM harvest
        WHERE hunt_unit = '{hunt_unit}'
          AND species = '{species}'
          AND weapon_type = 'All Weapons Combined'
          AND season_year BETWEEN {year - 3} AND {year - 1}
    """).fetchone()

    success_3yr_avg = hist[0] if hist[0] is not None else 10.0
    days_per_hunter = hist[1] if hist[1] is not None else 6.0

    # Weather features for the target year (or most recent available)
    weather = con.execute(f"""
        SELECT
            ROUND(AVG(temperature_2m_mean), 1)  AS temp_mean,
            ROUND(MIN(temperature_2m_min), 1)   AS temp_min_season,
            ROUND(MAX(temperature_2m_max), 1)   AS temp_max_season,
            ROUND(STDDEV(temperature_2m_mean), 1) AS temp_std,
            ROUND(
                AVG(CASE WHEN EXTRACT(MONTH FROM CAST(date AS DATE)) <= 9 THEN temperature_2m_mean END) -
                AVG(CASE WHEN EXTRACT(MONTH FROM CAST(date AS DATE)) >= 11 THEN temperature_2m_mean END),
            1) AS temp_early_late_delta,
            ROUND(SUM(precipitation_sum), 2)    AS precip_total_in,
            COUNT(CASE WHEN precipitation_sum > 0.1 THEN 1 END) AS precip_days,
            ROUND(SUM(snowfall_sum), 2)         AS snow_total_in,
            COUNT(CASE WHEN snowfall_sum > 0 THEN 1 END) AS snow_days,
            ROUND(MAX(snow_depth_max), 1)       AS snow_depth_max,
            MIN(CASE WHEN snowfall_sum > 0 THEN
                EXTRACT(DOY FROM CAST(date AS DATE)) END) AS first_snow_doy,
            ROUND(AVG(wind_speed_10m_max), 1)   AS wind_avg_max,
            ROUND(MAX(wind_gusts_10m_max), 1)   AS wind_gust_max,
            COUNT(CASE WHEN wind_speed_10m_max > 20 THEN 1 END) AS high_wind_days,
            ROUND(AVG(pressure_msl_mean), 1)    AS pressure_mean,
            ROUND(STDDEV(pressure_msl_mean), 2) AS pressure_std,
            ROUND(AVG(daylight_duration) / 3600, 2) AS daylight_avg_hrs
        FROM weather
        WHERE hunt_unit = '{hunt_unit}'
          AND season_year = {year}
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
    features["year_offset"] = year - 2003

    # One-hot encode unit + species
    for u in PANHANDLE_UNITS:
        features[f"hunt_unit_{u}"] = 1.0 if u == hunt_unit else 0.0
    for s in SPECIES_LIST:
        features[f"species_{s}"] = 1.0 if s == species else 0.0

    return features, success_3yr_avg


# ── Endpoints ────────────────────────────────────────────────────────────────


@app.get("/")
def root():
    return {
        "app": "Tagout",
        "version": "0.1.0",
        "description": "Idaho Panhandle hunting success prediction",
    }


@app.post("/v1/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    if req.species not in SPECIES_LIST:
        raise HTTPException(400, f"Species must be one of {SPECIES_LIST}")
    if req.hunt_unit not in PANHANDLE_UNITS:
        raise HTTPException(400, f"Hunt unit must be one of {PANHANDLE_UNITS}")

    con = get_db()
    features, hist_avg = get_unit_features(con, req.hunt_unit, req.species, req.year)
    con.close()

    # Build feature vector in model's expected order
    feature_names = model_meta["features"]
    X = pd.DataFrame([{f: features.get(f, -999) for f in feature_names}])

    pred = float(model.predict(X)[0])
    pred = max(0, min(100, round(pred, 1)))

    # Top contributing features (from model importance)
    importance = model_meta.get("feature_importance", {})
    top = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]
    top_factors = {k: round(v, 3) for k, v in top}

    return PredictResponse(
        species=req.species,
        hunt_unit=req.hunt_unit,
        year=req.year,
        predicted_success_pct=pred,
        historical_avg=round(hist_avg, 1) if hist_avg else None,
        confidence_note="Based on 22 years of IDFG harvest data + seasonal weather patterns",
        top_factors=top_factors,
    )


@app.get("/v1/predict/map")
def predict_map(
    species: str = Query("Elk"),
    year: int = Query(2024),
):
    if species not in SPECIES_LIST:
        raise HTTPException(400, f"Species must be one of {SPECIES_LIST}")

    con = get_db()
    results = []
    for unit in PANHANDLE_UNITS:
        features, hist_avg = get_unit_features(con, unit, species, year)
        feature_names = model_meta["features"]
        X = pd.DataFrame([{f: features.get(f, -999) for f in feature_names}])
        pred = float(model.predict(X)[0])
        pred = max(0, min(100, round(pred, 1)))
        results.append(UnitScore(
            hunt_unit=unit,
            species=species,
            predicted_success_pct=pred,
            historical_avg=round(hist_avg, 1) if hist_avg else None,
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
    # Filter to Panhandle units only
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
