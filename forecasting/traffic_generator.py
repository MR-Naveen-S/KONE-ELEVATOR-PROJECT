"""
Traffic / Scenario Generator (Section 6):
Generates realistic, seedable 24-hour elevator traffic profiles:
- Up-peak (morning arrival: ground -> upper floors, high load)
- Down-peak (evening departure: upper floors -> ground, high load, high regen)
- Lunch (two-way traffic: heavy up and down)
- Inter-floor (mid-day business travel)
- Night (very sparse, cleaning / security)
- Weekend (low activity)
Includes balanced loads (~400-500 kg where regen ≈ 0) and empty / full car extremes.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import numpy as np

@dataclass
class TripRequest:
    trip_id: int
    request_time_s: float
    origin_floor: int
    dest_floor: int
    passenger_load_kg: float
    dwell_time_s: float

class TrafficGenerator:
    def __init__(self, n_floors: int = 10, rated_load_kg: float = 1000.0, seed: int = 42):
        self.n_floors = n_floors
        self.rated_load = rated_load_kg
        self.rng = np.random.default_rng(seed)

    def generate_day(
        self,
        day_type: str = "weekday", # "weekday", "weekend", "holiday"
        trips_per_day: int = 300,
        seed: Optional[int] = None
    ) -> List[TripRequest]:
        """
        Generates a 24-hour chronological sequence of trip requests.
        """
        if seed is not None:
            self.rng = np.random.default_rng(seed)

        # 24-hour probability distribution of trip start times
        hourly_weights = np.zeros(24)
        if day_type == "weekend":
            # Relatively flat low weekend activity
            hourly_weights[0:7] = 0.05
            hourly_weights[7:22] = 0.5
            hourly_weights[22:24] = 0.1
        else:
            # Office building weekday profile
            hourly_weights[0:6] = 0.02   # Night
            hourly_weights[6:8] = 0.3    # Early morning
            hourly_weights[8:10] = 2.5   # Up-peak (Arrivals)
            hourly_weights[10:12] = 0.9  # Morning inter-floor
            hourly_weights[12:14] = 2.2  # Lunch two-way rush
            hourly_weights[14:17] = 1.0  # Afternoon inter-floor
            hourly_weights[17:19] = 2.4  # Down-peak (Departures)
            hourly_weights[19:22] = 0.5  # Evening overtime
            hourly_weights[22:24] = 0.05 # Late night

        prob_hours = hourly_weights / np.sum(hourly_weights)

        # Generate trip times across the day
        hours = self.rng.choice(24, size=trips_per_day, p=prob_hours)
        minute_offsets = self.rng.uniform(0.0, 3600.0, size=trips_per_day)
        trip_times = hours * 3600.0 + minute_offsets
        trip_times = np.sort(trip_times)

        trips: List[TripRequest] = []
        for i, t in enumerate(trip_times):
            hour = t / 3600.0
            
            # Determine traffic regime based on hour
            if 8.0 <= hour < 10.0:
                # Up-peak: 80% from ground floor (0) to upper floors
                if self.rng.random() < 0.8:
                    origin = 0
                    dest = int(self.rng.integers(1, self.n_floors))
                    load = float(self.rng.uniform(500.0, self.rated_load))
                else:
                    origin = int(self.rng.integers(0, self.n_floors))
                    dest = int(self.rng.integers(0, self.n_floors))
                    load = float(self.rng.uniform(100.0, 600.0))
            elif 17.0 <= hour < 19.0:
                # Down-peak: 80% from upper floors down to ground (0)
                if self.rng.random() < 0.8:
                    origin = int(self.rng.integers(1, self.n_floors))
                    dest = 0
                    load = float(self.rng.uniform(500.0, self.rated_load))
                else:
                    origin = int(self.rng.integers(0, self.n_floors))
                    dest = int(self.rng.integers(0, self.n_floors))
                    load = float(self.rng.uniform(100.0, 600.0))
            elif 12.0 <= hour < 14.0:
                # Lunch: 50% down to ground, 50% up from ground
                if self.rng.random() < 0.5:
                    origin = int(self.rng.integers(1, self.n_floors))
                    dest = 0
                else:
                    origin = 0
                    dest = int(self.rng.integers(1, self.n_floors))
                load = float(self.rng.uniform(300.0, 850.0))
            else:
                # Inter-floor & night: random floors
                origin = int(self.rng.integers(0, self.n_floors))
                dest = int(self.rng.integers(0, self.n_floors))
                # Explicitly include balanced loads near 400 kg (~50% rated)
                if self.rng.random() < 0.3:
                    load = float(self.rng.uniform(380.0, 420.0)) # balanced load
                else:
                    load = float(self.rng.uniform(50.0, 700.0))

            if origin == dest:
                dest = (origin + 1) % self.n_floors

            dwell = float(self.rng.uniform(2.5, 5.0))
            trips.append(TripRequest(
                trip_id=i + 1,
                request_time_s=float(t),
                origin_floor=origin,
                dest_floor=dest,
                passenger_load_kg=round(load, 1),
                dwell_time_s=round(dwell, 1)
            ))

        return trips
