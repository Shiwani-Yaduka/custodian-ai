# ruff: noqa: E501
"""Test Suite for 'Break It On Purpose' Demonstration.

Validates that:
1. Overly lenient policy configurations fail security gates (miss rate spikes -> RED).
2. Reverting to default calibrated policy restores 100% detection (GREEN).
3. Naive fixed-threshold baseline produces intolerable false-flag rates (>85% -> RED).
4. Safety invariant violation (e.g. channel cap >= WARNED threshold) is blocked by RiskPolicy validation.
5. Simulator correctly detects and classifies policy regressions.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from core.policy import load_policy
from fairness.baseline import FixedThresholdBaseline
from fairness.run import evaluate_fairness
from simulator.engine import build_modified_policy, run_simulation

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCENARIOS_PATH = PROJECT_ROOT / "fairness" / "scenarios.yaml"
CONFIG_PATH = PROJECT_ROOT / "fairness" / "fairness_config.yaml"


def test_baseline_is_unacceptable_red():
    """Verify legacy commercial fixed-threshold baseline turns RED with severe false flags."""
    baseline = FixedThresholdBaseline()

    with open(SCENARIOS_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    innocent_scenarios = [s for s in data["scenarios"] if s["label"] == "must_not_flag"]
    false_flags = 0
    for s in innocent_scenarios:
        res = baseline.evaluate_scenario(s)
        if res.flagged:
            false_flags += 1

    ff_rate = false_flags / len(innocent_scenarios)
    # Naive baseline flags nearly all normal behaviors (>85% false flag rate)
    assert ff_rate > 0.85, f"Expected baseline false flag rate > 85%, got {ff_rate * 100:.1f}%"


def test_break_security_by_excessive_leniency_then_revert():
    """Demonstrate 'Break It on Purpose' for security:

    When parameters are made overly lenient (caps slashed to 15.0 so max corroborated
    score is 36.0, well below HELD threshold 80.0), the suite turns RED because real
    cheating is missed.
    Reverting to default policy restores 100% detection (GREEN).
    """
    # 1. Break it on purpose: overly lenient policy (caps too low to reach HELD)
    lenient_policy = build_modified_policy(
        overrides={
            "cap_camera": 15.0,
            "cap_mic": 15.0,
            "cap_window": 15.0,
            "cap_device": 15.0,
            "corroboration_lambda": 0.0,
        }
    )

    report_broken = evaluate_fairness(
        scenarios_path=SCENARIOS_PATH,
        config_path=CONFIG_PATH,
        policy=lenient_policy,
    )

    # Must fail gates due to 100% missed violations (RED)
    assert not report_broken.passed_all_gates, "Overly lenient policy should fail fairness/security gates!"
    assert report_broken.adaptive_misses > 0, "Broken lenient policy must miss deliberate violations"
    assert report_broken.adaptive_miss_rate == 100.0, f"Expected 100% miss rate, got {report_broken.adaptive_miss_rate}"

    # 2. Revert to default calibrated policy (GREEN)
    default_policy = load_policy()
    report_reverted = evaluate_fairness(
        scenarios_path=SCENARIOS_PATH,
        config_path=CONFIG_PATH,
        policy=default_policy,
    )

    assert report_reverted.passed_all_gates, "Default policy must pass all regression gates!"
    assert report_reverted.adaptive_miss_rate == 0.0, "Default policy must have 0% misses"
    assert report_reverted.adaptive_false_flag_rate == 0.0, "Default policy must have 0% false flags"


def test_simulator_detects_regression_and_blocks_invariant_violation():
    """Verify Policy Simulator flags regressions and rejects unsafe policies."""
    # 1. Unsafe policy: single sensor can trigger WARNED (cap >= 45.0)
    with pytest.raises(Exception) as exc_info:
        build_modified_policy(overrides={"cap_camera": 45.0})
    assert "Safety Violation in Policy" in str(exc_info.value)

    # 2. Simulator detects regression when policy causes missed violations
    weak_policy = build_modified_policy(
        overrides={
            "cap_camera": 15.0,
            "cap_mic": 15.0,
            "cap_window": 15.0,
            "cap_device": 15.0,
        }
    )
    sim_report = run_simulation(SCENARIOS_PATH, modified_policy=weak_policy)
    assert sim_report.verdict == "REGRESSION"
    assert sim_report.regressions_count > 0
