"""Repository Layer for Custodian AI Evidence Ledger.

Enforces an append-only interface for tamper-evident recording of proctoring events,
Bayesian investigation records, student explanations, and faculty determinations.
Abstracted to allow seamless transition between SQLite (Phase A) and PostgreSQL (Phase B)
purely via connection URL configuration.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import List, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from core.ledger.models import (
    Base,
    Exam,
    ExamSession,
    LedgerCase,
    LedgerContribution,
    LedgerDecision,
    LedgerExplanation,
    LedgerFacultyDecision,
    LedgerHold,
    LedgerObservation,
    LedgerProbe,
    LedgerWarning,
    User,
)
from shared.config import get_settings


class LedgerRepository(ABC):
    """Abstract interface defining all append-only and query methods for the evidence ledger."""

    @abstractmethod
    def init_db(self) -> None:
        """Create database tables if they do not exist."""
        pass

    @abstractmethod
    def create_user(
        self,
        username: str,
        password_hash: str,
        role: str = "student",
        created_at: Optional[float] = None,
    ) -> User:
        """Register a user."""
        pass

    @abstractmethod
    def get_user(self, username: str) -> Optional[User]:
        """Fetch user by username."""
        pass

    @abstractmethod
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Fetch user by primary key id."""
        pass

    @abstractmethod
    def create_exam(
        self,
        title: str,
        description: str = "",
        duration_minutes: int = 60,
        created_at: Optional[float] = None,
    ) -> Exam:
        """Create an exam."""
        pass

    @abstractmethod
    def get_exam(self, exam_id: int) -> Optional[Exam]:
        """Fetch exam by ID."""
        pass

    @abstractmethod
    def create_session(
        self,
        session_id: str,
        student_id: int,
        exam_id: int,
        start_time: Optional[float] = None,
    ) -> ExamSession:
        """Initiate an exam session."""
        pass

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[ExamSession]:
        """Fetch exam session by session_id."""
        pass

    @abstractmethod
    def update_session_status(
        self,
        session_id: str,
        status: str,
        end_time: Optional[float] = None,
    ) -> None:
        """Update session lifecycle status (e.g., active, held, completed)."""
        pass

    @abstractmethod
    def append_observation(
        self,
        session_id: str,
        signal: str,
        confidence: float,
        duration: float = 0.0,
        timestamp: Optional[float] = None,
        metadata_json: str = "{}",
    ) -> LedgerObservation:
        """Append a raw sensor observation."""
        pass

    @abstractmethod
    def get_observations(self, session_id: str) -> List[LedgerObservation]:
        """Fetch all observations for a session ordered by timestamp."""
        pass

    @abstractmethod
    def append_contribution(
        self,
        session_id: str,
        observation_id: int,
        channel: str,
        raw_weight: float,
        held: bool = False,
        released: bool = True,
        resolution_multiplier: float = 1.0,
        final_weight: float = 0.0,
        timestamp: Optional[float] = None,
    ) -> LedgerContribution:
        """Append an observation's weight contribution record."""
        pass

    @abstractmethod
    def get_contributions(self, session_id: str) -> List[LedgerContribution]:
        """Fetch all weight contribution records for a session."""
        pass

    @abstractmethod
    def append_case(
        self,
        case_id: str,
        session_id: str,
        observation_id: Optional[int],
        open_reason: str,
        opened_at: Optional[float] = None,
    ) -> LedgerCase:
        """Record the opening of an investigation case."""
        pass

    @abstractmethod
    def resolve_case(
        self,
        case_id: str,
        resolution: str,
        multiplier: float,
        resolved_at: Optional[float] = None,
    ) -> None:
        """Mark an investigation case as resolved with findings."""
        pass

    @abstractmethod
    def get_cases(self, session_id: str) -> List[LedgerCase]:
        """Fetch all investigation cases opened for a session."""
        pass

    @abstractmethod
    def append_probe(
        self,
        case_id: str,
        probe_name: str,
        cost: float,
        outcome: str,
        prior_json: str,
        posterior_json: str,
        executed_at: Optional[float] = None,
    ) -> LedgerProbe:
        """Log the execution of an investigative probe."""
        pass

    @abstractmethod
    def get_probes(self, case_id: str) -> List[LedgerProbe]:
        """Fetch all probes executed for an investigation case."""
        pass

    @abstractmethod
    def append_decision(
        self,
        session_id: str,
        decision_type: str,
        score: float,
        from_tier: str,
        to_tier: str,
        candidate_tier: str,
        gate_passed: bool,
        reason: str,
        blocked_reason: Optional[str] = None,
        timestamp: Optional[float] = None,
    ) -> LedgerDecision:
        """Record a tier change or blocked escalation decision."""
        pass

    @abstractmethod
    def get_decisions(self, session_id: str) -> List[LedgerDecision]:
        """Fetch all gating and tier decisions for a session."""
        pass

    @abstractmethod
    def append_warning(
        self,
        session_id: str,
        warning_number: int,
        message: str,
        timestamp: Optional[float] = None,
    ) -> LedgerWarning:
        """Record an official warning notification delivered to candidate."""
        pass

    @abstractmethod
    def get_warnings(self, session_id: str) -> List[LedgerWarning]:
        """Fetch all warnings issued to candidate during a session."""
        pass

    @abstractmethod
    def append_explanation(
        self,
        session_id: str,
        explanation_text: str,
        timestamp: Optional[float] = None,
    ) -> LedgerExplanation:
        """Record an explanation submitted by the candidate."""
        pass

    @abstractmethod
    def get_explanations(self, session_id: str) -> List[LedgerExplanation]:
        """Fetch all candidate explanations for a session."""
        pass

    @abstractmethod
    def append_hold(
        self,
        session_id: str,
        evidence_summary: str,
        paused_at: Optional[float] = None,
    ) -> LedgerHold:
        """Record an exam pause and referral for human faculty review."""
        pass

    @abstractmethod
    def get_holds(self, session_id: Optional[str] = None) -> List[LedgerHold]:
        """Fetch hold referrals, optionally filtered by session_id."""
        pass

    @abstractmethod
    def append_faculty_decision(
        self,
        session_id: str,
        faculty_id: int,
        verdict: str,
        notes: str = "",
        timestamp: Optional[float] = None,
    ) -> LedgerFacultyDecision:
        """Record a final human faculty determination."""
        pass

    @abstractmethod
    def get_faculty_decisions(self, session_id: str) -> List[LedgerFacultyDecision]:
        """Fetch faculty decisions for a session."""
        pass

    # Safety assertions: append-only enforcement
    def update_event(self, *args, **kwargs) -> None:
        """Prohibit modifying past evidence ledger entries."""
        raise PermissionError(
            "Ledger events are append-only. Past observations, decisions, and evidence "
            "cannot be modified."
        )

    def delete_event(self, *args, **kwargs) -> None:
        """Prohibit deleting past evidence ledger entries."""
        raise PermissionError(
            "Ledger events are append-only. Past observations, decisions, and evidence "
            "cannot be deleted."
        )


