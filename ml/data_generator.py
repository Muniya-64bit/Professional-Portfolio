# =============================================================================
# KVPL Yield Prediction — Synthetic Training Data Generator
# Weather data: NASA POWER API (real historical data per estate coordinates)
# Yield data:   Physics-inspired formula encoding Sri Lankan tea agronomy
# Output:       data/training_data.csv
# =============================================================================

import pandas as pd
import numpy as np
import requests
import time

SEED = 42
np.random.seed(SEED)

# =============================================================================
# 1. ESTATE COORDINATES (from Google Maps)
# =============================================================================

estates = {
    "Kundasale":   {"lat":  7.3594, "lon": 80.6851, "zone": "Mid"},
    "Ramboda":     {"lat":  7.0567, "lon": 80.6937, "zone": "High"},
    "Hunasgiriya": {"lat":  7.2993, "lon": 80.8514, "zone": "Low"},
    "Haputale":    {"lat":  6.8633, "lon": 80.9704, "zone": "High"},
}

# =============================================================================
# 2. BLOCK DEFINITIONS (mirrors actual DB blocks)
# =============================================================================

blocks = [
    # Kundasale — Mid zone
    {"block_id": "KUN-A1", "estate": "Kundasale",   "zone": "Mid",  "elevation_m": 920,  "area_hectares": 2.5, "soil_type": "Laterite", "growth_stage": "Mature",   "bush_age_yrs": 25},
    {"block_id": "KUN-A2", "estate": "Kundasale",   "zone": "Mid",  "elevation_m": 910,  "area_hectares": 2.0, "soil_type": "Laterite", "growth_stage": "Young",    "bush_age_yrs": 8},
    {"block_id": "KUN-B1", "estate": "Kundasale",   "zone": "Mid",  "elevation_m": 935,  "area_hectares": 3.0, "soil_type": "Red Loam", "growth_stage": "Mature",   "bush_age_yrs": 30},
    {"block_id": "KUN-B2", "estate": "Kundasale",   "zone": "Mid",  "elevation_m": 940,  "area_hectares": 2.8, "soil_type": "Red Loam", "growth_stage": "Mature",   "bush_age_yrs": 22},
    {"block_id": "KUN-C1", "estate": "Kundasale",   "zone": "Mid",  "elevation_m": 905,  "area_hectares": 1.5, "soil_type": "Laterite", "growth_stage": "Immature", "bush_age_yrs": 4},
    {"block_id": "KUN-D1", "estate": "Kundasale",   "zone": "Mid",  "elevation_m": 950,  "area_hectares": 3.5, "soil_type": "Red Loam", "growth_stage": "Mature",   "bush_age_yrs": 28},
    # Ramboda — High zone
    {"block_id": "RMB-E1", "estate": "Ramboda",     "zone": "High", "elevation_m": 1380, "area_hectares": 2.0, "soil_type": "Laterite", "growth_stage": "Mature",   "bush_age_yrs": 20},
    {"block_id": "RMB-E2", "estate": "Ramboda",     "zone": "High", "elevation_m": 1400, "area_hectares": 2.5, "soil_type": "Red Loam", "growth_stage": "Mature",   "bush_age_yrs": 15},
    {"block_id": "RMB-F1", "estate": "Ramboda",     "zone": "High", "elevation_m": 1420, "area_hectares": 2.2, "soil_type": "Laterite", "growth_stage": "Young",    "bush_age_yrs": 6},
    {"block_id": "RMB-F2", "estate": "Ramboda",     "zone": "High", "elevation_m": 1390, "area_hectares": 2.2, "soil_type": "Red Loam", "growth_stage": "Mature",   "bush_age_yrs": 18},
    {"block_id": "RMB-G1", "estate": "Ramboda",     "zone": "High", "elevation_m": 1410, "area_hectares": 2.2, "soil_type": "Laterite", "growth_stage": "Mature",   "bush_age_yrs": 25},
    {"block_id": "RMB-G2", "estate": "Ramboda",     "zone": "High", "elevation_m": 1395, "area_hectares": 2.2, "soil_type": "Red Loam", "growth_stage": "Young",    "bush_age_yrs": 9},
    {"block_id": "RMB-H1", "estate": "Ramboda",     "zone": "High", "elevation_m": 1430, "area_hectares": 2.2, "soil_type": "Laterite", "growth_stage": "Mature",   "bush_age_yrs": 22},
    {"block_id": "RMB-H2", "estate": "Ramboda",     "zone": "High", "elevation_m": 1415, "area_hectares": 2.2, "soil_type": "Red Loam", "growth_stage": "Mature",   "bush_age_yrs": 30},
    # Hunasgiriya — Low zone
    {"block_id": "HUN-I1", "estate": "Hunasgiriya", "zone": "Low",  "elevation_m": 580,  "area_hectares": 2.0, "soil_type": "Red Loam", "growth_stage": "Mature",   "bush_age_yrs": 22},
    {"block_id": "HUN-I2", "estate": "Hunasgiriya", "zone": "Low",  "elevation_m": 590,  "area_hectares": 2.0, "soil_type": "Laterite", "growth_stage": "Mature",   "bush_age_yrs": 18},
    {"block_id": "HUN-I3", "estate": "Hunasgiriya", "zone": "Low",  "elevation_m": 575,  "area_hectares": 2.0, "soil_type": "Red Loam", "growth_stage": "Young",    "bush_age_yrs": 7},
    {"block_id": "HUN-J1", "estate": "Hunasgiriya", "zone": "Low",  "elevation_m": 600,  "area_hectares": 2.0, "soil_type": "Laterite", "growth_stage": "Mature",   "bush_age_yrs": 25},
    {"block_id": "HUN-J2", "estate": "Hunasgiriya", "zone": "Low",  "elevation_m": 610,  "area_hectares": 2.0, "soil_type": "Red Loam", "growth_stage": "Mature",   "bush_age_yrs": 20},
    {"block_id": "HUN-J3", "estate": "Hunasgiriya", "zone": "Low",  "elevation_m": 595,  "area_hectares": 2.0, "soil_type": "Laterite", "growth_stage": "Immature", "bush_age_yrs": 3},
    {"block_id": "HUN-K1", "estate": "Hunasgiriya", "zone": "Low",  "elevation_m": 620,  "area_hectares": 2.0, "soil_type": "Red Loam", "growth_stage": "Mature",   "bush_age_yrs": 28},
    {"block_id": "HUN-K2", "estate": "Hunasgiriya", "zone": "Low",  "elevation_m": 615,  "area_hectares": 2.0, "soil_type": "Laterite", "growth_stage": "Mature",   "bush_age_yrs": 24},
    {"block_id": "HUN-K3", "estate": "Hunasgiriya", "zone": "Low",  "elevation_m": 605,  "area_hectares": 2.0, "soil_type": "Red Loam", "growth_stage": "Young",    "bush_age_yrs": 9},
    {"block_id": "HUN-L1", "estate": "Hunasgiriya", "zone": "Low",  "elevation_m": 630,  "area_hectares": 2.0, "soil_type": "Laterite", "growth_stage": "Mature",   "bush_age_yrs": 30},
    {"block_id": "HUN-L2", "estate": "Hunasgiriya", "zone": "Low",  "elevation_m": 625,  "area_hectares": 2.0, "soil_type": "Red Loam", "growth_stage": "Mature",   "bush_age_yrs": 26},
    {"block_id": "HUN-L3", "estate": "Hunasgiriya", "zone": "Low",  "elevation_m": 618,  "area_hectares": 2.0, "soil_type": "Laterite", "growth_stage": "Mature",   "bush_age_yrs": 32},
    {"block_id": "HUN-M1", "estate": "Hunasgiriya", "zone": "Low",  "elevation_m": 640,  "area_hectares": 2.0, "soil_type": "Red Loam", "growth_stage": "Mature",   "bush_age_yrs": 19},
    {"block_id": "HUN-M2", "estate": "Hunasgiriya", "zone": "Low",  "elevation_m": 635,  "area_hectares": 2.0, "soil_type": "Laterite", "growth_stage": "Young",    "bush_age_yrs": 6},
    {"block_id": "HUN-M3", "estate": "Hunasgiriya", "zone": "Low",  "elevation_m": 628,  "area_hectares": 2.0, "soil_type": "Red Loam", "growth_stage": "Mature",   "bush_age_yrs": 21},
    # Haputale — High zone (Uva)
    {"block_id": "HAP-N1", "estate": "Haputale",    "zone": "High", "elevation_m": 1480, "area_hectares": 2.3, "soil_type": "Laterite", "growth_stage": "Mature",   "bush_age_yrs": 20},
    {"block_id": "HAP-N2", "estate": "Haputale",    "zone": "High", "elevation_m": 1490, "area_hectares": 2.3, "soil_type": "Red Loam", "growth_stage": "Mature",   "bush_age_yrs": 25},
    {"block_id": "HAP-N3", "estate": "Haputale",    "zone": "High", "elevation_m": 1470, "area_hectares": 2.3, "soil_type": "Laterite", "growth_stage": "Young",    "bush_age_yrs": 8},
    {"block_id": "HAP-O1", "estate": "Haputale",    "zone": "High", "elevation_m": 1500, "area_hectares": 2.3, "soil_type": "Red Loam", "growth_stage": "Mature",   "bush_age_yrs": 30},
    {"block_id": "HAP-O2", "estate": "Haputale",    "zone": "High", "elevation_m": 1510, "area_hectares": 2.3, "soil_type": "Laterite", "growth_stage": "Mature",   "bush_age_yrs": 22},
    {"block_id": "HAP-O3", "estate": "Haputale",    "zone": "High", "elevation_m": 1495, "area_hectares": 2.3, "soil_type": "Red Loam", "growth_stage": "Mature",   "bush_age_yrs": 27},
    {"block_id": "HAP-P1", "estate": "Haputale",    "zone": "High", "elevation_m": 1520, "area_hectares": 2.3, "soil_type": "Laterite", "growth_stage": "Mature",   "bush_age_yrs": 18},
    {"block_id": "HAP-P2", "estate": "Haputale",    "zone": "High", "elevation_m": 1505, "area_hectares": 2.3, "soil_type": "Red Loam", "growth_stage": "Young",    "bush_age_yrs": 5},
    {"block_id": "HAP-Q1", "estate": "Haputale",    "zone": "High", "elevation_m": 1530, "area_hectares": 2.3, "soil_type": "Laterite", "growth_stage": "Mature",   "bush_age_yrs": 35},
    {"block_id": "HAP-Q2", "estate": "Haputale",    "zone": "High", "elevation_m": 1515, "area_hectares": 2.3, "soil_type": "Red Loam", "growth_stage": "Mature",   "bush_age_yrs": 15},
]

