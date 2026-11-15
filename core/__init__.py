"""Custodian AI — Core Logic Package.

Pure Python implementation of:
- Risk accumulation, decay, and corroboration engine
- Bayesian investigation models and probes
- Safety gating and escalation criteria
- Safety invariants and closed system action sets
- Accusation-free warning text generators
- Append-only evidence ledger models and repository
- Student and faculty ledger readers
- Sensory feature processing and calibration
- In-process unified execution pipeline

Zero HTTP or web dependencies.
"""

from core.calibration import CalibrationBaseline, CalibrationDetector, FeatureBatch
from core.gating import GatingDecision, check_tier_gate, evaluate_escalation_gate
from core.investigator import (
    CaseResolution,
    Hypothesis,
    InvestigationCase,
    InvestigatorAgent,
    InvestigatorPolicy,
    ProbeConfig,
    ProbeRecord,
    ProbeRunner,
    ResolutionStatus,
    ScriptedProbeRunner,
    SimulatedProbeRunner,
    bayes_update,
    calculate_expected_information_gain,
    kl_divergence,
    load_investigator_policy,
)
from core.ledger import (
    Base,
    Exam,
    ExamSession,
    FacultyCaseDetail,
    FacultyProbeDetail,
    FacultyRiskPoint,
    FacultyTimeline,
    LedgerCase,
    LedgerContribution,
    LedgerDecision,
    LedgerExplanation,
    LedgerFacultyDecision,
    LedgerHold,
    LedgerObservation,
    LedgerProbe,
    LedgerRepository,
    LedgerWarning,
    SQLAlchemyLedgerRepository,
    StudentRecord,
    StudentTimelineEvent,
    User,
    build_faculty_timeline,
    build_student_record,
)
from core.models import (
    ChannelState,
    Observation,
    ProcessedObservation,
    RiskState,
    Tier,
)
from core.pipeline import InProcessPipeline, PipelineResult, run_in_process_pipeline
from core.policy import RiskPolicy, SignalDefinition, load_policy
from core.risk import RiskEngine
from core.safety import (
    PROHIBITED_ACTIONS,
    SystemAction,
    determine_system_action,
    verify_all_system_outcomes,
)
from core.state import InMemoryStateStore, StateStore
from core.warnings import (
    ACCUSATORY_WORDS_BLACKLIST,
    SIGNAL_WARNING_TEMPLATES,
    format_warning_message,
)

__version__ = "0.1.0"

__all__ = [
    "ACCUSATORY_WORDS_BLACKLIST",
    "Base",
    "CalibrationBaseline",
    "CalibrationDetector",
    "CaseResolution",
    "ChannelState",
    "Exam",
    "ExamSession",
    "FacultyCaseDetail",
    "FacultyProbeDetail",
    "FacultyRiskPoint",
    "FacultyTimeline",
    "FeatureBatch",
    "GatingDecision",
    "Hypothesis",
    "InMemoryStateStore",
    "InProcessPipeline",
    "InvestigationCase",
    "InvestigatorAgent",
    "InvestigatorPolicy",
    "LedgerCase",
    "LedgerContribution",
    "LedgerDecision",
    "LedgerExplanation",
    "LedgerFacultyDecision",
    "LedgerHold",
    "LedgerObservation",
    "LedgerProbe",
    "LedgerRepository",
    "LedgerWarning",
    "Observation",
    "PROHIBITED_ACTIONS",
    "PipelineResult",
    "ProbeConfig",
    "ProbeRecord",
    "ProbeRunner",
    "ProcessedObservation",
    "ResolutionStatus",
    "RiskEngine",
    "RiskPolicy",
    "RiskState",
    "SIGNAL_WARNING_TEMPLATES",
    "SQLAlchemyLedgerRepository",
    "ScriptedProbeRunner",
    "SignalDefinition",
    "SimulatedProbeRunner",
    "StateStore",
    "StudentRecord",
    "StudentTimelineEvent",
    "SystemAction",
    "Tier",
    "User",
    "bayes_update",
    "build_faculty_timeline",
    "build_student_record",
    "calculate_expected_information_gain",
    "check_tier_gate",
    "determine_system_action",
    "evaluate_escalation_gate",
    "format_warning_message",
    "kl_divergence",
    "load_investigator_policy",
    "load_policy",
    "run_in_process_pipeline",
    "verify_all_system_outcomes",
]
