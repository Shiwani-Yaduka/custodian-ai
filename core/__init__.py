"""Custodian AI — Core Logic Package.

Pure Python implementation of:
- Risk accumulation, decay, and corroboration engine
- Bayesian investigation models and probes
- Safety gating and escalation criteria
- In-memory state storage

Zero HTTP or web dependencies.
"""

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
from core.models import (
    ChannelState,
    Observation,
    ProcessedObservation,
    RiskState,
    Tier,
)
from core.policy import RiskPolicy, SignalDefinition, load_policy
from core.risk import RiskEngine
from core.state import InMemoryStateStore, StateStore

__version__ = "0.1.0"

__all__ = [
    "CaseResolution",
    "ChannelState",
    "Hypothesis",
    "InMemoryStateStore",
    "InvestigationCase",
    "InvestigatorAgent",
    "InvestigatorPolicy",
    "Observation",
    "ProbeConfig",
    "ProbeRecord",
    "ProbeRunner",
    "ProcessedObservation",
    "ResolutionStatus",
    "RiskEngine",
    "RiskPolicy",
    "RiskState",
    "ScriptedProbeRunner",
    "SignalDefinition",
    "SimulatedProbeRunner",
    "StateStore",
    "Tier",
    "bayes_update",
    "calculate_expected_information_gain",
    "kl_divergence",
    "load_investigator_policy",
    "load_policy",
]
