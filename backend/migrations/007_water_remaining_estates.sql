INSERT INTO water_baseline (factory_id, baseline_year, baseline_intensity, annual_target_pct, set_by)
SELECT f.id, 2023, 3.6, 2.0, NULL
FROM factory f JOIN estate e ON f.estate_id = e.id
WHERE e.name = 'Ramboda Heights'
ON CONFLICT (factory_id) DO NOTHING;

INSERT INTO water_baseline (factory_id, baseline_year, baseline_intensity, annual_target_pct, set_by)
SELECT f.id, 2023, 3.8, 2.0, NULL
FROM factory f JOIN estate e ON f.estate_id = e.id
WHERE e.name = 'Hunasgiriya Estate'
ON CONFLICT (factory_id) DO NOTHING;

INSERT INTO water_baseline (factory_id, baseline_year, baseline_intensity, annual_target_pct, set_by)
SELECT f.id, 2023, 3.7, 2.0, NULL
FROM factory f JOIN estate e ON f.estate_id = e.id
WHERE e.name = 'Haputale Park'
ON CONFLICT (factory_id) DO NOTHING;

INSERT INTO water_usage (factory_id, year, month, water_m3, yield_kg, track_status)
SELECT f.id, d.year, d.month, d.water_m3, d.yield_kg, d.track_status
FROM factory f JOIN estate e ON f.estate_id = e.id,
(VALUES
    (2026, 1, 7200.0, 2000000.0, 'on_track'),
    (2026, 2, 7350.0, 2100000.0, 'on_track'),
    (2026, 3, 7800.0, 2050000.0, 'at_risk'),
    (2026, 4, 7400.0, 2150000.0, 'on_track'),
    (2026, 5, 7100.0, 2200000.0, 'on_track')
) AS d(year, month, water_m3, yield_kg, track_status)
WHERE e.name = 'Ramboda Heights'
ON CONFLICT (factory_id, year, month) DO NOTHING;

INSERT INTO water_usage (factory_id, year, month, water_m3, yield_kg, track_status)
SELECT f.id, d.year, d.month, d.water_m3, d.yield_kg, d.track_status
FROM factory f JOIN estate e ON f.estate_id = e.id,
(VALUES
    (2026, 1, 9500.0, 2500000.0, 'on_track'),
    (2026, 2, 9800.0, 2600000.0, 'on_track'),
    (2026, 3, 10500.0, 2550000.0, 'at_risk'),
    (2026, 4, 9900.0, 2620000.0, 'on_track'),
    (2026, 5, 9600.0, 2700000.0, 'on_track')
) AS d(year, month, water_m3, yield_kg, track_status)
WHERE e.name = 'Hunasgiriya Estate'
ON CONFLICT (factory_id, year, month) DO NOTHING;

INSERT INTO water_usage (factory_id, year, month, water_m3, yield_kg, track_status)
SELECT f.id, d.year, d.month, d.water_m3, d.yield_kg, d.track_status
FROM factory f JOIN estate e ON f.estate_id = e.id,
(VALUES
    (2026, 1, 8100.0, 2200000.0, 'on_track'),
    (2026, 2, 8300.0, 2350000.0, 'on_track'),
    (2026, 3, 8900.0, 2300000.0, 'at_risk'),
    (2026, 4, 8500.0, 2400000.0, 'on_track'),
    (2026, 5, 8200.0, 2450000.0, 'on_track')
) AS d(year, month, water_m3, yield_kg, track_status)
WHERE e.name = 'Haputale Park'
ON CONFLICT (factory_id, year, month) DO NOTHING;