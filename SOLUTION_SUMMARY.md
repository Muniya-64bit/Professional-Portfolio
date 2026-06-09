# KVPL — Tea Plantation Input & Resource Optimization System

A full-stack platform for **Kelani Valley Plantations Ltd.** that optimizes the four
major operating inputs across 4 estates (Kundasale, Ramboda, Hunasgiriya, Haputale):
**labour rotation, fertilizer scheduling, water efficiency, and ROI** — backed by an
**ML yield predictor** that feeds the labour planner.

---

## Architecture (4 services)

| Service | Tech | Port | Role |
|---|---|---|---|
| Frontend | Next.js 14 / React 18 | 3000 | Dashboard, login, module tabs |
| Backend | Flask (Python 3) | 5000 | REST API, JWT auth, business logic |
| Database | PostgreSQL 16 (Docker) | 5432 | All persistent state |
| ML service | FastAPI + XGBoost | 8000 | Yield prediction (`/predict-batch`) |

The Flask backend is split into blueprints — `labour`, `water`, `reports`, `roi`,
`fertilizer` — plus `auth` and an APScheduler for monthly auto-generation.

---

## Core flow (how a request moves through the system)

```
Browser (Next.js)
   │  login → JWT stored in localStorage (apiService.js injects Bearer token)
   ▼
Flask backend  ── @token_required + role check (admin > estate_manager > manager)
   │
   ├── reads/writes PostgreSQL (tables + views like v_fertilizer_schedule_alerts)
   │
   └── for yield: POST block data → FastAPI ML service → predicted_yield_kg
                  → stored in yield_prediction → labour planner allocates workers
```

---

## The two signature workflows

### 1. Labour rotation planner
- Each estate has worker groups, blocks, and an **N-round rotation matrix** (every group
  visits every block once per cycle).
- ML predicts yield per block → backend allocates workers **proportionally** → generates a
  plan with block assignments.
- Managers can override a group or record actual yield; a scheduler auto-generates monthly
  plans in production. Falls back to **manual yield entry** if the ML service is down.

### 2. Fertilizer rotation planner
The key design is **template → instance separation**:

- **Programme** = per-estate template
  (*"Kundasale applies T0_200 at 200 kg/ha every 8 weeks to Mature blocks"*)
- **Schedule** = generated instances
  (*"Block A1 is due T0_200 on 2026-07-14"*)

The engine `_generate_schedule_for_estate()` walks every block × programme step through
**3 guards**:
1. Skip zero-area blocks.
2. Skip if an open entry already exists (**idempotent**).
3. Skip if over-fertilized (last application within the interval).

It then computes `due_date` and a `pending` / `due` / `overdue` status. Field staff close
entries by recording an **application**, which atomically marks the schedule `done`.
Alerts surface overdue/due items to the dashboard.

---

## ML pipeline

```
data_generator.py   →   preprocess.py   →   train_model.py   →   api.py
     ↓                       ↓                    ↓                  ↓
training_data.csv    X_train / X_test       yield_model.pkl     POST /predict-batch
(NASA POWER weather)  encoders.pkl          Test R² ≈ 0.95      port 8000
```

- Trained on **synthetic data** calibrated to KVPL's Integrated Annual Report figures and
  **real NASA POWER weather** (2022–2025).
- Predictions carry a ±10% confidence band, based on the model's empirical error rate.

---

## Auth & roles

- JWT bearer tokens (7-day expiry, frontend auto-refreshes within 1 hour of expiry).
- Role hierarchy: `admin` > `estate_manager` > `manager` (read-only, estate-scoped).
- Write endpoints require `admin` or `estate_manager`; `manager` is read-only.
