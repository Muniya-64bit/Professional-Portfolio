# =============================================================================
# KVPL Yield Prediction — Data Preprocessing
# Input:  data/training_data.csv
# Output: data/X_train.csv, data/X_test.csv,
#         data/y_train.csv, data/y_test.csv,
#         data/encoders.pkl
# =============================================================================

import pandas as pd
import numpy as np
import joblib
from sklearn.preprocessing import LabelEncoder, StandardScaler

df = pd.read_csv("data/training_data.csv")

# =============================================================================
# STEP 1: Handle nulls in yield_last_month
# Fill with block's own mean yield — better than 0 or global mean
# =============================================================================

df["yield_last_month"] = df.groupby("block_id")["yield_last_month"].transform(
    lambda x: x.fillna(x.mean())
)

print(f"Nulls after fill: {df['yield_last_month'].isnull().sum()}")

# =============================================================================
# STEP 2: Drop columns not needed for training
# block_id and estate are identifiers, not features
# year and month are used for splitting only, not as model features
# =============================================================================

df = df.drop(columns=["block_id", "estate"])

# =============================================================================
# STEP 3: Encode categorical columns
# zone, soil_type, growth_stage, last_fertilizer_type → integers
# =============================================================================

categorical_cols = ["zone", "soil_type", "growth_stage", "last_fertilizer_type"]
encoders = {}

for col in categorical_cols:
    le = LabelEncoder()
    df[col] = le.fit_transform(df[col])
    encoders[col] = le
    print(f"{col}: {dict(zip(le.classes_, le.transform(le.classes_)))}")

# =============================================================================
# STEP 4: Time-based train/test split
# Train: 2022-2024 (3 years), Test: 2025 (1 year)
# Never shuffle time series data
# =============================================================================

train = df[df["year"] < 2025].drop(columns=["year", "month"])
test  = df[df["year"] == 2025].drop(columns=["year", "month"])

X_train = train.drop(columns=["yield_kg"])
y_train = train["yield_kg"]

X_test = test.drop(columns=["yield_kg"])
y_test = test["yield_kg"]

print(f"\nTrain: {X_train.shape}, Test: {X_test.shape}")
print(f"Features: {list(X_train.columns)}")

# =============================================================================
# STEP 5: Scale numeric features
# XGBoost doesn't strictly need scaling but it helps convergence
# Fit scaler on train only — never fit on test
# =============================================================================

numeric_cols = [
    "elevation_m", "area_hectares", "bush_age_yrs",
    "rainfall_mm", "avg_temp_c", "avg_humidity_pct",
    "days_since_fertilized", "yield_last_month"
]

scaler = StandardScaler()
X_train[numeric_cols] = scaler.fit_transform(X_train[numeric_cols])
X_test[numeric_cols]  = scaler.transform(X_test[numeric_cols])

# =============================================================================
# STEP 6: Save everything
# =============================================================================

X_train.to_csv("data/X_train.csv", index=False)
X_test.to_csv("data/X_test.csv",   index=False)
y_train.to_csv("data/y_train.csv", index=False)
y_test.to_csv("data/y_test.csv",   index=False)

joblib.dump({"encoders": encoders, "scaler": scaler}, "data/encoders.pkl")

print("\n✅ Preprocessing complete")
print(f"   X_train: {X_train.shape}")
print(f"   X_test:  {X_test.shape}")
print(f"   Saved: data/X_train.csv, X_test.csv, y_train.csv, y_test.csv, encoders.pkl")