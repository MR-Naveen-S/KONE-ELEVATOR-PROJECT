"""
Gymnasium Elevator Drive RL Environment (Section 8):
Integrates FastElevatorSurrogate, Hard Safety Supervisor, Tariff Manager,
and Demand Forecaster.

Observation Space (22 continuous dimensions, normalized):
[SoC, Vsc, Vdc, P_inv_dc, lift_state, velocity, direction, position, load,
 time_sin, time_cos, weekday, tariff_now, tariff_next, running_peak_kW,
 fc_5m, fc_15m, fc_60m, fc_p10, fc_p90, SC_temp, SOH]

Action Space:
Box(-1.0, 1.0, shape=(1,)): normalized P_sc_ref in [-P_max, +P_max].
Hard Safety Supervisor intercepts and bounds every action before execution.

Reward per step (Section 8 Mandate):
r = - tariff * P_grid * dt - lambda1 * delta_peak - lambda2 * E_brake
    - lambda3 * |delta_P_sc| - lambda4 * aging - lambda5 * violations
    + beta * delta_E_sc * price_ref
"""

import math
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import gymnasium as gym
from gymnasium import spaces

from surrogate.elevator_surrogate import FastElevatorSurrogate
from rl.safety_supervisor import SafetySupervisor
from core.tariffs import TariffManager
from forecasting.traffic_generator import TrafficGenerator

