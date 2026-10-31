import pytest
import numpy as np

from core.health import SupercapHealthEstimator

def test_health_estimator_nominal():
    health = SupercapHealthEstimator(C_0=15.0, ESR_0=0.035, T_amb=25.0)
    
    # Run 10 seconds of idle
    res = health.update(Vsc=130.0, Isc=0.0, dt=1.0, time_now=10.0)
    assert res["SOH_pct"] == 100.0
    assert res["is_eol"] is False
    assert res["SC_temp_degC"] == 25.0
    assert res["RUL_years_nominal"] > 8.0

def test_online_c_and_esr_estimation():
    health = SupercapHealthEstimator(C_0=15.0, ESR_0=0.035)

    # 1. Simulate a current step: I jumps from 0 to 50 A
    # ESR = Delta_V / Delta_I = (150.0 - 148.25) / 50.0 = 1.75 / 50 = 0.035 Ohm
    health.update(Vsc=150.0, Isc=0.0, dt=1.0, time_now=1.0)
    res_esr = health.update(Vsc=148.25, Isc=50.0, dt=1.0, time_now=2.0)
    assert abs(res_esr["ESR_est_mOhm"] - 35.0) < 5.0

    # 2. Simulate a constant current charging segment: 30 A charging (Isc = -30 A)
    # Delta_V = 20 V over 10 seconds => C = 30 * 10 / 20 = 15.0 F
    V = 130.0
    for t in range(3, 15):
        V += 2.0
        health.update(Vsc=V, Isc=-30.0, dt=1.0, time_now=float(t))
    # Segment finishes when current drops to 0
    res_c = health.update(Vsc=V, Isc=0.0, dt=1.0, time_now=16.0)
    assert abs(res_c["C_est_F"] - 15.0) < 1.0

def test_degradation_injector_and_alerts():
    health = SupercapHealthEstimator(C_0=15.0, ESR_0=0.035)

    # Inject 78% C fade and 210% ESR growth (EOL conditions)
    health.inject_degradation(C_multiplier=0.78, ESR_multiplier=2.1)
    res = health.update(Vsc=130.0, Isc=0.0, dt=1.0, time_now=1.0)

    assert res["is_eol"] is True
    assert res["SOH_C_pct"] <= 80.0
    assert res["SOH_ESR_pct"] < 50.0
    assert len(res["alerts"]) >= 1
    assert any(a["alert_type"] == "LOW_SOH" and a["level"] == "CRITICAL" for a in res["alerts"])

    # Reset degradation injector
    health.reset_degradation()
    res_reset = health.update(Vsc=130.0, Isc=0.0, dt=1.0, time_now=2.0)
    assert res_reset["is_eol"] is False
    assert res_reset["SOH_pct"] == 100.0

def test_thermal_model_temperature_rise():
    health = SupercapHealthEstimator(C_0=15.0, ESR_0=0.035, T_amb=25.0, R_th=1.2, C_th=250.0)

    # Heavy continuous cycling with 80 A RMS
    for t in range(1, 100):
        res = health.update(Vsc=150.0, Isc=80.0, dt=1.0, time_now=float(t))

    # Temperature must rise above ambient
    assert res["SC_temp_degC"] > 25.0
    assert res["aging_acceleration"] > 1.0
