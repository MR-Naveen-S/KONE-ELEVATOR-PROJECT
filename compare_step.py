from adapters.web_sim_adapter import WebSimAdapter
from surrogate.elevator_surrogate import FastElevatorSurrogate

sim = WebSimAdapter()
surr = FastElevatorSurrogate()

sim.reset({"load": 800.0, "mode": "alt", "stage": 2, "vsc_init": 130.0})
surr.reset(load_kg=800.0, vsc_init=130.0)

for t in range(25):
    s_sim = sim.step(dt=1.0)
    s_surr = surr.step(dt=1.0)
    print(f"t={t:2d} | SIM: pos={s_sim.position:4.1f}, v={s_sim.velocity:4.2f}, Pi={s_sim.P_inv_dc:7.0f}, Pg={s_sim.P_grid:7.0f}, Vsc={s_sim.Vsc:5.1f}, Vdc={s_sim.Vdc:5.1f} | SURR: pos={s_surr['position']:4.1f}, v={s_surr['velocity']:4.2f}, Pi={s_surr['P_inv_dc']:7.0f}, Pg={s_surr['P_grid']:7.0f}, Vsc={s_surr['Vsc']:5.1f}, Vdc={s_surr['Vdc']:5.1f}")
