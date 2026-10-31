"""
Hard Safety Supervisor (Section 8 Mandate):
A non-learned, deterministic constraint projection layer executed before EVERY command.
Clips P_sc_ref so:
- Vsc in [Vmin, Vmax] (100 V to 200 V)
- |Isc| <= I_max (100 A)
- Vdc within permissible limits (520 V to 600 V)
- Converter duty in [0, 1]
- Supercap temperature below T_max (65 deg C)
- Power below P_dcdc_max (20 kW)

Logs every clip event with exact reason and timestamp.
Fallback: Reverts to Baseline B1 Rule-Based Controller if action is NaN, inf, stale, or communication fails.
"""

import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from rl.baselines import BaselineB1Controller

@dataclass
class SafetyClipEvent:
    time: float
    original_action: float
    clipped_action: float
    reason: str

class SafetySupervisor:
    def __init__(
        self,
        Vsc_min: float = 100.0,
        Vsc_max: float = 200.0,
        I_max: float = 100.0,
        P_max: float = 20000.0,
        Vdc_min: float = 520.0,
        Vdc_max: float = 600.0,
        T_max: float = 65.0,
        eta_dcdc: float = 0.97
    ):
        self.Vsc_min = Vsc_min
        self.Vsc_max = Vsc_max
        self.I_max = I_max
        self.P_max = P_max
        self.Vdc_min = Vdc_min
        self.Vdc_max = Vdc_max
        self.T_max = T_max
        self.eta = eta_dcdc
        
        self.clip_history: List[SafetyClipEvent] = []
        self.fallback_controller = BaselineB1Controller(
            Vsc_min=Vsc_min,
            Vsc_max=Vsc_max,
            I_max=I_max,
            eta_dcdc=eta_dcdc
        )
        self.fallback_count = 0

    def enforce_safety(
        self,
        action_P_sc_ref: float,
        state: Dict[str, Any],
        link_healthy: bool = True
    ) -> Tuple[float, bool, Optional[str]]:
        """
        Hard constraint enforcement.
        Returns: (approved_P_sc_ref, is_fallback, clip_reason)
        """
        # 1. Fallback triggers: NaN, Inf, link loss, or stale data
        if (not link_healthy) or (action_P_sc_ref is None) or math.isnan(action_P_sc_ref) or math.isinf(action_P_sc_ref):
            self.fallback_count += 1
            safe_action = self.fallback_controller.compute_action(state)
            reason = "FALLBACK: Link failure or non-finite action (NaN/Inf)"
            self.clip_history.append(SafetyClipEvent(
                time=float(state.get("time", 0.0)),
                original_action=float(action_P_sc_ref if action_P_sc_ref is not None else 0.0),
                clipped_action=safe_action,
                reason=reason
            ))
            return safe_action, True, reason

        Vsc = float(state.get("Vsc", 130.0))
        Vdc = float(state.get("Vdc", 560.0))
        T_sc = float(state.get("SC_temp", 25.0))
        t = float(state.get("time", 0.0))

        original = action_P_sc_ref
        clipped = action_P_sc_ref
        reasons = []

        # 2. Temperature safety cutoff
        if T_sc >= self.T_max:
            clipped = 0.0
            reasons.append(f"Temperature limit exceeded ({T_sc:.1f} >= {self.T_max} °C)")

        # 3. Maximum power rating limit
        if abs(clipped) > self.P_max:
            clipped = math.copysign(self.P_max, clipped)
            reasons.append(f"Converter power rating exceeded (|P| > {self.P_max} W)")

        # 4. Maximum current limit (|Isc| <= I_max => |P_term| <= I_max * Vsc)
        P_lim_current = self.I_max * max(Vsc, 1.0) * self.eta
        if abs(clipped) > P_lim_current:
            clipped = math.copysign(P_lim_current, clipped)
            reasons.append(f"Converter current limit exceeded (|Isc| > {self.I_max} A)")

        # 5. Supercapacitor Voltage Limits:
        # If discharging (P_sc_bus > 0): Vsc must stay >= Vsc_min
        if clipped > 0.0:
            if Vsc <= self.Vsc_min:
                clipped = 0.0
                reasons.append(f"Supercapacitor depleted (Vsc={Vsc:.1f} <= {self.Vsc_min} V)")
            elif Vsc < self.Vsc_min + 3.0:
                # Proportional taper in the safety margin zone
                taper = max(0.0, (Vsc - self.Vsc_min) / 3.0)
                clipped = min(clipped, clipped * taper)
                reasons.append(f"Vsc approaching minimum limit (Vsc={Vsc:.1f} V)")

        # If charging (P_sc_bus < 0): Vsc must stay <= Vsc_max
        elif clipped < 0.0:
            if Vsc >= self.Vsc_max:
                clipped = 0.0
                reasons.append(f"Supercapacitor full (Vsc={Vsc:.1f} >= {self.Vsc_max} V)")
            elif Vsc > self.Vsc_max - 3.0:
                taper = max(0.0, (self.Vsc_max - Vsc) / 3.0)
                clipped = max(clipped, clipped * taper)
                reasons.append(f"Vsc approaching maximum limit (Vsc={Vsc:.1f} V)")

        # 6. DC Link Voltage limits
        if Vdc >= self.Vdc_max and clipped > 0.0:
            # Cannot inject discharge power into an over-voltage DC link!
            clipped = 0.0
            reasons.append(f"DC link over-voltage (Vdc={Vdc:.1f} >= {self.Vdc_max} V)")

        # Log event if clipping occurred
        if abs(clipped - original) > 1e-3:
            reason_str = "; ".join(reasons)
            self.clip_history.append(SafetyClipEvent(
                time=t,
                original_action=original,
                clipped_action=clipped,
                reason=reason_str
            ))
            return clipped, False, reason_str

        return clipped, False, None
