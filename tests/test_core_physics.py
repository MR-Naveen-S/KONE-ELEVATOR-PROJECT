"""
Unit Tests for Core Physics & Accounting (Section 4 & Section 11)
Validates hand-calculated cases, schema sign conventions, and energy balance residuals.
"""

import math
import pytest
import numpy as np
from core.supercap import (
    compute_supercap_energy,
    compute_usable_energy,
    compute_soc,
    compute_voltage_from_soc,
    compute_boost_duty,
    compute_bank_params,
    compute_max_power_limit,
    compute_soh
)
from core.mechanics import (
    compute_elevator_force,
    compute_ideal_trip_energy,
    compute_mechanical_power
)
from core.electrical import (
    compute_pmsm_foc,
    compute_inverter_dc_power,
    compute_rectifier_current,
    update_brake_chopper
)
from core.schema import ElevatorSignals
from core.accounting import compute_trip_accounting
from adapters.web_sim_adapter import WebSimAdapter

def test_hand_calculated_supercap_energy():
    """Hand-calculated check from prompt: 15 F, 100->200 V gives E_usable = 62.5 Wh."""
    C = 15.0 # Farads
    Vmin = 100.0 # Volts
    Vmax = 200.0 # Volts
    E_joules = compute_usable_energy(C, Vmax, Vmin)
    E_wh = E_joules / 3600.0
    assert math.isclose(E_joules, 225000.0, rel_tol=1e-5), f"Expected 225,000 J, got {E_joules}"
    assert math.isclose(E_wh, 62.5, rel_tol=1e-5), f"Expected 62.5 Wh, got {E_wh}"

def test_supercap_soc():
    """Verify SoC is 0 at Vmin, 1 at Vmax, and 0.5 at 158.11 V."""
    Vmin, Vmax = 100.0, 200.0
    assert compute_soc(100.0, Vmax, Vmin) == 0.0
    assert compute_soc(200.0, Vmax, Vmin) == 1.0
    
    # At 50% SoC: V^2 = 100^2 + 0.5*(200^2 - 100^2) = 10000 + 15000 = 25000 => V = sqrt(25000)
    V_half = math.sqrt(25000.0)
    assert math.isclose(compute_soc(V_half, Vmax, Vmin), 0.5, rel_tol=1e-4)
    assert math.isclose(compute_voltage_from_soc(0.5, Vmax, Vmin), V_half, rel_tol=1e-4)

def test_bank_scaling():
    """Verify series/parallel cell scaling."""
    C_cell = 1125.0
    ESR_cell = 0.035 / 75.0
    V_cell = 2.7
    Ns = 75
    Np = 1
    C_bank, V_bank, ESR_bank = compute_bank_params(C_cell, ESR_cell, V_cell, Ns, Np)
    assert math.isclose(C_bank, 15.0, rel_tol=1e-5)
    assert math.isclose(V_bank, 202.5, rel_tol=1e-5)
    assert math.isclose(ESR_bank, 0.035, rel_tol=1e-5)

def test_ideal_trip_energy():
    """Verify constant-speed ideal trip energy: (m_car + m_load - m_cw) * g * h."""
    m_car = 1000.0
    m_load = 800.0
    m_cw = 1400.0
    h = 30.0
    g = 9.81
    # delta_m = 1800 - 1400 = 400 kg
    # E_ideal = 400 * 9.81 * 30 = 117,720 J = 32.7 Wh
    E_joules = compute_ideal_trip_energy(m_car, m_load, m_cw, h, g, eta=1.0)
    assert math.isclose(E_joules, 117720.0, rel_tol=1e-5)
    assert math.isclose(E_joules / 3600.0, 32.7, rel_tol=1e-4)

def test_inverter_efficiency():
    """Verify inverter power signs and efficiencies."""
    # Motoring: Pe = +10,000 W => P_dc = 10000 / 0.97
    P_inv_motor = compute_inverter_dc_power(10000.0, 0.97)
    assert P_inv_motor > 10000.0
    assert math.isclose(P_inv_motor, 10000.0 / 0.97, rel_tol=1e-4)

    # Regen: Pe = -10,000 W => P_dc = -10000 * 0.97
    P_inv_regen = compute_inverter_dc_power(-10000.0, 0.97)
    assert P_inv_regen < 0.0
    assert math.isclose(P_inv_regen, -9700.0, rel_tol=1e-4)

def test_boost_duty():
    """Verify ideal boost converter duty cycle: D = 1 - Vsc/Vdc."""
    D = compute_boost_duty(150.0, 600.0)
    assert math.isclose(D, 0.75, rel_tol=1e-5)

def test_soh_and_eol():
    """Verify SOH computation and EOL criteria."""
    # Nominal healthy state
    soh_c, soh_esr, overall, is_eol = compute_soh(15.0, 15.0, 0.035, 0.035)
    assert soh_c == 100.0 and soh_esr == 100.0 and overall == 100.0 and not is_eol

    # Degraded to 80% capacitance
    soh_c, soh_esr, overall, is_eol = compute_soh(12.0, 15.0, 0.035, 0.035)
    assert math.isclose(soh_c, 80.0)
    assert is_eol, "C <= 80% must trigger EOL"

    # Degraded to 200% ESR
    soh_c, soh_esr, overall, is_eol = compute_soh(15.0, 15.0, 0.070, 0.035)
    assert math.isclose(soh_esr, 50.0)
    assert is_eol, "ESR >= 200% must trigger EOL"

def test_schema_sign_enforcement():
    """Verify that negative P_grid, negative P_brake, etc. raise ValueError."""
    sig_valid = ElevatorSignals(P_grid=100.0, P_brake=0.0, P_aux=250.0)
    assert sig_valid.validate_signs()

    with pytest.raises(ValueError, match="P_grid cannot be negative"):
        ElevatorSignals(P_grid=-10.0).validate_signs()

    with pytest.raises(ValueError, match="P_brake cannot be negative"):
        ElevatorSignals(P_brake=-5.0).validate_signs()

def test_energy_balance_residuals_on_simulated_trip():
    """
    Run a full trip with WebSimAdapter and verify:
    Residual < 1.5% on all checks!
    """
    sim = WebSimAdapter()
    sim.reset({"load": 800.0, "mode": "alt", "stage": 2})

    # Collect 1-second signals for one full trip
    signals = []
    # Step until move completes
    for _ in range(35):
        s = sim.step(dt=1.0)
        signals.append(s)

    acct = compute_trip_accounting(signals)
    print(f"Residual Check 1: {acct.residual_check1_pct:.3f} %")
    print(f"Residual Check 2: {acct.residual_check2_pct:.3f} %")
    print(f"Max Bus Residual Check 3: {acct.max_bus_residual_pct:.3f} %")

    # Verify acceptance criteria: residual < 1.5%
    assert acct.residual_check1_pct < 1.5, f"Check 1 failed: {acct.residual_check1_pct}% >= 1.5%"
    assert acct.residual_check2_pct < 1.5, f"Check 2 failed: {acct.residual_check2_pct}% >= 1.5%"
    assert acct.max_bus_residual_pct < 1.5, f"Check 3 failed: {acct.max_bus_residual_pct}% >= 1.5%"
    assert not acct.data_quality_warning, f"Unexpected DATA_QUALITY_WARNING: {acct.warning_reasons}"

if __name__ == "__main__":
    pytest.main(["-v", __file__])
