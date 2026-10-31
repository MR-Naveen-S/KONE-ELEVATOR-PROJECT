"""
WebSimAdapter: High-fidelity Python port of the Elevator Drive Lab browser simulator.
Preserves exact discrete-time numerical physics (dt = 250 microseconds) from
'Elevator Drive Lab_ PMSM, Regen, Supercap.html'.

Choice rationale:
Porting directly to Python guarantees 100% reproducible numerical physics,
zero browser rendering/IPC overhead, headless deterministic testing,
and full compliance with Section 3 sign conventions.
"""

import math
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from core.schema import ElevatorSignals
from adapters.interface import SimulatorAdapter

class WebSimAdapter(SimulatorAdapter):
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = str(Path(__file__).parent.parent / "config" / "params.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            self.cfg = yaml.safe_load(f)
        
        self.params = {
            "stage": 2,                      # 1: conventional, 2: supercap
            "mode": "alt",                   # "alt", "up", "down"
            "load": self.cfg["lift"]["m_load_default_kg"],
            "H": self.cfg["lift"]["travel_height_m"],
            "vmax": self.cfg["lift"]["v_max_mps"],
            "acc": self.cfg["lift"]["acc_max_mps2"],
            "rbr": self.cfg["brake_chopper"]["R_brake_ohm"],
            "vbr": self.cfg["brake_chopper"]["V_brake_on_V"],
            "csc": self.cfg["supercapacitor"]["C_sc_F"],
            "vscm": self.cfg["supercapacitor"]["V_sc_max_V"],
            "ilim": self.cfg["dcdc_converter"]["I_dcdc_max_A"],
            "vref": self.cfg["dcdc_converter"]["V_dc_ref_V"],
            "dt_sim": self.cfg["simulation"]["dt_sim_s"], # 0.00025 s
            "P_aux_idle": self.cfg["electrical_grid"]["P_aux_idle_W"],
            "P_aux_door": self.cfg["electrical_grid"]["P_aux_door_W"],
            "droop_gain_W_per_V": self.cfg["dcdc_converter"]["droop_gain_W_per_V"],
            "ESR_sc": self.cfg["supercapacitor"]["ESR_sc_ohm"],
            "R_th": self.cfg["supercapacitor"]["R_th_K_per_W"],
            "C_th": self.cfg["supercapacitor"]["C_th_J_per_K"],
            "T_amb": self.cfg["supercapacitor"]["T_amb_C"],
        }
        self.reset()

    def reset(self, config: Optional[Dict[str, Any]] = None, seed: Optional[int] = None) -> ElevatorSignals:
        if config:
            self.params.update(config)

        self.time = 0.0
        self.trip_id = 0
        self.ph = "dwell"     # "dwell" or "move"
        self.tm = 1.0         # initial dwell timer (s)
        self.dir = -1 if self.params["mode"] == "down" else 1
        self.fr = 1.0 if self.params["mode"] == "down" else 0.0
        self.v = 0.0
        self.s = 0.0
        self.af = 0.0
        self.th = 0.0
        self.ang = 0.0
        self.Vdc = self.cfg["electrical_grid"]["V_rectifier_noload_V"]
        self.Vsc = float(self.params.get("vsc_init", 0.65 * self.params["vscm"])) # default 130 V
        self.brk = 0
        self.SC_temp = self.params["T_amb"]
        
        # Energy accumulators (Joules)
        self.E_grid = 0.0
        self.E_motoring = 0.0
        self.E_regen = 0.0
        self.E_brake = 0.0
        self.E_sc_in = 0.0
        self.E_sc_out = 0.0

        # Last instantaneous state
        self._last_signals = ElevatorSignals(
            time=0.0,
            trip_id=0,
            lift_state="idle",
            direction=0,
            floor=0,
            position=0.0 if self.dir > 0 else self.params["H"],
            velocity=0.0,
            accel=0.0,
            car_load_kg=self.params["load"],
            Vgrid=self.cfg["electrical_grid"]["V_grid_line_rms_V"],
            Igrid=0.0,
            P_grid=0.0,
            Vdc=self.Vdc,
            Idc_rect=0.0,
            P_inv_dc=0.0,
            P_aux=self.params["P_aux_door"],
            P_brake=0.0,
            brake_chopper_on=0,
            Vsc=self.Vsc,
            Isc=0.0,
            P_sc_term=0.0,
            P_sc_bus=0.0,
            dcdc_mode="idle",
            duty=self.Vsc / self.Vdc,
            Te=0.0,
            motor_speed_rpm=0.0,
            Iq=0.0,
            Id=0.0,
            SC_temp=self.SC_temp,
            T_amb=self.params["T_amb"]
        )
        return self._last_signals

    def _sim_substep(self, dt: float, P_sc_ref: Optional[float] = None) -> Dict[str, float]:
        """
        Executes one microsecond time-step of the physics engine (dt = 0.00025 s).
        Follows line-by-line the exact browser simulator formulas.
        """
        g = self.cfg["lift"]["g_mps2"]           # 9.81
        r = self.cfg["motor"]["r_sheave_m"]      # 0.3
        pp = self.cfg["motor"]["pole_pairs"]     # 12
        lam = self.cfg["motor"]["flux_linkage_Wb"] # 2.5
        R = self.cfg["motor"]["R_stator_ohm"]    # 0.5
        Ld = self.cfg["motor"]["Ld_H"]           # 0.02
        mcw = self.cfg["lift"]["m_cw_kg"]        # 1400

        aup = 0.0
        vup = 0.0
        F = 0.0

        # Kinematics state machine
        if self.ph == "dwell":
            self.tm -= dt
            if self.tm <= 0:
                self.ph = "move"
                self.s = 0.0
                self.fr = 0.0 if self.dir > 0 else 1.0
                self.trip_id += 1
        else:
            d = self.params["H"] - self.s
            vt = max(0.03, min(self.params["vmax"], math.sqrt(1.6 * self.params["acc"] * max(d, 0.0))))
            ar = max(-self.params["acc"], min(self.params["acc"], (vt - self.v) / 0.15))
            self.af += (ar - self.af) * dt / 0.25
            self.v = max(0.0, self.v + self.af * dt)
            self.s += self.v * dt
            if self.s >= self.params["H"] - 0.005:
                self.ph = "dwell"
                self.tm = 3.0
                self.v = 0.0
                self.af = 0.0
                self.fr = 1.0 if self.dir > 0 else 0.0
                if self.params["mode"] == "alt":
                    self.dir *= -1
            else:
                self.fr = self.s / self.params["H"] if self.dir > 0 else 1.0 - self.s / self.params["H"]

        # Mechanical Forces
        if self.ph == "move":
            aup = self.dir * self.af
            vup = self.dir * self.v
            m = 1000.0 + self.params["load"]
            F = (m - mcw) * g + (m + mcw + 300.0) * aup + 300.0 * math.tanh(vup / 0.05)
        else:
            aup = 0.0
            vup = 0.0
            F = 0.0

        # PMSM Motor Equations (id = 0 Field-Oriented Control)
        T = F * r
        wm = vup / r
        we = pp * wm
        iq = T / (1.5 * pp * lam)
        vq = R * iq + we * lam
        vd = -we * Ld * iq
        self.th += we * dt
        self.ang += wm * dt

        # Power Conversions & Inverter
        Pm = F * vup
        Pe = 1.5 * vq * iq
        Pi = Pe / 0.97 if Pe >= 0 else Pe * 0.97
        V = max(self.Vdc, 50.0)
        Ii = Pi / V

        # Auxiliary load on DC link
        P_aux = self.params["P_aux_door"] if self.ph == "dwell" else self.params["P_aux_idle"]
        I_aux = P_aux / V

        # Diode Rectifier
        Ir = max(0.0, (540.0 - self.Vdc) / 0.4)

        # Brake Chopper (hysteresis)
        if self.Vdc > self.params["vbr"]:
            self.brk = 1
        elif self.Vdc < self.params["vbr"] - 15.0:
            self.brk = 0
        Ib = (self.Vdc / self.params["rbr"]) if self.brk else 0.0

        # Supercapacitor & DC-DC Converter
        # Note on Sign Conventions:
        # In browser HTML simulator:
        #   p > 0 means taking power FROM DC link to charge SC.
        #   Pc > 0 is power entering SC cell, Ps > 0 is power leaving DC link into converter.
        # Under Section 3 Project Mandate:
        #   P_sc_bus: + discharge into DC link, - charge from DC link.
        #   P_sc_term: + discharge out of SC cells, - charge into SC cells.
        #   Isc: + discharge, - charge.
        Ps_bus = 0.0
        Pc_term = 0.0
        Isc = 0.0
        dcdc_mode = "idle"
        self.Vsc = min(self.Vsc, self.params["vscm"])
        vm = self.params["vscm"]

        if self.params["stage"] == 2:
            Pl = self.params["ilim"] * self.Vsc
            cl = lambda x: max(0.0, min(1.0, x))

            if P_sc_ref is not None:
                # Controlled by external command (RL / Safety Supervisor / Baseline)
                # P_sc_ref: + discharge (into DC bus), - charge (from DC bus)
                target_P_bus = P_sc_ref
                # Limit by terminal voltage window
                if target_P_bus > 0: # Discharging: ensure Vsc > 0.5 * Vmax
                    margin = cl((self.Vsc - 0.5 * vm) / (0.03 * vm))
                    target_P_bus *= margin
                    # Converter efficiency: discharging cell -> bus (loss)
                    Pc_needed = target_P_bus / 0.97
                    Pc_clamped = min(Pl, Pc_needed)
                    Ps_bus = Pc_clamped * 0.97
                    Pc_term = Pc_clamped
                    dcdc_mode = "boost" if Ps_bus > 50.0 else "idle"
                else: # Charging: ensure Vsc < Vmax
                    margin = cl((vm - self.Vsc) / (0.03 * vm))
                    target_P_bus *= margin
                    # Charging: bus -> cell
                    P_bus_in = abs(target_P_bus)
                    P_bus_clamped = min(Pl, P_bus_in)
                    Ps_bus = -P_bus_clamped
                    Pc_term = -(P_bus_clamped * 0.97)
                    dcdc_mode = "buck" if abs(Ps_bus) > 50.0 else "idle"
            else:
                # Autonomous Droop Law from browser simulator
                # p > 0 when Vdc > Vref (charge); p < 0 when Vdc < Vref (discharge)
                p = self.params["droop_gain_W_per_V"] * (self.Vdc - self.params["vref"])
                if p > 0:
                    p *= cl((vm - self.Vsc) / (0.03 * vm))
                    Pc = p * 0.97
                    Pc = min(Pl, Pc)
                    Ps_html = Pc / 0.97
                    # In our convention:
                    Ps_bus = -Ps_html
                    Pc_term = -Pc
                    dcdc_mode = "buck" if abs(Ps_bus) > 50.0 else "idle"
                else:
                    p *= cl((self.Vsc - 0.5 * vm) / (0.03 * vm))
                    Pc = p / 0.97
                    Pc = max(-Pl, Pc)
                    Ps_html = Pc * 0.97
                    # In our convention:
                    Ps_bus = -Ps_html
                    Pc_term = -Pc
                    dcdc_mode = "boost" if Ps_bus > 50.0 else "idle"

            # Update Supercapacitor Voltage (E = 0.5 * C * V^2, dE/dt = -Pc_term)
            # Pc_term is + for discharge, - for charge
            # Vsc^2(t+dt) = Vsc^2(t) - 2 * Pc_term * dt / C
            new_Vsc_sq = max(1.0, self.Vsc * self.Vsc - 2.0 * Pc_term * dt / self.params["csc"])
            self.Vsc = math.sqrt(new_Vsc_sq)
            Isc = Pc_term / max(self.Vsc, 1.0)
        else:
            Ps_bus = 0.0
            Pc_term = 0.0
            Isc = 0.0
            dcdc_mode = "idle"

        # DC-DC current on DC link (+ entering DC link when discharging)
        Isd = Ps_bus / V

        # Update DC-Link Voltage:
        # Cdc * dVdc/dt = Ir - Ii - Ib - I_aux + Isd
        dVdc = dt * (Ir - Ii - Ib - I_aux + Isd) / 4.7e-3
        self.Vdc += dVdc

        # Thermal Model for Supercapacitor
        # P_loss_esr = Isc^2 * ESR
        P_loss_esr = (Isc ** 2) * self.params["ESR_sc"]
        dT = dt * ((P_loss_esr / self.params["C_th"]) - ((self.SC_temp - self.params["T_amb"]) / (self.params["R_th"] * self.params["C_th"])))
        self.SC_temp += dT

        # Aggregate Energy (Joules)
        P_grid = Ir * V
        P_brake = Ib * V
        self.E_grid += P_grid * dt
        self.E_motoring += max(Pi, 0.0) * dt
        self.E_regen += max(-Pi, 0.0) * dt
        self.E_brake += P_brake * dt
        if Ps_bus > 0:
            self.E_sc_out += Ps_bus * dt
        else:
            self.E_sc_in += (-Ps_bus) * dt

        # Lift kinematic state determination
        if self.ph == "dwell":
            lift_state = "door" if (self.tm > 2.0 or self.tm < 1.0) else "idle"
        else:
            if abs(self.af) > 0.05 and abs(self.v) < self.params["vmax"] * 0.95:
                lift_state = "accel" if (ar * self.dir > 0) else "decel"
            else:
                lift_state = "cruise"

        duty = min(1.0, max(0.0, self.Vsc / max(self.Vdc, 1.0)))
        motor_speed_rpm = (wm * 60.0) / (2.0 * math.pi)

        return {
            "vup": vup,
            "aup": aup,
            "F": F,
            "position": self.s if self.dir > 0 else (self.params["H"] - self.s),
            "lift_state": lift_state,
            "direction": self.dir if self.ph == "move" else 0,
            "floor": 1 if self.fr > 0.5 else 0,
            "P_grid": P_grid,
            "Ir": Ir,
            "Vdc": self.Vdc,
            "Pi": Pi,
            "Ii": Ii,
            "P_aux": P_aux,
            "P_brake": P_brake,
            "brake_on": self.brk,
            "Vsc": self.Vsc,
            "Isc": Isc,
            "P_sc_term": Pc_term,
            "P_sc_bus": Ps_bus,
            "dcdc_mode": dcdc_mode,
            "duty": duty,
            "Te": T,
            "motor_speed_rpm": motor_speed_rpm,
            "Iq": iq,
            "Id": 0.0,
            "SC_temp": self.SC_temp,
            "P_Cdc": (Ir - Ii - Ib - I_aux + Isd) * V,
            "Vgrid": self.cfg["electrical_grid"]["V_grid_line_rms_V"],
            "Igrid": P_grid / (math.sqrt(3.0) * self.cfg["electrical_grid"]["V_grid_line_rms_V"] * 0.95) if P_grid > 10.0 else 0.0
        }

    def step(self, P_sc_ref: Optional[float] = None, dt: float = 1.0) -> ElevatorSignals:
        """
        Advances the simulation by dt seconds (default 1.0 s) by running
        internal micro-steps of dt_sim (250 microseconds).
        Averages power/voltage/current, integrates energy, and logs state.
        """
        dt_sim = self.params["dt_sim"]
        n_steps = max(1, int(round(dt / dt_sim)))

        # Accumulators for 1-second aggregation
        sum_P_grid = 0.0
        sum_Ir = 0.0
        sum_Vdc = 0.0
        sum_Pi = 0.0
        sum_Ii = 0.0
        sum_P_aux = 0.0
        sum_P_brake = 0.0
        sum_Vsc = 0.0
        sum_Isc = 0.0
        sum_P_sc_term = 0.0
        sum_P_sc_bus = 0.0
        sum_duty = 0.0
        sum_Te = 0.0
        sum_rpm = 0.0
        sum_Iq = 0.0
        sum_Igrid = 0.0
        sum_vup = 0.0
        sum_aup = 0.0
        sum_P_Cdc = 0.0

        last_state = None
        for _ in range(n_steps):
            last_state = self._sim_substep(dt_sim, P_sc_ref)
            sum_P_grid += last_state["P_grid"]
            sum_Ir += last_state["Ir"]
            sum_Vdc += last_state["Vdc"]
            sum_Pi += last_state["Pi"]
            sum_Ii += last_state["Ii"]
            sum_P_aux += last_state["P_aux"]
            sum_P_brake += last_state["P_brake"]
            sum_Vsc += last_state["Vsc"]
            sum_Isc += last_state["Isc"]
            sum_P_sc_term += last_state["P_sc_term"]
            sum_P_sc_bus += last_state["P_sc_bus"]
            sum_duty += last_state["duty"]
            sum_Te += last_state["Te"]
            sum_rpm += last_state["motor_speed_rpm"]
            sum_Iq += last_state["Iq"]
            sum_Igrid += last_state["Igrid"]
            sum_vup += last_state["vup"]
            sum_aup += last_state["aup"]
            sum_P_Cdc += last_state["P_Cdc"]

        self.time += dt
        inv_n = 1.0 / n_steps

        signals = ElevatorSignals(
            time=round(self.time, 4),
            trip_id=self.trip_id,
            lift_state=last_state["lift_state"],
            direction=last_state["direction"],
            floor=last_state["floor"],
            position=last_state["position"],
            velocity=sum_vup * inv_n,
            accel=sum_aup * inv_n,
            car_load_kg=self.params["load"],
            Vgrid=last_state["Vgrid"],
            Igrid=sum_Igrid * inv_n,
            P_grid=sum_P_grid * inv_n,
            Vdc=sum_Vdc * inv_n,
            Idc_rect=sum_Ir * inv_n,
            P_inv_dc=sum_Pi * inv_n,
            P_aux=sum_P_aux * inv_n,
            P_brake=sum_P_brake * inv_n,
            brake_chopper_on=last_state["brake_on"],
            Vsc=sum_Vsc * inv_n,
            Isc=sum_Isc * inv_n,
            P_sc_term=sum_P_sc_term * inv_n,
            P_sc_bus=sum_P_sc_bus * inv_n,
            dcdc_mode=last_state["dcdc_mode"],
            duty=sum_duty * inv_n,
            Te=sum_Te * inv_n,
            motor_speed_rpm=sum_rpm * inv_n,
            Iq=sum_Iq * inv_n,
            Id=0.0,
            SC_temp=self.SC_temp,
            T_amb=self.params["T_amb"],
            P_Cdc=sum_P_Cdc * inv_n
        )

        signals.validate_signs()
        self._last_signals = signals
        return signals

    def get_static_params(self) -> Dict[str, Any]:
        return dict(self.params)
