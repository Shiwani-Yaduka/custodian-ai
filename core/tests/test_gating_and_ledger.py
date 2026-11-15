"""Comprehensive Tests for Escalation Gating, Safety Invariants, and Evidence Ledger.

Validates AGENTS.md Sections 5, 7, and 10:
- Gate evaluations: WARNED (2 channels), ELEVATED (2 channels + warning 1),
  HELD (2 channels + deliberate P>=0.85 + 2 warnings).
- Fallback hierarchy for blocked escalations with plain-language reasons.
- Safety invariants: only 5 sanctioned system outcomes exist, with an explicit blacklist
  guaranteeing no automated failures or mark penalties.
- Warning generation: polite, respectful text free from accusing vocabulary.
- Append-only repository enforcement: rejection of updates/deletions on ledger events.
- Student-facing and faculty-facing audit timeline compilation.
"""

import itertools

import pytest

from core.gating import check_tier_gate, evaluate_escalation_gate
from core.ledger import (
    SQLAlchemyLedgerRepository,
    build_faculty_timeline,
    build_student_record,
)
from core.models import Tier
from core.safety import (
    PROHIBITED_ACTIONS,
    SystemAction,
    determine_system_action,
    verify_all_system_outcomes,
)
from core.warnings import (
    ACCUSATORY_WORDS_BLACKLIST,
    format_warning_message,
)


@pytest.fixture
def mem_repo() -> SQLAlchemyLedgerRepository:
    """Provide an isolated, clean in-memory SQLite ledger repository for each test."""
    repo = SQLAlchemyLedgerRepository(database_url="sqlite:///:memory:")
    repo.init_db()
    return repo


