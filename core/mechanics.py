"""
Core Mechanics Module:
Elevator kinematics, forces, mechanical shaft power, and trip energy checks.
All formulas strictly adhere to Section 4.
"""

import math
from typing import Dict, Any, Tuple

def compute_kinematics_step(
    s: float,
    v: float,
    af: float,
    H: float,
    vmax: float,
    acc: float,
    dt: float,
    decel_factor: float = 1.6,
    tau_jerk: float = 0.15,
    tau_acc: float = 0.25
) -> Tuple[float, float, float, bool]:
    """
    Computes one kinematic update step.
    Returns: (new_s, new_v, new_af, reached_end)
    """
    d = max(0.0, H - s)
    vt = max(0.03, min(vmax, math.sqrt(decel_factor * acc * d)))
    ar = max(-acc, min(acc, (vt - v) / tau_jerk))
    new_af = af + (ar - af) * dt / tau_acc
    new_v = max(0.0, v + new_af * dt)
    new_s = s + new_v * dt
    reached_end = (new_s >= H - 0.005)
    return new_s, new_v, new_af, reached_end

def compute_elevator_force(
    m_car: float,
    m_load: float,
    m_cw: float,
    a_up: float,
    v_up: float,
    g: float = 9.81,
    m_extra: float = 300.0,
    friction_coulomb: float = 300.0,
    v_th: float = 0.05,
    friction_viscous: float = 0.0
) -> float:
    """
    F = (m_car + m_load - m_cw)*g + (m_car + m_load + m_cw + m_extra)*a + F_fric
    F_fric = friction_coulomb * tanh(v / v_th) + friction_viscous * v
    Force is positive upwards (pulling car up).
    """
    m_total_car = m_car + m_load
    F_grav = (m_total_car - m_cw) * g
    F_inertial = (m_total_car + m_cw + m_extra) * a_up
    F_fric = friction_coulomb * math.tanh(v_up / v_th) + friction_viscous * v_up
    return F_grav + F_inertial + F_fric

def compute_mechanical_power(F: float, v_up: float) -> float:
    """
    P_mech = F * v (+ motoring, - regenerating)
    """
    return F * v_up

def compute_ideal_trip_energy(
    m_car: float,
    m_load: float,
    m_cw: float,
    H: float,
    g: float = 9.81,
    eta: float = 1.0
) -> float:
    """
    Ideal single-trip constant-speed mechanical energy (Joules):
    E_mech = (m_car + m_load - m_cw) * g * H
    """
    delta_m = (m_car + m_load) - m_cw
    E_ideal = delta_m * g * H
    if delta_m > 0:
        return E_ideal / eta
    else:
        return E_ideal * eta
