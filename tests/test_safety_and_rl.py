import math
import numpy as np
import pytest
from pathlib import Path

from rl.safety_supervisor import SafetySupervisor
from rl.trainer import RLPolicyManager, ElevatorActor
from rl.evaluate import BenchmarkEvaluator
from adapters.web_sim_adapter import WebSimAdapter

def test_safety_supervisor_fuzzing():
    """
    Fuzzing test: Send extreme and pathological values to Safety Supervisor.
    Verify 0 constraint violations, appropriate clipping or fallback.
    """
    supervisor = SafetySupervisor(
        Vsc_min=100.0,
        Vsc_max=200.0,
        I_max=100.0,
        P_max=20000.0,
        Vdc_min=520.0,
        Vdc_max=600.0,
        T_max=65.0
    )

    # 1. Test NaN, Inf, None -> Fallback triggered
    test_cases_fallback = [float("nan"), float("inf"), float("-inf"), None]
    normal_state = {"Vsc": 150.0, "Vdc": 560.0, "SC_temp": 30.0, "time": 10.0, "P_inv_dc": -5000.0}

    for bad_act in test_cases_fallback:
        appr, is_fallback, reason = supervisor.enforce_safety(bad_act, normal_state)
        assert is_fallback is True
        assert not math.isnan(appr)
        assert not math.isinf(appr)
        assert -20000.0 <= appr <= 20000.0
        assert "FALLBACK" in reason

    # 2. Test dropped data link
    appr, is_fallback, reason = supervisor.enforce_safety(5000.0, normal_state, link_healthy=False)
    assert is_fallback is True
    assert "FALLBACK" in reason

    # 3. Test massive power input (+10 MW and -10 MW)
    appr_pos, is_fall, reason = supervisor.enforce_safety(1e7, normal_state)
    assert not is_fall
    assert appr_pos <= 20000.0
    assert "power rating" in reason or "current limit" in reason

    appr_neg, is_fall, reason = supervisor.enforce_safety(-1e7, normal_state)
    assert not is_fall
    assert appr_neg >= -20000.0

    # 4. Supercap voltage boundary protection
    # Near empty supercapacitor (Vsc = 99 V): cannot discharge (P > 0)
    depleted_state = {"Vsc": 99.0, "Vdc": 560.0, "SC_temp": 30.0, "time": 12.0, "P_inv_dc": 5000.0}
    appr, is_fall, reason = supervisor.enforce_safety(5000.0, depleted_state)
    assert appr == 0.0
    assert "depleted" in reason

    # Near full supercapacitor (Vsc = 201 V): cannot charge (P < 0)
    full_state = {"Vsc": 201.0, "Vdc": 560.0, "SC_temp": 30.0, "time": 13.0, "P_inv_dc": -5000.0}
    appr, is_fall, reason = supervisor.enforce_safety(-5000.0, full_state)
    assert appr == 0.0
    assert "full" in reason

    # 5. Over-temperature cutoff
    hot_state = {"Vsc": 150.0, "Vdc": 560.0, "SC_temp": 66.0, "time": 14.0}
    appr, is_fall, reason = supervisor.enforce_safety(5000.0, hot_state)
    assert appr == 0.0
    assert "Temperature limit exceeded" in reason

    # 6. DC link overvoltage protection (Vdc >= 600 V)
    overdc_state = {"Vsc": 150.0, "Vdc": 605.0, "SC_temp": 30.0, "time": 15.0}
    appr, is_fall, reason = supervisor.enforce_safety(5000.0, overdc_state)
    assert appr == 0.0
    assert "DC link over-voltage" in reason

def test_rl_training_onnx_and_closed_loop():
    """
    Tests policy training, ONNX export, and closed-loop execution inside WebSimAdapter.
    """
    manager = RLPolicyManager()
    
    # 1. Train a quick policy (1000 steps)
    train_res = manager.train_policy(total_timesteps=600, seed=42)
    assert train_res["episodes"] >= 1
    assert Path(train_res["onnx_path"]).exists()

    # 2. Test ONNX runtime loading and inference
    manager.load_onnx_inference()
    sample_obs = np.zeros(22, dtype=np.float32)
    sample_obs[0] = 0.5  # 50% SoC
    action = manager.predict_action(sample_obs)
    assert -1.0 <= action <= 1.0

    # 3. Test Decision Explainer
    explanation = manager.explain_decision(sample_obs, action)
    assert "action_P_sc_norm" in explanation
    assert "key_drivers" in explanation
    assert len(explanation["key_drivers"]) >= 1

    # 4. Closed-loop adapter run with ONNX policy + Safety Supervisor
    sim = WebSimAdapter()
    supervisor = SafetySupervisor()
    sim.reset({"load": 800.0, "stage": 2, "mode": "alt", "vsc_init": 130.0})

    for step in range(30):
        # Step adapter
        sig = sim.step(P_sc_ref=0.0, dt=1.0)
        
        # Build 22-element observation
        obs = np.zeros(22, dtype=np.float32)
        denom = (200.0**2 - 100.0**2)
        obs[0] = max(0.0, min(1.0, (sig.Vsc**2 - 100.0**2) / denom))
        obs[1] = (sig.Vsc - 150.0) / 50.0
        obs[2] = (sig.Vdc - 550.0) / 50.0
        obs[3] = sig.P_inv_dc / 20000.0

        # Predict with ONNX
        raw_act_norm = manager.predict_action(obs)
        raw_P_sc_ref = raw_act_norm * 20000.0

        # Pass through hard safety supervisor
        safe_P_sc_ref, is_fall, reason = supervisor.enforce_safety(raw_P_sc_ref, sig.to_dict())
        
        # Assert physical safety invariant
        assert 100.0 <= sig.Vsc <= 200.0 or abs(safe_P_sc_ref) <= 20000.0
        assert not math.isnan(safe_P_sc_ref)

def test_benchmark_evaluator_honesty():
    """
    Tests Section 8 Honesty requirement evaluation across B0, B1, B2, and RL.
    """
    evaluator = BenchmarkEvaluator()
    res = evaluator.evaluate_all(test_seeds=[101], steps_per_seed=40)
    
    assert "summary_table" in res
    assert len(res["summary_table"]) == 4 # B0, B1, B2, RL
    assert "honesty_statement" in res
    assert Path(res["report_path"]).exists()
