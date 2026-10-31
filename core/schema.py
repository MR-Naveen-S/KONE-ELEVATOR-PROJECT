"""
Signal Schema and Physical Sign Conventions
Section 3 Mandates:
- P_inv_dc: inverter DC-side power, + motoring, - regenerating (W)
- P_sc_bus: power from the DC-DC into the DC bus, + discharge, - charge (W)
- P_sc_term: supercap terminal power, + discharge, - charge (W)
- P_grid: rectifier output power, always >= 0 (W)
- P_brake: brake-resistor power, >= 0 (W)
- P_aux: auxiliary load on the DC bus, >= 0 (W)
- Current signs follow same logic: position + is up; velocity + is up; accel + is up.
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, Any, Optional
import math

# Signal definitions with units, descriptions, and sign conventions
SIGNAL_METADATA = {
    "time": {"unit": "s", "desc": "Elapsed simulation time", "sign": "+ forward"},
    "trip_id": {"unit": "id", "desc": "Current trip identifier (integer)", "sign": ">= 0"},
    "lift_state": {"unit": "state", "desc": "State: idle / accel / cruise / decel / door", "sign": "categorical"},
    "direction": {"unit": "dir", "desc": "Direction of travel: +1 (up), -1 (down), 0 (standstill)", "sign": "+ up / - down"},
    "floor": {"unit": "floor", "desc": "Current floor level (0 to N)", "sign": ">= 0"},
    "position": {"unit": "m", "desc": "Vertical elevator position from ground buffer", "sign": "+ up"},
    "velocity": {"unit": "m/s", "desc": "Vertical elevator velocity", "sign": "+ up / - down"},
    "accel": {"unit": "m/s^2", "desc": "Vertical elevator acceleration", "sign": "+ up / - down"},
    "car_load_kg": {"unit": "kg", "desc": "Passenger / payload mass inside the cabin", "sign": ">= 0"},
    "Vgrid": {"unit": "V", "desc": "AC grid RMS line voltage", "sign": ">= 0"},
    "Igrid": {"unit": "A", "desc": "AC grid RMS line current drawn by rectifier", "sign": ">= 0"},
    "P_grid": {"unit": "W", "desc": "Rectifier output power into DC link", "sign": "always >= 0 (no export)"},
    "Vdc": {"unit": "V", "desc": "DC link bus voltage", "sign": ">= 0"},
    "Idc_rect": {"unit": "A", "desc": "Rectifier DC output current into DC bus", "sign": "always >= 0"},
    "P_inv_dc": {"unit": "W", "desc": "Inverter DC-side power", "sign": "+ motoring, - regenerating"},
    "P_aux": {"unit": "W", "desc": "Auxiliary load power drawn from DC bus", "sign": "always >= 0"},
    "P_brake": {"unit": "W", "desc": "Power dissipated in braking resistor", "sign": "always >= 0"},
    "brake_chopper_on": {"unit": "bool", "desc": "Brake chopper IGBT firing state (0 or 1)", "sign": "binary"},
    "Vsc": {"unit": "V", "desc": "Supercapacitor bank terminal voltage", "sign": ">= 0"},
    "Isc": {"unit": "A", "desc": "Supercapacitor cell terminal current", "sign": "+ discharge, - charge"},
    "P_sc_term": {"unit": "W", "desc": "Supercapacitor cell terminal power", "sign": "+ discharge, - charge"},
    "P_sc_bus": {"unit": "W", "desc": "Power injected from DC-DC into the DC bus", "sign": "+ discharge, - charge"},
    "dcdc_mode": {"unit": "mode", "desc": "DC-DC converter state: idle / buck / boost", "sign": "categorical"},
    "duty": {"unit": "ratio", "desc": "DC-DC converter duty cycle (Vsc / Vdc)", "sign": "0.0 to 1.0"},
    "Te": {"unit": "N*m", "desc": "PMSM electromagnetic shaft torque", "sign": "+ motoring, - braking"},
    "motor_speed_rpm": {"unit": "rpm", "desc": "PMSM mechanical rotor rotational speed", "sign": "+ up / - down"},
    "Iq": {"unit": "A", "desc": "PMSM quadrature axis current (torque producing)", "sign": "+ motoring, - braking"},
    "Id": {"unit": "A", "desc": "PMSM direct axis current (flux control)", "sign": "typically 0 in id=0 FOC"},
    "SC_temp": {"unit": "degC", "desc": "Supercapacitor bank internal temperature", "sign": ">= T_amb"},
    "T_amb": {"unit": "degC", "desc": "Ambient temperature", "sign": "degC"}
}

@dataclass
class ElevatorSignals:
    time: float = 0.0
    trip_id: int = 0
    lift_state: str = "idle"         # "idle", "accel", "cruise", "decel", "door"
    direction: int = 0               # +1 up, -1 down, 0 standstill
    floor: int = 0
    position: float = 0.0            # m
    velocity: float = 0.0            # m/s (+ up)
    accel: float = 0.0               # m/s^2 (+ up)
    car_load_kg: float = 800.0       # kg
    Vgrid: float = 400.0             # V
    Igrid: float = 0.0               # A
    P_grid: float = 0.0              # W (>= 0)
    Vdc: float = 540.0               # V
    Idc_rect: float = 0.0            # A (>= 0)
    P_inv_dc: float = 0.0            # W (+ motoring, - regenerating)
    P_aux: float = 250.0             # W (>= 0)
    P_brake: float = 0.0             # W (>= 0)
    brake_chopper_on: int = 0        # 0 or 1
    Vsc: float = 130.0               # V
    Isc: float = 0.0                 # A (+ discharge, - charge)
    P_sc_term: float = 0.0           # W (+ discharge, - charge)
    P_sc_bus: float = 0.0            # W (+ discharge, - charge)
    dcdc_mode: str = "idle"          # "idle", "buck", "boost"
    duty: float = 0.24               # 0.0 to 1.0
    Te: float = 0.0                  # N*m
    motor_speed_rpm: float = 0.0     # rpm
    Iq: float = 0.0                  # A
    Id: float = 0.0                  # A
    SC_temp: float = 25.0            # deg C
    T_amb: float = 25.0              # deg C
    P_Cdc: float = 0.0               # W, rate of energy stored in Cdc capacitor: d(0.5*Cdc*Vdc^2)/dt

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def validate_signs(self) -> bool:
        """Verify strict sign conventions specified in Section 3."""
        if self.P_grid < -1e-3:
            raise ValueError(f"Sign violation: P_grid cannot be negative (got {self.P_grid} W)")
        if self.P_brake < -1e-3:
            raise ValueError(f"Sign violation: P_brake cannot be negative (got {self.P_brake} W)")
        if self.P_aux < -1e-3:
            raise ValueError(f"Sign violation: P_aux cannot be negative (got {self.P_aux} W)")
        if self.Vdc < 0.0:
            raise ValueError(f"Sign violation: Vdc cannot be negative (got {self.Vdc} V)")
        if self.Vsc < 0.0:
            raise ValueError(f"Sign violation: Vsc cannot be negative (got {self.Vsc} V)")
        return True
