# ruff: noqa: E501
"""Unit and regression tests for the Fairness Evaluation Suite."""

from pathlib import Path

import pytest
import yaml

from fairness.baseline import FixedThresholdBaseline
from fairness.run import evaluate_fairness


@pytest.fixture
def scenarios_file():
    return Path("fairness/scenarios.yaml")


@pytest.fixture
def config_file():
    return Path("fairness/fairness_config.yaml")


def test_scenario_library_completeness(scenarios_file):
    """Verify scenario library has at least 30 well-formed scenarios."""
    assert scenarios_file.exists(), "scenarios.yaml must exist"
    with open(scenarios_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    scenarios = data.get("scenarios", [])
    assert len(scenarios) >= 30, f"Expected >= 30 scenarios, found {len(scenarios)}"

    labels = {s.get("label") for s in scenarios}
    assert labels == {"must_not_flag", "must_catch"}

    for sc in scenarios:
        assert "id" in sc and sc["id"]
        assert "class" in sc and sc["class"]
        assert "label" in sc and sc["label"]
        assert "timeline" in sc and len(sc["timeline"]) > 0


def test_all_behavioral_classes_represented(scenarios_file):
    """Verify all 6 behavioral/environmental categories are represented."""
    with open(scenarios_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    classes = {s.get("class") for s in data["scenarios"]}
    expected_classes = {
        "reading_thinking_habits",
        "movement_patterns",
        "lighting_conditions",
        "equipment_faults",
        "environmental_noise",
        "deliberate_violations",
    }
    assert expected_classes.issubset(classes)


def test_adaptive_fairness_suite_passes_all_gates(scenarios_file, config_file):
    """Verify that Custodian AI achieves 0% false flags and 0% misses."""
    report = evaluate_fairness(scenarios_path=scenarios_file, config_path=config_file)
    assert report.passed_all_gates is True
    assert report.adaptive_false_flag_rate == 0.0, f"False flag rate was {report.adaptive_false_flag_rate}%"
    assert report.adaptive_miss_rate == 0.0, f"Miss rate was {report.adaptive_miss_rate}%"
    assert report.adaptive_false_flags == 0
    assert report.adaptive_misses == 0


def test_baseline_detector_demonstrates_high_false_flag_rate(scenarios_file):
    """Verify naive fixed-threshold baseline flags innocent human behaviors (>50% false flags)."""
    with open(scenarios_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    innocent = [s for s in data["scenarios"] if s.get("label") == "must_not_flag"]
    detector = FixedThresholdBaseline()

    flagged_count = sum(1 for sc in innocent if detector.evaluate_scenario(sc).flagged)
    baseline_ff_rate = (flagged_count / len(innocent)) * 100.0

    # Demonstrates empirical superiority of adaptive corroboration
    assert baseline_ff_rate > 50.0, f"Expected baseline false flag rate > 50%, got {baseline_ff_rate:.1f}%"
