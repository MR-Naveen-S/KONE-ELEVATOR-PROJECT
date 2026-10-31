"""
Demand & Generation Forecaster (Section 7):
Predicts per 5-min and 15-min intervals:
- trip_count
- net_demand_kWh
- regen_kWh
- peak_kW
Features: hour_sin, hour_cos, weekday, holiday_flag, lag1, lag2, lag4, lag96, rolling statistics.
Models:
1. Naive Seasonal Baseline (predicts value from 24h prior / same time slot)
2. LightGBM Quantile Regressors (P10, P50, P90)
Metrics: RMSE, MAPE, Pinball Loss.
Includes Automated Benchmark Gate (must beat naive baseline).
Includes Slow-Timescale Charge/Discharge Schedule Planner.
"""

import math
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import root_mean_squared_error, mean_absolute_percentage_error

def pinball_loss(y_true: np.ndarray, y_pred: np.ndarray, alpha: float) -> float:
    """Pinball (quantile) loss: max(alpha*(y - y_hat), (alpha - 1)*(y - y_hat))"""
    diff = y_true - y_pred
    return float(np.mean(np.maximum(alpha * diff, (alpha - 1.0) * diff)))

class NaiveSeasonalForecaster:
    """
    Naive Seasonal Baseline: Predicts today's slot value from yesterday's same slot (lag 96 for 15-min).
    """
    def __init__(self, season_length: int = 96):
        self.season_length = season_length

    def fit(self, y: np.ndarray):
        self.y_hist = np.copy(y)

    def predict(self, y_history: np.ndarray, horizon: int = 1) -> np.ndarray:
        preds = []
        for h in range(horizon):
            idx = len(y_history) - self.season_length + h
            val = y_history[idx] if idx >= 0 else y_history[-1]
            preds.append(max(0.0, float(val)))
        return np.array(preds)

