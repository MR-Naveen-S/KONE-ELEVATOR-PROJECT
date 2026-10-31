# Regenerative Supercapacitor Elevator Energy Manager
*(Simulation Adapter + Demand Forecasting + Safe RL + Energy Accounting + Lift Manager Dashboard)*

An industrial-grade energy management system for traction elevators featuring a Permanent Magnet Synchronous Motor (PMSM), DC link capacitor, bidirectional DC-DC converter, and supercapacitor energy storage bank.

---

## 1. Quick Start (One-Command Setup & Run)

### Prerequisites
- Python 3.10+ (Tested on Python 3.12)
- Node.js 18+ (Tested on Node.js v24) & npm

### Automated Launch (Production Server + Frontend)
```bash
# Clone the repository
git clone https://github.com/kone/elevator-supercap-manager.git
cd elevator-supercap-manager

# Run the unified application server
python run.py
```
This single command:
1. Verifies virtual environment and installs Python dependencies (`fastapi`, `uvicorn`, `torch`, `onnx`, `onnxruntime`, `lightgbm`, `reportlab`, `sqlalchemy`, `scipy`).
2. Builds the React + TypeScript frontend into production bundle (`frontend/dist/`).
3. Starts the FastAPI server and live controller loop at **`http://localhost:8000`**.

