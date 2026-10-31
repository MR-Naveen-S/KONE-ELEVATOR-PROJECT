"""
Abstract Simulator Adapter Interface
Defines the contract for all elevator drive simulation sources:
- WebSimAdapter (Python port of browser model with exact 250 microsecond numerical integration)
- FileReplayAdapter (CSV / JSON / MAT replay)
- MatlabEngineAdapter (MATLAB Simulink engine stub)
- FmuAdapter (Functional Mock-up Interface stub)
- PythonSurrogateAdapter (Fast average-value model for RL / sweep)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from core.schema import ElevatorSignals

class SimulatorAdapter(ABC):
    @abstractmethod
    def reset(self, config: Optional[Dict[str, Any]] = None, seed: Optional[int] = None) -> ElevatorSignals:
        """
        Reset the simulation to initial conditions.
        Returns the initial ElevatorSignals state.
        """
        pass

    @abstractmethod
    def step(self, P_sc_ref: Optional[float] = None, dt: float = 1.0) -> ElevatorSignals:
        """
        Advance the simulation by dt seconds.
        P_sc_ref: Supercapacitor DC-bus target power command in Watts (+ discharge, - charge).
                  If None, runs in autonomous Stage 2 (or Stage 1) droop control mode.
        dt: Duration to advance (typically 1.0 s for high-level loop).
        Returns the aggregated ElevatorSignals state over the interval.
        """
        pass

    @abstractmethod
    def get_static_params(self) -> Dict[str, Any]:
        """
        Return the dictionary of physical and electrical parameters configured in the model.
        """
        pass
