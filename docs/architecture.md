# System Architecture & Monorepo Design
**Regenerative Supercapacitor Elevator Energy Manager**
*End-to-End System Specifications, Interfaces, and Operational Dataflows*

---

## 1. High-Level Architecture Overview

The system is organized as a high-performance modular monorepo supporting hardware-in-the-loop (HIL) simulators, physical elevator drives, offline mathematical surrogates, multi-horizon demand forecasting, non-learned Safety Supervision, and interactive management dashboards.

```
+---------------------------------------------------------------------------------------+
|                                    REACT DASHBOARD                                    |
|   Live Drive Lab  |  Energy Waterfall  |  Savings  |  Health  |  Forecast  |  Trips   |
+---------------------------------------------------------------------------------------+
        ^                                               ^
        | WebSocket (/ws/live)                          | REST API (/api/*)
+---------------------------------------------------------------------------------------+
|                                 FASTAPI BACKEND                                       |
|  Simulation Service  |  1-s Aggregator  |  ReportLab Exporter  |  SQLAlchemy Models   |
+---------------------------------------------------------------------------------------+
        |                                               |
        v                                               v
+----------------------------------+            +---------------------------------------+
|      SAFETY SUPERVISOR           |            |         ENERGY ACCOUNTING             |
|  - Physical Vsc/Vdc bounds       |            |  - Trapezoidal integration            |
|  - Idcdc inductor limits         |            |  - Gross regen vs captured vs brake   |
|  - Thermal cutoff (65 degC)      |            |  - Automated balance checks (< 1.5%)  |
|  - Duty cycle validation         |            |  - Counterfactual baseline comparison |
+----------------------------------+            +---------------------------------------+
        ^                                               ^
        | Controlled Action (P_sc_ref)                  | 1-second Telemetry
+----------------------------------+                    |
|       ACTIVE CONTROLLER          |                    |
|  - SAC / TD3 Reinforcement Agent |                    |
|  - Rule-Based Autonomous (B1)    |                    |
|  - Conventional Baseline (B0)    |                    |
|  - Perfect-Knowledge MPC (B2)    |                    |
+----------------------------------+                    |
        ^                                               |
        | State & Forecast                              |
+---------------------------------------------------------------------------------------+
|                              SIMULATION ADAPTER LAYER                                 |
|  [WebSimAdapter]     [FastElevatorSurrogate]     [FileReplay]     [Matlab/FMU Stubs]  |
|   (Browser Model)        (> 100k steps/s)        (CSV/MAT)          (Hardware/Sim)    |
+---------------------------------------------------------------------------------------+
```

---

## 2. Directory Layout & Module Responsibilities

- **`adapters/`**: Simulator adapter interface (`SimulatorAdapter`) exposing `reset()`, `step(P_sc_ref, dt)`, and `get_static_params()`.
  - `WebSimAdapter`: High-fidelity discrete physical model mirroring browser simulator dynamics.
  - `FastElevatorSurrogate`: Average-value numerical model running $> 100{,}000$ steps/s passing the validation gate.
  - `FileReplayAdapter`: Replays historical field CSV/JSON telemetry recordings.
  - `MatlabEngineAdapter`: Integration stub for MATLAB/Simulink Simscape models.
  - `FmuAdapter`: FMI 2.0 co-simulation FMU bridge for industrial drive benches.
- **`core/`**: Pure, unit-tested physical equations, accounting, and supercapacitor estimators:
  - `mechanics.py`: Traction forces, counterweight dynamics, rope roping inertia, and sheave power.
  - `electrical.py`: DC link capacitor dynamics, rectifier, dynamic brake chopper, and inverter FOC models.
  - `supercap.py`: Bank scaling, usable energy, ESR losses, boost duty, and maximum power limits.
  - `accounting.py`: Section 9 energy integrations, counterfactual savings engine, and balance residual audits.
  - `tariffs.py`: Multi-tier Time-of-Use (ToU) billing and rolling maximum demand charges.
  - `health.py`: Online $C = \int i \, dt / \Delta V$, ESR $= \Delta V / \Delta I$, first-order thermal model, and degradation injector.
- **`forecasting/`**:
  - `traffic_generator.py`: Stochastic building traffic simulator (morning peak, lunch, evening peak, inter-floor, night).
  - `demand_forecaster.py`: Quantile LightGBM/XGBoost predictor outputting P10/P50/P90 forward demand and planned charge/discharge schedules.
- **`rl/`**: Safe Reinforcement Learning environment and benchmarks:
  - `safety_supervisor.py`: Hard non-learned physical projection clipping action $P_{\text{sc\_ref}}$.
  - `elevator_env.py`: Standard Gymnasium environment with normalized observation spaces and multi-objective rewards.
  - `trainer.py`: SAC/TD3 policy trainer with automated TorchScript ONNX export.
  - `baselines.py`: Conventional B0, Rule-Based B1, and Perfect-Knowledge MPC B2 baselines.
  - `evaluate.py`: Benchmark evaluation suite enforcing the Section 8 Honesty Requirement.
- **`backend/`**:
  - `services/simulation_service.py`: 1-second orchestrator, WebSocket broadcaster, and controller loop.
  - `services/report_generator.py`: PDF executive generator (ReportLab) and CSV ledger generator.
  - `routers/`: FastAPI REST endpoints and WebSocket channels.
  - `db/`: SQLAlchemy database models and SQLite/PostgreSQL session handlers.
- **`frontend/`**:
  - Modern React + TypeScript + Vite dashboard featuring 10 dedicated tabs, interactive animated SVG power flows, and real-time supervisory diagnostics.

---

## 3. Dataflow & Controller Loop

Every 1-second physical step:
1. **Kinematic State Observation**:
   - Current velocity $v$, position $x$, floor, load $m_{\text{load}}$, state $\text{lift\_state}$, $V_{\text{dc}}$, $V_{\text{sc}}$, and $\text{SoC}$.
2. **Demand Forecast & Tariff Ingestion**:
   - Time-of-day clock, forward 15-min and 60-min demand quantiles ($P_{10}, P_{50}, P_{90}$), and current ToU rate block.
3. **Policy Evaluation**:
   - Selected controller (RL SAC, Rule-Based B1, or MPC B2) proposes raw command $P_{\text{sc\_ref, raw}}$.
4. **Safety Supervisor Enactment**:
   - Verified against physical bounds: $V_{\text{min}} \le V_{\text{sc}} \le V_{\text{max}}$, $|I_{\text{sc}}| \le I_{\text{max}}$, $T_{\text{sc}} < 65^\circ\text{C}$, converter duty cycle $D \in [0.05, 0.95]$.
   - If constraint violated, hard-projects $P_{\text{sc\_ref}}$ to the boundary and logs clip reason.
   - Fallback: If policy outputs `NaN` or data connection drops, falls back to safe rule-based controller.
5. **Drive Execution**:
   - Step executed on physical elevator / adapter.
6. **Energy Accounting & Balance Check**:
   - Trapezoidal integration. Check residual:
     $$\text{Residual} = \frac{|E_{\text{regen}} - (E_{\text{captured}} + E_{\text{brake}} + \Delta E_{C_{\text{dc}}})|}{\max(E_{\text{regen}}, E_{\text{captured}} + E_{\text{brake}})}$$
   - If $\text{Residual} > 1.5\%$, system raises `DATA_QUALITY_WARNING`.
7. **Broadcast & Store**:
   - Dispatched via WebSocket to React frontend and persisted in database.
