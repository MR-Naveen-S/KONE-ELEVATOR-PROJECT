"""
SQLAlchemy Database Models for Elevator Energy Manager (Section 2 & 7):
Compatible with SQLite in development and Postgres/TimescaleDB in production.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class TelemetryRecord(Base):
    __tablename__ = "telemetry_records"

    record_id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(Float, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    trip_id = Column(Integer, default=0, index=True)
    lift_id = Column(String(32), default="LIFT-01", index=True)
    
    # Kinematics & States
    lift_state = Column(String(32), default="dwell") # idle, accel, cruise, decel, door
    direction = Column(Integer, default=0) # 1 (up), -1 (down), 0 (stopped)
    floor = Column(Integer, default=1)
    position = Column(Float, default=0.0)
    velocity = Column(Float, default=0.0)
    accel = Column(Float, default=0.0)
    car_load_kg = Column(Float, default=800.0)

    # Electrical & Powers (Strict Section 3 Sign Conventions)
    Vgrid = Column(Float, default=400.0)
    Igrid = Column(Float, default=0.0)
    P_grid = Column(Float, default=0.0) # >= 0 (W)
    Vdc = Column(Float, default=560.0)
    Idc_rect = Column(Float, default=0.0)
    P_inv_dc = Column(Float, default=0.0) # + motoring, - regen (W)
    P_aux = Column(Float, default=250.0)
    P_brake = Column(Float, default=0.0) # >= 0 (W)
    brake_chopper_on = Column(Boolean, default=False)
    
    # Supercapacitor & DC-DC Converter
    Vsc = Column(Float, default=130.0)
    Isc = Column(Float, default=0.0)
    P_sc_term = Column(Float, default=0.0) # + discharge, - charge (W)
    P_sc_bus = Column(Float, default=0.0)  # + discharge, - charge (W)
    soc = Column(Float, default=0.33)
    dcdc_mode = Column(String(32), default="idle")
    duty = Column(Float, default=0.23)
    SC_temp = Column(Float, default=25.0)

    # Motor State
    Te = Column(Float, default=0.0)
    motor_speed_rpm = Column(Float, default=0.0)
    Iq = Column(Float, default=0.0)
    Id = Column(Float, default=0.0)

    # Balance Residuals & Data Quality (Section 9 Mandate)
    residual_regen_pct = Column(Float, default=0.0)
    residual_sc_pct = Column(Float, default=0.0)
    residual_bus_pct = Column(Float, default=0.0)
    data_quality_warning = Column(Boolean, default=False)
    controller_mode = Column(String(32), default="B1_RULE_BASED")

class TripRecord(Base):
    __tablename__ = "trip_records"

    trip_id = Column(Integer, primary_key=True)
    lift_id = Column(String(32), default="LIFT-01", index=True)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    duration_s = Column(Float, default=0.0)
    direction = Column(Integer, default=1)
    car_load_kg = Column(Float, default=800.0)
    
    # Energy Accounting (kWh)
    E_grid_kWh = Column(Float, default=0.0)
    E_motoring_kWh = Column(Float, default=0.0)
    E_regen_gross_kWh = Column(Float, default=0.0)
    E_captured_bus_kWh = Column(Float, default=0.0)
    E_stored_in_sc_kWh = Column(Float, default=0.0)
    E_sc_out_kWh = Column(Float, default=0.0)
    E_brake_kWh = Column(Float, default=0.0)
    E_losses_kWh = Column(Float, default=0.0)

    # Counterfactual Savings vs B0
    E_baseline_grid_kWh = Column(Float, default=0.0)
    E_saved_kWh = Column(Float, default=0.0)
    cost_actual_INR = Column(Float, default=0.0)
    cost_baseline_INR = Column(Float, default=0.0)
    cost_saved_INR = Column(Float, default=0.0)
    
    # Quality & Residuals
    data_quality_warning = Column(Boolean, default=False)
    max_residual_pct = Column(Float, default=0.0)

class DailySummary(Base):
    __tablename__ = "daily_summaries"

    date_str = Column(String(32), primary_key=True) # YYYY-MM-DD
    lift_id = Column(String(32), default="LIFT-01", primary_key=True)
    trip_count = Column(Integer, default=0)
    
    E_grid_total_kWh = Column(Float, default=0.0)
    E_motoring_total_kWh = Column(Float, default=0.0)
    E_regen_total_kWh = Column(Float, default=0.0)
    E_captured_total_kWh = Column(Float, default=0.0)
    E_sc_out_total_kWh = Column(Float, default=0.0)
    E_brake_total_kWh = Column(Float, default=0.0)
    E_saved_total_kWh = Column(Float, default=0.0)
    
    cost_actual_INR = Column(Float, default=0.0)
    cost_baseline_INR = Column(Float, default=0.0)
    cost_saved_INR = Column(Float, default=0.0)
    
    peak_demand_actual_kW = Column(Float, default=0.0)
    peak_demand_baseline_kW = Column(Float, default=0.0)
    peak_reduction_pct = Column(Float, default=0.0)
    
    regen_capture_ratio = Column(Float, default=0.0)
    self_sufficiency = Column(Float, default=0.0)
    equivalent_full_cycles = Column(Float, default=0.0)
    average_soc = Column(Float, default=0.5)
    SOH_pct = Column(Float, default=100.0)

class HealthRecord(Base):
    __tablename__ = "health_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(Float, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    lift_id = Column(String(32), default="LIFT-01")
    
    C_est_F = Column(Float, default=15.0)
    ESR_est_mOhm = Column(Float, default=35.0)
    SOH_C_pct = Column(Float, default=100.0)
    SOH_ESR_pct = Column(Float, default=100.0)
    SOH_pct = Column(Float, default=100.0)
    SC_temp_degC = Column(Float, default=25.0)
    aging_acceleration = Column(Float, default=1.0)
    RUL_years_nominal = Column(Float, default=10.0)
    is_eol = Column(Boolean, default=False)

class AlertRecord(Base):
    __tablename__ = "alert_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    lift_id = Column(String(32), default="LIFT-01")
    level = Column(String(16), default="INFO") # INFO, WARNING, CRITICAL
    alert_type = Column(String(32), default="DATA_QUALITY") # HIGH_TEMP, LOW_SOH, SAFETY_CLIP, DATA_QUALITY_WARNING
    message = Column(Text, nullable=False)
    metric_value = Column(Float, default=0.0)
    threshold = Column(Float, default=0.0)
    resolved = Column(Boolean, default=False)

class ConfigVersion(Base):
    __tablename__ = "config_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(Integer, default=1)
    timestamp = Column(DateTime, default=datetime.utcnow)
    author = Column(String(64), default="Lift Manager")
    description = Column(String(256), default="Active System Parameters & Tariff Configuration")
    config_json = Column(Text, nullable=False)
