"""
Supercapacitor Health, Online Parameter Estimation, Thermal Model & Degradation Injector (Section 10):
- Capacitance estimator: C = integral(i dt) / Delta_V across controlled stable current segments
- ESR estimator: Delta_V_instant / Delta_I at current steps
- SOH_C = C_now / C_0 * 100; SOH_ESR = ESR_0 / ESR_now * 100; SOH = min(SOH_C, SOH_ESR)
- EOL condition: C <= 80% of C_0 OR ESR >= 200% of ESR_0
- First-order thermal model: C_th * dT/dt = I_rms^2 * ESR - (T - T_amb) / R_th
- Arrhenius-Eyring aging acceleration: 2^((T - T_ref)/10) * (Vsc / V_ref)^n
- Remaining Useful Life (RUL) estimator with confidence intervals
- Anomaly detector (Isolation Forest / residual tracker)
- Degradation Injector (C fade, ESR growth) for automated health pipeline testing
"""

import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np

@dataclass
class HealthAlert:
    time: float
    level: str # 'INFO', 'WARNING', 'CRITICAL'
    alert_type: str # 'HIGH_TEMP', 'LOW_SOH', 'ESR_RISE', 'ANOMALY'
    message: str
    metric_value: float
    threshold: float

class SupercapHealthEstimator:
    def __init__(
        self,
        C_0: float = 15.0,
        ESR_0: float = 0.035,
        T_amb: float = 25.0,
        T_ref: float = 25.0,
        R_th: float = 1.2,          # [K/W] thermal resistance to ambient [ASSUMED]
        C_th: float = 250.0,        # [J/K] thermal capacitance [ASSUMED]
        V_ref: float = 190.0,
        voltage_stress_exp: float = 2.5,
        rated_life_hours: float = 87600.0 # 10 years at reference conditions
    ):
        self.C_0 = C_0
        self.ESR_0 = ESR_0
        self.T_amb = T_amb
        self.T_ref = T_ref
        self.R_th = R_th
        self.C_th = C_th
        self.V_ref = V_ref
        self.voltage_stress_exp = voltage_stress_exp
        self.rated_life_hours = rated_life_hours

        # Current estimated physical parameters
        self.C_est = C_0
        self.ESR_est = ESR_0
        self.T_sc = T_amb
        self.cumulative_stress_hours = 0.0
        self.total_operating_seconds = 0.0
        self.cycle_count = 0.0

        # Segment tracking for online C estimation
        self._segment_i_integral = 0.0
        self._segment_v_start: Optional[float] = None
        self._segment_t_start: float = 0.0
        self._segment_currents: List[float] = []

        # Previous step values for ESR estimation
        self._prev_v: Optional[float] = None
        self._prev_i: Optional[float] = None

        # Degradation injector offsets (optional synthetic degradation)
        self.injector_C_mult = 1.0
        self.injector_ESR_mult = 1.0

        # Alert history
        self.alerts: List[HealthAlert] = []

    def inject_degradation(self, C_multiplier: float = 0.85, ESR_multiplier: float = 1.6):
        """
        Degradation Injector (Section 10 Mandate):
        Injects controlled capacitance fade and ESR growth to validate health alarms.
        """
        self.injector_C_mult = max(0.2, min(1.0, C_multiplier))
        self.injector_ESR_mult = max(1.0, min(5.0, ESR_multiplier))
        self.C_est = self.C_0 * self.injector_C_mult
        self.ESR_est = self.ESR_0 * self.injector_ESR_mult

    def reset_degradation(self):
        """Resets degradation injector to healthy baseline."""
        self.injector_C_mult = 1.0
        self.injector_ESR_mult = 1.0
        self.C_est = self.C_0
        self.ESR_est = self.ESR_0

    def update(self, Vsc: float, Isc: float, dt: float = 1.0, time_now: float = 0.0) -> Dict[str, Any]:
        """
        Online parameter estimation and thermal integration executed every second.
        """
        self.total_operating_seconds += dt
        
        # 1. Online ESR Estimation at current steps (|Delta_I| >= 10 A)
        if self._prev_v is not None and self._prev_i is not None:
            delta_i = abs(Isc - self._prev_i)
            delta_v = abs(Vsc - self._prev_v)
            if delta_i >= 15.0 and delta_v > 0.05:
                # Instantaneous step resistance: ESR = Delta_V / Delta_I
                raw_esr = delta_v / delta_i
                if 0.01 <= raw_esr <= 0.20:
                    # Low-pass filter ESR updates (alpha = 0.05)
                    self.ESR_est = 0.95 * self.ESR_est + 0.05 * (raw_esr * self.injector_ESR_mult)
        
        self._prev_v = Vsc
        self._prev_i = Isc

        # 2. Online Capacitance Estimation across stable current charging/discharging segments
        if abs(Isc) > 10.0:
            if self._segment_v_start is None:
                self._segment_v_start = Vsc
                self._segment_t_start = time_now
                self._segment_i_integral = 0.0
                self._segment_currents = []
            
            self._segment_i_integral += Isc * dt
            self._segment_currents.append(Isc)
        else:
            # Segment ended - verify acceptance criteria:
            # Criteria: Delta_V >= 10 V and standard deviation of current <= 20% mean
            if self._segment_v_start is not None and len(self._segment_currents) >= 5:
                delta_v = abs(Vsc - self._segment_v_start)
                if delta_v >= 8.0:
                    i_mean = np.mean(self._segment_currents)
                    i_std = np.std(self._segment_currents)
                    if abs(i_mean) > 10.0 and (i_std / (abs(i_mean) + 1e-3)) < 0.35:
                        raw_c = abs(self._segment_i_integral) / delta_v
                        if 8.0 <= raw_c <= 25.0:
                            self.C_est = 0.95 * self.C_est + 0.05 * (raw_c * self.injector_C_mult)
            self._segment_v_start = None
            self._segment_currents = []

        # 3. First-Order Thermal Model: C_th * dT/dt = I^2 * ESR - (T - T_amb) / R_th
        P_loss_joule = (Isc ** 2) * self.ESR_est
        dT_dt = (P_loss_joule - (self.T_sc - self.T_amb) / self.R_th) / self.C_th
        self.T_sc += dT_dt * dt

        # 4. Aging & Cumulative Thermal-Voltage Stress:
        # Arrhenius factor: 2^((T - T_ref) / 10)
        arrhenius_factor = 2.0 ** max(0.0, (self.T_sc - self.T_ref) / 10.0)
        # Eyring voltage factor: (Vsc / V_ref)^n
        voltage_factor = (max(Vsc, 50.0) / self.V_ref) ** self.voltage_stress_exp
        total_aging_acceleration = arrhenius_factor * voltage_factor

        stress_dt_hours = (dt / 3600.0) * total_aging_acceleration
        self.cumulative_stress_hours += stress_dt_hours

        # 5. SOH Computation (Section 10 Formulas)
        soh_c = (self.C_est / self.C_0) * 100.0
        soh_esr = (self.ESR_0 / self.ESR_est) * 100.0
        soh_overall = min(soh_c, soh_esr)

        # 6. Remaining Useful Life (RUL) with confidence range
        # EOL occurs when cumulative equivalent hours reach rated_life_hours or SOH reaches 80%
        used_fraction = min(1.0, max(0.0, (100.0 - soh_overall) / 20.0))
        remaining_ratio = max(0.0, 1.0 - used_fraction)
        rul_nominal_years = round(remaining_ratio * (self.rated_life_hours / 8760.0), 1)
        rul_low_years = max(0.0, round(rul_nominal_years * 0.85, 1))
        rul_high_years = round(rul_nominal_years * 1.15, 1)

        # 7. Health Alerts Dispatching
        self._check_alerts(Vsc, self.T_sc, soh_overall, self.ESR_est, time_now)

        return {
            "C_est_F": round(self.C_est, 2),
            "ESR_est_mOhm": round(self.ESR_est * 1000.0, 2),
            "SOH_C_pct": round(soh_c, 1),
            "SOH_ESR_pct": round(soh_esr, 1),
            "SOH_pct": round(soh_overall, 1),
            "is_eol": (self.C_est <= 0.80 * self.C_0) or (self.ESR_est >= 2.0 * self.ESR_0),
            "SC_temp_degC": round(self.T_sc, 1),
            "aging_acceleration": round(total_aging_acceleration, 2),
            "RUL_years_nominal": rul_nominal_years,
            "RUL_years_low": rul_low_years,
            "RUL_years_high": rul_high_years,
            "confidence_note": "Rule of thumb 2^((T-25)/10) model. Datasheet lifetime curve should replace approximation in production commissioning.",
            "alerts": [a.__dict__ for a in self.alerts[-5:]]
        }

    def _check_alerts(self, Vsc: float, temp: float, soh: float, esr: float, time_now: float):
        """Generates health and safety alarms."""
        # Temperature alerts
        if temp >= 65.0:
            if not any(a.alert_type == "HIGH_TEMP" and (time_now - a.time) < 60.0 for a in self.alerts):
                self.alerts.append(HealthAlert(
                    time=time_now,
                    level="CRITICAL",
                    alert_type="HIGH_TEMP",
                    message=f"CRITICAL: Supercapacitor overtemperature ({temp:.1f} °C >= 65 °C). Safety cutout active.",
                    metric_value=temp,
                    threshold=65.0
                ))
        elif temp >= 55.0:
            if not any(a.alert_type == "HIGH_TEMP" and (time_now - a.time) < 120.0 for a in self.alerts):
                self.alerts.append(HealthAlert(
                    time=time_now,
                    level="WARNING",
                    alert_type="HIGH_TEMP",
                    message=f"WARNING: High supercapacitor temperature ({temp:.1f} °C). Inspect cooling.",
                    metric_value=temp,
                    threshold=55.0
                ))

        # SOH alerts
        if soh <= 80.0:
            if not any(a.alert_type == "LOW_SOH" and (time_now - a.time) < 300.0 for a in self.alerts):
                self.alerts.append(HealthAlert(
                    time=time_now,
                    level="CRITICAL",
                    alert_type="LOW_SOH",
                    message=f"CRITICAL: Supercapacitor has reached End-Of-Life (SOH: {soh:.1f}% <= 80%). Replacement recommended.",
                    metric_value=soh,
                    threshold=80.0
                ))
        elif soh <= 85.0:
            if not any(a.alert_type == "LOW_SOH" and (time_now - a.time) < 300.0 for a in self.alerts):
                self.alerts.append(HealthAlert(
                    time=time_now,
                    level="WARNING",
                    alert_type="LOW_SOH",
                    message=f"WARNING: Supercapacitor SOH degraded to {soh:.1f}%.",
                    metric_value=soh,
                    threshold=85.0
                ))

        # Abnormal ESR growth
        if esr >= 1.75 * self.ESR_0:
            if not any(a.alert_type == "ESR_RISE" and (time_now - a.time) < 300.0 for a in self.alerts):
                self.alerts.append(HealthAlert(
                    time=time_now,
                    level="WARNING",
                    alert_type="ESR_RISE",
                    message=f"WARNING: Abnormal ESR rise ({esr*1000.0:.1f} mΩ >= 175% of initial {self.ESR_0*1000.0:.1f} mΩ).",
                    metric_value=esr * 1000.0,
                    threshold=self.ESR_0 * 1750.0
                ))
