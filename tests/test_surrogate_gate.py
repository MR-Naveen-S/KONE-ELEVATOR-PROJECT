"""
Unit Test for Surrogate Validation Gate (Section 5 & Section 11)
Automated verification that:
- Surrogate speed >= 100,000 steps/second
- Per-trip energy error < 3.0 %
- Vsc trajectory RMSE < 2.0 % of Vmax (< 4.0 V)
- Total grid energy error < 3.0 %
"""

import pytest
from surrogate.validator import run_speed_benchmark, run_validation_gate

def test_surrogate_speed_benchmark():
    speed = run_speed_benchmark(n_steps=100000)
    print(f"\nSurrogate Benchmark Speed: {speed:,.0f} steps/second")
    assert speed >= 100000.0, f"Surrogate speed must be >= 100,000 steps/s (got {speed:,.0f})"

def test_surrogate_validation_gate_accuracy():
    report = run_validation_gate(n_trips=4, seconds_per_trip=30)
    print("\n--- Validation Gate Results ---")
    print(f"Gate Passed: {report['gate_passed']}")
    print(f"Per-Trip Error: {report['max_per_trip_error_pct']}% (< 3.0%)")
    print(f"Vsc RMSE: {report['vsc_rmse_V']} V ({report['vsc_rmse_pct_vmax']}% of Vmax, < 2.0%)")
    print(f"Total Grid Energy Error: {report['total_energy_error_pct']}% (< 3.0%)")

    assert report["gate_passed"], "Surrogate validation gate failed!"
    assert report["max_per_trip_error_pct"] < 3.0
    assert report["vsc_rmse_pct_vmax"] < 2.0
    assert report["total_energy_error_pct"] < 3.0

if __name__ == "__main__":
    pytest.main(["-v", __file__])
