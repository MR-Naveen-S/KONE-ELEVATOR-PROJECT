"""
Core Electrical Module:
PMSM FOC modeling, Inverter efficiency, DC link dynamics, Diode rectifier,
and Brake Chopper hysteresis dissipation.
"""

import math
from typing import Tuple

def compute_pmsm_foc(
    F: float,
    v_up: float,
    r_sheave: float = 0.3,
    pole_pairs: int = 12,
    flux_linkage: float = 2.5,
    R_stator: float = 0.5,
    Ld: float = 0.02
) -> Tuple[float, float, float, float, float, float]:
    """
    Field-Oriented Control with id = 0:
    T = F * r
    wm = v / r (rad/s)
    we = pole_pairs * wm (rad/s)
    iq = T / (1.5 * pole_pairs * flux_linkage) (A)
    vq = R * iq + we * flux_linkage (V)
    vd = -we * Ld * iq (V)
    Pe = 1.5 * vq * iq (W)
    Returns: (T, wm, we, iq, vd, vq, Pe)
    """
    T = F * r_sheave
    wm = v_up / r_sheave
    we = pole_pairs * wm
    iq = T / (1.5 * pole_pairs * flux_linkage)
    vq = R_stator * iq + we * flux_linkage
    vd = -we * Ld * iq
    Pe = 1.5 * vq * iq
    return T, wm, we, iq, vd, vq, Pe

def compute_inverter_dc_power(
    Pe: float,
    eta_inverter: float = 0.97
) -> float:
    """
    DC bus inverter power:
    P_inv_dc = Pe / eta_inverter if Pe >= 0 (motoring) else Pe * eta_inverter (regen)
    """
    if Pe >= 0.0:
        return Pe / eta_inverter
    else:
        return Pe * eta_inverter

def compute_rectifier_current(
    Vdc: float,
    V_rect_noload: float = 540.0,
    R_rect: float = 0.4
) -> float:
    """
    Diode rectifier output current (A):
    I_rect = max(0, (V_rect_noload - Vdc) / R_rect)
    Never negative (diode blocking, no grid export).
    """
    return max(0.0, (V_rect_noload - Vdc) / R_rect)

def update_brake_chopper(
    Vdc: float,
    current_chopper_state: int,
    V_brake_on: float = 600.0,
    hysteresis: float = 15.0,
    R_brake: float = 20.0
) -> Tuple[int, float, float]:
    """
    Brake chopper hysteresis logic:
    ON when Vdc > V_brake_on
    OFF when Vdc < V_brake_on - hysteresis
    Returns: (new_state, I_brake, P_brake)
    """
    if Vdc > V_brake_on:
        new_state = 1
    elif Vdc < (V_brake_on - hysteresis):
        new_state = 0
    else:
        new_state = current_chopper_state

    I_brake = (Vdc / R_brake) if new_state == 1 else 0.0
    P_brake = I_brake * Vdc
    return new_state, I_brake, P_brake

def compute_dc_link_dvdt(
    I_grid: float,
    I_sc_bus: float,
    I_inv_dc: float,
    I_aux: float,
    I_brake: float,
    C_dc: float = 0.0047
) -> float:
    """
    C_dc * dVdc/dt = I_grid + I_sc_bus - I_inv_dc - I_aux - I_brake
    """
    return (I_grid + I_sc_bus - I_inv_dc - I_aux - I_brake) / C_dc
