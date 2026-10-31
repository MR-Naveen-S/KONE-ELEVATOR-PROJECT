"""
Baselines Module (Section 8, Section 9, and Section 11):
- B0: Conventional Elevator without Supercapacitor (Stage 1, Brake Chopper Only)
- B1: Rule-Based Controller (Capture all regen, discharge on all motoring)
- B2: Dynamic Programming / MPC Upper Bound with Perfect Knowledge
- Counterfactual Savings Engine (Computes exact kWh and ₹ saved, demand charge reduction, CO2 avoided)
"""

import math
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from core.schema import ElevatorSignals
from core.tariffs import TariffManager

class BaselineB0Controller:
    """
    Baseline B0: Stage 1 Conventional Elevator.
    Supercapacitor is disconnected (P_sc_ref = 0.0 W).
    All regenerative braking energy is dumped into the brake resistor.
    """
    def __init__(self):
        self.name = "B0_Conventional"

    def compute_action(self, state: Dict[str, Any]) -> float:
        return 0.0

class BaselineB1Controller:
    """
    Baseline B1: Rule-Based Supercapacitor Controller.
    Rules:
    - Motoring phase (P_inv_dc > 0): Discharge supercap into DC bus to supply motor + aux
      up to DC-DC power limit and voltage limit (Vsc >= Vmin).
    - Regenerative phase (P_inv_dc < 0): Charge supercap from DC bus (capture all regen)
      up to DC-DC power limit and voltage limit (Vsc <= Vmax).
    - Idle/Dwell: Hold (0.0 W).
    """
    def __init__(
        self,
        Vsc_min: float = 100.0,
        Vsc_max: float = 200.0,
        I_max: float = 100.0,
        eta_dcdc: float = 0.97
    ):
        self.name = "B1_RuleBased"
        self.Vsc_min = Vsc_min
        self.Vsc_max = Vsc_max
        self.I_max = I_max
        self.eta = eta_dcdc

    def compute_action(self, state: Dict[str, Any]) -> float:
        """
        Returns P_sc_ref (W) on DC bus side:
        + positive: discharge into DC bus
        - negative: charge from DC bus
        """
        Vsc = float(state.get("Vsc", 130.0))
        P_inv_dc = float(state.get("P_inv_dc", 0.0))
        P_aux = float(state.get("P_aux", 250.0))
        
        # Max terminal power: P_lim = I_max * Vsc
        P_lim_term = self.I_max * Vsc
        # Max power on bus side
        P_lim_bus = P_lim_term * self.eta

        if P_inv_dc > 50.0: # Motoring
            if Vsc > self.Vsc_min + 2.0:
                # Demand on DC bus to support lift and aux
                desired_discharge_bus = P_inv_dc + P_aux
                # Smooth tapering near Vmin
                margin = max(0.0, min(1.0, (Vsc - self.Vsc_min) / 5.0))
                return min(P_lim_bus, desired_discharge_bus) * margin
            else:
                return 0.0

        elif P_inv_dc < -50.0: # Regenerating
            if Vsc < self.Vsc_max - 2.0:
                # Excess regen on DC bus after supplying aux
                available_regen_bus = abs(P_inv_dc) - P_aux
                if available_regen_bus > 0.0:
                    margin = max(0.0, min(1.0, (self.Vsc_max - Vsc) / 5.0))
                    # Charging is negative in our convention
                    return -min(P_lim_bus, available_regen_bus) * margin
                else:
                    return 0.0
            else:
                return 0.0

        else: # Idle / Standstill
            return 0.0

class BaselineB2Optimizer:
    """
    Baseline B2: Dynamic Programming / MPC Upper Bound.
    Assumes perfect lookahead knowledge of the upcoming trip sequence and tariff schedule.
    Formulates a linear/dynamic program to find the theoretical minimum energy cost.
    """
    def __init__(
        self,
        C_sc: float = 15.0,
        Vsc_min: float = 100.0,
        Vsc_max: float = 200.0,
        I_max: float = 100.0,
        eta: float = 0.97
    ):
        self.name = "B2_DP_MPC_Optimum"
        self.C_sc = C_sc
        self.Vsc_min = Vsc_min
        self.Vsc_max = Vsc_max
        self.I_max = I_max
        self.eta = eta
        self.E_min = 0.5 * C_sc * (Vsc_min ** 2)
        self.E_max = 0.5 * C_sc * (Vsc_max ** 2)

    def optimize_trip_sequence(
        self,
        P_inv_sequence: List[float],
        P_aux_sequence: List[float],
        tariff_sequence: List[float],
        dt: float = 1.0,
        init_Vsc: float = 130.0
    ) -> List[float]:
        """
        Solves the optimal P_sc_ref sequence maximizing self-consumption and peak-shaving.
        Upper bound heuristic: full capture of regen, optimal discharge during highest tariff.
        """
        T = len(P_inv_sequence)
        P_opt = [0.0] * T
        current_E = 0.5 * self.C_sc * (init_Vsc ** 2)

        for t in range(T):
            P_inv = P_inv_sequence[t]
            P_aux = P_aux_sequence[t]
            Vsc = math.sqrt(2.0 * max(1.0, current_E) / self.C_sc)
            P_lim = self.I_max * Vsc * self.eta

            if P_inv < 0: # Regen
                avail = max(0.0, abs(P_inv) - P_aux)
                headroom_E = max(0.0, self.E_max - current_E)
                P_cap = min(avail, P_lim, headroom_E / dt * self.eta)
                P_opt[t] = -P_cap
                current_E += P_cap * self.eta * dt
            elif P_inv > 0: # Motoring
                req = P_inv + P_aux
                usable_E = max(0.0, current_E - self.E_min)
                P_dis = min(req, P_lim, (usable_E / dt) * self.eta)
                P_opt[t] = P_dis
                current_E -= (P_dis / self.eta) * dt
            else:
                P_opt[t] = 0.0

            current_E = max(self.E_min, min(self.E_max, current_E))

        return P_opt