class SQLAlchemyLedgerRepository(LedgerRepository):
    """SQLAlchemy-backed implementation of the append-only ledger repository."""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or get_settings().database_url
        connect_args = {}
        if self.database_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False

        self.engine = create_engine(self.database_url, connect_args=connect_args)
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            expire_on_commit=False,
        )

    def init_db(self) -> None:
        """Create all tables defined in models."""
        Base.metadata.create_all(bind=self.engine)

    def _get_session(self) -> Session:
        return self.SessionLocal()

    def create_user(
        self,
        username: str,
        password_hash: str,
        role: str = "student",
        created_at: Optional[float] = None,
    ) -> User:
        created_at = created_at if created_at is not None else time.time()
        with self._get_session() as session:
            user = User(
                username=username,
                password_hash=password_hash,
                role=role,
                created_at=created_at,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            return user

    def get_user(self, username: str) -> Optional[User]:
        with self._get_session() as session:
            return session.query(User).filter(User.username == username).first()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        with self._get_session() as session:
            return session.query(User).filter(User.id == user_id).first()

    def create_exam(
        self,
        title: str,
        description: str = "",
        duration_minutes: int = 60,
        created_at: Optional[float] = None,
    ) -> Exam:
        created_at = created_at if created_at is not None else time.time()
        with self._get_session() as session:
            exam = Exam(
                title=title,
                description=description,
                duration_minutes=duration_minutes,
                created_at=created_at,
            )
            session.add(exam)
            session.commit()
            session.refresh(exam)
            return exam

    def get_exam(self, exam_id: int) -> Optional[Exam]:
        with self._get_session() as session:
            return session.query(Exam).filter(Exam.id == exam_id).first()

    def create_session(
        self,
        session_id: str,
        student_id: int,
        exam_id: int,
        start_time: Optional[float] = None,
    ) -> ExamSession:
        start_time = start_time if start_time is not None else time.time()
        with self._get_session() as session:
            exam_session = ExamSession(
                id=session_id,
                student_id=student_id,
                exam_id=exam_id,
                start_time=start_time,
                status="active",
            )
            session.add(exam_session)
            session.commit()
            session.refresh(exam_session)
            return exam_session

    def get_session(self, session_id: str) -> Optional[ExamSession]:
        with self._get_session() as session:
            return session.query(ExamSession).filter(ExamSession.id == session_id).first()

    def update_session_status(
        self,
        session_id: str,
        status: str,
        end_time: Optional[float] = None,
    ) -> None:
        with self._get_session() as session:
            exam_session = session.query(ExamSession).filter(ExamSession.id == session_id).first()
            if exam_session:
                exam_session.status = status
                if end_time is not None:
                    exam_session.end_time = end_time
                session.commit()

    def append_observation(
        self,
        session_id: str,
        signal: str,
        confidence: float,
        duration: float = 0.0,
        timestamp: Optional[float] = None,
        metadata_json: str = "{}",
    ) -> LedgerObservation:
        ts = timestamp if timestamp is not None else time.time()
        with self._get_session() as session:
            obs = LedgerObservation(
                session_id=session_id,
                signal=signal,
                confidence=confidence,
                duration=duration,
                timestamp=ts,
                metadata_json=metadata_json,
            )
            session.add(obs)
            session.commit()
            session.refresh(obs)
            return obs

    def get_observations(self, session_id: str) -> List[LedgerObservation]:
        with self._get_session() as session:
            return (
                session.query(LedgerObservation)
                .filter(LedgerObservation.session_id == session_id)
                .order_by(LedgerObservation.timestamp.asc(), LedgerObservation.id.asc())
                .all()
            )

    def append_contribution(
        self,
        session_id: str,
        observation_id: int,
        channel: str,
        raw_weight: float,
        held: bool = False,
        released: bool = True,
        resolution_multiplier: float = 1.0,
        final_weight: float = 0.0,
        timestamp: Optional[float] = None,
    ) -> LedgerContribution:
        ts = timestamp if timestamp is not None else time.time()
        with self._get_session() as session:
            contrib = LedgerContribution(
                session_id=session_id,
                observation_id=observation_id,
                channel=channel,
                raw_weight=raw_weight,
                held=held,
                released=released,
                resolution_multiplier=resolution_multiplier,
                final_weight=final_weight,
                timestamp=ts,
            )
            session.add(contrib)
            session.commit()
            session.refresh(contrib)
            return contrib

    def get_contributions(self, session_id: str) -> List[LedgerContribution]:
        with self._get_session() as session:
            return (
                session.query(LedgerContribution)
                .filter(LedgerContribution.session_id == session_id)
                .order_by(LedgerContribution.timestamp.asc(), LedgerContribution.id.asc())
                .all()
            )

    def append_case(
        self,
        case_id: str,
        session_id: str,
        observation_id: Optional[int],
        open_reason: str,
        opened_at: Optional[float] = None,
    ) -> LedgerCase:
        opened_at = opened_at if opened_at is not None else time.time()
        with self._get_session() as session:
            case = LedgerCase(
                case_id=case_id,
                session_id=session_id,
                observation_id=observation_id,
                open_reason=open_reason,
                is_open=True,
                opened_at=opened_at,
            )
            session.add(case)
            session.commit()
            session.refresh(case)
            return case

    def resolve_case(
        self,
        case_id: str,
        resolution: str,
        multiplier: float,
        resolved_at: Optional[float] = None,
    ) -> None:
        resolved_at = resolved_at if resolved_at is not None else time.time()
        with self._get_session() as session:
            case = session.query(LedgerCase).filter(LedgerCase.case_id == case_id).first()
            if case:
                case.is_open = False
                case.resolution = resolution
                case.multiplier = multiplier
                case.resolved_at = resolved_at
                session.commit()

    def get_cases(self, session_id: str) -> List[LedgerCase]:
        with self._get_session() as session:
            return (
                session.query(LedgerCase)
                .filter(LedgerCase.session_id == session_id)
                .order_by(LedgerCase.opened_at.asc())
                .all()
            )

    def append_probe(
        self,
        case_id: str,
        probe_name: str,
        cost: float,
        outcome: str,
        prior_json: str,
        posterior_json: str,
        executed_at: Optional[float] = None,
    ) -> LedgerProbe:
        executed_at = executed_at if executed_at is not None else time.time()
        with self._get_session() as session:
            probe = LedgerProbe(
                case_id=case_id,
                probe_name=probe_name,
                cost=cost,
                outcome=outcome,
                prior_json=prior_json,
                posterior_json=posterior_json,
                executed_at=executed_at,
            )
            session.add(probe)
            session.commit()
            session.refresh(probe)
            return probe

    def get_probes(self, case_id: str) -> List[LedgerProbe]:
        with self._get_session() as session:
            return (
                session.query(LedgerProbe)
                .filter(LedgerProbe.case_id == case_id)
                .order_by(LedgerProbe.executed_at.asc(), LedgerProbe.id.asc())
                .all()
            )

    def append_decision(
        self,
        session_id: str,
        decision_type: str,
        score: float,
        from_tier: str,
        to_tier: str,
        candidate_tier: str,
        gate_passed: bool,
        reason: str,
        blocked_reason: Optional[str] = None,
        timestamp: Optional[float] = None,
    ) -> LedgerDecision:
        ts = timestamp if timestamp is not None else time.time()
        with self._get_session() as session:
            dec = LedgerDecision(
                session_id=session_id,
                decision_type=decision_type,
                score=score,
                from_tier=from_tier,
                to_tier=to_tier,
                candidate_tier=candidate_tier,
                gate_passed=gate_passed,
                reason=reason,
                blocked_reason=blocked_reason,
                timestamp=ts,
            )
            session.add(dec)
            session.commit()
            session.refresh(dec)
            return dec

    def get_decisions(self, session_id: str) -> List[LedgerDecision]:
        with self._get_session() as session:
            return (
                session.query(LedgerDecision)
                .filter(LedgerDecision.session_id == session_id)
                .order_by(LedgerDecision.timestamp.asc(), LedgerDecision.id.asc())
                .all()
            )

    def append_warning(
        self,
        session_id: str,
        warning_number: int,
        message: str,
        timestamp: Optional[float] = None,
    ) -> LedgerWarning:
        ts = timestamp if timestamp is not None else time.time()
        with self._get_session() as session:
            warn = LedgerWarning(
                session_id=session_id,
                warning_number=warning_number,
                message=message,
                timestamp=ts,
            )
            session.add(warn)
            session.commit()
            session.refresh(warn)
            return warn

    def get_warnings(self, session_id: str) -> List[LedgerWarning]:
        with self._get_session() as session:
            return (
                session.query(LedgerWarning)
                .filter(LedgerWarning.session_id == session_id)
                .order_by(LedgerWarning.timestamp.asc(), LedgerWarning.id.asc())
                .all()
            )

    def append_explanation(
        self,
        session_id: str,
        explanation_text: str,
        timestamp: Optional[float] = None,
    ) -> LedgerExplanation:
        ts = timestamp if timestamp is not None else time.time()
        with self._get_session() as session:
            exp = LedgerExplanation(
                session_id=session_id,
                explanation_text=explanation_text,
                timestamp=ts,
            )
            session.add(exp)
            session.commit()
            session.refresh(exp)
            return exp

    def get_explanations(self, session_id: str) -> List[LedgerExplanation]:
        with self._get_session() as session:
            return (
                session.query(LedgerExplanation)
                .filter(LedgerExplanation.session_id == session_id)
                .order_by(LedgerExplanation.timestamp.asc(), LedgerExplanation.id.asc())
                .all()
            )

    def append_hold(
        self,
        session_id: str,
        evidence_summary: str,
        paused_at: Optional[float] = None,
    ) -> LedgerHold:
        ts = paused_at if paused_at is not None else time.time()
        with self._get_session() as session:
            hold = LedgerHold(
                session_id=session_id,
                paused_at=ts,
                evidence_summary=evidence_summary,
                status="pending",
            )
            session.add(hold)
            session.commit()
            session.refresh(hold)
            return hold

    def get_holds(self, session_id: Optional[str] = None) -> List[LedgerHold]:
        with self._get_session() as session:
            query = session.query(LedgerHold)
            if session_id:
                query = query.filter(LedgerHold.session_id == session_id)
            return query.order_by(LedgerHold.paused_at.asc(), LedgerHold.id.asc()).all()

    def append_faculty_decision(
        self,
        session_id: str,
        faculty_id: int,
        verdict: str,
        notes: str = "",
        timestamp: Optional[float] = None,
    ) -> LedgerFacultyDecision:
        ts = timestamp if timestamp is not None else time.time()
        with self._get_session() as session:
            fdec = LedgerFacultyDecision(
                session_id=session_id,
                faculty_id=faculty_id,
                verdict=verdict,
                notes=notes,
                timestamp=ts,
            )
            session.add(fdec)
            session.commit()
            session.refresh(fdec)
            return fdec

    def get_faculty_decisions(self, session_id: str) -> List[LedgerFacultyDecision]:
        with self._get_session() as session:
            return (
                session.query(LedgerFacultyDecision)
                .filter(LedgerFacultyDecision.session_id == session_id)
                .order_by(LedgerFacultyDecision.timestamp.asc(), LedgerFacultyDecision.id.asc())
                .all()
            )
