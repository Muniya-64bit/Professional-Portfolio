# KVPL Yield Prediction — ML Module

Machine learning module for the KVPL Input & Resource Optimization System.  
Predicts monthly tea yield per block to feed the Labour Allocation Optimizer (Module 4).

---

## Overview

This module satisfies **FR-LAO-03** from the SRS:
> *"System shall accept target kg yield per block (fed from Yield Prediction or manually entered)."*

The model predicts **expected green leaf yield (kg) per block per month**, which the Flask backend uses to calculate optimal worker allocation across blocks.

---

## Pipeline

```
data_generator.py   →   preprocess.py   →   train_model.py   →   api.py
     ↓                       ↓                    ↓                  ↓
training_data.csv    X_train / X_test       yield_model.pkl     POST /predict-batch
(NASA POWER weather)  encoders.pkl          R² = 0.95           port 8000
```

---

## Files

| File | Purpose |
|---|---|
| `data_generator.py` | Generates synthetic training data using real NASA POWER weather |
| `eda.ipynb` | Exploratory data analysis — distributions, correlations, seasonality |
| `preprocess.py` | Encodes categoricals, scales numerics, time-based train/test split |
| `train_model.py` | Trains XGBoost model, evaluates, saves model and metrics |
| `api.py` | FastAPI service exposing `/predict-batch` endpoint on port 8000 |
| `data/training_data.csv` | Generated training dataset (1,872 rows, 17 features) |
| `data/encoders.pkl` | LabelEncoders + StandardScaler saved from preprocessing |
| `models/yield_model.pkl` | Trained XGBoost model |
| `models/model_metrics.json` | Model evaluation metrics |
| `models/feature_importance.png` | Feature importance chart |
| `models/actual_vs_predicted.png` | Actual vs predicted scatter plot |

---

## Features Used

| Feature | Type | Description |
|---|---|---|
| `zone` | Categorical | Agro-climatic zone — Low / Mid / High |
| `elevation_m` | Numeric | Block elevation in metres |
| `area_hectares` | Numeric | Block area in hectares |
| `soil_type` | Categorical | Laterite / Red Loam |
| `growth_stage` | Categorical | Mature / Young / Immature |
| `bush_age_yrs` | Numeric | Age of tea bushes in years |
| `rainfall_mm` | Numeric | Monthly rainfall (NASA POWER, mm/month) |
| `avg_temp_c` | Numeric | Monthly average temperature (NASA POWER, °C) |
| `avg_humidity_pct` | Numeric | Monthly average humidity (NASA POWER, %) |
| `days_since_fertilized` | Numeric | Days since last fertilizer application |
| `last_fertilizer_type` | Categorical | Most recent fertilizer type applied |
| `yield_last_month` | Numeric | Previous month's yield — lag feature |

**Target variable:** `yield_kg` — total green leaf yield for the block that month

---

## Data Sources

- **Weather data:** [NASA POWER API](https://power.larc.nasa.gov/) — real historical monthly weather at each estate's GPS coordinates (2022–2025)
- **Yield calibration:** KVPL Integrated Annual Report 2023/24 — 3,859,000 kg made tea / 3,263 ha mature tea × 4.5 green leaf ratio = ~444 kg/ha/month
- **Block data:** Mirrors actual DB blocks from migration 006

---

## Model Performance

| Metric | Value |
|---|---|
| Train R² | 0.9969 |
| Test R² | 0.9499 |
| Test RMSE | 92.91 kg |
| Test MAE | 66.71 kg |
| CV Mean R² (5-fold) | 0.8666 |

Train/test split: **time-based** — 2022–2024 for training, 2025 for testing.  
Random shuffling is not used as this is time series data.

---

## API Reference

Base URL: `http://localhost:8000`

### GET /health
Check if the service is running and model is loaded.

**Response:**
```json
{
  "status": "ok",
  "model_version": "xgboost_v1",
  "model_loaded": true
}
```

---

### POST /predict-batch
Predict yield for multiple blocks in one request.

**Request:**
```json
{
  "blocks": [
    {
      "block_id": "uuid-here",
      "zone": "Mid",
      "elevation_m": 920,
      "area_hectares": 2.5,
      "soil_type": "Laterite",
      "growth_stage": "Mature",
      "bush_age_yrs": 25,
      "rainfall_mm": 185.5,
      "avg_temp_c": 22.4,
      "avg_humidity_pct": 78.2,
      "days_since_fertilized": 35,
      "last_fertilizer_type": "T0_200",
      "yield_last_month": 850.0
    }
  ],
  "year": 2026,
  "month": 6
}
```

**Response:**
```json
{
  "predictions": [
    {
      "block_id": "uuid-here",
      "predicted_yield_kg": 1322.05,
      "confidence_low": 1189.84,
      "confidence_high": 1454.25,
      "model_version": "xgboost_v1"
    }
  ]
}
```

---

### POST /predict-single
Predict yield for a single block.  
Request body: single `BlockInput` object (same fields as above, no wrapping array).

---

## Setup & Running

### Prerequisites
All ML dependencies are installed in the shared backend virtual environment.

```powershell
# From project root, activate venv
.venv\Scripts\Activate.ps1

# Install ML dependencies (if not already installed)
pip install pandas numpy scikit-learn xgboost fastapi uvicorn joblib requests
```

### Reproduce the full pipeline

```powershell
cd ml

# Step 1: Generate training data (fetches real weather from NASA POWER)
python data_generator.py

# Step 2: Preprocess
python preprocess.py

# Step 3: Train model
python train_model.py

# Step 4: Start API
python api.py
```

### Start API only (model already trained)

```powershell
cd ml
python api.py
# API runs at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

---

## Integration with Flask Backend

The Flask backend calls this service when generating a labour plan.  
Set the environment variable in `backend/.env`:

```env
FASTAPI_URL=http://localhost:8000
```

The backend sends block data → receives predicted yield → stores in `yield_prediction` table → labour planner uses it for worker allocation.

If the FastAPI service is unavailable, the system falls back to manual yield entry as specified in FR-LAO-03.

---

## Database Tables (Migration 006)

| Table | Description |
|---|---|
| `block.elevation_m` | New column added for ML feature |
| `block.bush_age_yrs` | New column added for ML feature |
| `block.zone` | New column added for ML feature |
| `block_yield_record` | Monthly actual yield per block (training ground truth) |
| `estate_weather` | Monthly weather per estate |
| `yield_prediction` | Model output — predicted yield per block per month |

---

## Notes

- The model is trained on **synthetic data** calibrated against real KVPL annual report figures and real NASA POWER weather data. In production, it should be retrained as real block-level yield records accumulate in `block_yield_record`.
- Confidence interval is ±10% of predicted value, based on the model's empirical error rate (~8.5% MAE/mean).
- Model version is tracked in `yield_prediction.model_version` to support future retraining.