class DemandForecaster:
    def __init__(self, interval_minutes: int = 15):
        self.interval_min = interval_minutes
        self.slots_per_day = int(1440 / interval_minutes) # 96 slots for 15-min, 288 for 5-min
        self.models: Dict[str, Dict[str, lgb.LGBMRegressor]] = {} # target -> {P10, P50, P90}
        self.targets = ["trip_count", "net_demand_kWh", "regen_kWh", "peak_kW"]
        self.quantiles = [0.10, 0.50, 0.90]
        self.naive_baseline = NaiveSeasonalForecaster(season_length=self.slots_per_day)

    def extract_features(self, df_intervals: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Creates time-of-day harmonic features, calendar indicators, and lag features.
        """
        df = df_intervals.copy()
        
        # Harmonic time of day
        hour = (df["slot_idx"] * self.interval_min / 60.0) % 24.0
        df["hour_sin"] = np.sin(2.0 * np.pi * hour / 24.0)
        df["hour_cos"] = np.cos(2.0 * np.pi * hour / 24.0)
        if "weekday" not in df.columns:
            df["weekday"] = 1
        df["is_weekend"] = (df["weekday"] >= 5).astype(int)
        if "is_holiday" not in df.columns:
            df["is_holiday"] = 0
        else:
            df["is_holiday"] = df["is_holiday"].astype(int)

        feature_cols = ["hour_sin", "hour_cos", "weekday", "is_weekend", "is_holiday"]

        # Add lag features for each target
        for tgt in self.targets:
            if tgt in df.columns:
                df[f"{tgt}_lag1"] = df[tgt].shift(1).bfill()
                df[f"{tgt}_lag2"] = df[tgt].shift(2).bfill()
                df[f"{tgt}_lag4"] = df[tgt].shift(4).bfill()
                df[f"{tgt}_lag_season"] = df[tgt].shift(self.slots_per_day).bfill()
                df[f"{tgt}_roll_mean4"] = df[tgt].rolling(4, min_periods=1).mean()
                feature_cols.extend([
                    f"{tgt}_lag1", f"{tgt}_lag2", f"{tgt}_lag4",
                    f"{tgt}_lag_season", f"{tgt}_roll_mean4"
                ])

        X = df[feature_cols].copy()
        y = df[self.targets].copy() if all(t in df.columns for t in self.targets) else pd.DataFrame()
        return X, y

    def train_and_evaluate(
        self,
        df_train_intervals: pd.DataFrame,
        df_val_intervals: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Trains LightGBM quantile models and checks the Section 7 acceptance criterion:
        Must beat Naive Seasonal Baseline on held-out test data!
        """
        X_train, y_train = self.extract_features(df_train_intervals)
        X_val, y_val = self.extract_features(df_val_intervals)

        results = {}
        all_beat_naive = True

        for tgt in self.targets:
            self.models[tgt] = {}
            tgt_results = {}
            
            # 1. Evaluate Naive Baseline
            y_val_arr = y_val[tgt].to_numpy()
            y_train_arr = y_train[tgt].to_numpy()
            y_full_hist = np.concatenate([y_train_arr, y_val_arr])
            
            # Naive prediction using seasonal lag
            naive_preds = []
            for i in range(len(y_val)):
                idx = len(y_train_arr) + i - self.slots_per_day
                val = y_full_hist[idx] if idx >= 0 else y_train_arr[-1]
                naive_preds.append(max(0.0, float(val)))
            naive_preds = np.array(naive_preds)
            
            naive_rmse = float(root_mean_squared_error(y_val_arr, naive_preds))
            tgt_results["naive_rmse"] = round(naive_rmse, 4)

            # 2. Train Quantile Models (P10, P50, P90)
            preds_dict = {}
            for q in self.quantiles:
                q_name = f"P{int(q*100)}"
                model = lgb.LGBMRegressor(
                    objective="quantile",
                    alpha=q,
                    n_estimators=60,
                    learning_rate=0.08,
                    num_leaves=15,
                    random_state=42,
                    verbose=-1
                )
                model.fit(X_train, y_train[tgt])
                self.models[tgt][q_name] = model
                
                preds = model.predict(X_val)
                preds = np.maximum(0.0, preds)
                preds_dict[q_name] = preds
                
                ploss = pinball_loss(y_val_arr, preds, q)
                tgt_results[f"{q_name}_pinball_loss"] = round(ploss, 4)

            # Check P50 RMSE vs Naive
            p50_rmse = float(root_mean_squared_error(y_val_arr, preds_dict["P50"]))
            tgt_results["p50_rmse"] = round(p50_rmse, 4)
            beat_naive = (p50_rmse < naive_rmse)
            tgt_results["beat_naive"] = beat_naive
            tgt_results["rmse_improvement_pct"] = round((naive_rmse - p50_rmse) / max(naive_rmse, 1e-4) * 100.0, 2)
            
            if not beat_naive:
                all_beat_naive = False
                
            results[tgt] = tgt_results

        results["gate_passed_beat_naive"] = all_beat_naive
        return results

    def predict_next_window(self, features_df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """Generates P10, P50, P90 predictions for the upcoming interval."""
        predictions = {}
        for tgt in self.targets:
            predictions[tgt] = {}
            for q_name, model in self.models.get(tgt, {}).items():
                val = float(model.predict(features_df)[0])
                predictions[tgt][q_name] = max(0.0, round(val, 3))
        return predictions

    def generate_advisory_schedule(
        self,
        forecast_p50_kW: List[float],
        tariff_schedule_INR_kWh: List[float],
        start_hour: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Slow-Timescale Energy Management Scheduler:
        Identifies high-tariff and peak-demand windows ahead of time and schedules:
        - "Pre-charge supercap to X% SoC before peak window"
        - "Hold and discharge supercap to shave peak kW during peak window"
        """
        schedule = []
        n_slots = len(forecast_p50_kW)
        slot_hours = [(start_hour + i * self.interval_min / 60.0) % 24.0 for i in range(n_slots)]

        for i in range(n_slots):
            h = slot_hours[i]
            tariff = tariff_schedule_INR_kWh[int(h) % 24]
            peak_fc = forecast_p50_kW[i]
            
            # Check if next 1-2 hours contains peak tariff
            next_hours = [(h + offset) % 24 for offset in [1.0, 2.0]]
            next_tariffs = [tariff_schedule_INR_kWh[int(nh) % 24] for nh in next_hours]
            approaching_peak_tariff = any(t >= 11.0 for t in next_tariffs) and (tariff < 10.0)

            if approaching_peak_tariff:
                action = "PRE_CHARGE"
                target_soc = 85.0
                reason = "Pre-charge from low-tariff grid ahead of approaching peak pricing window"
            elif tariff >= 11.0 or peak_fc > 15.0:
                action = "PEAK_SHAVE_DISCHARGE"
                target_soc = 30.0
                reason = "Discharge supercapacitor to shave peak demand and offset ₹11.50/kWh peak tariff"
            elif 12.0 <= h < 14.0 or 17.0 <= h < 19.0:
                action = "REGEN_CAPTURE_PRIORITY"
                target_soc = 50.0
                reason = "Hold headroom in supercapacitor to absorb high regenerative braking energy"
            else:
                action = "STANDARD_OPERATION"
                target_soc = 60.0
                reason = "Normal real-time autonomous droop control"

            schedule.append({
                "slot_idx": i,
                "hour": round(h, 2),
                "action": action,
                "target_soc_pct": target_soc,
                "forecast_peak_kW": round(peak_fc, 2),
                "tariff_INR_kWh": tariff,
                "reason": reason
            })

        return schedule
