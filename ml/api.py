# =============================================================================
# KVPL Yield Prediction — FastAPI Service
# Endpoints: GET /health, POST /predict-batch, POST /predict-single
# Port: 8000
# =============================================================================

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

# =============================================================================
# Load model and encoders on startup
# =============================================================================

MODEL_VERSION = "xgboost_v1"

try:
    model    = joblib.load("models/yield_model.pkl")
    artifacts = joblib.load("data/encoders.pkl")
    encoders  = artifacts["encoders"]
    scaler    = artifacts["scaler"]
    print("✅ Model and encoders loaded successfully")
except Exception as e:
    print(f"❌ Failed to load model: {e}")
    model    = None
    encoders = None
    scaler   = None

app = FastAPI(
    title="KVPL Yield Prediction API",
    description="Predicts monthly tea yield per block for labour planning",
    version="1.0.0"
)

# =============================================================================
# Pydantic schemas
# =============================================================================

class BlockInput(BaseModel):
    block_id:              str
    zone:                  str      # Low / Mid / High
    elevation_m:           int
    area_hectares:         float
    soil_type:             str      # Laterite / Red Loam
    growth_stage:          str      # Mature / Young / Immature
    bush_age_yrs:          int
    rainfall_mm:           float
    avg_temp_c:            float
    avg_humidity_pct:      float
    days_since_fertilized: int
    last_fertilizer_type:  str      # T0_200 / U750 / EP_GOLD / MOP / RPR / DOLOMITE
    yield_last_month:      Optional[float] = None

class PredictBatchRequest(BaseModel):
    blocks: List[BlockInput]
    year:   int
    month:  int

class BlockPrediction(BaseModel):
    block_id:           str
    predicted_yield_kg: float
    confidence_low:     float
    confidence_high:    float
    model_version:      str

class PredictBatchResponse(BaseModel):
    predictions: List[BlockPrediction]

# =============================================================================
# Helper: preprocess a single block input into model features
# =============================================================================

NUMERIC_COLS = [
    "elevation_m", "area_hectares", "bush_age_yrs",
    "rainfall_mm", "avg_temp_c", "avg_humidity_pct",
    "days_since_fertilized", "yield_last_month"
]

FEATURE_ORDER = [
    "zone", "elevation_m", "area_hectares", "soil_type",
    "growth_stage", "bush_age_yrs", "rainfall_mm",
    "avg_temp_c", "avg_humidity_pct", "days_since_fertilized",
    "last_fertilizer_type", "yield_last_month"
]

def preprocess_block(block: BlockInput, fallback_yield: float = 0.0) -> np.ndarray:
    """Convert a BlockInput into a scaled feature vector."""

    yield_last = block.yield_last_month if block.yield_last_month is not None else fallback_yield

    row = {
        "zone":                  encoders["zone"].transform([block.zone])[0],
        "elevation_m":           block.elevation_m,
        "area_hectares":         block.area_hectares,
        "soil_type":             encoders["soil_type"].transform([block.soil_type])[0],
        "growth_stage":          encoders["growth_stage"].transform([block.growth_stage])[0],
        "bush_age_yrs":          block.bush_age_yrs,
        "rainfall_mm":           block.rainfall_mm,
        "avg_temp_c":            block.avg_temp_c,
        "avg_humidity_pct":      block.avg_humidity_pct,
        "days_since_fertilized": block.days_since_fertilized,
        "last_fertilizer_type":  encoders["last_fertilizer_type"].transform([block.last_fertilizer_type])[0],
        "yield_last_month":      yield_last,
    }

    df = pd.DataFrame([row])[FEATURE_ORDER]
    df[NUMERIC_COLS] = scaler.transform(df[NUMERIC_COLS])
    return df.values

# =============================================================================
# Routes
# =============================================================================

@app.get("/health")
def health():
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {
        "status":        "ok",
        "model_version": MODEL_VERSION,
        "model_loaded":  True
    }


@app.post("/predict-batch", response_model=PredictBatchResponse)
def predict_batch(request: PredictBatchRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    predictions = []

    for block in request.blocks:
        try:
            features = preprocess_block(block)
            pred     = float(model.predict(features)[0])
            pred     = max(0, pred)

            # Confidence interval: ±10% based on model MAE/mean ratio
            low  = round(pred * 0.90, 2)
            high = round(pred * 1.10, 2)

            predictions.append(BlockPrediction(
                block_id=           block.block_id,
                predicted_yield_kg= round(pred, 2),
                confidence_low=     low,
                confidence_high=    high,
                model_version=      MODEL_VERSION
            ))

        except Exception as e:
            raise HTTPException(
                status_code=422,
                detail=f"Error processing block {block.block_id}: {str(e)}"
            )

    return PredictBatchResponse(predictions=predictions)


@app.post("/predict-single", response_model=BlockPrediction)
def predict_single(block: BlockInput):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        features = preprocess_block(block)
        pred     = float(model.predict(features)[0])
        pred     = max(0, pred)

        return BlockPrediction(
            block_id=           block.block_id,
            predicted_yield_kg= round(pred, 2),
            confidence_low=     round(pred * 0.90, 2),
            confidence_high=    round(pred * 1.10, 2),
            model_version=      MODEL_VERSION
        )

    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


# =============================================================================
# Run
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)