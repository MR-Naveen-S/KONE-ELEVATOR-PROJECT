"""
Unit Tests for Phase 5: Forecasting & Scenario Generator (Section 7 & Section 11)
Tests:
1. TrafficGenerator produces valid multi-regime daily schedules with seed repeatability.
2. DemandForecaster trains LightGBM quantile models (P10/P50/P90).
3. Section 11 Acceptance Criterion: Forecaster beats Naive Seasonal Baseline on held-out test days.
4. Advisory schedule planner generates pre-charge and peak-shave directives.
"""

import pytest
import numpy as np
import pandas as pd
from forecasting.traffic_generator import TrafficGenerator
from forecasting.demand_forecaster import DemandForecaster
from surrogate.elevator_surrogate import FastElevatorSurrogate
from core.tariffs import TariffManager

def test_traffic_generator_profiles():
    """Verify seed repeatability and regime distributions."""
    tg = TrafficGenerator(n_floors=10, seed=123)
    trips_weekday = tg.generate_day(day_type="weekday", trips_per_day=150)
    assert len(trips_weekday) == 150
    assert trips_weekday[0].request_time_s >= 0.0
    assert trips_weekday[-1].request_time_s <= 86400.0

    # Test seed repeatability
    tg2 = TrafficGenerator(n_floors=10, seed=123)
    trips_repeat = tg2.generate_day(day_type="weekday", trips_per_day=150)
    assert trips_weekday[10].passenger_load_kg == trips_repeat[10].passenger_load_kg

    # Check that balanced loads around 400 kg exist
    balanced_trips = [tr for tr in trips_weekday if 370.0 <= tr.passenger_load_kg <= 430.0]
    assert len(balanced_trips) > 0, "Traffic generator must include balanced loads near 50% rated load!"

def test_forecasting_beats_naive_baseline():
    """
    Section 11 Gate:
    Train on historical days (Days 1-5), test on held-out days (Days 6-7).
    Model must beat Naive Seasonal Baseline on RMSE!
    """
    # Synthesize realistic multi-day 15-minute interval dataset (7 days = 672 slots)
    n_days = 7
    slots_per_day = 96
    total_slots = n_days * slots_per_day
    
    rng = np.random.default_rng(42)
    records = []

    for d in range(n_days):
        weekday = d % 7
        is_wknd = 1 if weekday >= 5 else 0
        for s in range(slots_per_day):
            hour = (s * 15.0 / 60.0) % 24.0
            
            # Base diurnal pattern
            if 8.0 <= hour < 10.0:
                base_trips = 15.0 if not is_wknd else 3.0
                base_dem = 8.0 if not is_wknd else 1.5
                base_reg = 2.0 if not is_wknd else 0.5
                base_pk = 18.0 if not is_wknd else 6.0
            elif 17.0 <= hour < 19.0:
                base_trips = 16.0 if not is_wknd else 4.0
                base_dem = 5.0 if not is_wknd else 1.5
                base_reg = 7.0 if not is_wknd else 1.0 # high regen down-peak
                base_pk = 16.0 if not is_wknd else 5.0
            elif 12.0 <= hour < 14.0:
                base_trips = 12.0 if not is_wknd else 5.0
                base_dem = 6.0 if not is_wknd else 2.0
                base_reg = 4.5 if not is_wknd else 1.0
                base_pk = 15.0 if not is_wknd else 5.0
            elif 0.0 <= hour < 6.0:
                base_trips = 1.0
                base_dem = 0.5
                base_reg = 0.1
                base_pk = 2.0
            else:
                base_trips = 6.0 if not is_wknd else 2.0
                base_dem = 3.0 if not is_wknd else 1.0
                base_reg = 2.0 if not is_wknd else 0.5
                base_pk = 10.0 if not is_wknd else 4.0

            # Add stochastic weather/traffic noise
            trips = max(0, int(base_trips + rng.normal(0.0, 1.5)))
            net_dem = max(0.0, base_dem + rng.normal(0.0, 0.4))
            regen = max(0.0, base_reg + rng.normal(0.0, 0.3))
            peak_kw = max(1.0, base_pk + rng.normal(0.0, 0.8))

            records.append({
                "slot_idx": s,
                "day": d,
                "weekday": weekday,
                "is_weekend": is_wknd,
                "trip_count": float(trips),
                "net_demand_kWh": float(net_dem),
                "regen_kWh": float(regen),
                "peak_kW": float(peak_kw)
            })

    df = pd.DataFrame(records)
    split_slot = 5 * slots_per_day
    df_train = df.iloc[:split_slot].copy()
    df_val = df.iloc[split_slot:].copy()

    forecaster = DemandForecaster(interval_minutes=15)
    results = forecaster.train_and_evaluate(df_train, df_val)

    print("\n--- Forecasting Benchmark vs Naive Baseline ---")
    for tgt in forecaster.targets:
        t_res = results[tgt]
        print(f"Target: {tgt:15s} | Naive RMSE: {t_res['naive_rmse']:6.3f} | LightGBM P50 RMSE: {t_res['p50_rmse']:6.3f} | Beat Naive: {t_res['beat_naive']} (+{t_res['rmse_improvement_pct']}%)")

    assert results["gate_passed_beat_naive"], "Forecasting models must beat Naive Baseline on held-out days!"

def test_advisory_schedule_generation():
    """Verify pre-charge and peak-shave directive generation."""
    forecaster = DemandForecaster(interval_minutes=15)
    tariffs = TariffManager()
    
    # 24 hours = 96 slots
    fc_peak_kW = [4.0] * 96
    # Morning rush peak at 9:00 AM (slot 36)
    fc_peak_kW[36] = 22.0
    
    schedule = forecaster.generate_advisory_schedule(
        forecast_p50_kW=fc_peak_kW,
        tariff_schedule_INR_kWh=tariffs.hourly_schedule,
        start_hour=0.0
    )
    assert len(schedule) == 96
    
    # Check that pre-charge action is generated before peak tariff
    actions = [s["action"] for s in schedule]
    assert "PRE_CHARGE" in actions, "Scheduler must identify approaching peak and schedule PRE_CHARGE!"
    assert "PEAK_SHAVE_DISCHARGE" in actions, "Scheduler must schedule PEAK_SHAVE_DISCHARGE during peak windows!"

if __name__ == "__main__":
    pytest.main(["-v", __file__])
