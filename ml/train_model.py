# =============================================================================
# KVPL Yield Prediction — Model Training
# Input:  data/X_train.csv, X_test.csv, y_train.csv, y_test.csv
# Output: models/yield_model.pkl, models/model_metrics.json
# =============================================================================

import pandas as pd
import numpy as np
import joblib
import json
import matplotlib.pyplot as plt
from xgboost import XGBRegressor
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.model_selection import cross_val_score

# =============================================================================
# STEP 1: Load data
# =============================================================================

X_train = pd.read_csv("data/X_train.csv")
X_test  = pd.read_csv("data/X_test.csv")
y_train = pd.read_csv("data/y_train.csv").squeeze()
y_test  = pd.read_csv("data/y_test.csv").squeeze()

print(f"X_train: {X_train.shape}, X_test: {X_test.shape}")

# =============================================================================
# STEP 2: Train XGBoost
# =============================================================================

model = XGBRegressor(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    n_jobs=-1
)

model.fit(X_train, y_train,
          eval_set=[(X_test, y_test)],
          verbose=50)

# =============================================================================
# STEP 3: Evaluate
# =============================================================================

y_pred_train = model.predict(X_train)
y_pred_test  = model.predict(X_test)

r2_train  = r2_score(y_train, y_pred_train)
r2_test   = r2_score(y_test,  y_pred_test)
rmse_test = np.sqrt(mean_squared_error(y_test, y_pred_test))
mae_test  = mean_absolute_error(y_test, y_pred_test)

print(f"\n{'='*40}")
print(f"Train R²  : {r2_train:.4f}")
print(f"Test  R²  : {r2_test:.4f}")
print(f"Test  RMSE: {rmse_test:.2f} kg")
print(f"Test  MAE : {mae_test:.2f} kg")
print(f"{'='*40}")

# Cross-validation on training set
cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring="r2")
print(f"\n5-Fold CV R² scores: {cv_scores.round(4)}")
print(f"Mean CV R²: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

# =============================================================================
# STEP 4: Feature importance plot
# =============================================================================

feat_importance = pd.Series(model.feature_importances_, index=X_train.columns)
feat_importance = feat_importance.sort_values(ascending=True)

plt.figure(figsize=(10, 6))
feat_importance.plot(kind="barh", color="steelblue")
plt.title("Feature Importance (XGBoost)")
plt.xlabel("Importance Score")
plt.tight_layout()
plt.savefig("models/feature_importance.png", dpi=150)
plt.show()
print("Saved: models/feature_importance.png")

# =============================================================================
# STEP 5: Actual vs Predicted plot
# =============================================================================

plt.figure(figsize=(8, 6))
plt.scatter(y_test, y_pred_test, alpha=0.3, color="steelblue")
plt.plot([y_test.min(), y_test.max()],
         [y_test.min(), y_test.max()], "r--", linewidth=2)
plt.xlabel("Actual yield_kg")
plt.ylabel("Predicted yield_kg")
plt.title(f"Actual vs Predicted (Test Set) — R²={r2_test:.4f}")
plt.tight_layout()
plt.savefig("models/actual_vs_predicted.png", dpi=150)
plt.show()
print("Saved: models/actual_vs_predicted.png")

# =============================================================================
# STEP 6: Save model and metrics
# =============================================================================

joblib.dump(model, "models/yield_model.pkl")

metrics = {
    "r2_train": round(r2_train, 4),
    "r2_test":  round(r2_test, 4),
    "rmse_test": round(rmse_test, 2),
    "mae_test":  round(mae_test, 2),
    "cv_r2_mean": round(cv_scores.mean(), 4),
    "cv_r2_std":  round(cv_scores.std(), 4),
    "model_version": "xgboost_v1",
    "features": list(X_train.columns),
    "n_train": len(X_train),
    "n_test":  len(X_test)
}

with open("models/model_metrics.json", "w") as f:
    json.dump(metrics, f, indent=2)

print(f"\n✅ Model saved: models/yield_model.pkl")
print(f"✅ Metrics saved: models/model_metrics.json")