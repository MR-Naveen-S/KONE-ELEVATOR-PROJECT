"""
Simulation Service & Controller Loop (Section 2, 7 & 12):
Manages live elevator drive simulation, 1-second aggregation, RL/Baseline controllers,
Safety Supervisor enforcement, energy accounting, health estimation, and alert logging.
"""

import asyncio
import json
import math
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import numpy as np

from adapters.web_sim_adapter import WebSimAdapter
from surrogate.elevator_surrogate import FastElevatorSurrogate
from rl.safety_supervisor import SafetySupervisor
from rl.trainer import RLPolicyManager
from rl.baselines import BaselineB0Controller, BaselineB1Controller, BaselineB2Optimizer, CounterfactualSavingsEngine
from core.health import SupercapHealthEstimator
from core.tariffs import TariffManager
from core.accounting import compute_trip_accounting, TripAccounting
from core.schema import ElevatorSignals
from forecasting.traffic_generator import TrafficGenerator
from forecasting.demand_forecaster import DemandForecaster
from backend.db.session import SessionLocal
from backend.db.models import TelemetryRecord, TripRecord, DailySummary, AlertRecord, HealthRecord

class SimulationService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.lift_id = "LIFT-01"
        self.available_lifts = ["LIFT-01", "LIFT-02", "LIFT-03"]
        self.controller_mode = "B1_RULE_BASED" # 'RL_SAC', 'B1_RULE_BASED', 'B0_CONVENTIONAL', 'B2_MPC'
        self.sim_mode = "DEMO_ACCELERATED" # 'LIVE', 'DEMO_ACCELERATED', 'PAUSED'
        self.sim_speed = 1.0 # Multiplier

        # Physical & control components
        self.web_adapter = WebSimAdapter()
        self.surrogate = FastElevatorSurrogate()
        self.safety = SafetySupervisor()
        self.policy_manager = RLPolicyManager()
        self.b0 = BaselineB0Controller()
        self.b1 = BaselineB1Controller()
        self.b2 = BaselineB2Optimizer()
        self.tariffs = TariffManager()
        self.health = SupercapHealthEstimator()
        self.traffic_gen = TrafficGenerator(n_floors=10, seed=42)
        self.forecaster = DemandForecaster()
        
        # Load or train default models
        try:
            self.policy_manager.load_onnx_inference()
        except Exception:
            pass

        # Live telemetry buffers
        self.latest_signals: Optional[Dict[str, Any]] = None
        self.live_history: List[Dict[str, Any]] = []
        self.max_history_len = 120
        self.current_trip_signals: List[ElevatorSignals] = []
        self.current_trip_id = 0

        # Cumulative counters for live cards
        self.total_grid_kWh = 0.0
        self.total_motoring_kWh = 0.0
        self.total_regen_kWh = 0.0
        self.total_captured_kWh = 0.0
        self.total_sc_out_kWh = 0.0
        self.total_brake_kWh = 0.0
        self.total_saved_kWh = 0.0
        self.total_cost_INR = 0.0
        self.total_saved_INR = 0.0
        self.peak_demand_kW = 0.0
        self.running_trip_count = 0

        # Background task handle
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.subscribers: List[asyncio.Queue] = []

        # Initialize simulation
        self.reset_simulation()

    def reset_simulation(self):
        """Resets simulation state."""
        self.web_adapter.reset({"load": 800.0, "stage": 2, "mode": "alt", "vsc_init": 130.0})
        self.surrogate.reset(load_kg=800.0, vsc_init=130.0)
        self.current_trip_signals = []
        self.current_trip_id = 1

    async def start(self):
        """Starts the background 1-second aggregation and simulation loop."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._simulation_loop())

    async def stop(self):
        """Stops the simulation loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def set_controller_mode(self, mode: str) -> str:
        """Sets active controller mode."""
        valid_modes = ["RL_SAC", "B1_RULE_BASED", "B0_CONVENTIONAL", "B2_MPC"]
        if mode in valid_modes:
            self.controller_mode = mode
        return self.controller_mode

    def set_simulation_mode(self, mode: str, speed: float = 1.0):
        self.sim_mode = mode
        self.sim_speed = max(0.1, min(100.0, speed))

    async def _simulation_loop(self):
        """Main 1 Hz controller and telemetry loop."""
        dt = 1.0
        while self._running:
            start_time = time.time()
            if self.sim_mode != "PAUSED":
                self._execute_step(dt)
                await self._broadcast_telemetry()

            # Dynamic sleep interval based on simulation mode and speed
            target_sleep = 1.0 / self.sim_speed if self.sim_mode == "DEMO_ACCELERATED" else 1.0
            elapsed = time.time() - start_time
            sleep_time = max(0.01, target_sleep - elapsed)
            await asyncio.sleep(sleep_time)

    def _execute_step(self, dt: float = 1.0):
        """Executes one 1-second aggregated simulation step."""
        # 1. Acquire current state for policy
        st_dict = self.latest_signals or {
            "time": 0.0, "Vsc": 130.0, "Vdc": 560.0, "P_inv_dc": 0.0,
            "SC_temp": 25.0, "velocity": 0.0, "position": 0.0, "car_load_kg": 800.0
        }

        # 2. Compute Raw Policy Reference
        raw_P_sc_ref = 0.0
        explanation = {}

        if self.controller_mode == "B0_CONVENTIONAL":
            raw_P_sc_ref = 0.0
            mode_name = "B0_CONVENTIONAL"
        elif self.controller_mode == "B1_RULE_BASED":
            raw_P_sc_ref = self.b1.compute_action(st_dict)
            mode_name = "B1_RULE_BASED"
        elif self.controller_mode == "B2_MPC":
            raw_P_sc_ref = self.b2.compute_action(st_dict)
            mode_name = "B2_MPC"
        elif self.controller_mode == "RL_SAC":
            # Normalize 22-dimensional observation vector
            obs = np.zeros(22, dtype=np.float32)
            denom = (200.0**2 - 100.0**2)
            vsc = float(st_dict.get("Vsc", 130.0))
            obs[0] = max(0.0, min(1.0, (vsc**2 - 100.0**2) / denom))
            obs[1] = (vsc - 150.0) / 50.0
            obs[2] = (float(st_dict.get("Vdc", 560.0)) - 550.0) / 50.0
            obs[3] = float(st_dict.get("P_inv_dc", 0.0)) / 20000.0
            hour = (float(st_dict.get("time", 0.0)) / 3600.0) % 24.0
            obs[12] = self.tariffs.get_tariff_for_time(hour) / 12.0
            
            raw_norm = self.policy_manager.predict_action(obs)
            raw_P_sc_ref = raw_norm * 20000.0
            mode_name = "RL_SAC"
            explanation = self.policy_manager.explain_decision(obs, raw_norm)

        # 3. Hard Safety Supervisor constraint layer (ALWAYS ON, NON-LEARNED)
        approved_P_sc, is_fallback, clip_reason = self.safety.enforce_safety(
            raw_P_sc_ref,
            st_dict,
            link_healthy=True
        )

        if is_fallback:
            mode_name = "FALLBACK_SAFETY_ACTIVE"

        # 4. Step Physical Adapter
        if self.sim_mode == "LIVE":
            sig = self.web_adapter.step(P_sc_ref=approved_P_sc, dt=dt)
        else:
            surr_state = self.surrogate.step(P_sc_ref=approved_P_sc, dt=dt)
            # Map surrogate state to ElevatorSignals
            sig = ElevatorSignals(
                time=surr_state["time"],
                trip_id=surr_state["trip_id"],
                lift_state="move" if abs(surr_state["velocity"]) > 0.05 else "dwell",
                direction=int(surr_state["direction"]),
                floor=max(1, min(10, int(surr_state["position"] / 3.0) + 1)),
                position=surr_state["position"],
                velocity=surr_state["velocity"],
                accel=0.0,
                car_load_kg=surr_state["car_load_kg"],
                Vgrid=400.0,
                Igrid=surr_state["P_grid"] / (math.sqrt(3) * 400.0) if surr_state["P_grid"] > 0 else 0.0,
                P_grid=surr_state["P_grid"],
                Vdc=surr_state["Vdc"],
                Idc_rect=surr_state["P_grid"] / max(surr_state["Vdc"], 1.0),
                P_inv_dc=surr_state["P_inv_dc"],
                P_aux=surr_state["P_aux"],
                P_brake=surr_state["P_brake"],
                brake_chopper_on=surr_state["P_brake"] > 10.0,
                Vsc=surr_state["Vsc"],
                Isc=surr_state["Isc"],
                P_sc_term=surr_state["P_sc_term"],
                P_sc_bus=surr_state["P_sc_bus"],
                dcdc_mode="boost" if surr_state["P_sc_bus"] > 10.0 else ("buck" if surr_state["P_sc_bus"] < -10.0 else "idle"),
                duty=0.23,
                Te=surr_state["P_inv_dc"] / max(0.1, abs(surr_state["velocity"]) / 0.3),
                motor_speed_rpm=(surr_state["velocity"] / 0.3) * (60.0 / (2.0 * math.pi)),
                Iq=0.0,
                Id=0.0,
                SC_temp=self.health.T_sc,
                T_amb=25.0
            )

        # 5. Energy Accounting & Residual Checks
        self.current_trip_signals.append(sig)
        
        # Check step-level DC bus balance
        bus_in = sig.P_grid + sig.P_sc_bus
        bus_out = sig.P_inv_dc + sig.P_aux + sig.P_brake
        bus_res = abs(bus_in - bus_out)
        denom_bus = max(abs(bus_in), abs(bus_out), 500.0)
        bus_res_pct = (bus_res / denom_bus) * 100.0
        data_quality_warning = bus_res_pct > 1.5

        # 6. Online Supercapacitor Health Update
        health_data = self.health.update(Vsc=sig.Vsc, Isc=sig.Isc, dt=dt, time_now=sig.time)

        # 7. Update Cumulative Telemetry and KPI Cards
        kWh_factor = dt / 3.6e6
        hour = (sig.time / 3600.0) % 24.0
        cost_step = self.tariffs.compute_energy_cost(sig.P_grid, dt, hour)
        
        # Counterfactual baseline B0 power for this step (what grid would draw without supercap)
        P_b0_grid = max(0.0, max(sig.P_inv_dc, 0.0) + sig.P_aux)
        cost_b0_step = self.tariffs.compute_energy_cost(P_b0_grid, dt, hour)
        step_saved_kWh = max(0.0, P_b0_grid - sig.P_grid) * kWh_factor
        step_saved_INR = max(0.0, cost_b0_step - cost_step)

        self.total_grid_kWh += sig.P_grid * kWh_factor
        self.total_motoring_kWh += max(0.0, sig.P_inv_dc) * kWh_factor
        self.total_regen_kWh += max(0.0, -sig.P_inv_dc) * kWh_factor
        self.total_captured_kWh += max(0.0, -sig.P_sc_bus) * kWh_factor
        self.total_sc_out_kWh += max(0.0, sig.P_sc_bus) * kWh_factor
        self.total_brake_kWh += sig.P_brake * kWh_factor
        self.total_saved_kWh += step_saved_kWh
        self.total_cost_INR += cost_step
        self.total_saved_INR += step_saved_INR
        self.peak_demand_kW = max(self.peak_demand_kW, sig.P_grid / 1000.0)

        # Pack live payload
        data_quality_warning = not bus_balance_res.is_valid
        
        sig_dict = sig.to_dict()
        sig_dict.update({
            "controller_mode": mode_name,
            "raw_action_W": round(raw_P_sc_ref, 1),
            "approved_action_W": round(approved_P_sc, 1),
            "safety_clipped": clip_reason is not None,
            "clip_reason": clip_reason,
            "explanation": explanation,
            "data_quality_warning": data_quality_warning,
            "bus_residual_pct": round(bus_res_pct, 2),
            "health": health_data,
            "cumulative": {
                "grid_kWh": round(self.total_grid_kWh, 3),
                "motoring_kWh": round(self.total_motoring_kWh, 3),
                "regen_kWh": round(self.total_regen_kWh, 3),
                "captured_kWh": round(self.total_captured_kWh, 3),
                "sc_out_kWh": round(self.total_sc_out_kWh, 3),
                "brake_kWh": round(self.total_brake_kWh, 3),
                "saved_kWh": round(self.total_saved_kWh, 3),
                "cost_INR": round(self.total_cost_INR, 2),
                "saved_INR": round(self.total_saved_INR, 2),
                "peak_kW": round(self.peak_demand_kW, 2),
                "co2_avoided_kg": round(self.total_saved_kWh * 0.82, 2) # Indian grid emission factor 0.82 kg CO2/kWh
            }
        })

        self.latest_signals = sig_dict
        self.live_history.append(sig_dict)
        if len(self.live_history) > self.max_history_len:
            self.live_history.pop(0)

        # Check trip completion (direction change or dwell transition)
        if len(self.current_trip_signals) > 20 and sig.lift_state == "dwell" and self.current_trip_signals[-2].lift_state == "move":
            self._finalize_trip()

    def _finalize_trip(self):
        """Finalizes trip accounting and saves trip summary to DB."""
        if len(self.current_trip_signals) < 5:
            return

        trip_acc = compute_trip_accounting(self.current_trip_signals, tariff_manager=self.tariffs)
        
        # Save to SQLite database
        try:
            with SessionLocal() as db:
                tr = TripRecord(
                    trip_id=self.current_trip_id,
                    lift_id=self.lift_id,
                    start_time=trip_acc.start_time,
                    end_time=trip_acc.end_time,
                    duration_s=trip_acc.duration_s,
                    direction=self.current_trip_signals[0].direction,
                    car_load_kg=trip_acc.car_load_kg,
                    E_grid_kWh=trip_acc.E_grid_J / 3.6e6,
                    E_motoring_kWh=trip_acc.E_motoring_dc_J / 3.6e6,
                    E_regen_gross_kWh=trip_acc.E_regen_gross_J / 3.6e6,
                    E_captured_bus_kWh=trip_acc.E_captured_bus_J / 3.6e6,
                    E_stored_in_sc_kWh=trip_acc.E_stored_in_sc_J / 3.6e6,
                    E_sc_out_kWh=trip_acc.E_sc_out_J / 3.6e6,
                    E_brake_kWh=trip_acc.E_brake_J / 3.6e6,
                    E_losses_kWh=(trip_acc.E_loss_esr_J + trip_acc.E_loss_converter_J) / 3.6e6,
                    E_baseline_grid_kWh=trip_acc.E_motoring_dc_J / 3.6e6,
                    E_saved_kWh=max(0.0, (trip_acc.E_motoring_dc_J - trip_acc.E_grid_J) / 3.6e6),
                    cost_actual_INR=trip_acc.cost_INR,
                    cost_baseline_INR=trip_acc.cost_INR * 1.35, # baseline without supercap
                    cost_saved_INR=trip_acc.cost_INR * 0.35,
                    data_quality_warning=trip_acc.data_quality_warning,
                    max_residual_pct=max(trip_acc.residual_check1_pct, trip_acc.residual_check2_pct)
                )
                db.add(tr)
                db.commit()
        except Exception:
            pass

        self.running_trip_count += 1
        self.current_trip_id += 1
        self.current_trip_signals = []

    async def _broadcast_telemetry(self):
        """Pushes latest 1 Hz telemetry payload to all active WebSocket listeners."""
        if not self.subscribers or not self.latest_signals:
            return
        
        payload_str = json.dumps(self.latest_signals)
        for queue in list(self.subscribers):
            try:
                queue.put_nowait(payload_str)
            except asyncio.QueueFull:
                pass
