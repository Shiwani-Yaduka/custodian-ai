"""Comprehensive unit tests for Custodian AI Core Risk Engine.

Verifies:
- Grace window filtering (3s glance = 0 weight)
- Duration factor smooth ramp
- Exponential half-life decay (240s halving, 480s quartering)
- Single-channel cap isolation (broken sensor cannot reach WARNED alone)
- Multi-channel corroboration multiplier
- Repetition scaling with rolling 5-minute window and max step clamp
- Spontaneous score decay back to CLEAR during good behavior
- 6-second hysteresis hold and anti-flapping protection
- Policy validation refusing caps >= WARNED threshold
"""

import pytest

from core.models import Observation, Tier
from core.policy import RiskPolicy, SignalDefinition
from core.risk import RiskEngine


def test_grace_window_three_second_glance_is_zero():
    """A 3-second glance (under the 4s grace window) contributes exactly 0."""
    engine = RiskEngine()
    obs = Observation(
        session_id="test_grace",
        signal="gaze_off_screen",  # g_s = 4.0s, f_s = 20.0s
        timestamp=100.0,
        duration=3.0,
        confidence=1.0,
    )
    processed, state = engine.process_observation(obs)

    assert processed.duration_factor == 0.0
    assert processed.raw_weight == 0.0
    assert state.current_score == 0.0
    assert state.channels["camera"].accumulator == 0.0
    assert state.current_tier == Tier.CLEAR


def test_duration_factor_smooth_ramp():
    """Contribution increases smoothly between grace window and full-weight duration."""
    engine = RiskEngine()
    # gaze_off_screen: g_s = 4.0, f_s = 20.0, span = 16.0
    d_under = engine.calculate_duration_factor("gaze_off_screen", 3.9)
    d_at_grace = engine.calculate_duration_factor("gaze_off_screen", 4.0)
    d_quarter = engine.calculate_duration_factor("gaze_off_screen", 8.0)    # (8-4)/16 = 0.25
    d_half = engine.calculate_duration_factor("gaze_off_screen", 12.0)     # (12-4)/16 = 0.50
    d_three_q = engine.calculate_duration_factor("gaze_off_screen", 16.0)  # (16-4)/16 = 0.75
    d_full = engine.calculate_duration_factor("gaze_off_screen", 20.0)     # 1.0
    d_over = engine.calculate_duration_factor("gaze_off_screen", 35.0)     # clamped 1.0

    assert d_under == 0.0
    assert d_at_grace == 0.0
    assert pytest.approx(d_quarter, 0.001) == 0.25
    assert pytest.approx(d_half, 0.001) == 0.50
    assert pytest.approx(d_three_q, 0.001) == 0.75
    assert d_full == 1.0
    assert d_over == 1.0


def test_half_life_decay_240s_and_480s():
    """After 240 s a contribution has halved; after 480 s it is a quarter."""
    engine = RiskEngine()
    # multiple_faces: channel camera, b_s=18, g_s=2, f_s=10. Duration=10 => d_i=1.0
    obs = Observation(
        session_id="test_decay",
        signal="multiple_faces",
        timestamp=0.0,
        duration=10.0,
        confidence=1.0,
    )
    processed, initial_state = engine.process_observation(obs, now=0.0)
    initial_score = initial_state.current_score
    assert initial_score == 18.0

    # Evaluate after 240 seconds (1 half-life)
    state_240 = engine.evaluate_session("test_decay", now=240.0)
    assert pytest.approx(state_240.current_score, 0.001) == initial_score * 0.5
    assert pytest.approx(state_240.channels["camera"].accumulator, 0.001) == 9.0

    # Evaluate after 480 seconds (2 half-lives)
    state_480 = engine.evaluate_session("test_decay", now=480.0)
    assert pytest.approx(state_480.current_score, 0.001) == initial_score * 0.25
    assert pytest.approx(state_480.channels["camera"].accumulator, 0.001) == 4.5


def test_single_channel_continuous_firing_never_exceeds_cap_and_never_warns():
    """A single channel firing continuously for an hour never exceeds its cap."""
    engine = RiskEngine()
    session_id = "broken_webcam_session"

    # Fire every 30 seconds for 1 hour (120 events)
    for step in range(120):
        t = step * 30.0
        obs = Observation(
            session_id=session_id,
            signal="face_absent",  # camera channel, base 12, max duration
            timestamp=t,
            duration=30.0,
            confidence=1.0,
        )
        _, state = engine.process_observation(obs, now=t)

        # Invariant 1: Camera accumulator must never exceed its cap K_c = 40.0
        assert state.channels["camera"].accumulator <= 40.0

        # Invariant 2: Total score must never exceed 40.0
        assert state.current_score <= 40.0

        # Invariant 3: Single channel can NEVER push student to WARNED (45.0)
        assert state.current_tier in (Tier.CLEAR, Tier.WATCHING)
        assert state.current_tier != Tier.WARNED
        assert state.candidate_tier != Tier.WARNED


