"""
Unit Tests for Phase 3: Baselines & Counterfactual Savings (Section 11 Criteria)
Tests:
1. When regen exists (e.g. 800 kg load down-trip), Stage 2 (supercap) grid energy < Stage 1 (B0).
2. With balanced load (400 kg = 50% rated load), regen ≈ 0 and savings ≈ 0 (Honesty Requirement).
"""

import pytest
from adapters.web_sim_adapter import WebSimAdapter
from rl.baselines import BaselineB1Controller, CounterfactualSavingsEngine

def test_savings_with_regenerative_load():
    """Verify that with 800 kg load, Stage 2 saves grid energy vs Stage 1 (B0)."""
    sim_b0 = WebSimAdapter()
    sim_b1 = WebSimAdapter()

    # Identical trip sequence: 800 kg load, alt mode, 60 seconds
    sim_b0.reset({"load": 800.0, "stage": 1, "mode": "alt"})
    sim_b1.reset({"load": 800.0, "stage": 2, "mode": "alt"})

    signals_b0 = []
    signals_b1 = []
    ctrl_b1 = BaselineB1Controller()

    for _ in range(60):
        s0 = sim_b0.step(P_sc_ref=0.0, dt=1.0)
        signals_b0.append(s0)

        action = ctrl_b1.compute_action(s0.to_dict())
        s1 = sim_b1.step(P_sc_ref=action, dt=1.0)
        signals_b1.append(s1)

    savings_engine = CounterfactualSavingsEngine()
    results = savings_engine.compare_runs(signals_b0, signals_b1)

    print(f"\n--- 800 kg Heavy Load Trip Results ---")
    print(f"B0 Grid Energy: {results['E_grid_b0_kWh']:.4f} kWh")
    print(f"B1 Grid Energy: {results['E_grid_actual_kWh']:.4f} kWh")
    print(f"Energy Saved: {results['E_saved_kWh']:.4f} kWh ({results['energy_saved_pct']:.1f}%)")
    print(f"B0 Brake Dumped: {results['E_brake_b0_kWh']:.4f} kWh vs B1: {results['E_brake_actual_kWh']:.4f} kWh")
    print(f"Total Money Saved: ₹{results['total_saved_INR']:.2f}")

    assert results["E_grid_actual_kWh"] < results["E_grid_b0_kWh"], "Stage 2 must draw less grid energy than Stage 1!"
    assert results["E_saved_kWh"] > 0.0, "Energy saved must be positive when regen exists!"
    assert results["E_brake_actual_kWh"] < results["E_brake_b0_kWh"], "Brake chopper dissipation must be substantially reduced!"

def test_honesty_requirement_balanced_load():
    """
    Honesty Requirement (Section 11):
    With balanced load (~400 kg = 50% rated load), car + load = 1000 + 400 = 1400 kg = counterweight.
    Net potential energy change is zero, regen ≈ 0, and savings ≈ 0.
    The system must honestly reflect this.
    """
    sim_b0 = WebSimAdapter()
    sim_b1 = WebSimAdapter()

    # 400 kg load exactly balances 1400 kg counterweight (empty supercap so no pre-charge is discharged)
    sim_b0.reset({"load": 400.0, "stage": 1, "mode": "alt", "vsc_init": 100.0})
    sim_b1.reset({"load": 400.0, "stage": 2, "mode": "alt", "vsc_init": 100.0})

    signals_b0 = []
    signals_b1 = []
    ctrl_b1 = BaselineB1Controller()

    for _ in range(60):
        s0 = sim_b0.step(P_sc_ref=0.0, dt=1.0)
        signals_b0.append(s0)

        action = ctrl_b1.compute_action(s0.to_dict())
        s1 = sim_b1.step(P_sc_ref=action, dt=1.0)
        signals_b1.append(s1)

    savings_engine = CounterfactualSavingsEngine()
    results = savings_engine.compare_runs(signals_b0, signals_b1)

    print(f"\n--- 400 kg Balanced Load Trip Results (Honesty Check) ---")
    print(f"B0 Grid Energy: {results['E_grid_b0_kWh']:.4f} kWh")
    print(f"B1 Grid Energy: {results['E_grid_actual_kWh']:.4f} kWh")
    print(f"Energy Saved: {results['E_saved_kWh']:.4f} kWh ({results['energy_saved_pct']:.1f}%)")
    print(f"B0 Brake Dumped: {results['E_brake_b0_kWh']:.4f} kWh")

    # When balanced, brake energy in B0 is practically zero (< 0.005 kWh)
    assert results["E_brake_b0_kWh"] < 0.005, f"Expected near-zero brake dump for balanced load, got {results['E_brake_b0_kWh']} kWh"
    # Savings should be near zero (< 0.005 kWh)
    assert results["E_saved_kWh"] < 0.005, f"Expected near-zero savings for balanced load, got {results['E_saved_kWh']} kWh"

if __name__ == "__main__":
    pytest.main(["-v", __file__])
