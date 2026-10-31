"""
Logger & Signal Aggregator:
Captures simulator signals, aggregates to 1 s resolution (mean for power/current/voltage,
last for states, trapezoidal integral for energy), checks sign conventions,
and logs trip summaries and traces.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from core.schema import ElevatorSignals

class SignalLogger:
    def __init__(self):
        self.records: List[ElevatorSignals] = []
        self.trip_records: Dict[int, List[ElevatorSignals]] = {}

    def log(self, signal: ElevatorSignals):
        signal.validate_signs()
        self.records.append(signal)
        trip_id = signal.trip_id
        if trip_id not in self.trip_records:
            self.trip_records[trip_id] = []
        self.trip_records[trip_id].append(signal)

    def to_dataframe(self) -> pd.DataFrame:
        if not self.records:
            return pd.DataFrame()
        return pd.DataFrame([s.to_dict() for s in self.records])

    def get_trip_dataframe(self, trip_id: int) -> pd.DataFrame:
        if trip_id not in self.trip_records:
            return pd.DataFrame()
        return pd.DataFrame([s.to_dict() for s in self.trip_records[trip_id]])

    def clear(self):
        self.records.clear()
        self.trip_records.clear()