def test_corroboration_two_channels_exceed_plain_sum():
    """Two channels together produce a higher score than the sum would if added plainly."""
    engine = RiskEngine()
    session_id = "corroboration_session"

    # Channel 1: camera (gaze_off_screen, weight = 8.0)
    obs_cam = Observation(
        session_id=session_id,
        signal="gaze_off_screen",
        timestamp=10.0,
        duration=20.0,
        confidence=1.0,
    )
    engine.process_observation(obs_cam, now=10.0)

    # Channel 2: exam_window (window_blur, weight = 15.0)
    obs_win = Observation(
        session_id=session_id,
        signal="window_blur",
        timestamp=10.0,
        duration=20.0,
        confidence=1.0,
    )
    _, state = engine.process_observation(obs_win, now=10.0)

    cam_val = state.channels["camera"].accumulator
    win_val = state.channels["exam_window"].accumulator
    plain_sum = cam_val + win_val

    # 2 contributing channels => multiplier = 1 + 0.20*(2-1) = 1.20
    expected_score = plain_sum * 1.20

    assert state.corroboration_multiplier == 1.20
    assert len(state.contributing_channels) == 2
    assert pytest.approx(state.current_score, 0.001) == expected_score
    assert state.current_score > plain_sum


def test_repetition_escalation_within_five_minutes_capped_at_max():
    """Repeated occurrences within 5 minutes escalate weight, capped at the max step."""
    engine = RiskEngine()
    session_id = "repetition_session"

    # Occurrence 1 at t=0
    obs1 = Observation(
        session_id=session_id,
        signal="head_turn",  # b_s = 8.0
        timestamp=0.0,
        duration=20.0,
        confidence=1.0,
    )
    p1, _ = engine.process_observation(obs1, now=0.0)
    assert p1.repetition_multiplier == 1.0  # n=1
    assert pytest.approx(p1.raw_weight, 0.001) == 8.0

    # Occurrence 2 at t=30 (within 5 mins)
    obs2 = Observation(
        session_id=session_id, signal="head_turn", timestamp=30.0, duration=20.0, confidence=1.0
    )
    p2, _ = engine.process_observation(obs2, now=30.0)
    assert pytest.approx(p2.repetition_multiplier, 0.001) == 1.35  # n=2: 1 + 0.35*1
    assert pytest.approx(p2.raw_weight, 0.001) == 8.0 * 1.35

    # Occurrence 3 at t=60
    obs3 = Observation(
        session_id=session_id, signal="head_turn", timestamp=60.0, duration=20.0, confidence=1.0
    )
    p3, _ = engine.process_observation(obs3, now=60.0)
    assert pytest.approx(p3.repetition_multiplier, 0.001) == 1.70  # n=3: 1 + 0.35*2

    # Occurrence 4 at t=90
    obs4 = Observation(
        session_id=session_id, signal="head_turn", timestamp=90.0, duration=20.0, confidence=1.0
    )
    p4, _ = engine.process_observation(obs4, now=90.0)
    assert pytest.approx(p4.repetition_multiplier, 0.001) == 2.05  # n=4: 1 + 0.35*3

    # Occurrence 5 at t=120
    obs5 = Observation(
        session_id=session_id, signal="head_turn", timestamp=120.0, duration=20.0, confidence=1.0
    )
    p5, _ = engine.process_observation(obs5, now=120.0)
    assert pytest.approx(p5.repetition_multiplier, 0.001) == 2.40  # n=5: 1 + 0.35*4 (max step)

    # Occurrence 6 at t=150 (still capped at max steps = 4)
    obs6 = Observation(
        session_id=session_id, signal="head_turn", timestamp=150.0, duration=20.0, confidence=1.0
    )
    p6, _ = engine.process_observation(obs6, now=150.0)
    assert pytest.approx(p6.repetition_multiplier, 0.001) == 2.40

    # Occurrence 7 at t=400 (5 minutes after obs1, obs2, obs3)
    # At t=400, window start is 400 - 300 = 100.
    # Prior occurrences in [100, 400]: obs5 (120), obs6 (150) => 2 prior occurrences
    obs7 = Observation(
        session_id=session_id, signal="head_turn", timestamp=400.0, duration=20.0, confidence=1.0
    )
    p7, _ = engine.process_observation(obs7, now=400.0)
    assert pytest.approx(p7.repetition_multiplier, 0.001) == 1.70  # n = 2 + 1 = 3


def test_score_decays_back_to_clear_after_good_behavior():
    """The score decays back to CLEAR by itself after good behavior."""
    engine = RiskEngine()
    session_id = "good_student_session"

    # Generate some risk
    obs = Observation(
        session_id=session_id,
        signal="head_turn",
        timestamp=0.0,
        duration=20.0,
        confidence=1.0,
    )
    engine.process_observation(obs, now=0.0)

    # Advance time by 5 half-lives (1200 seconds)
    state = engine.evaluate_session(session_id, now=1200.0)
    assert state.current_score < 1.0
    assert state.current_tier == Tier.CLEAR
    assert len(state.contributing_channels) == 0


