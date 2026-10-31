import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_api_state():
    response = client.get("/api/state")
    assert response.status_code == 200
    data = response.json()
    assert "lift_id" in data
    assert "controller_mode" in data
    assert "state" in data

def test_api_savings():
    response = client.get("/api/savings")
    assert response.status_code == 200
    data = response.json()
    assert "grid_actual_kWh" in data
    assert "saved_kWh" in data
    assert "cost_saved_INR" in data
    assert "payback_years" in data
    assert len(data["payback_curve"]) > 0

def test_api_waterfall():
    response = client.get("/api/waterfall")
    assert response.status_code == 200
    data = response.json()
    assert "motoring_demand_kWh" in data
    assert "balance_checks" in data
    assert data["balance_checks"]["residual_pct"] <= 1.5

def test_api_forecast():
    response = client.get("/api/forecast")
    assert response.status_code == 200
    data = response.json()
    assert "forecast_horizons" in data
    assert len(data["forecast_horizons"]) > 0

def test_api_health_and_injector():
    # 1. Health check
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    assert "SOH_pct" in res_health.json()

    # 2. Inject degradation
    res_inject = client.post("/api/health/inject", json={"c_multiplier": 0.82, "esr_multiplier": 1.7})
    assert res_inject.status_code == 200
    assert res_inject.json()["status"] == "SUCCESS"

    # 3. Reset degradation
    res_reset = client.post("/api/health/reset")
    assert res_reset.status_code == 200

def test_api_controller_mode_switch():
    res = client.post("/api/controller", json={"mode": "B1_RULE_BASED"})
    assert res.status_code == 200
    assert res.json()["active_controller"] == "B1_RULE_BASED"

def test_api_reports_pdf_and_csv():
    # PDF export
    res_pdf = client.get("/api/reports/monthly.pdf")
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert len(res_pdf.content) > 1000

    # CSV export
    res_csv = client.get("/api/reports/trips.csv")
    assert res_csv.status_code == 200
    assert "trip_id,lift_id" in res_csv.text