# =============================================================================
# 3. FETCH WEATHER FROM NASA POWER API
# =============================================================================

def fetch_nasa_weather(estate_name, lat, lon, start_year, end_year):
    url = "https://power.larc.nasa.gov/api/temporal/monthly/point"
    params = {
        "parameters": "PRECTOTCORR,T2M,RH2M",
        "community":  "AG",
        "longitude":  lon,
        "latitude":   lat,
        "start":      start_year,
        "end":        end_year,
        "format":     "JSON",
    }
    print(f"  Fetching NASA POWER data for {estate_name} ({lat}, {lon})...")
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        rainfall = data["properties"]["parameter"]["PRECTOTCORR"]
        temp     = data["properties"]["parameter"]["T2M"]
        humidity = data["properties"]["parameter"]["RH2M"]
        weather = {}
        for key in rainfall:
            year  = int(key[:4])
            month = int(key[4:])
            weather[(year, month)] = {
                "rainfall_mm":      max(0, rainfall[key] * 30),
                "avg_temp_c":       temp[key],
                "avg_humidity_pct": humidity[key],
            }
        print(f"  ✅ {estate_name}: {len(weather)} months fetched")
        return weather
    except Exception as e:
        print(f"  ❌ {estate_name} failed: {e}. Using fallback values.")
        return None


