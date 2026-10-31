from adapters.web_sim_adapter import WebSimAdapter
from surrogate.elevator_surrogate import FastElevatorSurrogate

sim = WebSimAdapter()
surr = FastElevatorSurrogate()

sim.reset({"load": 800.0, "mode": "alt", "stage": 2, "vsc_init": 130.0})
surr.reset(load_kg=800.0, vsc_init=130.0)

sim_p = []
surr_p = []

for t in range(120):
    s_sim = sim.step(dt=1.0)
    s_surr = surr.step(dt=1.0)
    sim_p.append(s_sim.P_grid)
    surr_p.append(s_surr["P_grid"])
    if abs(s_sim.P_grid - s_surr["P_grid"]) > 50:
        print(f"t={t:2d}: sim_grid={s_sim.P_grid:6.1f} W, surr_grid={s_surr['P_grid']:6.1f} W, diff={s_sim.P_grid - s_surr['P_grid']:6.1f} W, Vsc_sim={s_sim.Vsc:5.1f}, Vsc_surr={s_surr['Vsc']:5.1f}")

total_sim = sum(sim_p)
total_surr = sum(surr_p)
print(f"Total sim grid: {total_sim:.1f} J, surr grid: {total_surr:.1f} J, diff: {abs(total_sim - total_surr)/total_sim*100:.2f}%")