def test_no_tier_flapping_under_six_seconds_hysteresis():
    """No tier flapping when the score oscillates around a threshold for less than 6 seconds."""
    engine = RiskEngine()
    session_id = "flapping_test_session"
    state = engine._initialize_session_state(session_id, 0.0)

    # Initial state is CLEAR at t=0
    assert state.current_tier == Tier.CLEAR
    assert state.candidate_tier == Tier.CLEAR

    # At t=1.0, score spikes to WARNED range
    engine._apply_hysteresis(state, Tier.WARNED, current_time=1.0)
    assert state.candidate_tier == Tier.WARNED
    # Crucial: current_tier must STILL be CLEAR because 6s have not elapsed
    assert state.current_tier == Tier.CLEAR

    # At t=4.0 (3.0 seconds later, < 6.0s), spike subsides back to CLEAR
    engine._apply_hysteresis(state, Tier.CLEAR, current_time=4.0)
    assert state.candidate_tier == Tier.CLEAR
    assert state.current_tier == Tier.CLEAR  # Never flapped!

    # At t=5.0, score enters WARNED range again
    engine._apply_hysteresis(state, Tier.WARNED, current_time=5.0)
    assert state.candidate_tier == Tier.WARNED
    assert state.current_tier == Tier.CLEAR

    # At t=10.0 (5.0s of continuous hold, still < 6.0s)
    engine._apply_hysteresis(state, Tier.WARNED, current_time=10.0)
    assert state.candidate_tier == Tier.WARNED
    assert state.current_tier == Tier.CLEAR

    # At t=11.1 (6.1s of continuous hold >= 6.0s)
    engine._apply_hysteresis(state, Tier.WARNED, current_time=11.1)
    assert state.candidate_tier == Tier.WARNED
    assert state.current_tier == Tier.WARNED  # Now legitimately transitioned!


def test_end_to_end_observation_hysteresis_hold():
    """Verify hysteresis when processing real corroborated observations."""
    engine = RiskEngine()
    session_id = "e2e_hysteresis_session"

    # Push score >= 45.0 with camera + exam_window corroboration
    engine.process_observation(
        Observation(
            session_id=session_id,
            signal="multiple_faces",
            timestamp=0.0,
            duration=10.0,
            confidence=1.0,
        ),
        now=0.0,
    )
    engine.process_observation(
        Observation(
            session_id=session_id,
            signal="face_absent",
            timestamp=0.0,
            duration=30.0,
            confidence=1.0,
        ),
        now=0.0,
    )
    _, state_0 = engine.process_observation(
        Observation(
            session_id=session_id,
            signal="tab_hidden",
            timestamp=0.0,
            duration=15.0,
            confidence=1.0,
        ),
        now=0.0,
    )

    assert state_0.current_score >= 45.0
    assert state_0.candidate_tier == Tier.WARNED
    # Must STILL be CLEAR immediately upon event arrival (t=0.0)
    assert state_0.current_tier == Tier.CLEAR

    # At t=3.0 (3 seconds later, < 6s)
    state_3 = engine.evaluate_session(session_id, now=3.0)
    assert state_3.candidate_tier == Tier.WARNED
    assert state_3.current_tier == Tier.CLEAR

    # At t=6.5 (6.5 seconds later >= 6s)
    state_6 = engine.evaluate_session(session_id, now=6.5)
    assert state_6.candidate_tier == Tier.WARNED
    assert state_6.current_tier == Tier.WARNED


def test_policy_validator_rejects_cap_at_or_above_warned_threshold():
    """The policy validator refuses to start if any K_c >= WARNED threshold."""
    # Test cap exactly equal to WARNED threshold (45.0)
    with pytest.raises(ValueError) as exc1:
        RiskPolicy(
            channel_caps={"camera": 45.0, "microphone": 40.0, "exam_window": 40.0, "device": 40.0},
            tier_thresholds={"WARNED": 45.0},
        )
    assert "strictly less than the WARNED threshold" in str(exc1.value)

    # Test cap greater than WARNED threshold (50.0 > 45.0)
    with pytest.raises(ValueError) as exc2:
        RiskPolicy(
            channel_caps={"camera": 50.0, "microphone": 40.0, "exam_window": 40.0, "device": 40.0},
            tier_thresholds={"WARNED": 45.0},
        )
    assert "strictly less than the WARNED threshold" in str(exc2.value)


def test_policy_validator_rejects_invalid_durations():
    """Signals must have f_s > g_s."""
    with pytest.raises(ValueError) as exc:
        SignalDefinition(channel="camera", b_s=10.0, g_s=10.0, f_s=5.0)
    assert "must be strictly greater than grace duration" in str(exc.value)