class TestEscalationGating:
    """Verify procedural gates guarding each tier transition."""

    def test_clear_and_watching_require_no_gate(self):
        """CLEAR and WATCHING require 0 sensory corroboration or warnings."""
        passed, reason, _ = check_tier_gate(
            tier=Tier.CLEAR,
            contributing_channels=[],
            warnings_shown_count=0,
            deliberate_cases_p85_count=0,
        )
        assert passed is True

        passed, reason, _ = check_tier_gate(
            tier=Tier.WATCHING,
            contributing_channels=["camera"],
            warnings_shown_count=0,
            deliberate_cases_p85_count=0,
        )
        assert passed is True

    def test_single_channel_cannot_reach_warned_or_beyond(self):
        """Even if score is high (e.g. 50), single channel cannot breach WARNED."""
        decision = evaluate_escalation_gate(
            candidate_tier=Tier.WARNED,
            current_tier=Tier.WATCHING,
            score=50.0,
            contributing_channels=["camera"],
            warnings_shown_count=0,
            deliberate_cases_p85_count=0,
        )
        assert decision.approved is False
        assert decision.candidate_tier == Tier.WARNED
        assert decision.target_tier == Tier.WATCHING
        assert "Gate blocked" in decision.blocked_reason
        assert "at least 2 independent sensory channels" in decision.blocked_reason

    def test_single_channel_blocked_at_elevated_and_held(self):
        """Single channel cannot reach ELEVATED or HELD."""
        for candidate in (Tier.ELEVATED, Tier.HELD):
            decision = evaluate_escalation_gate(
                candidate_tier=candidate,
                current_tier=Tier.WATCHING,
                score=85.0,
                contributing_channels=["camera"],
                warnings_shown_count=2,
                deliberate_cases_p85_count=1,
            )
            assert decision.approved is False
            assert decision.target_tier == Tier.WATCHING

    def test_elevated_requires_two_channels_and_prior_warning(self):
        """ELEVATED gate fails if 1st warning was not shown yet."""
        # 2 channels, but warnings_shown_count = 0
        decision = evaluate_escalation_gate(
            candidate_tier=Tier.ELEVATED,
            current_tier=Tier.WARNED,
            score=68.0,
            contributing_channels=["camera", "exam_window"],
            warnings_shown_count=0,
            deliberate_cases_p85_count=0,
        )
        assert decision.approved is False
        # Highest allowed tier whose gate passes is WARNED (2 channels)
        assert decision.target_tier == Tier.WARNED
        assert "requires first warning to have been shown" in decision.blocked_reason

        # When warning has been shown, it passes
        decision_approved = evaluate_escalation_gate(
            candidate_tier=Tier.ELEVATED,
            current_tier=Tier.WARNED,
            score=68.0,
            contributing_channels=["camera", "exam_window"],
            warnings_shown_count=1,
            deliberate_cases_p85_count=0,
        )
        assert decision_approved.approved is True
        assert decision_approved.target_tier == Tier.ELEVATED

    def test_held_requires_all_three_prerequisites_exhaustively(self):
        """HELD requires: 2 channels AND deliberate case (P>=0.85) AND 2 prior warnings."""
        # Baseline complete condition:
        complete_args = {
            "candidate_tier": Tier.HELD,
            "current_tier": Tier.ELEVATED,
            "score": 88.0,
            "contributing_channels": ["camera", "microphone"],
            "warnings_shown_count": 2,
            "deliberate_cases_p85_count": 1,
        }

        # 1. Approved when all hold
        dec = evaluate_escalation_gate(**complete_args)
        assert dec.approved is True
        assert dec.target_tier == Tier.HELD

        # 2. Missing deliberate case
        args_no_deliberate = dict(complete_args, deliberate_cases_p85_count=0)
        dec = evaluate_escalation_gate(**args_no_deliberate)
        assert dec.approved is False
        assert dec.target_tier == Tier.ELEVATED
        assert "DELIBERATE with posterior >= 0.85" in dec.blocked_reason

        # 3. Missing 2nd warning (only 1 warning shown)
        args_one_warning = dict(complete_args, warnings_shown_count=1)
        dec = evaluate_escalation_gate(**args_one_warning)
        assert dec.approved is False
        assert dec.target_tier == Tier.ELEVATED
        assert "two prior warnings shown" in dec.blocked_reason

        # 4. Missing both warnings (0 warnings shown)
        args_zero_warnings = dict(complete_args, warnings_shown_count=0)
        dec = evaluate_escalation_gate(**args_zero_warnings)
        assert dec.approved is False
        # Falls back to WARNED because warnings=0 fails ELEVATED too
        assert dec.target_tier == Tier.WARNED

        # 5. Missing 2nd channel (only 1 channel)
        args_one_channel = dict(complete_args, contributing_channels=["camera"])
        dec = evaluate_escalation_gate(**args_one_channel)
        assert dec.approved is False
        # Falls back to WATCHING because WARNED and ELEVATED also require 2 channels
        assert dec.target_tier == Tier.WATCHING

    def test_natural_decay_deescalation_always_approved(self):
        """Score decay (moving down the tier ladder) is always approved without gates."""
        decision = evaluate_escalation_gate(
            candidate_tier=Tier.CLEAR,
            current_tier=Tier.WARNED,
            score=15.0,
            contributing_channels=["camera"],
            warnings_shown_count=1,
            deliberate_cases_p85_count=0,
        )
        assert decision.approved is True
        assert decision.target_tier == Tier.CLEAR


class TestSafetyProofAndInvariants:
    """Formally prove no automatic failing, disqualification, or marks deductions occur."""

    def test_all_system_outcomes_strictly_sanctioned(self):
        """Verify the closed set of all possible outcomes."""
        all_actions = verify_all_system_outcomes()
        expected = {
            SystemAction.NOTHING_SHOWN,
            SystemAction.INTERNAL_NOTE,
            SystemAction.FIRST_WARNING,
            SystemAction.SECOND_WARNING_TIME_ADDED,
            SystemAction.PAUSE_AND_HOLD_FOR_HUMAN,
        }
        assert all_actions == expected

    def test_prohibited_actions_disjoint_from_system_actions(self):
        """Assert no prohibited punitive action is present in the system action set."""
        system_values = {a.value for a in SystemAction}
        intersection = system_values.intersection(PROHIBITED_ACTIONS)
        assert len(intersection) == 0, f"Prohibited actions found: {intersection}"

    def test_exhaustive_permutation_safety_proof(self):
        """Exhaustively verify all permutations of inputs map solely to sanctioned actions."""
        tiers = [Tier.CLEAR, Tier.WATCHING, Tier.WARNED, Tier.ELEVATED, Tier.HELD]
        channels_options = [
            [],
            ["camera"],
            ["camera", "microphone"],
            ["camera", "exam_window", "device"],
        ]
        warnings_options = [0, 1, 2, 3]
        deliberate_options = [0, 1, 2]
        scores = [0.0, 20.0, 35.0, 50.0, 70.0, 95.0]

        for cand, curr, ch, w, d, score in itertools.product(
            tiers, tiers, channels_options, warnings_options, deliberate_options, scores
        ):
            decision = evaluate_escalation_gate(
                candidate_tier=cand,
                current_tier=curr,
                score=score,
                contributing_channels=ch,
                warnings_shown_count=w,
                deliberate_cases_p85_count=d,
            )
            # Check target tier is valid
            assert decision.target_tier in tiers
            action = determine_system_action(decision.target_tier)
            assert action in SystemAction
            assert action.value not in PROHIBITED_ACTIONS


