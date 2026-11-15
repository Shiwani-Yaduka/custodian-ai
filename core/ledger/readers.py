"""Ledger Reader Services for Custodian AI.

Generates:
1. Student-Facing Record: Polite, transparent, plain-language audit trail of all
   observations, notices, and submitted student explanations.
2. Faculty-Facing Audit Timeline: Technical audit trail of risk scores over time,
   Bayesian investigator reasoning, executed probes, stub clip markers, and hold referrals.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from core.ledger.repository import LedgerRepository


class StudentTimelineEvent(BaseModel):
    """A single human-readable event on the student's audit record."""

    timestamp: float
    event_type: str  # "notice", "explanation", "status_change", "observation", "info"
    description: str
    title: Optional[str] = None
    severity: Optional[str] = "info"


class StudentRecord(BaseModel):
    """Complete student-facing audit trail."""

    session_id: str
    status: str
    start_time: float
    events: List[StudentTimelineEvent] = Field(default_factory=list)
    observations: List[StudentTimelineEvent] = Field(default_factory=list)
    summary: str
    plain_text_summary: str = ""
    disclaimer: str = (
        "Custodian AI records evidence under uncertainty and never takes automated disciplinary "
        "or grading action. You have the right to inspect this record and submit explanations."
    )

    def to_plain_text(self) -> str:
        """Render the student record into a clean, readable text document."""
        lines = [
            f"=== Exam Session Evidence Record (Session: {self.session_id}) ===",
            f"Session Status: {self.status.upper()}",
            f"Session Summary: {self.summary}",
            "-" * 60,
            "Chronological Timeline of Observations and Notices:",
        ]
        for ev in self.events:
            lines.append(f"[{ev.timestamp:8.1f}s] [{ev.event_type.upper()}] {ev.description}")
        lines.append("-" * 60)
        lines.append(f"Student Rights Notice: {self.disclaimer}")
        return "\n".join(lines)


class FacultyProbeDetail(BaseModel):
    """Faculty-facing probe execution audit record."""

    probe_name: str
    cost: float
    outcome: str
    prior: Dict[str, float]
    posterior: Dict[str, float]
    executed_at: float


class FacultyCaseDetail(BaseModel):
    """Faculty-facing investigation case audit record."""

    case_id: str
    open_reason: str
    is_open: bool
    resolution: Optional[str]
    multiplier: Optional[float]
    opened_at: float
    resolved_at: Optional[float]
    probes: List[FacultyProbeDetail] = Field(default_factory=list)


class FacultyRiskPoint(BaseModel):
    """Risk and gating event marker on faculty timeline."""

    timestamp: float
    score: float
    from_tier: str
    to_tier: str
    candidate_tier: str
    gate_passed: bool
    reason: str
    blocked_reason: Optional[str] = None
    stub_clip_marker: Optional[str] = None


class FacultyTimeline(BaseModel):
    """Comprehensive technical audit timeline for faculty review."""

    session_id: str
    status: str
    start_time: float
    peak_risk_score: float
    risk_points: List[FacultyRiskPoint] = Field(default_factory=list)
    investigation_cases: List[FacultyCaseDetail] = Field(default_factory=list)
    warnings_issued: List[Dict[str, Any]] = Field(default_factory=list)
    student_explanations: List[Dict[str, Any]] = Field(default_factory=list)
    hold_summary: Optional[str] = None
    faculty_decisions: List[Dict[str, Any]] = Field(default_factory=list)
    observations: List[Dict[str, Any]] = Field(default_factory=list)
    recommendation: str


