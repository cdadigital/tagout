"""
Train XGBoost model to predict hunting success rate.

Target: success_pct (0-100)
Features: weather aggregates + historical success + unit characteristics

Validation: hold out 2022-2024 as test set.

Usage:
    python -m src.model.train
"""

import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import cross_val_score
import xgboost as xgb

from src.model.features import build_training_data

MODEL_DIR = Path(__file__).parents[2] / "data" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

TARGET = "success_pct"

FEATURE_COLS = [
    # Weather
    "temp_mean",
    "temp_min_season",
    "temp_max_season",
    "temp_std",
    "temp_early_late_delta",
    "precip_total_in",
    "precip_days",
    "snow_total_in",
    "snow_days",
    "snow_depth_max",
    "first_snow_doy",
    "wind_avg_max",
    "wind_gust_max",
    "high_wind_days",
    "pressure_mean",
    "pressure_std",
    "daylight_avg_hrs",
    # Historical
    "success_3yr_avg",
    "days_per_hunter",
    # Trend
    "year_offset",
]

# Categorical features encoded as numeric
CAT_FEATURES = ["hunt_unit", "species"]

TEST_YEARS = [2022, 2023, 2024]


def encode_categoricals(df: pd.DataFrame) -> pd.DataFrame:
    """One-hot encode hunt_unit and species."""
    df = df.copy()
    for col in CAT_FEATURES:
        dummies = pd.get_dummies(df[col], prefix=col, drop_first=False)
        df = pd.concat([df, dummies], axis=1)
    dummy_cols = [c for c in df.columns if any(c.startswith(f"{cat}_") for cat in CAT_FEATURES)]
    return df, dummy_cols


def train():
    print("Building training data...")
    df = build_training_data()

    # Drop rows with missing target
    df = df.dropna(subset=[TARGET])
    print(f"Total samples: {len(df)}")

    # Encode categoricals
    df, dummy_cols = encode_categoricals(df)
    all_features = FEATURE_COLS + dummy_cols

    # Train/test split by year
    train_df = df[~df["season_year"].isin(TEST_YEARS)].copy()
    test_df = df[df["season_year"].isin(TEST_YEARS)].copy()
    print(f"Train: {len(train_df)} ({train_df['season_year'].min()}-{train_df['season_year'].max()})")
    print(f"Test:  {len(test_df)} ({test_df['season_year'].min()}-{test_df['season_year'].max()})")

    X_train = train_df[all_features].fillna(-999)
    y_train = train_df[TARGET]
    X_test = test_df[all_features].fillna(-999)
    y_test = test_df[TARGET]

    # XGBoost
    model = xgb.XGBRegressor(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=1.0,
        reg_lambda=2.0,
        min_child_weight=3,
        random_state=42,
    )

    print("\nTraining XGBoost...")
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    # Cross-validation on training set
    cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring="neg_mean_absolute_error")
    print(f"5-fold CV MAE: {-cv_scores.mean():.2f} (+/- {cv_scores.std():.2f})")

    # Test set performance
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    print(f"\nTest Set Performance:")
    print(f"  MAE:  {mae:.2f} percentage points")
    print(f"  RMSE: {rmse:.2f}")
    print(f"  R²:   {r2:.3f}")

    # Baseline: predict 3-year average
    baseline_pred = test_df["success_3yr_avg"].fillna(y_train.mean())
    baseline_mae = mean_absolute_error(y_test, baseline_pred)
    print(f"\nBaseline (3yr avg) MAE: {baseline_mae:.2f}")
    print(f"Model improvement: {baseline_mae - mae:.2f} pp")

    # Feature importance
    importance = dict(zip(all_features, model.feature_importances_))
    sorted_imp = sorted(importance.items(), key=lambda x: x[1], reverse=True)
    print(f"\nTop 15 features:")
    for feat, imp in sorted_imp[:15]:
        print(f"  {feat:30s} {imp:.4f}")

    # Save model
    model_path = MODEL_DIR / "xgb_success.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    print(f"\nSaved model: {model_path}")

    # Save feature list and metadata
    meta = {
        "features": all_features,
        "target": TARGET,
        "test_years": TEST_YEARS,
        "metrics": {"mae": round(mae, 2), "rmse": round(rmse, 2), "r2": round(r2, 3)},
        "baseline_mae": round(baseline_mae, 2),
        "feature_importance": {k: round(float(v), 4) for k, v in sorted_imp},
    }
    meta_path = MODEL_DIR / "model_meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"Saved metadata: {meta_path}")

    # Show predictions vs actuals for test set
    test_df = test_df.copy()
    test_df["predicted"] = y_pred.round(1)
    print(f"\nTest predictions sample:")
    cols = ["hunt_unit", "species", "season_year", "success_pct", "predicted", "success_3yr_avg"]
    print(test_df[cols].head(20).to_string(index=False))

    return model, meta


if __name__ == "__main__":
    train()
