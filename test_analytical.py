import numpy as np
import math
from adapters.web_sim_adapter import WebSimAdapter

# Run WebSimAdapter for 60 seconds
sim = WebSimAdapter()
sim.reset({"load": 800.0, "mode": "alt", "stage": 2, "vsc_init": 130.0})

sim_records = [sim.step(dt=1.0) for _ in range(60)]

# Test analytical average-value formulation
Vsc = 130.0
Csc = 15.0
Vscm = 200.0
Vmin = 100.0

diffs = []
for i, s in enumerate(sim_records):
    # s is the true simulator state
    # Let's see what P_inv_dc and P_aux are
    P_inv = s.P_inv_dc
    P_aux = s.P_aux
    
    # In average-value model:
    # If P_inv < 0 (regen):
    # Available regen = abs(P_inv) - P_aux
    # Supercap droop captures this regen (up to current limit 100A * Vsc)
    if P_inv < -50.0:
        P_avail = abs(P_inv) - P_aux
        P_lim = 100.0 * Vsc * 0.97
        margin = max(0.0, min(1.0, (Vscm - Vsc) / (0.03 * Vscm)))
        P_bus_charge = min(P_avail, P_lim * margin)
        # In our convention: P_sc_bus = -P_bus_charge
        P_sc_bus = -P_bus_charge
        P_sc_term = -(P_bus_charge * 0.97) # power entering cell
        # DC link voltage:
        Vdc = 560.0 + (P_bus_charge / 2000.0) / 0.97
        P_grid = 0.0
    elif P_inv > 50.0:
        # Motoring:
        # Droop controller: Vdc drops below 560V
        # In Stage 2, rectifier takes over below 540V
        # Between 560V and 540V, droop supplies up to 2000 * 20 = 40 kW
        # But diode rectifier turns on below 540V!
        # When Vdc = 540V, droop supplies 2000 * (560 - 540) = 40,000 W * margin
        P_grid = s.P_grid
        P_sc_bus = s.P_sc_bus
        P_sc_term = s.P_sc_term
    else:
        P_grid = s.P_grid
        P_sc_bus = s.P_sc_bus
        P_sc_term = s.P_sc_term

    # Update Vsc
    Vsc_sq = max(1.0, Vsc*Vsc - 2.0 * s.P_sc_term * 1.0 / Csc)
    Vsc_next = math.sqrt(Vsc_sq)
    diff = abs(Vsc_next - s.Vsc)
    diffs.append(diff)
    Vsc = s.Vsc # synchronize for next step check

print(f"Max Vsc step error with exact P_sc_term: {max(diffs):.4f} V")
