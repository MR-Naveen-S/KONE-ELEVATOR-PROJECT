"""
FileReplayAdapter: Replays historical or offline simulated elevator drive logs
from CSV, JSON, or MATLAB MAT files, conforming to the SimulatorAdapter interface.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List
from core.schema import ElevatorSignals
from adapters.interface import SimulatorAdapter

class FileReplayAdapter(SimulatorAdapter):
    def __init__(self, filepath: Optional[str] = None):
        self.filepath = filepath
        self.df: Optional[pd.DataFrame] = None
        self.current_idx = 0
        if filepath:
            self.load_file(filepath)

    def load_file(self, filepath: str):
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Replay file not found: {filepath}")
        
        if path.suffix.lower() == ".csv":
            self.df = pd.read_csv(filepath)
        elif path.suffix.lower() == ".json":
            self.df = pd.read_json(filepath)
        elif path.suffix.lower() == ".mat":
            import scipy.io as sio
            mat = sio.loadmat(filepath)
            # Find first 2D array or structured data
            for k, v in mat.items():
                if not k.startswith("__") and isinstance(v, np.ndarray):
                    self.df = pd.DataFrame(v)
                    break
        else:
            raise ValueError(f"Unsupported file format for replay: {path.suffix}")
        
        self.current_idx = 0

    def reset(self, config: Optional[Dict[str, Any]] = None, seed: Optional[int] = None) -> ElevatorSignals:
        self.current_idx = 0
        if self.df is None or len(self.df) == 0:
            return ElevatorSignals()
        row = self.df.iloc[0].to_dict()
        return self._row_to_signals(row)

    def step(self, P_sc_ref: Optional[float] = None, dt: float = 1.0) -> ElevatorSignals:
        if self.df is None or len(self.df) == 0:
            return ElevatorSignals()
        
        if self.current_idx >= len(self.df):
            self.current_idx = len(self.df) - 1 # hold last state
        
        row = self.df.iloc[self.current_idx].to_dict()
        self.current_idx += 1
        return self._row_to_signals(row)

    def _row_to_signals(self, row: Dict[str, Any]) -> ElevatorSignals:
        signals = ElevatorSignals(
            time=float(row.get("time", self.current_idx)),
            trip_id=int(row.get("trip_id", 0)),
            lift_state=str(row.get("lift_state", "idle")),
            direction=int(row.get("direction", 0)),
            floor=int(row.get("floor", 0)),
            position=float(row.get("position", 0.0)),
            velocity=float(row.get("velocity", 0.0)),
            accel=float(row.get("accel", 0.0)),
            car_load_kg=float(row.get("car_load_kg", 800.0)),
            Vgrid=float(row.get("Vgrid", 400.0)),
            Igrid=float(row.get("Igrid", 0.0)),
            P_grid=float(row.get("P_grid", 0.0)),
            Vdc=float(row.get("Vdc", 540.0)),
            Idc_rect=float(row.get("Idc_rect", 0.0)),
            P_inv_dc=float(row.get("P_inv_dc", 0.0)),
            P_aux=float(row.get("P_aux", 250.0)),
            P_brake=float(row.get("P_brake", 0.0)),
            brake_chopper_on=int(row.get("brake_chopper_on", 0)),
            Vsc=float(row.get("Vsc", 130.0)),
            Isc=float(row.get("Isc", 0.0)),
            P_sc_term=float(row.get("P_sc_term", 0.0)),
            P_sc_bus=float(row.get("P_sc_bus", 0.0)),
            dcdc_mode=str(row.get("dcdc_mode", "idle")),
            duty=float(row.get("duty", 0.24)),
            Te=float(row.get("Te", 0.0)),
            motor_speed_rpm=float(row.get("motor_speed_rpm", 0.0)),
            Iq=float(row.get("Iq", 0.0)),
            Id=float(row.get("Id", 0.0)),
            SC_temp=float(row.get("SC_temp", 25.0)),
            T_amb=float(row.get("T_amb", 25.0))
        )
        signals.validate_signs()
        return signals

    def get_static_params(self) -> Dict[str, Any]:
        return {"source": "file_replay", "filepath": self.filepath, "rows": len(self.df) if self.df is not None else 0}
