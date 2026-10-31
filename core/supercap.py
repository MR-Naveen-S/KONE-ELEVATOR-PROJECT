"""
Core Supercapacitor Module:
Formulas from Section 4 and Section 10:
- Energy: E = 1/2 * C * V^2; E_usable = 1/2 * C * (Vmax^2 - Vmin^2)
- State of Charge: SoC = (V^2 - Vmin^2) / (Vmax^2 - Vmin^2)
- Current & ESR: I = P / V; P_esr = I^2 * ESR
- Boost duty: D = 1 - Vsc / Vdc; Ripple: Delta_I = Vsc * D / (L * fsw)
- Bank topology: C = C_cell * Np / Ns; V = Ns * V_cell; ESR = ESR_cell * Ns / Np
- Converter loss: P_loss_dcdc = |P_sc_term| - |P_sc_bus|
- Max-power limit at efficiency eta: P_max = eta * (1 - eta) * V^2 / ESR
- Online C and ESR estimators, SOH, and thermal aging.
"""

import math
from typing import Tuple, Dict, Any, Optional

def compute_supercap_energy(C: float, V: float) -> float:
    """E = 1/2 * C * V^2 (Joules)"""
    return 0.5 * C * (V ** 2)

def compute_usable_energy(C: float, Vmax: float, Vmin: float) -> float:
    """
    E_usable = 1/2 * C * (Vmax^2 - Vmin^2) (Joules)
    Hand-calc verification: 15 F, 100 -> 200 V gives:
    0.5 * 15 * (40000 - 10000) = 225,000 J = 62.5 Wh.
    """
    return 0.5 * C * ((Vmax ** 2) - (Vmin ** 2))

def compute_soc(V: float, Vmax: float, Vmin: float) -> float:
    """
    SoC = (V^2 - Vmin^2) / (Vmax^2 - Vmin^2), clamped to [0.0, 1.0]
    """
    denom = (Vmax ** 2) - (Vmin ** 2)
    if denom <= 0:
        return 0.0
    val = ((V ** 2) - (Vmin ** 2)) / denom
    return max(0.0, min(1.0, val))

def compute_voltage_from_soc(soc: float, Vmax: float, Vmin: float) -> float:
    """V = sqrt(Vmin^2 + soc * (Vmax^2 - Vmin^2))"""
    clamped_soc = max(0.0, min(1.0, soc))
    return math.sqrt((Vmin ** 2) + clamped_soc * ((Vmax ** 2) - (Vmin ** 2)))

def compute_boost_duty(Vsc: float, Vdc: float) -> float:
    """Ideal boost converter duty cycle: D = 1 - Vsc / Vdc"""
    if Vdc <= 1.0:
        return 0.0
    return max(0.0, min(1.0, 1.0 - (Vsc / Vdc)))

def compute_current_ripple(Vsc: float, D: float, L: float = 0.0015, fsw: float = 20000.0) -> float:
    """Ripple Delta_I = Vsc * D / (L * fsw) (A)"""
    if L <= 0 or fsw <= 0:
        return 0.0
    return (Vsc * D) / (L * fsw)

def compute_bank_params(
    C_cell: float,
    ESR_cell: float,
    V_cell_nom: float,
    Ns: int,
    Np: int
) -> Tuple[float, float, float]:
    """
    Bank: C = C_cell * Np / Ns
          V = Ns * V_cell
          ESR = ESR_cell * Ns / Np
    """
    C_bank = C_cell * Np / Ns
    V_bank = Ns * V_cell_nom
    ESR_bank = ESR_cell * Ns / Np
    return C_bank, V_bank, ESR_bank

def compute_converter_loss(P_sc_term: float, P_sc_bus: float) -> float:
    """
    Converter loss: P_loss_dcdc = |P_sc_term| - |P_sc_bus|
    Both powers share sign convention: + discharge, - charge.
    """
    return abs(P_sc_term) - abs(P_sc_bus)

def compute_max_power_limit(V: float, ESR: float, eta: float = 0.97) -> float:
    """
    Max-power limit at efficiency eta:
    P = eta * (1 - eta) * V^2 / ESR (W)
    """
    if ESR <= 0:
        return 1e6
    return eta * (1.0 - eta) * (V ** 2) / ESR

def compute_thermal_aging_factor(T_sc: float, T_ref: float = 25.0) -> float:
    """
    Arrhenius rule-of-thumb: aging acceleration ≈ 2^((T - T_ref) / 10)
    """
    return 2.0 ** ((T_sc - T_ref) / 10.0)

def compute_soh(
    C_now: float,
    C_0: float,
    ESR_now: float,
    ESR_0: float
) -> Tuple[float, float, float, bool]:
    """
    SOH_C = (C_now / C_0) * 100 (%)
    SOH_ESR = (ESR_0 / ESR_now) * 100 (%)
    overall_SOH = min(SOH_C, SOH_ESR)
    EOL (End of Life): C <= 80% of C_0 OR ESR >= 200% of ESR_0 (SOH_ESR <= 50%).
    """
    soh_c = (C_now / C_0) * 100.0 if C_0 > 0 else 0.0
    soh_esr = (ESR_0 / ESR_now) * 100.0 if ESR_now > 0 else 0.0
    overall_soh = min(soh_c, soh_esr)
    is_eol = (soh_c <= 80.0) or (esr_growth := (ESR_now / ESR_0) >= 2.0)
    return soh_c, soh_esr, overall_soh, is_eol
