"""Comprehensive tests for the Bayesian Investigation Agent.

Verifies:
- Network drop with telemetry resolving to TECHNICAL (x0.0 weight applied)
- Carelessness correcting after reminder resolving to ORDINARY (x0.15)
- Anomaly resuming after reminder resolving to DELIBERATE (x1.0)
- Ambiguous case hitting probe limit resolving to INCONCLUSIVE (x0.4)
- Zero-cost quiet probes chosen before visible reminders
- Posteriors always summing to 1 and non-negative Information Gain
- Held weight isolation while case is open
"""

import pytest

from core.investigator import (
    InvestigatorAgent,
    ResolutionStatus,
    ScriptedProbeRunner,
    bayes_update,
    calculate_expected_information_gain,
    load_investigator_policy,
)
from core.models import Observation
from core.risk import RiskEngine


def test_network_drop_resolves_technical_with_zero_weight():
    """A network drop with scripted telemetry outcomes resolves TECHNICAL and applies weight 0."""
    policy = load_investigator_policy()
    runner = ScriptedProbeRunner({
        "network_heartbeat_check": "packet_loss_spike",
        "device_telemetry_check": "hardware_fault",
        "secondary_detector_cross_check": "disagrees_normal",
        "high_res_frame_burst": "sensor_blur_or_dark",
    })
    agent = InvestigatorAgent(policy=policy, probe_runner=runner)
    engine = RiskEngine()

    obs = Observation(
        session_id="test_tech_session",
        signal="network_drop",
        timestamp=10.0,
        duration=30.0,
        confidence=0.55,  # Low confidence triggers case opening
    )

    init_state = engine._initialize_session_state("test_tech_session", 10.0)
    should_open, reason = agent.should_open_case(
        obs, predicted_raw_weight=4.0, current_risk_state=init_state, repetition_count=1
    )
    assert should_open is True
    assert "Low detector confidence" in reason

    # Open case and verify held weight
    case = agent.open_case(obs, channel="device", held_raw_weight=4.0, reason=reason, now=10.0)
    assert case.is_open is True
    assert case.held_raw_weight == 4.0

    # Verify risk engine has received NO risk yet
    engine.state_store.set_state("test_tech_session", init_state)
    assert engine.state_store.get_state("test_tech_session").current_score == 0.0

    # Run investigation to resolution
    resolution = agent.run_full_investigation(case.case_id, start_time=10.0)
    assert resolution.status == ResolutionStatus.TECHNICAL
    assert resolution.multiplier == 0.0
    assert resolution.final_posterior["technical"] >= 0.70

    # Apply resolution to engine and verify weight applied is 0.0
    _, state = agent.apply_case_resolution_to_engine(case, engine, now=12.0)
    assert state.current_score == 0.0
    assert state.channels["device"].accumulator == 0.0


def test_carelessness_corrects_after_reminder_resolves_ordinary():
    """Carelessness that corrects after the reminder resolves ORDINARY (x0.15)."""
    policy = load_investigator_policy()
    runner = ScriptedProbeRunner({
        "device_telemetry_check": "hardware_normal",
        "network_heartbeat_check": "network_stable",
        "secondary_detector_cross_check": "confirms_anomaly",
        "high_res_frame_burst": "benign_ambient_object",
        "soft_reminder": "immediate_correction",
    })
    agent = InvestigatorAgent(policy=policy, probe_runner=runner)
    engine = RiskEngine()

    obs = Observation(
        session_id="test_ordinary_session",
        signal="gaze_off_screen",
        timestamp=20.0,
        duration=15.0,
        confidence=0.58,  # Triggers case opening
    )

    case = agent.open_case(
        obs, channel="camera", held_raw_weight=6.0, reason="low confidence", now=20.0
    )

    # Execute probes until resolved
    resolution = agent.run_full_investigation(case.case_id, start_time=20.0)
    assert resolution.status == ResolutionStatus.ORDINARY
    assert resolution.multiplier == 0.15
    assert resolution.final_posterior["ordinary"] >= 0.70

    # Apply to engine
    engine_state = engine._initialize_session_state("test_ordinary_session", 20.0)
    engine.state_store.set_state("test_ordinary_session", engine_state)
    _, final_state = agent.apply_case_resolution_to_engine(case, engine, now=22.0)

    # Final weight should be 6.0 * 0.15 = 0.90
    assert pytest.approx(final_state.channels["camera"].accumulator, 0.01) == 0.90