class ElevatorRLEnv(gym.Env):
    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        max_steps_per_episode: int = 1440 # 1440 steps of 60s = 1 day, or 3600 steps of 1s
    ):
        super().__init__()
        self.cfg = config or {}
        self.dt = float(self.cfg.get("dt_aggregate_s", 1.0)) # 1.0 s step
        self.max_steps = max_steps_per_episode
        
        # Reward coefficients from config / prompt Section 8
        self.lambda1 = float(self.cfg.get("lambda1_peak", 5.0))
        self.lambda2 = float(self.cfg.get("lambda2_brake", 0.005))
        self.lambda3 = float(self.cfg.get("lambda3_action_rate", 0.0001))
        self.lambda4 = float(self.cfg.get("lambda4_aging", 0.001))
        self.lambda5 = float(self.cfg.get("lambda5_violation", 50.0))
        self.beta = float(self.cfg.get("beta_stored_value", 0.85))

        # Core subsystems
        self.surrogate = FastElevatorSurrogate(self.cfg)
        self.safety = SafetySupervisor(
            Vsc_min=self.surrogate.Vsc_min,
            Vsc_max=self.surrogate.Vsc_max,
            I_max=self.surrogate.I_dcdc_max,
            P_max=20000.0,
            eta_dcdc=self.surrogate.eta_dcdc
        )
        self.tariffs = TariffManager(self.cfg)
        self.traffic_gen = TrafficGenerator(n_floors=10, seed=42)

        # Action Space: normalized P_sc_ref in [-1.0, 1.0]
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(1,), dtype=np.float32)

        # Observation Space: 22 normalized signals
        self.observation_space = spaces.Box(low=-2.0, high=2.0, shape=(22,), dtype=np.float32)

        self.step_count = 0
        self.running_peak_kW = 0.0
        self.prev_action_W = 0.0
        self.prev_Vsc = 130.0
        self.soh = 100.0

    def reset(
        self,
        *,
        seed: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed)
        if seed is not None:
            self.traffic_gen = TrafficGenerator(n_floors=10, seed=seed)

        load = float(options.get("load", 800.0)) if options else 800.0
        vsc_init = float(options.get("vsc_init", 130.0)) if options else 130.0
        
        state = self.surrogate.reset(load_kg=load, vsc_init=vsc_init)
        self.step_count = 0
        self.running_peak_kW = 0.0
        self.prev_action_W = 0.0
        self.prev_Vsc = state["Vsc"]
        self.soh = 100.0

        obs = self._get_obs(state)
        info = {"initial_state": state}
        return obs, info

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        # 1. Denormalize action from [-1.0, 1.0] to [-P_max, +P_max]
        raw_action = float(action[0]) if isinstance(action, (np.ndarray, list)) else float(action)
        P_max = 20000.0
        demanded_P_sc_ref = raw_action * P_max

        # 2. Hard Safety Supervisor constraint layer
        curr_state = self.surrogate._get_state_dict(
            0.0, 0.0, 250.0, 0.0, 0.0, 0.0,
            self.surrogate.Vdc, self.surrogate.Vsc, 0.0, self.surrogate.v
        )
        approved_P_sc, is_fallback, clip_reason = self.safety.enforce_safety(
            demanded_P_sc_ref,
            curr_state,
            link_healthy=True
        )

        # 3. Step the physical surrogate
        next_state = self.surrogate.step(P_sc_ref=approved_P_sc, dt=self.dt)
        self.step_count += 1

        # 4. Compute Billing and Rewards
        hour = (next_state["time"] / 3600.0) % 24.0
        current_tariff = self.tariffs.get_tariff_for_time(hour)
        
        # Grid power and cost
        P_grid_kW = next_state["P_grid"] / 1000.0
        energy_cost_INR = (next_state["P_grid"] * self.dt / 3.6e6) * current_tariff

        # Running peak demand penalty (billing window peak ratchet)
        delta_peak = max(0.0, P_grid_kW - self.running_peak_kW)
        self.running_peak_kW = max(self.running_peak_kW, P_grid_kW)
        r_peak = self.lambda1 * delta_peak

        # Brake dump penalty
        E_brake_Wh = (next_state["P_brake"] * self.dt) / 3600.0
        r_brake = self.lambda2 * E_brake_Wh

        # Action rate / jerk penalty
        delta_action = abs(approved_P_sc - self.prev_action_W)
        r_action_rate = self.lambda3 * (delta_action / P_max)
        self.prev_action_W = approved_P_sc

        # Aging wear cost
        T_sc = float(next_state.get("SC_temp", 25.0))
        aging_factor = 2.0 ** ((T_sc - 25.0) / 10.0)
        r_aging = self.lambda4 * (aging_factor - 1.0)

        # Safety violation penalty (if clipped)
        r_violation = self.lambda5 if (clip_reason is not None and not is_fallback) else 0.0

        # Future stored energy credit
        # delta E_sc (Joules) = 0.5 * C * (V_end^2 - V_start^2)
        delta_E_sc_J = 0.5 * self.surrogate.C_sc * (next_state["Vsc"]**2 - self.prev_Vsc**2)
        delta_E_sc_kWh = delta_E_sc_J / 3.6e6
        future_price_ref = 8.5 # expected average future tariff
        r_stored_credit = self.beta * delta_E_sc_kWh * future_price_ref
        self.prev_Vsc = next_state["Vsc"]

        # Total reward per step
        reward = (
            - energy_cost_INR
            - r_peak
            - r_brake
            - r_action_rate
            - r_aging
            - r_violation
            + r_stored_credit
        )

        terminated = (self.step_count >= self.max_steps)
        truncated = False

        obs = self._get_obs(next_state)
        info = {
            "time": next_state["time"],
            "P_grid_W": next_state["P_grid"],
            "P_inv_dc_W": next_state["P_inv_dc"],
            "P_sc_bus_W": next_state["P_sc_bus"],
            "P_brake_W": next_state["P_brake"],
            "Vsc": next_state["Vsc"],
            "Vdc": next_state["Vdc"],
            "SoC": next_state["soc"],
            "energy_cost_INR": energy_cost_INR,
            "running_peak_kW": self.running_peak_kW,
            "approved_P_sc": approved_P_sc,
            "is_fallback": is_fallback,
            "clip_reason": clip_reason,
            "reward_breakdown": {
                "energy_cost": -energy_cost_INR,
                "peak_penalty": -r_peak,
                "brake_penalty": -r_brake,
                "stored_credit": r_stored_credit,
                "violation_penalty": -r_violation
            }
        }

        return obs, float(reward), terminated, truncated, info

    def _get_obs(self, st: Dict[str, float]) -> np.ndarray:
        hour = (st["time"] / 3600.0) % 24.0
        time_sin = math.sin(2.0 * math.pi * hour / 24.0)
        time_cos = math.cos(2.0 * math.pi * hour / 24.0)
        tariff_now = self.tariffs.get_tariff_for_time(hour) / 12.0
        tariff_next = self.tariffs.get_tariff_for_time((hour + 1.0) % 24.0) / 12.0
        
        # State encoding
        lift_state_code = 1.0 if abs(st["velocity"]) > 0.05 else 0.0
        v_norm = st["velocity"] / self.surrogate.vmax
        pos_norm = st["position"] / self.surrogate.H
        load_norm = st["car_load_kg"] / 1000.0
        P_inv_norm = st["P_inv_dc"] / 20000.0
        Vsc_norm = (st["Vsc"] - 150.0) / 50.0 # centered around 150V
        Vdc_norm = (st["Vdc"] - 550.0) / 50.0 # centered around 550V

        # Heuristic forecast inputs
        fc_5m = min(1.0, abs(st["P_inv_dc"]) / 20000.0)
        fc_15m = 0.5 + 0.3 * time_sin
        fc_60m = 0.5 + 0.4 * time_sin
        fc_p10 = max(0.0, fc_15m - 0.2)
        fc_p90 = min(1.0, fc_15m + 0.2)
        temp_norm = (st.get("SC_temp", 25.0) - 25.0) / 40.0

        obs = np.array([
            st["soc"],
            Vsc_norm,
            Vdc_norm,
            P_inv_norm,
            lift_state_code,
            v_norm,
            float(st["direction"]),
            pos_norm,
            load_norm,
            time_sin,
            time_cos,
            0.5, # weekday normalized
            tariff_now,
            tariff_next,
            self.running_peak_kW / 30.0,
            fc_5m,
            fc_15m,
            fc_60m,
            fc_p10,
            fc_p90,
            temp_norm,
            self.soh / 100.0
        ], dtype=np.float32)

        return np.clip(obs, -2.0, 2.0)
