import numpy as np
import pandas as pd
from adapters.web_sim_adapter import WebSimAdapter

# Run WebSimAdapter for 120 seconds
sim = WebSimAdapter()
sim.reset({"load": 800.0, "mode": "alt", "stage": 2, "vsc_init": 130.0})

sim_records = [sim.step(dt=1.0).to_dict() for _ in range(120)]
df_sim = pd.DataFrame(sim_records)

# Now test the algebraic average-value model on the exact same kinematics
Vsc = 130.0
Csc = 15.0
Vscm = 200.0
Vmin = 100.0
I_max = 100.0
eta = 0.97

surr_records = []
for i in range(120):
    row = df_sim.iloc[i]
    Pi = row["P_inv_dc"]
    P_aux = row["P_aux"]
    
    Pl = I_max * Vsc
    cl = lambda x: max(0.0, min(1.0, x))
    
    if Pi < -50.0: # Regen
        # Excess power on DC link
        P_avail = abs(Pi) - P_aux
        margin = cl((Vscm - Vsc) / (0.03 * Vscm))
        P_bus_charge = min(P_avail, Pl * margin)
        P_sc_bus = -P_bus_charge
        Pc_term = -(P_bus_charge * eta)
        P_brake = max(0.0, P_avail - P_bus_charge) if margin < 0.9 else 0.0
        P_grid = 0.0
        Vdc = 560.0 + (P_bus_charge / 2000.0) / eta
    elif Pi > 50.0: # Motoring
        margin = cl((Vsc - Vmin) / (0.03 * Vscm))
        # Droop in Stage 2 discharges to hold Vdc
        # Up to Pl * margin
        P_req = Pi + P_aux
        P_dis_bus = min(P_req, Pl * margin * eta)
        P_sc_bus = P_dis_bus
        Pc_term = P_dis_bus / eta
        P_grid = max(0.0, P_req - P_dis_bus)
        P_brake = 0.0
        if P_grid > 10.0:
            Vdc = 540.0 - 0.4 * (P_grid / 540.0)
        else:
            Vdc = 560.0 - (P_dis_bus / 2000.0) * eta
    else: # Idle / Dwell
        P_grid = P_aux
        P_sc_bus = 0.0
        Pc_term = 0.0
        P_brake = 0.0
        Vdc = 540.0

    # Update Vsc
    Vsc_sq = max(1.0, Vsc*Vsc - 2.0 * Pc_term * 1.0 / Csc)
    Vsc = np.sqrt(Vsc_sq)
    surr_records.append({
        "P_grid": P_grid,
        "P_inv_dc": Pi,
        "Vsc": Vsc,
        "Vdc": Vdc
    })

df_surr = pd.DataFrame(surr_records)

# Errors:
vsc_rmse = np.sqrt(np.mean((df_sim["Vsc"] - df_surr["Vsc"])**2))
total_sim_grid = np.sum(df_sim["P_grid"])
total_surr_grid = np.sum(df_surr["P_grid"])
grid_err_pct = abs(total_sim_grid - total_surr_grid) / total_sim_grid * 100.0

print(f"Vsc RMSE: {vsc_rmse:.3f} V ({vsc_rmse/200.0*100.0:.2f}% of Vmax) [Target: < 2%]")
print(f"Total Grid Energy Error: {grid_err_pct:.2f}% [Target: < 3%]")