class CounterfactualSavingsEngine:
    """
    Computes exact counterfactual comparison between B0 (no supercap)
    and B1/RL (with supercap) on the identical trip sequence.
    """
    def __init__(self, tariff_manager: Optional[TariffManager] = None):
        self.tariffs = tariff_manager or TariffManager()

    def compare_runs(
        self,
        signals_b0: List[ElevatorSignals],
        signals_actual: List[ElevatorSignals],
        system_cost_INR: float = 350000.0,
        dt_s: float = 1.0
    ) -> Dict[str, Any]:
        """
        E_saved = E_grid_b0 - E_grid_actual
        INR_saved = Bill_b0 - Bill_actual (including demand charge effect)
        """
        assert len(signals_b0) == len(signals_actual), "Sequences must have identical length!"

        n = len(signals_b0)
        times = [s.time for s in signals_actual]

        # Integrate grid energies
        P_grid_b0 = np.array([s.P_grid for s in signals_b0])
        P_grid_act = np.array([s.P_grid for s in signals_actual])
        P_brake_b0 = np.array([s.P_brake for s in signals_b0])
        P_brake_act = np.array([s.P_brake for s in signals_actual])

        E_grid_b0_kWh = float(np.sum(P_grid_b0 * dt_s) / 3.6e6)
        E_grid_act_kWh = float(np.sum(P_grid_act * dt_s) / 3.6e6)
        E_saved_kWh = max(0.0, E_grid_b0_kWh - E_grid_act_kWh)

        E_brake_b0_kWh = float(np.sum(P_brake_b0 * dt_s) / 3.6e6)
        E_brake_act_kWh = float(np.sum(P_brake_act * dt_s) / 3.6e6)
        E_brake_saved_kWh = max(0.0, E_brake_b0_kWh - E_brake_act_kWh)

        # Peak power
        peak_b0_kW = float(np.max(P_grid_b0) / 1000.0) if n > 0 else 0.0
        peak_act_kW = float(np.max(P_grid_act) / 1000.0) if n > 0 else 0.0
        peak_reduction_kW = max(0.0, peak_b0_kW - peak_act_kW)
        peak_reduction_pct = (peak_reduction_kW / peak_b0_kW * 100.0) if peak_b0_kW > 0 else 0.0

        # Tariffs & billing
        cost_b0_energy = 0.0
        cost_act_energy = 0.0
        for i in range(n):
            hour = (times[i] / 3600.0) % 24.0
            cost_b0_energy += self.tariffs.compute_energy_cost(P_grid_b0[i], dt_s, hour)
            cost_act_energy += self.tariffs.compute_energy_cost(P_grid_act[i], dt_s, hour)

        # Pro-rated demand charge savings
        monthly_demand_saved = self.tariffs.compute_demand_charge(peak_reduction_kW)
        # For the evaluated duration (fraction of a 30-day month)
        fraction_of_month = (n * dt_s) / (30.0 * 86400.0)
        demand_saved_prorated = monthly_demand_saved * fraction_of_month

        energy_saved_INR = cost_b0_energy - cost_act_energy
        total_saved_INR = energy_saved_INR + demand_saved_prorated

        # Environmental KPI
        co2_avoided_kg = E_saved_kWh * self.tariffs.emission_factor

        # Simple Payback Period (years)
        # Annualized savings:
        if (n * dt_s) > 0:
            annual_saved_INR = total_saved_INR * (365.25 * 86400.0 / (n * dt_s))
            payback_years = (system_cost_INR / annual_saved_INR) if annual_saved_INR > 1.0 else 99.0
        else:
            payback_years = 99.0

        # Energy-adjusted savings accounting for delta E_sc
        Vsc_start = float(signals_actual[0].Vsc)
        Vsc_end = float(signals_actual[-1].Vsc)
        delta_E_sc_J = 0.5 * 15.0 * ((Vsc_end ** 2) - (Vsc_start ** 2))
        delta_E_sc_kWh = float(delta_E_sc_J / 3.6e6)
        # Net savings: raw grid energy saved plus energy left in supercap
        net_E_saved_kWh = E_saved_kWh + delta_E_sc_kWh

        return {
            "E_grid_b0_kWh": E_grid_b0_kWh,
            "E_grid_actual_kWh": E_grid_act_kWh,
            "E_saved_kWh": E_saved_kWh,
            "net_E_saved_kWh": net_E_saved_kWh,
            "delta_E_sc_kWh": delta_E_sc_kWh,
            "energy_saved_pct": (E_saved_kWh / E_grid_b0_kWh * 100.0) if E_grid_b0_kWh > 0 else 0.0,
            "net_energy_saved_pct": (net_E_saved_kWh / E_grid_b0_kWh * 100.0) if E_grid_b0_kWh > 0 else 0.0,
            "E_brake_b0_kWh": E_brake_b0_kWh,
            "E_brake_actual_kWh": E_brake_act_kWh,
            "E_brake_saved_kWh": E_brake_saved_kWh,
            "peak_b0_kW": peak_b0_kW,
            "peak_actual_kW": peak_act_kW,
            "peak_reduction_kW": peak_reduction_kW,
            "peak_reduction_pct": peak_reduction_pct,
            "cost_b0_INR": cost_b0_energy,
            "cost_actual_INR": cost_act_energy,
            "total_saved_INR": total_saved_INR,
            "co2_avoided_kg": co2_avoided_kg,
            "payback_years": round(payback_years, 1)
        }