Open your browser to:
- **Interactive Dashboard:** [http://localhost:8000](http://localhost:8000)
- **Interactive API Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Live WebSocket Telemetry Stream:** `ws://localhost:8000/ws/live`

---

## 2. Running Test Suite
Execute all unit, integration, surrogate gate, and safety fuzzing tests:
```bash
python -m pytest -v
```
All **30 tests** cover:
- Section 4 exact physical formulas with hand-calculated benchmark cases (e.g. 15 F, 100V → 200V = 62.50 Wh).
- Energy balance residuals ($\text{residual} < 1.5\%$ on all trips).
- Surrogate validation gate: $> 100{,}000$ steps/s speed, $< 3\%$ energy error, $< 2\%$ $V_{\text{sc}}$ RMSE.
- Section 8 Honesty Requirement: rule-based baseline comparison and automatic defaulting to B1 if RL does not beat B1.
- Safety Supervisor constraint fuzzing (`NaN`, inf, extreme loads) and zero-violation hard clipping.
- Supercapacitor health estimation ($C, \text{ESR}$, thermal model, EOL alerts, and degradation injector).
- Backend REST endpoints and ReportLab PDF/CSV exports.

---

## 3. System Architecture & Directory Structure

```
elevator-supercap-manager/
├── config/
│   └── params.yaml            # Physical parameters (unmodeled marked [ASSUMED] with units)
├── core/
│   ├── schema.py              # Strict sign conventions, units, and ElevatorSignals schema
│   ├── mechanics.py           # Elevator traction dynamics & kinematics
│   ├── electrical.py          # DC link Kirchhoff balance, rectifier, chopper, inverter FOC
│   ├── supercap.py            # Supercapacitor bank scaling, ESR, usable energy, boost duty
│   ├── accounting.py          # Section 9 energy integrations, counterfactual savings & audits
│   ├── tariffs.py             # Time-of-Use (ToU) energy rates & rolling demand charge billing
│   └── health.py              # Online C/ESR estimation, Arrhenius thermal model & degradation injector
├── adapters/
│   ├── interface.py           # Unified SimulatorAdapter abstract base class
│   ├── web_sim_adapter.py     # High-fidelity discrete physical model matching browser simulator
│   ├── file_replay_adapter.py # Telemetry playback from CSV/MAT logs
│   ├── matlab_adapter.py      # MATLAB/Simulink Simscape engine bridge stub
│   └── fmu_adapter.py         # Functional Mock-up Unit (FMI 2.0) co-simulation stub
├── surrogate/
│   ├── elevator_surrogate.py  # High-speed average-value model (> 100k steps/second)
│   └── validator.py           # Surrogate validation gate & comparative error analysis
├── forecasting/
│   ├── traffic_generator.py   # Multi-pattern stochastic passenger traffic generator
│   └── demand_forecaster.py   # LightGBM P10/P50/P90 quantile forecaster & advisory scheduler
├── rl/
│   ├── safety_supervisor.py   # Non-learned hard constraint projection layer
│   ├── elevator_env.py        # Gymnasium environment with normalized observation space
│   ├── trainer.py             # Soft Actor-Critic (SAC) & TD3 policy trainer with ONNX export
│   ├── baselines.py           # Baselines: B0 Conventional, B1 Rule-Based, B2 Perfect MPC
│   ├── evaluate.py            # Section 8 Honesty benchmark comparative evaluator
│   └── policy.onnx            # Exported ONNX policy for offline inference
├── backend/
│   ├── main.py                # FastAPI app with static frontend mounting
│   ├── routers/api.py         # REST endpoints for state, savings, health, config, reports
│   ├── routers/websocket.py   # Real-time WebSocket telemetry push
│   ├── services/              # 1-second orchestrator & ReportLab PDF generator
│   └── db/                    # SQLAlchemy models & SQLite/Postgres session handlers
├── frontend/                  # React + TypeScript + Vite + Tailwind/Modern CSS
│   └── src/components/        # 10 dedicated tabs for live drive lab, waterfall, health, config
├── docs/                      # Technical documentation, formulas, and validation reports
├── tests/                     # 30 unit & integration test suites
└── run.py                     # One-click startup script
```

---

## 4. Connecting Adapters to Real Drives / MATLAB / FMU

The `SimulatorAdapter` interface allows seamless switching between virtual environments and physical elevator controllers without modifying backend logic:

```python
from adapters.interface import SimulatorAdapter

class MyCustomLiftAdapter(SimulatorAdapter):
    def reset(self, config=None, seed=None):
        # Connect to Modbus TCP / OPC UA / CANopen drive interface
        return initial_signals

    def step(self, P_sc_ref, dt):
        # 1. Send supervisory P_sc_ref command to DC-DC converter PLC
        # 2. Read physical drive sensors (Vdc, Vsc, Isc, P_grid, motor speed)
        # 3. Return ElevatorSignals object with strict sign conventions
        return signals
```

### MATLAB/Simulink Simscape Integration
Point the adapter to MATLAB Engine by specifying the `.slx` model file in `config/params.yaml`:
```python
from adapters.matlab_adapter import MatlabEngineAdapter
adapter = MatlabEngineAdapter(model_path="simulations/kone_pmsm_supercap.slx")
```

### FMU (Functional Mock-up Unit) Co-Simulation
Deploy pre-compiled FMUs from Dymola, OpenModelica, or Amesim:
```python
from adapters.fmu_adapter import FmuAdapter
adapter = FmuAdapter(fmu_path="bin/kone_drive_fmi2.fmu")
```

---

## 5. Strict Sign Conventions & Units

| Signal | Units | Sign Convention |
| :--- | :--- | :--- |
| `P_inv_dc` | W | $+ \text{ motoring}$ (power into motor), $- \text{ regenerating}$ (power from motor to DC link) |
| `P_sc_bus` | W | $+ \text{ discharge}$ (power out of supercap into DC link), $- \text{ charge}$ (absorbed into supercap) |
| `P_sc_term`| W | $+ \text{ discharge}$, $- \text{ charge}$ (terminal power including internal ESR losses) |
| `P_grid` | W | $\ge 0$ strictly (diode rectifier prohibits grid export) |
| `P_brake`| W | $\ge 0$ strictly (heat dissipated across 20 $\Omega$ dynamic brake resistor) |
| `P_aux` | W | $\ge 0$ strictly (cabin lighting, ventilation, and controller power) |
| `velocity` | m/s | $+ \text{ moving up}$, $- \text{ moving down}$ |

---

## 6. Known Limitations & Sim-to-Real Gap

1. **Diode Rectifier No-Load Float Voltage:**
   The browser simulator models a 3-phase diode rectifier with an open-circuit voltage around $\approx 533-540\text{ V}$. In physical substations, grid voltage fluctuates with distribution tap changers ($\pm 10\%$), which will slightly vary the baseline rectifier threshold.
2. **Supercapacitor Internal Equivalent Series Resistance (ESR):**
   The browser simulator models a simplified internal resistance. In physical supercapacitor modules (e.g., Maxwell 48V/165F modules), ESR varies non-linearly with cell temperature and operating frequency. The health estimator accounts for this using online step-transient estimation.
3. **Shaft Air Drag and Guide Rail Friction:**
   Kinematic friction is modeled with a Coulomb + viscous approximation ($300\text{ N} \cdot \tanh(20v)$). In tall shafts ($> 100\text{ m}$), aerodynamic piston effects become significant at speeds above $4\text{ m/s}$.
4. **Thermal Dissipation Dynamics:**
   Thermal resistance $R_{\text{th}} = 0.85\text{ K/W}$ and heat capacity $C_{\text{th}} = 1200\text{ J/K}$ are configured as `[ASSUMED]` constants pending physical wind-tunnel testbench characterization.