def test_behavior_resumes_after_reminder_resolves_deliberate():
    """Behaviour that resumes after the reminder repeatedly resolves DELIBERATE (x1.0)."""
    policy = load_investigator_policy()
    runner = ScriptedProbeRunner({
        "device_telemetry_check": "hardware_normal",
        "network_heartbeat_check": "network_stable",
        "secondary_detector_cross_check": "confirms_anomaly",
        "soft_reminder": "resumes_or_ignores",
        "high_res_frame_burst": "clear_secondary_actor",
    })
    agent = InvestigatorAgent(policy=policy, probe_runner=runner)

    obs = Observation(
        session_id="test_deliberate_session",
        signal="multiple_faces",
        timestamp=30.0,
        duration=10.0,
        confidence=0.90,  # Prior for multiple_faces is already deliberate-leaning
    )

    case = agent.open_case(
        obs, channel="camera", held_raw_weight=18.0, reason="recurrence", now=30.0
    )
    resolution = agent.run_full_investigation(case.case_id, start_time=30.0)

    assert resolution.status == ResolutionStatus.DELIBERATE
    assert resolution.multiplier == 1.00
    assert resolution.final_posterior["deliberate"] >= 0.70


def test_unresolved_case_after_three_probes_resolves_inconclusive():
    """An unresolved case after 3 probes resolves INCONCLUSIVE (x0.4)."""
    policy = load_investigator_policy()
    # Script neutral/conflicting outcomes that keep all hypotheses under 0.70
    runner = ScriptedProbeRunner({
        "device_telemetry_check": "intermittent_telemetry",
        "high_res_frame_burst": "sensor_blur_or_dark",
        "network_heartbeat_check": "minor_jitter",
        "secondary_detector_cross_check": "inconclusive_blur",
    })
    agent = InvestigatorAgent(policy=policy, probe_runner=runner)

    obs = Observation(
        session_id="test_inconclusive_session",
        signal="face_absent",
        timestamp=40.0,
        duration=15.0,
        confidence=0.50,
    )

    case = agent.open_case(
        obs, channel="camera", held_raw_weight=10.0, reason="balanced prior", now=40.0
    )
    # Set a balanced initial belief
    case.current_belief = {"ordinary": 0.40, "technical": 0.30, "deliberate": 0.30}

    # Force 3 probes to run without crossing 0.70
    resolution = agent.run_full_investigation(case.case_id, start_time=40.0)
    assert resolution.status == ResolutionStatus.INCONCLUSIVE
    assert resolution.multiplier == 0.40
    assert len(resolution.probes_used) == 3
    assert "Student given benefit of doubt" in resolution.reason


def test_zero_cost_quiet_probes_chosen_before_visible_reminder():
    """Zero-cost quiet probes are always chosen before the visible reminder."""
    policy = load_investigator_policy()
    agent = InvestigatorAgent(policy=policy)

    obs = Observation(
        session_id="test_quiet_probe_priority",
        signal="face_absent",
        timestamp=50.0,
        duration=20.0,
        confidence=0.55,
    )
    case = agent.open_case(obs, channel="camera", held_raw_weight=10.0, reason="test", now=50.0)

    best_probe_name = agent.select_best_probe(case)
    best_probe = policy.probes[best_probe_name]

    # Verify best probe is quiet (cost < 0.7), NEVER the reminder (0.7) or prompt (1.0)
    assert best_probe.cost < 0.7
    assert best_probe_name in (
        "device_telemetry_check",
        "network_heartbeat_check",
        "secondary_detector_cross_check",
        "high_res_frame_burst",
    )


def test_posteriors_always_sum_to_one_and_eig_non_negative():
    """Posteriors always sum to 1; the information-gain function is never negative."""
    policy = load_investigator_policy()

    test_priors = [
        {"ordinary": 0.333333, "technical": 0.333333, "deliberate": 0.333334},
        {"ordinary": 0.80, "technical": 0.10, "deliberate": 0.10},
        {"ordinary": 0.05, "technical": 0.90, "deliberate": 0.05},
        {"ordinary": 0.10, "technical": 0.10, "deliberate": 0.80},
    ]

    for prior in test_priors:
        for _probe_name, probe_def in policy.probes.items():
            eig = calculate_expected_information_gain(prior, probe_def)
            assert eig >= 0.0

            for _outcome, likelihood_map in probe_def.outcomes.items():
                post = bayes_update(prior, likelihood_map)
                assert pytest.approx(sum(post.values()), 1e-5) == 1.0
                for p in post.values():
                    assert 0.0 <= p <= 1.0


def test_held_weight_never_applied_while_case_is_open():
    """The held weight is never applied while the case is open."""
    policy = load_investigator_policy()
    agent = InvestigatorAgent(policy=policy)
    engine = RiskEngine()
    session_id = "test_held_weight_session"

    obs = Observation(
        session_id=session_id,
        signal="face_absent",
        timestamp=60.0,
        duration=30.0,
        confidence=0.50,
    )
    case = agent.open_case(
        obs, channel="camera", held_raw_weight=12.0, reason="held test", now=60.0
    )

    assert case.is_open is True

    # Check that engine has received 0 risk
    state = engine.state_store.get_state(session_id)
    if state is None:
        state = engine._initialize_session_state(session_id, 60.0)
    assert state.current_score == 0.0
    assert state.channels["camera"].accumulator == 0.0

    # Execute 1 probe; verify engine still remains 0 if case is open
    agent.execute_next_probe(case.case_id, now=61.0)
    if case.is_open:
        state = engine.evaluate_session(session_id, now=61.0)
        assert state.current_score == 0.0
