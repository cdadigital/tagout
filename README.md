# tagout

Hunting harvest data pipeline + prediction model for Idaho, powered by Idaho Fish & Game public data.

## What it does

Pulls harvest records from Idaho Fish & Game (1998–2024), combines with NOAA weather data, and runs probability models for hunting success by **species**, **hunt unit**, **weapon type**, and **weather conditions**.

## Stack

- **Data**: Idaho F&G Harvest Finder + ArcGIS REST API
- **Storage**: DuckDB (local exploration) → Supabase/PostGIS (production)
- **Modeling**: scikit-learn / XGBoost
- **Weather**: NOAA Climate Data API
- **API**: FastAPI
- **Frontend**: Next.js (Phase 3)

## Project structure

```
tagout/
├── data/
│   ├── raw/          # Downloaded CSVs and shapefiles
│   ├── processed/    # Cleaned, normalized data
│   └── shapefiles/   # Hunt unit boundaries (GIS)
├── src/
│   ├── ingest/       # Data ingestion scripts
│   ├── model/        # Prediction model
│   └── api/          # FastAPI routes
├── notebooks/        # Exploration and analysis
└── scripts/          # One-off utility scripts
```

## Phases

| Phase | Focus |
|-------|-------|
| 1 | Data acquisition + exploration |
| 2 | Prediction model |
| 3 | App + API |
| 4 | Weather integration |

## Data sources

- [Idaho F&G Harvest Finder](https://fishandgame.idaho.gov/ifwis/huntplanner/harvestfinder.aspx)
- [Idaho F&G Open Data Portal (ArcGIS)](https://data-idfggis.opendata.arcgis.com/)
- [NOAA Climate Data API](https://www.ncdc.noaa.gov/cdo-web/webservices/v2)