class TestWarningMessages:
    """Verify warning notifications are non-accusing, clear, and informative."""

    def test_warning_message_formatting(self):
        msg = format_warning_message(
            signal_name="face_absent",
            duration=35.0,
            warning_number=1,
        )
        assert "Notice 1: Your face was not visible" in msg
        assert "approximately 35 seconds" in msg
        assert "You may submit an explanation" in msg

    def test_second_warning_mentions_time_added(self):
        msg = format_warning_message(
            signal_name="tab_hidden",
            duration=12.0,
            warning_number=2,
        )
        assert "Second Notice (10 Minutes Added to Clock)" in msg
        assert "tab was minimized or switched away" in msg

    def test_accusatory_blacklist_enforcement(self):
        """Confirm that if any blacklisted word appears in custom context, it is rejected."""
        for word in ACCUSATORY_WORDS_BLACKLIST:
            with pytest.raises(ValueError, match="Accusatory word"):
                format_warning_message(
                    signal_name="face_absent",
                    duration=20.0,
                    warning_number=1,
                    custom_context=f"Suspected {word}",
                )


class TestEvidenceLedgerAppendOnlyRepository:
    """Verify the append-only evidence ledger repository and readers."""

    def test_schema_bootstrap_and_session_lifecycle(self, mem_repo: SQLAlchemyLedgerRepository):
        user = mem_repo.create_user("student1", "hashed_pwd", role="student")
        assert user.id is not None

        exam = mem_repo.create_exam("Midterm Exam", duration_minutes=90)
        assert exam.id is not None

        sess = mem_repo.create_session("sess_001", student_id=user.id, exam_id=exam.id)
        assert sess.status == "active"

        mem_repo.update_session_status("sess_001", status="held", end_time=1000.0)
        updated = mem_repo.get_session("sess_001")
        assert updated.status == "held"
        assert updated.end_time == 1000.0

    def test_append_and_query_observations_and_contributions(
        self, mem_repo: SQLAlchemyLedgerRepository
    ):
        mem_repo.create_user("student1", "hashed_pwd")
        mem_repo.create_exam("Test Exam")
        mem_repo.create_session("sess_002", student_id=1, exam_id=1)

        obs = mem_repo.append_observation(
            session_id="sess_002",
            signal="face_absent",
            confidence=0.92,
            duration=22.0,
            timestamp=10.0,
        )
        assert obs.id is not None

        contrib = mem_repo.append_contribution(
            session_id="sess_002",
            observation_id=obs.id,
            channel="camera",
            raw_weight=14.5,
            held=False,
            released=True,
            resolution_multiplier=1.0,
            final_weight=14.5,
            timestamp=10.0,
        )
        assert contrib.id is not None

        all_obs = mem_repo.get_observations("sess_002")
        assert len(all_obs) == 1
        assert all_obs[0].signal == "face_absent"

    def test_investigation_cases_and_probes(self, mem_repo: SQLAlchemyLedgerRepository):
        mem_repo.create_user("student1", "pwd")
        mem_repo.create_exam("Ex")
        mem_repo.create_session("sess_003", student_id=1, exam_id=1)

        case = mem_repo.append_case(
            case_id="case_101",
            session_id="sess_003",
            observation_id=1,
            open_reason="Ambiguous camera telemetry",
            opened_at=50.0,
        )
        assert case.is_open is True

        probe = mem_repo.append_probe(
            case_id="case_101",
            probe_name="device_telemetry_check",
            cost=0.0,
            outcome="hardware_pause",
            prior_json='{"ordinary": 0.5, "technical": 0.3, "deliberate": 0.2}',
            posterior_json='{"ordinary": 0.1, "technical": 0.85, "deliberate": 0.05}',
            executed_at=51.0,
        )
        assert probe.id is not None

        mem_repo.resolve_case(
            case_id="case_101",
            resolution="technical",
            multiplier=0.0,
            resolved_at=52.0,
        )

        cases = mem_repo.get_cases("sess_003")
        assert len(cases) == 1
        assert cases[0].is_open is False
        assert cases[0].resolution == "technical"
        assert cases[0].multiplier == 0.0

        probes = mem_repo.get_probes("case_101")
        assert len(probes) == 1
        assert probes[0].probe_name == "device_telemetry_check"

    def test_append_only_immutability_enforcement(self, mem_repo: SQLAlchemyLedgerRepository):
        """Verify repository explicitly forbids event modification or deletion."""
        with pytest.raises(PermissionError, match="Ledger events are append-only"):
            mem_repo.update_event(event_id=1, new_data={})

        with pytest.raises(PermissionError, match="Ledger events are append-only"):
            mem_repo.delete_event(event_id=1)

    def test_student_and_faculty_readers(self, mem_repo: SQLAlchemyLedgerRepository):
        """Simulate a realistic sequence and verify compiled student/faculty timelines."""
        mem_repo.create_user("student1", "hashed", role="student")
        mem_repo.create_user("faculty1", "hashed", role="faculty")
        mem_repo.create_exam("Final Exam", duration_minutes=120)
        mem_repo.create_session("sess_demo", student_id=1, exam_id=1, start_time=100.0)

        # 1. First warning
        mem_repo.append_warning(
            session_id="sess_demo",
            warning_number=1,
            message="Notice 1: Your face was not visible for approximately 25 seconds.",
            timestamp=150.0,
        )

        # 2. Student explanation
        mem_repo.append_explanation(
            session_id="sess_demo",
            explanation_text="My pencil dropped on the floor and I had to pick it up.",
            timestamp=165.0,
        )

        # 3. Blocked escalation decision recorded
        mem_repo.append_decision(
            session_id="sess_demo",
            decision_type="BLOCKED_ESCALATION",
            score=48.0,
            from_tier="WATCHING",
            to_tier="WATCHING",
            candidate_tier="WARNED",
            gate_passed=False,
            reason="Escalation to WARNED was BLOCKED. Candidate held at WATCHING.",
            blocked_reason=(
                "Gate blocked: First warning requires at least 2 independent sensory channels."
            ),
            timestamp=180.0,
        )

        # 4. Approved escalation to WARNED with 2 channels
        mem_repo.append_decision(
            session_id="sess_demo",
            decision_type="TIER_TRANSITION",
            score=52.0,
            from_tier="WATCHING",
            to_tier="WARNED",
            candidate_tier="WARNED",
            gate_passed=True,
            reason=(
                "Escalation to WARNED approved. Gate passed: 2 independent channels contributing."
            ),
            blocked_reason=None,
            timestamp=210.0,
        )

        # 5. Hold referral
        mem_repo.append_hold(
            session_id="sess_demo",
            evidence_summary="Corroborated notes and phone signals with deliberate posterior 0.88.",
            paused_at=290.0,
        )

        # 6. Faculty verdict
        mem_repo.append_faculty_decision(
            session_id="sess_demo",
            faculty_id=2,
            verdict="warning_stands",
            notes=(
                "Reviewed student explanation; student dropped pencil, warning stands but no "
                "further action."
            ),
            timestamp=350.0,
        )

        # Build Student Record
        student_rec = build_student_record("sess_demo", mem_repo)
        assert student_rec.session_id == "sess_demo"
        assert len(student_rec.events) == 3  # warning, explanation, hold
        plain_text = student_rec.to_plain_text()
        assert "Notice 1: Your face was not visible" in plain_text
        assert "My pencil dropped on the floor" in plain_text
        assert "Exam paused and forwarded to faculty" in plain_text
        assert "never takes automated disciplinary" in student_rec.disclaimer

        # Build Faculty Timeline
        faculty_tl = build_faculty_timeline("sess_demo", mem_repo)
        assert faculty_tl.session_id == "sess_demo"
        assert faculty_tl.peak_risk_score == 52.0
        assert len(faculty_tl.risk_points) == 2
        # Verify stub clip marker was attached to score-raising event
        assert faculty_tl.risk_points[1].stub_clip_marker == "stub-clip-sess_demo-210"
        assert len(faculty_tl.warnings_issued) == 1
        assert len(faculty_tl.student_explanations) == 1
        assert faculty_tl.hold_summary is not None
        assert faculty_tl.faculty_decisions[0]["verdict"] == "warning_stands"
