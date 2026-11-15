"""Automated verification tests for the 7 demonstration scenarios in AGENTS.md Section 9."""

import pytest

from core.scenarios import SCENARIOS_META, ScenarioRunner


@pytest.fixture
def runner():
    """Create a scenario runner instance with in-memory ledger."""
    from core.ledger import SQLAlchemyLedgerRepository

    repo = SQLAlchemyLedgerRepository("sqlite:///:memory:")
    repo.init_db()
    return ScenarioRunner(repo=repo)


def test_scenario_glance_away_3s(runner):
    """Scenario 1: Glance away 3s -> Risk stays exactly 0 (grace window is 4s)."""
    res = runner.run_glance_away_3s()
    assert res.passed is True
    assert res.final_score == 0.0
    assert res.final_tier == "CLEAR"
    assert res.warnings_count == 0
    assert res.is_held is False


def test_scenario_brief_network_drop(runner):
    """Scenario 2: Brief network drop -> Investigator resolves TECHNICAL, no penalty."""
    res = runner.run_brief_network_drop()
    assert res.passed is True
    assert res.resolution == "technical"
    assert res.final_score == 0.0
    assert res.final_tier == "CLEAR"
    assert res.warnings_count == 0


def test_scenario_sibling_walks_by(runner):
    """Scenario 3: Sibling walks by -> Resolved ORDINARY, tiny weight, decays away."""
    res = runner.run_sibling_walks_by()
    assert res.passed is True
    assert res.resolution == "ordinary"
    assert res.final_score < 2.0
    assert res.final_tier == "CLEAR"
    assert res.warnings_count == 0


def test_scenario_failing_webcam_repeated(runner):
    """Scenario 4: Failing webcam, repeated -> Camera channel hits cap (40), never warns."""
    res = runner.run_failing_webcam_repeated()
    assert res.passed is True
    # Invariant: single channel cannot cross WARNED (45.0) threshold
    assert res.final_score <= 40.0
    assert res.warnings_count == 0
    assert res.is_held is False


def test_scenario_phone_and_notes_corroborated(runner):
    """Scenario 5: Phone + notes, corroborated -> 2 channels, DELIBERATE, warnings, HELD."""
    res = runner.run_phone_and_notes_corroborated()
    assert res.passed is True
    assert res.is_held is True
    assert res.final_tier == "HELD"
    assert res.warnings_count >= 2


def test_scenario_calm_student_3min(runner):
    """Scenario 6: Calm student 3 minutes -> Stays CLEAR (0.0)."""
    res = runner.run_calm_student_3min()
    assert res.passed is True
    assert res.final_score == 0.0
    assert res.final_tier == "CLEAR"
    assert res.warnings_count == 0
    assert res.is_held is False


def test_scenario_mass_flag(runner):
    """Scenario 7: Mass flag -> Many sessions flag at once, thresholds relax, notice shown."""
    res = runner.run_mass_flag()
    assert res.passed is True
    assert res.system_notice is not None
    assert "possible platform/network failure" in res.system_notice
    assert res.final_tier == "CLEAR"


def test_scenario_metadata_and_dispatch(runner):
    """Verify all 7 scenarios in SCENARIOS_META can be dispatched via runner.run_scenario."""
    assert len(SCENARIOS_META) == 7
    scenario_ids = [m["id"] for m in SCENARIOS_META]
    assert "glance_away_3s" in scenario_ids
    assert "phone_and_notes_corroborated" in scenario_ids

    for meta in SCENARIOS_META:
        res = runner.run_scenario(meta["id"])
        assert res.scenario_id == meta["id"]
        assert res.passed is True
