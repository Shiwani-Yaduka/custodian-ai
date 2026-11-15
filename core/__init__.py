"""Custodian AI — Core Logic Package.

Pure Python implementation of:
- Risk accumulation, decay, and corroboration engine
- Bayesian investigation models and probes
- Safety gating and escalation criteria
- In-memory state storage

Zero HTTP or web dependencies.
"""

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
    "ChannelState",
    "InMemoryStateStore",
    "Observation",
    "ProcessedObservation",
    "RiskEngine",
    "RiskPolicy",
    "RiskState",
    "SignalDefinition",
    "StateStore",
    "Tier",
    "load_policy",
]