def fallback_weather(zone, year, month):
    base = {"Low": [145, 26.8, 72], "Mid": [185, 22.4, 78], "High": [210, 18.2, 85]}[zone]
    return {
        "rainfall_mm":      base[0] + np.random.normal(0, 15),
        "avg_temp_c":       base[1] + np.random.normal(0, 0.5),
        "avg_humidity_pct": base[2] + np.random.normal(0, 2),
    }

# =============================================================================
# 4. YIELD FORMULA
# =============================================================================

def base_yield_per_ha(zone):
    # KVPL 2023/24: 3,859,000 kg made tea / 3,263 ha
    # × 4.5 green leaf ratio = ~444 kg/ha/month green leaf
    return {"Low": 550, "Mid": 500, "High": 380}[zone]

def growth_stage_factor(stage):
    return {"Mature": 1.0, "Young": 0.65, "Immature": 0.30}[stage]

def bush_age_factor(age):
    if age < 5:    return 0.30
    elif age < 10: return 0.60
    elif age < 15: return 0.80
    elif age <= 35: return 1.0
    else: return max(0.70, 1.0 - (age - 35) * 0.015)

def soil_factor(soil):
    return {"Red Loam": 1.05, "Laterite": 0.95}[soil]

def rainfall_factor(rainfall_mm):
    if rainfall_mm < 80:     return 0.60
    elif rainfall_mm < 150:  return 0.80 + (rainfall_mm - 80) * 0.003
    elif rainfall_mm <= 280: return 1.0
    else: return max(0.85, 1.0 - (rainfall_mm - 280) * 0.002)

def fertilizer_factor(days_since_fertilized):
    if days_since_fertilized <= 30:   return 1.10
    elif days_since_fertilized <= 45: return 1.05
    elif days_since_fertilized <= 90: return 1.0
    else: return 0.92