def build_student_record(session_id: str, repo: LedgerRepository) -> StudentRecord:
    """Compile the transparent student-facing audit trail."""
    session = repo.get_session(session_id)
    status = session.status if session else "unknown"
    start_time = session.start_time if session else 0.0

    events: List[StudentTimelineEvent] = []

    # Include notices (warnings)
    warnings = repo.get_warnings(session_id)
    for w in warnings:
        events.append(
            StudentTimelineEvent(
                timestamp=w.timestamp,
                event_type="notice",
                title=f"Official Notice #{w.warning_number}",
                description=w.message,
                severity="warning" if w.warning_number == 1 else "alert",
            )
        )

    # Include explanations submitted by the student
    explanations = repo.get_explanations(session_id)
    for exp in explanations:
        events.append(
            StudentTimelineEvent(
                timestamp=exp.timestamp,
                event_type="explanation",
                title="Student Explanation Recorded",
                description=f'You submitted explanation: "{exp.explanation_text}"',
                severity="info",
            )
        )

    # Include holds if session was referred
    holds = repo.get_holds(session_id)
    for h in holds:
        events.append(
            StudentTimelineEvent(
                timestamp=h.paused_at,
                event_type="status_change",
                title="Human Review Referral",
                description=(
                    "Exam paused and forwarded to faculty for human review. "
                    "No automatic penalty has been applied."
                ),
                severity="alert",
            )
        )

    # Sort core decision events chronologically
    events.sort(key=lambda e: e.timestamp)

    # Extract sensory observations from ledger (coalescing continuous episodes)
    obs_events: List[StudentTimelineEvent] = []
    try:
        raw_obs = repo.get_observations(session_id)
        # Group adjacent 1-second samples of the same signal into coherent episodes
        episodes: List[List[Any]] = []
        for obs in raw_obs:
            if not episodes:
                episodes.append([obs])
            else:
                last_ep = episodes[-1]
                last_obs = last_ep[-1]
                # If same signal and occurred within 2.5s of prior sample, group into same episode
                if obs.signal == last_obs.signal and (obs.timestamp - last_obs.timestamp) <= 2.5:
                    last_ep.append(obs)
                else:
                    episodes.append([obs])

        for ep in episodes:
            peak_obs = max(ep, key=lambda o: o.duration)
            if peak_obs.duration >= 2.0:
                sig_name = peak_obs.signal.replace("_", " ").title()
                obs_events.append(
                    StudentTimelineEvent(
                        timestamp=ep[0].timestamp,
                        event_type="observation",
                        title=f"Observation: {sig_name}",
                        description=(
                            f"Sensory detector noted {sig_name} for {peak_obs.duration:.1f}s "
                            f"(confidence: {int(peak_obs.confidence * 100)}%)."
                        ),
                        severity="info" if peak_obs.duration < 8.0 else "warning",
                    )
                )
    except Exception:
        pass

    obs_events.sort(key=lambda e: e.timestamp)

    # Generate constructive plain-language summary
    if holds:
        summary = (
            "Your exam was paused after two notices were shown and referred to a faculty "
            "member for personal review. Your answers are saved."
        )
    elif len(warnings) == 2:
        summary = (
            "Two notices were issued during your exam. An extra 10 minutes was added to your "
            "timer off-the-clock."
        )
    elif len(warnings) == 1:
        summary = (
            "One notice was issued during your exam. You were able to continue without "
            "interruption."
        )
    elif len(explanations) > 0:
        summary = (
            f"{len(explanations)} student explanation(s) recorded in your verified ledger. "
            "No disciplinary notices or interventions were issued."
        )
    elif len(obs_events) > 0:
        summary = (
            f"{len(obs_events)} sensory observation(s) noted under uncertainty. "
            "Risk score remained low (CLEAR). No disciplinary notices were issued."
        )
    else:
        summary = "No notices or interventions occurred during your exam session."

    return StudentRecord(
        session_id=session_id,
        status=status,
        start_time=start_time,
        events=events,
        observations=obs_events,
        summary=summary,
        plain_text_summary=summary,
    )


