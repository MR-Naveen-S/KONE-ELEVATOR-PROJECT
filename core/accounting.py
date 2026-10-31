"""
Energy Accounting & Automated Balance Verification Engine
Strict implementation of Section 9 formulas, KPIs, and the three mandatory balance checks.
Integrates 1s power using trapezoidal integration and flags DATA_QUALITY_WARNING
whenever any residual exceeds 1.5% of the larger term.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd
from core.schema import ElevatorSignals

@dataclass
class TripAccounting:
    trip_id: int
    direction: int
    car_load_kg: float
    duration_s: float
    start_time: float
    end_time: float
    
    # Energies in Joules and Watt-hours
    E_grid_J: float = 0.0
    E_motoring_dc_J: float = 0.0
    E_regen_gross_J: float = 0.0
    E_captured_bus_J: float = 0.0
    E_stored_in_sc_J: float = 0.0
    E_unstored_J: float = 0.0
    E_brake_J: float = 0.0
    E_sc_out_J: float = 0.0
    E_sc_out_lift_J: float = 0.0
    E_sc_out_aux_J: float = 0.0
    E_sc_out_remainder_J: float = 0.0
    delta_E_sc_stored_J: float = 0.0
    delta_E_Cdc_J: float = 0.0
    
    # Losses
    E_loss_converter_J: float = 0.0
    E_loss_esr_J: float = 0.0
    E_loss_self_discharge_J: float = 0.0
    
    # Voltages
    Vsc_start: float = 0.0
    Vsc_end: float = 0.0
    Vdc_start: float = 0.0
    Vdc_end: float = 0.0
    peak_kW: float = 0.0
    
    # Financials
    cost_INR: float = 0.0
    
    # KPIs
    regen_capture_ratio: float = 0.0
    self_sufficiency: float = 0.0
    round_trip_efficiency: float = 0.0
    avg_soc: float = 0.0
    equiv_full_cycles: float = 0.0
    
    # Balance Residuals & Flags
    residual_check1_pct: float = 0.0
    residual_check2_pct: float = 0.0
    max_bus_residual_pct: float = 0.0
    data_quality_warning: bool = False
    warning_reasons: List[str] = field(default_factory=list)

    @property
    def E_grid_Wh(self) -> float:
        return self.E_grid_J / 3600.0

    @property
    def E_motoring_dc_Wh(self) -> float:
        return self.E_motoring_dc_J / 3600.0

    @property
    def E_regen_gross_Wh(self) -> float:
        return self.E_regen_gross_J / 3600.0

    @property
    def E_captured_bus_Wh(self) -> float:
        return self.E_captured_bus_J / 3600.0

    @property
    def E_brake_Wh(self) -> float:
        return self.E_brake_J / 3600.0

def compute_trip_accounting(
    signals: List[ElevatorSignals],
    C_sc: float = 15.0,
    Vsc_max: float = 200.0,
    Vsc_min: float = 100.0,
    C_dc: float = 0.0047,
    ESR_sc: float = 0.035,
    tariff_manager = None
) -> TripAccounting:
    """
    Computes rigorous trapezoidal energy accounting and executes balance checks.
    """
    if not signals:
        return TripAccounting(0, 0, 0, 0, 0, 0)

    n = len(signals)
    times = np.array([s.time for s in signals])
    P_grid = np.array([s.P_grid for s in signals])
    P_inv_dc = np.array([s.P_inv_dc for s in signals])
    P_sc_bus = np.array([s.P_sc_bus for s in signals])
    P_sc_term = np.array([s.P_sc_term for s in signals])
    P_brake = np.array([s.P_brake for s in signals])
    P_aux = np.array([s.P_aux for s in signals])
    Vdc = np.array([s.Vdc for s in signals])
    Vsc = np.array([s.Vsc for s in signals])
    Isc = np.array([s.Isc for s in signals])

    # Trapezoidal integration helper
    def trapz_int(y: np.ndarray) -> float:
        if n == 1:
            return float(y[0] * 1.0)
        return float(np.trapezoid(y, times))

    E_grid = trapz_int(P_grid)
    E_motoring_dc = trapz_int(np.maximum(P_inv_dc, 0.0))
    E_regen_gross = trapz_int(np.maximum(-P_inv_dc, 0.0))
    
    # E_captured_bus: energy leaving DC bus into the supercap path (P_sc_bus < 0 is charging)
    P_bus_charge = np.maximum(-P_sc_bus, 0.0)
    E_captured_bus = trapz_int(P_bus_charge)

    # E_sc_out: energy injected from supercap into DC bus (P_sc_bus > 0 is discharging)
    P_bus_discharge = np.maximum(P_sc_bus, 0.0)
    E_sc_out = trapz_int(P_bus_discharge)

    # Step-by-step split of discharged energy:
    # to_lift = min(P_sc_bus_pos, max(P_inv_dc, 0))
    # to_aux = min(P_sc_bus_pos - to_lift, P_aux)
    # remainder = flagged if > 0
    P_lift_pos = np.maximum(P_inv_dc, 0.0)
    P_to_lift = np.minimum(P_bus_discharge, P_lift_pos)
    P_to_aux = np.minimum(P_bus_discharge - P_to_lift, P_aux)
    P_rem = P_bus_discharge - P_to_lift - P_to_aux

    E_sc_out_lift = trapz_int(P_to_lift)
    E_sc_out_aux = trapz_int(P_to_aux)
    E_sc_out_rem = trapz_int(P_rem)

    E_brake = trapz_int(P_brake)

    # Converter loss: |P_sc_term| - |P_sc_bus|
    P_loss_conv = np.maximum(0.0, np.abs(P_sc_term) - np.abs(P_sc_bus))
    E_loss_converter = trapz_int(P_loss_conv)
    E_stored_in_sc = max(0.0, E_captured_bus - E_loss_converter)

    # ESR loss = Isc^2 * ESR
    P_loss_esr = (Isc ** 2) * ESR_sc
    E_loss_esr = trapz_int(P_loss_esr)

    # Stored energy change in Supercapacitor: delta E = 0.5 * C * (V_end^2 - V_start^2)
    Vsc_start = float(Vsc[0])
    Vsc_end = float(Vsc[-1])
    delta_E_sc_stored = 0.5 * C_sc * ((Vsc_end ** 2) - (Vsc_start ** 2))

    # Stored energy change in DC Link Capacitor
    Vdc_start = float(Vdc[0])
    Vdc_end = float(Vdc[-1])
    delta_E_Cdc = 0.5 * C_dc * ((Vdc_end ** 2) - (Vdc_start ** 2))

    E_unstored = E_brake + max(0.0, E_regen_gross - E_captured_bus - E_brake)

    # Peak kW
    peak_kW = float(np.max(P_grid) / 1000.0) if len(P_grid) > 0 else 0.0

    # Financial cost calculation
    cost_INR = 0.0
    if tariff_manager:
        for s in signals:
            hour = (s.time / 3600.0) % 24.0
            cost_INR += tariff_manager.compute_energy_cost(s.P_grid, 1.0, hour)

    # KPIs
    regen_capture_ratio = (E_captured_bus / E_regen_gross) if E_regen_gross > 1.0 else 0.0
    self_sufficiency = (E_sc_out_lift / E_motoring_dc) if E_motoring_dc > 1.0 else 0.0
    
    # Energy-adjusted roundtrip efficiency: E_sc_out / (E_captured_bus - delta_E_sc_stored)
    denom_rt = (E_captured_bus - delta_E_sc_stored)
    round_trip_eff = (E_sc_out / denom_rt) if denom_rt > 10.0 else 0.0

    # SoC calculation
    soc_arr = np.clip((Vsc ** 2 - Vsc_min ** 2) / (Vsc_max ** 2 - Vsc_min ** 2), 0.0, 1.0)
    avg_soc = float(np.mean(soc_arr))

    # Usable energy for full cycles
    E_usable = 0.5 * C_sc * (Vsc_max ** 2 - Vsc_min ** 2)
    equiv_cycles = E_captured_bus / E_usable if E_usable > 0 else 0.0

    # ==============================================================
    # MANDATORY BALANCE CHECKS (Section 9)
    # Residual limit: 1.5% of the larger term
    # ==============================================================
    data_quality_warning = False
    warning_reasons = []

    # Check 1: E_regen_gross ≈ E_captured_bus + E_brake + delta_E_Cdc (+ direct aux use)
    # During regenerative phase (P_inv_dc < 0), DC bus auxiliary loads are supplied directly by regen
    P_aux_from_regen = np.where(P_inv_dc < 0.0, np.minimum(-P_inv_dc, P_aux), 0.0)
    E_aux_direct_use = trapz_int(P_aux_from_regen)

    term1_left = E_regen_gross
    term1_right = E_captured_bus + E_brake + delta_E_Cdc + E_aux_direct_use
    larger1 = max(abs(term1_left), abs(term1_right), 100.0)
    residual1_pct = (abs(term1_left - term1_right) / larger1) * 100.0
    if E_regen_gross > 500.0 and residual1_pct > 1.5:
        data_quality_warning = True
        warning_reasons.append(f"Regen balance check 1 failed: residual={residual1_pct:.2f}% (> 1.5%)")

    # Check 2: E_captured_bus ≈ E_sc_out + delta_E_sc_stored + E_losses
    term2_left = E_captured_bus
    term2_right = E_sc_out + delta_E_sc_stored + E_loss_converter + E_loss_esr
    larger2 = max(abs(term2_left), abs(term2_right), 100.0)
    residual2_pct = (abs(term2_left - term2_right) / larger2) * 100.0
    if E_captured_bus > 500.0 and residual2_pct > 1.5:
        data_quality_warning = True
        warning_reasons.append(f"SC storage balance check 2 failed: residual={residual2_pct:.2f}% (> 1.5%)")

    # Check 3: Instantaneous bus balance residual at every step
    # P_grid + P_sc_bus = P_inv_dc + P_aux + P_brake + d(0.5 * Cdc * Vdc^2)/dt
    P_cdc = np.array([getattr(s, "P_Cdc", 0.0) for s in signals])
    bus_in = P_grid + P_sc_bus
    bus_out = P_inv_dc + P_aux + P_brake + P_cdc
    bus_residual = np.abs(bus_in - bus_out)
    denom_bus = np.maximum(np.maximum(np.abs(bus_in), np.abs(bus_out)), 500.0)
    step_res_pct = (bus_residual / denom_bus) * 100.0
    max_bus_res_pct = float(np.max(step_res_pct))
    if max_bus_res_pct > 1.5:
        data_quality_warning = True
        warning_reasons.append(f"Bus balance check 3 step residual exceeded: max={max_bus_res_pct:.2f}% (> 1.5%)")

    return TripAccounting(
        trip_id=signals[0].trip_id,
        direction=signals[0].direction,
        car_load_kg=signals[0].car_load_kg,
        duration_s=float(times[-1] - times[0]),
        start_time=float(times[0]),
        end_time=float(times[-1]),
        E_grid_J=E_grid,
        E_motoring_dc_J=E_motoring_dc,
        E_regen_gross_J=E_regen_gross,
        E_captured_bus_J=E_captured_bus,
        E_stored_in_sc_J=E_stored_in_sc,
        E_unstored_J=E_unstored,
        E_brake_J=E_brake,
        E_sc_out_J=E_sc_out,
        E_sc_out_lift_J=E_sc_out_lift,
        E_sc_out_aux_J=E_sc_out_aux,
        E_sc_out_remainder_J=E_sc_out_rem,
        delta_E_sc_stored_J=delta_E_sc_stored,
        delta_E_Cdc_J=delta_E_Cdc,
        E_loss_converter_J=E_loss_converter,
        E_loss_esr_J=E_loss_esr,
        E_loss_self_discharge_J=0.0,
        Vsc_start=Vsc_start,
        Vsc_end=Vsc_end,
        Vdc_start=Vdc_start,
        Vdc_end=Vdc_end,
        peak_kW=peak_kW,
        cost_INR=cost_INR,
        regen_capture_ratio=regen_capture_ratio,
        self_sufficiency=self_sufficiency,
        round_trip_efficiency=round_trip_eff,
        avg_soc=avg_soc,
        equiv_full_cycles=equiv_cycles,
        residual_check1_pct=residual1_pct,
        residual_check2_pct=residual2_pct,
        max_bus_residual_pct=max_bus_res_pct,
        data_quality_warning=data_quality_warning,
        warning_reasons=warning_reasons
    )
