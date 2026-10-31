export interface TelemetryState {
  time: number;
  trip_id: number;
  lift_state: string; // 'dwell', 'move', 'accel', 'cruise', 'decel'
  direction: number; // 1 (up), -1 (down), 0 (stopped)
  floor: number;
  position: number;
  velocity: number;
  accel: number;
  car_load_kg: number;
  
  // Electrical
  Vgrid: number;
  Igrid: number;
  P_grid: number;
  Vdc: number;
  Idc_rect: number;
  P_inv_dc: number; // + motoring, - regen
  P_aux: number;
  P_brake: number;
  brake_chopper_on: boolean;

  // Supercapacitor
  Vsc: number;
  Isc: number;
  P_sc_term: number;
  P_sc_bus: number; // + discharge, - charge
  soc: number;
  dcdc_mode: string;
  duty: number;
  SC_temp: number;

  // Motor
  Te: number;
  motor_speed_rpm: number;

  // Controller & Safety
  controller_mode: string;
  raw_action_W: number;
  approved_action_W: number;
  safety_clipped: boolean;
  clip_reason?: string;
  explanation?: {
    action_kW?: number;
    soc_pct?: number;
    tariff_INR_kWh?: number;
    key_drivers?: string[];
    primary_driver?: string;
  };

  // Residual & Health
  data_quality_warning: boolean;
  bus_residual_pct: number;
  health?: HealthStatus;
  cumulative?: CumulativeData;
}

export interface CumulativeData {
  grid_kWh: number;
  motoring_kWh: number;
  regen_kWh: number;
  captured_kWh: number;
  sc_out_kWh: number;
  brake_kWh: number;
  saved_kWh: number;
  cost_INR: number;
  saved_INR: number;
  peak_kW: number;
  co2_avoided_kg: number;
}

export interface HealthStatus {
  C_est_F: number;
  ESR_est_mOhm: number;
  SOH_C_pct: number;
  SOH_ESR_pct: number;
  SOH_pct: number;
  is_eol: boolean;
  SC_temp_degC: number;
  aging_acceleration: number;
  RUL_years_nominal: number;
  RUL_years_low: number;
  RUL_years_high: number;
  confidence_note: string;
  alerts?: AlertItem[];
}

export interface AlertItem {
  time: number;
  level: string; // 'INFO', 'WARNING', 'CRITICAL'
  alert_type: string;
  message: string;
  metric_value: number;
  threshold: number;
}

export interface WaterfallData {
  motoring_demand_kWh: number;
  grid_drawn_kWh: number;
  gross_regen_kWh: number;
  captured_in_sc_kWh: number;
  stored_energy_used_kWh: number;
  brake_burnt_kWh: number;
  energy_in_sc_kWh: number;
  saved_kWh: number;
  balance_checks: {
    check_1_regen_balance: string;
    residual_pct: number;
    threshold_pct: number;
  };
}

export interface SavingsData {
  grid_actual_kWh: number;
  grid_baseline_kWh: number;
  saved_kWh: number;
  cost_actual_INR: number;
  cost_baseline_INR: number;
  saved_INR: number;
  cost_saved_INR?: number;
  peak_actual_kW: number;
  peak_baseline_kW: number;
  peak_reduction_pct: number;
  co2_avoided_kg: number;
  system_cost_INR: number;
  payback_years: number;
  payback_curve: Array<{
    year: number;
    savings_INR: number;
    net_benefit_INR: number;
  }>;
}

export interface ForecastHorizon {
  minute_ahead: number;
  hour_clock: string;
  p10_kW: number;
  p50_kW: number;
  p90_kW: number;
  tariff_INR_kWh: number;
  advisory_action: string;
}

export interface TripRecordItem {
  trip_id: number;
  lift_id: string;
  start_time: number;
  end_time: number;
  duration_s: number;
  direction: number;
  car_load_kg: number;
  E_grid_kWh: number;
  E_motoring_kWh: number;
  E_regen_gross_kWh: number;
  E_captured_bus_kWh: number;
  E_stored_in_sc_kWh: number;
  E_sc_out_kWh: number;
  E_brake_kWh: number;
  E_saved_kWh: number;
  cost_actual_INR: number;
  cost_saved_INR: number;
  data_quality_warning: boolean;
  max_residual_pct: number;
}

export interface BenchmarkSummaryItem {
  Controller: string;
  Cost_INR: number;
  Grid_kWh: number;
  Peak_kW: number;
  Brake_kWh: number;
  Cycles: number;
  Violations: number;
}
