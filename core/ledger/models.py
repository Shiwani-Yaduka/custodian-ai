"""SQLAlchemy ORM Data Models for Custodian AI Evidence Ledger.

Append-only tables for tamper-evident recording of proctoring events,
investigator findings, candidate explanations, and faculty determinations.
"""

from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    """System user record (student or faculty member)."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(32), nullable=False, default="student")  # "student" or "faculty"
    created_at = Column(Float, nullable=False)


class Exam(Base):
    """Exam metadata definition."""

    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(128), nullable=False)
    description = Column(Text, default="")
    duration_minutes = Column(Integer, default=60, nullable=False)
    created_at = Column(Float, nullable=False)


class ExamSession(Base):
    """Candidate exam session."""

    __tablename__ = "sessions"

    id = Column(String(64), primary_key=True)  # session_id
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=True)
    status = Column(String(32), nullable=False, default="active")  # "active", "held", "completed"


class LedgerObservation(Base):
    """Append-only raw observation record."""

    __tablename__ = "observations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), nullable=False, index=True)
    signal = Column(String(64), nullable=False)
    timestamp = Column(Float, nullable=False)
    duration = Column(Float, nullable=False, default=0.0)
    confidence = Column(Float, nullable=False)
    metadata_json = Column(Text, default="{}")


class LedgerContribution(Base):
    """Append-only observation weight contribution record."""

    __tablename__ = "contributions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), nullable=False, index=True)
    observation_id = Column(Integer, nullable=False)
    channel = Column(String(32), nullable=False)
    raw_weight = Column(Float, nullable=False)
    held = Column(Boolean, nullable=False, default=False)
    released = Column(Boolean, nullable=False, default=True)
    resolution_multiplier = Column(Float, nullable=False, default=1.0)
    final_weight = Column(Float, nullable=False)
    timestamp = Column(Float, nullable=False)


class LedgerCase(Base):
    """Append-only investigation case record."""

    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(64), unique=True, nullable=False, index=True)
    session_id = Column(String(64), nullable=False, index=True)
    observation_id = Column(Integer, nullable=True)
    open_reason = Column(Text, nullable=False)
    is_open = Column(Boolean, nullable=False, default=True)
    resolution = Column(String(32), nullable=True)
    multiplier = Column(Float, nullable=True)
    opened_at = Column(Float, nullable=False)
    resolved_at = Column(Float, nullable=True)


class LedgerProbe(Base):
    """Append-only probe execution log."""

    __tablename__ = "probes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(64), nullable=False, index=True)
    probe_name = Column(String(64), nullable=False)
    cost = Column(Float, nullable=False)
    outcome = Column(String(64), nullable=False)
    prior_json = Column(Text, nullable=False)
    posterior_json = Column(Text, nullable=False)
    executed_at = Column(Float, nullable=False)


class LedgerDecision(Base):
    """Append-only gating decision record (approved escalation or blocked escalation)."""

    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), nullable=False, index=True)
    decision_type = Column(String(32), nullable=False)  # "TIER_TRANSITION" or "BLOCKED_ESCALATION"
    score = Column(Float, nullable=False)
    from_tier = Column(String(32), nullable=False)
    to_tier = Column(String(32), nullable=False)
    candidate_tier = Column(String(32), nullable=False)
    gate_passed = Column(Boolean, nullable=False)
    reason = Column(Text, nullable=False)
    blocked_reason = Column(Text, nullable=True)
    timestamp = Column(Float, nullable=False)


class LedgerWarning(Base):
    """Append-only student warning notification log."""

    __tablename__ = "warnings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), nullable=False, index=True)
    warning_number = Column(Integer, nullable=False)
    message = Column(Text, nullable=False)
    timestamp = Column(Float, nullable=False)


class LedgerExplanation(Base):
    """Append-only student submitted explanation text."""

    __tablename__ = "student_explanations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), nullable=False, index=True)
    explanation_text = Column(Text, nullable=False)
    timestamp = Column(Float, nullable=False)


class LedgerHold(Base):
    """Append-only exam pause-and-hold referral for human faculty review."""

    __tablename__ = "holds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), nullable=False, index=True)
    paused_at = Column(Float, nullable=False)
    evidence_summary = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="pending")  # "pending", "resolved"


class LedgerFacultyDecision(Base):
    """Append-only human faculty determination."""

    __tablename__ = "faculty_decisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), nullable=False, index=True)
    faculty_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    verdict = Column(String(32), nullable=False)  # "cleared", "warning_stands", "refer_onward"
    notes = Column(Text, default="")
    timestamp = Column(Float, nullable=False)