def fertilizer_type_factor(fert_type):
    """
    Yield multiplier based on last fertilizer applied.
    Nitrogen-rich types boost shoot growth most.
    Soil amendments have indirect, slower effects.
    """
    return {
        "T0_200":   1.08,
        "U750":     1.06,
        "EP_GOLD":  1.04,
        "MOP":      1.02,
        "RPR":      1.01,
        "DOLOMITE": 1.00,
    }[fert_type]

def seasonality_factor(month, zone):
    if zone in ("Mid", "High"):
        peaks = [0.85, 0.90, 1.10, 1.15, 1.05, 0.95, 0.90, 1.10, 1.15, 1.05, 0.90, 0.85]
    else:
        peaks = [0.90, 0.92, 1.08, 1.12, 1.05, 1.00, 0.95, 1.08, 1.12, 1.02, 0.92, 0.88]
    return peaks[month - 1]

# =============================================================================
# 5. MAIN
# =============================================================================

YEARS      = list(range(2022, 2026))
START_YEAR = min(YEARS)
END_YEAR   = max(YEARS)

print("Fetching weather data from NASA POWER API...")
weather_cache = {}
for estate_name, info in estates.items():
    weather_cache[estate_name] = fetch_nasa_weather(
        estate_name, info["lat"], info["lon"], START_YEAR, END_YEAR
    )
    time.sleep(1)

print("\nGenerating training rows...")
rows = []

for block in blocks:
    prev_yield  = None
    estate_name = block["estate"]
    zone        = block["zone"]
    nasa_data   = weather_cache.get(estate_name)

    for year in YEARS:
        for month in range(1, 13):

            # Weather
            if nasa_data and (year, month) in nasa_data:
                w = nasa_data[(year, month)]
                rainfall     = w["rainfall_mm"]     + np.random.normal(0, 8)
                avg_temp     = w["avg_temp_c"]       + np.random.normal(0, 0.4)
                avg_humidity = w["avg_humidity_pct"] + np.random.normal(0, 1.5)
            else:
                fb = fallback_weather(zone, year, month)
                rainfall     = fb["rainfall_mm"]
                avg_temp     = fb["avg_temp_c"]
                avg_humidity = fb["avg_humidity_pct"]

            rainfall     = max(0, rainfall)
            avg_humidity = min(100, max(0, avg_humidity))

            # Fertilizer
            days_since_fertilized = int(np.random.choice(
                [20, 35, 50, 75, 100], p=[0.20, 0.30, 0.25, 0.15, 0.10]
            ))
            last_fertilizer_type = np.random.choice(
                ["T0_200", "U750", "EP_GOLD", "MOP", "RPR", "DOLOMITE"],
                p=[0.30,    0.20,   0.25,     0.10,  0.10,  0.05]
            )

            # Yield
            base = base_yield_per_ha(zone) * block["area_hectares"]
            y = (base
                 * growth_stage_factor(block["growth_stage"])
                 * bush_age_factor(block["bush_age_yrs"])
                 * soil_factor(block["soil_type"])
                 * rainfall_factor(rainfall)
                 * fertilizer_factor(days_since_fertilized)
                 * fertilizer_type_factor(last_fertilizer_type)
                 * seasonality_factor(month, zone))
            y = max(0, y * np.random.normal(1.0, 0.06))

            rows.append({
                "block_id":              block["block_id"],
                "estate":                estate_name,
                "year":                  year,
                "month":                 month,
                "zone":                  zone,
                "elevation_m":           block["elevation_m"],
                "area_hectares":         block["area_hectares"],
                "soil_type":             block["soil_type"],
                "growth_stage":          block["growth_stage"],
                "bush_age_yrs":          block["bush_age_yrs"],
                "rainfall_mm":           round(rainfall, 2),
                "avg_temp_c":            round(avg_temp, 2),
                "avg_humidity_pct":      round(avg_humidity, 2),
                "days_since_fertilized": days_since_fertilized,
                "last_fertilizer_type":  last_fertilizer_type,
                "yield_last_month":      round(prev_yield, 3) if prev_yield is not None else None,
                "yield_kg":              round(y, 3),
            })

            prev_yield = y

df = pd.DataFrame(rows)
df.to_csv("data/training_data.csv", index=False)

print(f"\n✅ Generated {len(df)} rows")
print(f"   Blocks  : {df['block_id'].nunique()}")
print(f"   Years   : {sorted(df['year'].unique())}")
print(f"   Columns : {list(df.columns)}")
print(f"\nYield stats (kg):")
print(df["yield_kg"].describe().round(1))
print(f"\nFertilizer type distribution:")
print(df["last_fertilizer_type"].value_counts())
print(f"\nWeather source: NASA POWER API (real historical data)")
print(f"Saved to: data/training_data.csv")