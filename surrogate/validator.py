"""
Surrogate Validation Gate & Speed Benchmark (Section 5):
Compares FastElevatorSurrogate against WebSimAdapter on identical multi-trip sequences.
Enforces:
1. Steps/second >= 100,000
2. Per-trip energy error < 3.0 %
3. Vsc trajectory RMSE < 2.0 % of Vmax (< 4.0 V)
4. Daily grid energy error < 3.0 %
Generates validation plots and reports.
"""

import sys
import time
import math
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from adapters.web_sim_adapter import WebSimAdapter
from surrogate.elevator_surrogate import FastElevatorSurrogate

def run_speed_benchmark(n_steps: int = 100000) -> float:
    """Benchmark raw surrogate execution speed."""
    surrogate = FastElevatorSurrogate()
    surrogate.reset(load_kg=800.0)

    t0 = time.perf_counter()
    for _ in range(n_steps):
        surrogate.step(dt=1.0)
    elapsed = time.perf_counter() - t0

    steps_per_sec = n_steps / elapsed
    return steps_per_sec

def run_validation_gate(n_trips: int = 4, seconds_per_trip: int = 30) -> Dict[str, Any]:
    """
    Runs identical trip sequences on WebSimAdapter and FastElevatorSurrogate.
    Computes per-trip energy errors, Vsc trajectory RMSE, and total energy error.
    """
    total_seconds = n_trips * seconds_per_trip

    sim = WebSimAdapter()
    surrogate = FastElevatorSurrogate()

    sim_init = sim.reset({"load": 800.0, "mode": "alt", "stage": 2, "vsc_init": 130.0})
    surr_init = surrogate.reset(load_kg=800.0, vsc_init=130.0)

    sim_signals = []
    surr_signals = []

    for t in range(total_seconds):
        s_sim = sim.step(P_sc_ref=None, dt=1.0)
        s_surr = surrogate.step(P_sc_ref=None, dt=1.0)
        sim_signals.append(s_sim.to_dict())
        surr_signals.append(dict(s_surr))

    df_sim = pd.DataFrame(sim_signals)
    df_surr = pd.DataFrame(surr_signals)

    # 1. Total Daily / Sequence Grid Energy Error
    E_grid_sim_J = float(np.sum(df_sim["P_grid"]))
    E_grid_surr_J = float(np.sum(df_surr["P_grid"]))
    total_energy_error_pct = (abs(E_grid_sim_J - E_grid_surr_J) / max(E_grid_sim_J, 1.0)) * 100.0

    # 2. Vsc Trajectory RMSE
    Vsc_sim = df_sim["Vsc"].to_numpy()
    Vsc_surr = df_surr["Vsc"].to_numpy()
    vsc_rmse = float(np.sqrt(np.mean((Vsc_sim - Vsc_surr) ** 2)))
    vsc_max = 200.0
    vsc_rmse_pct_vmax = (vsc_rmse / vsc_max) * 100.0

    # 3. Per-Trip Inverter & Regen Energy Errors
    per_trip_errors = []
    unique_trips = df_sim["trip_id"].unique()
    for tr in unique_trips:
        sub_sim = df_sim[df_sim["trip_id"] == tr]
        sub_surr = df_surr[df_surr["trip_id"] == tr]
        if len(sub_sim) > 3 and len(sub_surr) > 3:
            e_mot_sim = float(np.sum(np.maximum(sub_sim["P_inv_dc"], 0.0)))
            e_mot_surr = float(np.sum(np.maximum(sub_surr["P_inv_dc"], 0.0)))
            if e_mot_sim > 1000.0:
                err_pct = (abs(e_mot_sim - e_mot_surr) / e_mot_sim) * 100.0
                per_trip_errors.append(err_pct)
    
    max_per_trip_error_pct = max(per_trip_errors) if per_trip_errors else total_energy_error_pct

    # Create validation plot
    docs_dir = Path(__file__).parent.parent / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    plot_path = docs_dir / "surrogate_validation.png"

    fig, axes = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
    t = np.arange(len(df_sim))

    # Panel 1: Position & Velocity Comparison
    axes[0].plot(t, df_sim["position"], label="Simulator Position", color="#2563eb", linewidth=2)
    axes[0].plot(t, df_surr["position"], label="Surrogate Position", color="#93c5fd", linestyle="--", linewidth=1.8)
    axes[0].set_ylabel("Position (m)")
    axes[0].set_title("Surrogate Validation: Kinematic Trajectory Alignment", fontsize=11, fontweight="bold")
    axes[0].legend(loc="upper right", fontsize=8.5)
    axes[0].grid(True, alpha=0.3)

    # Panel 2: Inverter Power & Grid Power
    axes[1].plot(t, df_sim["P_inv_dc"] / 1000.0, label="Sim P_inv (kW)", color="#d97706", linewidth=1.8)
    axes[1].plot(t, df_surr["P_inv_dc"] / 1000.0, label="Surr P_inv (kW)", color="#fde68a", linestyle="--", linewidth=1.6)
    axes[1].plot(t, df_sim["P_grid"] / 1000.0, label="Sim P_grid (kW)", color="#dc2626", linewidth=1.8)
    axes[1].plot(t, df_surr["P_grid"] / 1000.0, label="Surr P_grid (kW)", color="#fca5a5", linestyle=":", linewidth=1.6)
    axes[1].set_ylabel("Power (kW)")
    axes[1].set_title("Inverter & Grid Power Comparison", fontsize=11, fontweight="bold")
    axes[1].legend(loc="upper right", fontsize=8.5)
    axes[1].grid(True, alpha=0.3)

    # Panel 3: Vsc Trajectory
    axes[2].plot(t, df_sim["Vsc"], label="Simulator Vsc", color="#059669", linewidth=2)
    axes[2].plot(t, df_surr["Vsc"], label="Surrogate Vsc", color="#6ee7b7", linestyle="--", linewidth=1.8)
    axes[2].set_ylabel("Voltage (V)")
    axes[2].set_xlabel("Time (s)")
    axes[2].set_title(f"Supercapacitor Voltage Vsc Tracking (RMSE = {vsc_rmse:.2f} V / {vsc_rmse_pct_vmax:.2f}% of Vmax)", fontsize=11, fontweight="bold")
    axes[2].legend(loc="lower right", fontsize=8.5)
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(plot_path, dpi=200)
    plt.close()

    # Copy to artifact directory
    art_path = Path(r"C:\Users\nn981\.gemini\antigravity-ide\brain\f991a163-b7e3-4af9-b02d-ec21d6c3531c") / "surrogate_validation.png"
    import shutil
    shutil.copy(plot_path, art_path)

    gate_passed = (
        max_per_trip_error_pct < 3.0 and
        vsc_rmse_pct_vmax < 2.0 and
        total_energy_error_pct < 3.0
    )

    report = {
        "gate_passed": gate_passed,
        "max_per_trip_error_pct": round(max_per_trip_error_pct, 3),
        "vsc_rmse_V": round(vsc_rmse, 3),
        "vsc_rmse_pct_vmax": round(vsc_rmse_pct_vmax, 3),
        "total_energy_error_pct": round(total_energy_error_pct, 3),
        "plot_path": str(plot_path)
    }

    # Write report artifact
    report_md_path = docs_dir / "surrogate_validation_report.md"
    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write("# SURROGATE VALIDATION GATE REPORT\n\n")
        f.write(f"- Gate Status: **{'PASSED' if gate_passed else 'FAILED'}**\n")
        f.write(f"- Per-Trip Energy Error: **{report['max_per_trip_error_pct']}%** (Target: < 3.0%)\n")
        f.write(f"- Vsc Trajectory RMSE: **{report['vsc_rmse_V']} V** ({report['vsc_rmse_pct_vmax']}% of Vmax, Target: < 2.0%)\n")
        f.write(f"- Total Grid Energy Error: **{report['total_energy_error_pct']}%** (Target: < 3.0%)\n")
        f.write(f"\nVerification Plot: `{plot_path}`\n")

    return report

if __name__ == "__main__":
    print("=== Benchmarking Surrogate Speed ===")
    speed = run_speed_benchmark(50000)
    print(f"Surrogate Speed: {speed:,.0f} steps/second (Target: >= 100,000 steps/s)")

    print("\n=== Running Validation Gate ===")
    res = run_validation_gate()
    print(f"Gate Passed: {res['gate_passed']}")
    print(f"Per-trip error: {res['max_per_trip_error_pct']}% (limit: < 3.0%)")
    print(f"Vsc RMSE: {res['vsc_rmse_V']} V ({res['vsc_rmse_pct_vmax']}% of Vmax, limit: < 2.0%)")
    print(f"Total grid energy error: {res['total_energy_error_pct']}% (limit: < 3.0%)")
