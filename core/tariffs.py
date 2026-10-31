"""
Core Tariffs Module:
Configurable Time-of-Use (ToU) billing, 15-minute rolling maximum demand charges,
and grid-arbitrage decision evaluator.
"""

from typing import Dict, Any, List, Optional
import numpy as np

class TariffManager:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        # Default placeholder rates (user-editable in UI)
        self.rate_offpeak = 4.50    # ₹ / kWh (22:00 - 06:00)
        self.rate_normal = 7.50     # ₹ / kWh (06:00 - 09:00, 12:00 - 18:00, 21:00 - 22:00)
        self.rate_peak = 11.50      # ₹ / kWh (09:00 - 12:00, 18:00 - 21:00)
        self.demand_rate = 450.0    # ₹ / kW / month
        self.currency = "₹"
        self.emission_factor = 0.72 # kg CO2 / kWh
        
        # 24-hour tariff schedule mapping hour -> rate
        self.hourly_schedule = [self.rate_offpeak] * 24
        self._build_schedule()

        if config:
            self.update_config(config)

    def _build_schedule(self):
        for h in range(24):
            if (h >= 22) or (h < 6):
                self.hourly_schedule[h] = self.rate_offpeak
            elif (9 <= h < 12) or (18 <= h < 21):
                self.hourly_schedule[h] = self.rate_peak
            else:
                self.hourly_schedule[h] = self.rate_normal

    def update_config(self, cfg: Dict[str, Any]):
        if "rate_offpeak_per_kWh" in cfg:
            self.rate_offpeak = float(cfg["rate_offpeak_per_kWh"])
        if "rate_normal_per_kWh" in cfg:
            self.rate_normal = float(cfg["rate_normal_per_kWh"])
        if "rate_peak_per_kWh" in cfg:
            self.rate_peak = float(cfg["rate_peak_per_kWh"])
        if "demand_rate_per_kW_month" in cfg:
            self.demand_rate = float(cfg["demand_rate_per_kW_month"])
        if "currency_symbol" in cfg:
            self.currency = str(cfg["currency_symbol"])
        if "grid_emission_factor_kg_per_kWh" in cfg:
            self.emission_factor = float(cfg["grid_emission_factor_kg_per_kWh"])
        self._build_schedule()

    def get_tariff_for_time(self, hour: float) -> float:
        """Returns ₹/kWh for a given hour of day (0.0 to 24.0)"""
        h_idx = int(hour) % 24
        return self.hourly_schedule[h_idx]

    def compute_energy_cost(self, P_grid_W: float, dt_s: float, hour: float) -> float:
        """
        Energy bill increment:
        cost = tariff(hour) * P_grid * dt / 3600 / 1000 (₹)
        """
        tariff = self.get_tariff_for_time(hour)
        energy_kWh = (max(0.0, P_grid_W) * dt_s) / 3.6e6
        return tariff * energy_kWh

    def compute_demand_charge(self, peak_kW: float) -> float:
        """Monthly demand charge for peak kW (₹)"""
        return self.demand_rate * max(0.0, peak_kW)

    def is_arbitrage_profitable(
        self,
        offpeak_tariff: float,
        peak_tariff: float,
        eta_roundtrip: float = 0.94, # 0.97 * 0.97 = 0.9409
        hold_time_hours: float = 4.0,
        self_discharge_pct_day: float = 1.0
    ) -> bool:
        """
        Section 4 Grid-Arbitrage Rule:
        Charging the supercapacitor from the grid pays off only if:
        price_peak * eta_roundtrip * (1 - self_discharge_hold) > price_offpeak.
        """
        daily_retention = 1.0 - (self_discharge_pct_day / 100.0)
        retention_hold = daily_retention ** (hold_time_hours / 24.0)
        effective_efficiency = eta_roundtrip * retention_hold
        return (peak_tariff * effective_efficiency) > offpeak_tariff
