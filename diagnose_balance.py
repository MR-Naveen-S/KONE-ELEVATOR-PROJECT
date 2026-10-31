import numpy as np
from adapters.web_sim_adapter import WebSimAdapter

sim = WebSimAdapter()
sim.reset({"load": 800.0, "mode": "alt", "stage": 2})

signals = []
for i in range(35):
    s = sim.step(dt=1.0)
    signals.append(s)

# Examine during regen steps (where velocity < -0.1)
for i, s in enumerate(signals):
    if s.velocity < -0.1:
        # Check power balance at this step:
        # P_in = P_grid + P_sc_bus
        # P_out = P_inv_dc + P_aux + P_brake
        # During regen: P_inv_dc is negative (-P_regen)
        # So power entering DC link is: -P_inv_dc + P_grid
        # Power leaving DC link is: -P_sc_bus (charging SC) + P_aux + P_brake
        P_regen = max(-s.P_inv_dc, 0.0)
        P_sc_charge = max(-s.P_sc_bus, 0.0)
        print(f"Step {i:2d} (t={s.time:4.1f}s): P_regen={P_regen:7.1f} W, P_sc_charge={P_sc_charge:7.1f} W, P_aux={s.P_aux:5.1f} W, Diff={P_regen - (P_sc_charge + s.P_aux):6.1f} W, Vdc={s.Vdc:.1f} V")
