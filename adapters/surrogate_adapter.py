"""
PythonSurrogateAdapter: Implements the SimulatorAdapter interface using FastElevatorSurrogate.
Provides ultra-fast stepping (>= 100,000 steps/s) for RL and large scenario sweeps.
"""

from typing import Dict, Any, Optional
from core.schema import ElevatorSignals
from adapters.interface import SimulatorAdapter
from surrogate.elevator_surrogate import FastElevatorSurrogate

class PythonSurrogateAdapter(SimulatorAdapter):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.surrogate = FastElevatorSurrogate(config)
        self.last_state = self.surrogate.reset()

    def reset(self, config: Optional[Dict[str, Any]] = None, seed: Optional[int] = None) -> ElevatorSignals:
        load = float(config.get("load", 800.0)) if config else 800.0
        vsc_init = float(config.get("vsc_init", 130.0)) if config else None
        st = self.surrogate.reset(load_kg=load, vsc_init=vsc_init)
        self.last_state = st
        return self._dict_to_signals(st)

    def step(self, P_sc_ref: Optional[float] = None, dt: float = 1.0) -> ElevatorSignals:
        st = self.surrogate.step(P_sc_ref=P_sc_ref, dt=dt)
        self.last_state = st
        return self._dict_to_signals(st)

    def _dict_to_signals(self, st: Dict[str, float]) -> ElevatorSignals:
        duty = min(1.0, max(0.0, st["Vsc"] / max(st["Vdc"], 1.0)))
        dcdc_mode = "boost" if st["P_sc_bus"] > 50.0 else "buck" if st["P_sc_bus"] < -50.0 else "idle"
        sig = ElevatorSignals(
            time=round(st["time"], 4),
            trip_id=int(st["trip_id"]),
            lift_state="move" if abs(st["velocity"]) > 0.05 else "idle",
            direction=int(st["direction"]),
            floor=1 if st["position"] > 15.0 else 0,
            position=st["position"],
            velocity=st["velocity"],
            accel=0.0,
            car_load_kg=st["car_load_kg"],
            Vgrid=400.0,
            Igrid=st["P_grid"] / (math_sqrt3_400 := 657.0) if st["P_grid"] > 10.0 else 0.0,
            P_grid=st["P_grid"],
            Vdc=st["Vdc"],
            Idc_rect=st["P_grid"] / max(st["Vdc"], 1.0),
            P_inv_dc=st["P_inv_dc"],
            P_aux=st["P_aux"],
            P_brake=st["P_brake"],
            brake_chopper_on=1 if st["P_brake"] > 10.0 else 0,
            Vsc=st["Vsc"],
            Isc=st["Isc"],
            P_sc_term=st["P_sc_term"],
            P_sc_bus=st["P_sc_bus"],
            dcdc_mode=dcdc_mode,
            duty=duty,
            Te=0.0,
            motor_speed_rpm=(st["velocity"] / 0.3 * 60.0) / (2.0 * 3.14159),
            Iq=0.0,
            Id=0.0,
            SC_temp=25.0,
            T_amb=25.0
        )
        return sig

    def get_static_params(self) -> Dict[str, Any]:
        return {
            "source": "PythonSurrogateAdapter",
            "m_car": self.surrogate.m_car,
            "C_sc": self.surrogate.C_sc,
            "Vsc_max": self.surrogate.Vsc_max
        }