def build_faculty_timeline(session_id: str, repo: LedgerRepository) -> FacultyTimeline:
    """Compile comprehensive technical audit trail for faculty review."""
    session = repo.get_session(session_id)
    status = session.status if session else "unknown"
    start_time = session.start_time if session else 0.0

    decisions = repo.get_decisions(session_id)
    peak_score = max([d.score for d in decisions], default=0.0)

    # Risk points with stub clip markers around score-raising events
    risk_points: List[FacultyRiskPoint] = []
    for d in decisions:
        clip_marker = None
        if d.score >= 45.0:  # Score-raising event in WARNED or above
            clip_marker = f"stub-clip-{session_id}-{int(d.timestamp)}"

        risk_points.append(
            FacultyRiskPoint(
                timestamp=d.timestamp,
                score=d.score,
                from_tier=d.from_tier,
                to_tier=d.to_tier,
                candidate_tier=d.candidate_tier,
                gate_passed=d.gate_passed,
                reason=d.reason,
                blocked_reason=d.blocked_reason,
                stub_clip_marker=clip_marker,
            )
        )

    # Investigation cases and probes
    cases = repo.get_cases(session_id)
    case_details: List[FacultyCaseDetail] = []
    for c in cases:
        probes = repo.get_probes(c.case_id)
        probe_details: List[FacultyProbeDetail] = []
        for p in probes:
            try:
                prior = json.loads(p.prior_json)
                posterior = json.loads(p.posterior_json)
            except Exception:
                prior, posterior = {}, {}
            probe_details.append(
                FacultyProbeDetail(
                    probe_name=p.probe_name,
                    cost=p.cost,
                    outcome=p.outcome,
                    prior=prior,
                    posterior=posterior,
                    executed_at=p.executed_at,
                )
            )

        case_details.append(
            FacultyCaseDetail(
                case_id=c.case_id,
                open_reason=c.open_reason,
                is_open=c.is_open,
                resolution=c.resolution,
                multiplier=c.multiplier,
                opened_at=c.opened_at,
                resolved_at=c.resolved_at,
                probes=probe_details,
            )
        )

    # Warnings issued
    warnings = repo.get_warnings(session_id)
    warnings_issued = [
        {"warning_number": w.warning_number, "message": w.message, "timestamp": w.timestamp}
        for w in warnings
    ]

    # Explanations
    explanations = repo.get_explanations(session_id)
    student_explanations = [
        {"text": exp.explanation_text, "timestamp": exp.timestamp}
        for exp in explanations
    ]

    # Holds
    holds = repo.get_holds(session_id)
    hold_summary = holds[0].evidence_summary if holds else None

    # Faculty decisions
    fdecs = repo.get_faculty_decisions(session_id)
    faculty_decisions = [
        {
            "faculty_id": fd.faculty_id,
            "verdict": fd.verdict,
            "notes": fd.notes,
            "timestamp": fd.timestamp,
        }
        for fd in fdecs
    ]

    # Observations
    raw_obs = repo.get_observations(session_id)
    observations_list = [
        {
            "signal": o.signal,
            "duration": o.duration,
            "confidence": o.confidence,
            "timestamp": o.timestamp,
        }
        for o in raw_obs
    ]

    # Recommendation
    if holds:
        recommendation = (
            "Session was held following multiple warnings and corroborated deliberate findings. "
            "Inspect evidence timeline, student explanation, and recorded stub clips before "
            "deciding."
        )
    elif peak_score >= 45.0:
        recommendation = (
            "Minor concerns observed and addressed with warning notices. Review suggested."
        )
    else:
        recommendation = (
            "Exam proceeded within acceptable baseline variations. No intervention needed."
        )

    return FacultyTimeline(
        session_id=session_id,
        status=status,
        start_time=start_time,
        peak_risk_score=peak_score,
        risk_points=risk_points,
        investigation_cases=case_details,
        warnings_issued=warnings_issued,
        student_explanations=student_explanations,
        hold_summary=hold_summary,
        faculty_decisions=faculty_decisions,
        observations=observations_list,
        recommendation=recommendation,
    )
