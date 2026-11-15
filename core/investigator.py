"""Bayesian Investigation Agent for Custodian AI.

Pure Python implementation of Section 6 of AGENTS.md:
- Case opening rules: confidence < 0.6, tier escalation risk, or recurrence
- Exact Bayesian posterior updates over H = {ordinary, technical, deliberate}
- Optimal probe selection via Expected Information Gain: argmax E[KL] / (1 + cost)
- Resolution multipliers: deliberate 1.0, inconclusive 0.4, ordinary 0.15, technical 0.0
- Channel discount on technical resolution
- Scripted and Simulated probe runner interfaces
"""

import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from pydantic import BaseModel, Field

from core.models import Observation, ProcessedObservation, RiskState
from core.risk import RiskEngine


class Hypothesis(str, Enum):
    """The three competing explanations for candidate anomalies."""

    ORDINARY = "ordinary"        # Natural human movement, sneeze, lighting change
    TECHNICAL = "technical"      # Camera driver fault, network jitter, frame drop
    DELIBERATE = "deliberate"    # Deliberate exam misconduct or unauthorized aid


class ResolutionStatus(str, Enum):
    """Final resolution classification of an investigation case."""

    ORDINARY = "ordinary"
    TECHNICAL = "technical"
    DELIBERATE = "deliberate"
    INCONCLUSIVE = "inconclusive"


class ProbeConfig(BaseModel):
    """Configuration for an individual investigation probe."""

    cost: float = Field(..., ge=0.0)
    description: str
    outcomes: Dict[str, Dict[str, float]]  # outcome_name -> {hypothesis -> P(outcome|hypothesis)}


class InvestigatorPolicy(BaseModel):
    """Configuration and priors for the Investigation Agent."""

    version: str = "1.0"
    confidence_threshold: float = Field(default=0.60, ge=0.0, le=1.0)
    closing_threshold: float = Field(default=0.70, ge=0.5, le=1.0)
    max_probes: int = Field(default=3, ge=1)
    resolution_multipliers: Dict[str, float] = Field(
        default_factory=lambda: {
            "deliberate": 1.00,
            "inconclusive": 0.40,
            "ordinary": 0.15,
            "technical": 0.00,
        }
    )
    signal_priors: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    probes: Dict[str, ProbeConfig] = Field(default_factory=dict)


def load_investigator_policy(source: Optional[Any] = None) -> InvestigatorPolicy:
    """Load InvestigatorPolicy from YAML file, dictionary, or default path."""
    if source is None:
        source = Path(__file__).resolve().parent / "investigator_policy.yaml"

    if isinstance(source, (str, Path)):
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Investigator policy file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    elif isinstance(source, dict):
        raw = source
    else:
        raise TypeError(f"Invalid source type for investigator policy: {type(source).__name__}")

    return InvestigatorPolicy.model_validate(raw)


# Domain Models for Investigations
class ProbeRecord(BaseModel):
    """Audit log of a probe execution and its belief update."""

    probe_name: str
    cost: float
    outcome: str
    prior_belief: Dict[str, float]
    posterior_belief: Dict[str, float]
    executed_at: float


class CaseResolution(BaseModel):
    """Final determination of an investigation case."""

    status: ResolutionStatus
    multiplier: float
    final_posterior: Dict[str, float]
    probes_used: List[ProbeRecord]
    reason: str
    resolved_at: float


class InvestigationCase(BaseModel):
    """Full lifecycle tracking of an investigated observation."""

    case_id: str
    session_id: str
    observation: Observation
    channel: str
    held_raw_weight: float
    open_reason: str
    opened_at: float
    is_open: bool = True
    current_belief: Dict[str, float]
    probe_history: List[ProbeRecord] = Field(default_factory=list)
    resolution: Optional[CaseResolution] = None


# Probe Runner Interfaces
class ProbeRunner(ABC):
    """Abstract interface to execute observation probes."""

    @abstractmethod
    def run_probe(self, probe_name: str, context: Dict[str, Any]) -> str:
        """Execute the probe and return the observed outcome name."""
        pass


class ScriptedProbeRunner(ProbeRunner):
    """Probe runner that returns pre-scripted outcomes for deterministic testing."""

    def __init__(self, script: Optional[Dict[str, str]] = None) -> None:
        self.script: Dict[str, str] = script or {}
        self.call_history: List[str] = []

    def set_outcome(self, probe_name: str, outcome: str) -> None:
        self.script[probe_name] = outcome

    def run_probe(self, probe_name: str, context: Dict[str, Any]) -> str:
        self.call_history.append(probe_name)
        if probe_name in self.script:
            return self.script[probe_name]
        return context.get("default_outcome", "normal")


class SimulatedProbeRunner(ProbeRunner):
    """Simulates probe outcomes by sampling from likelihood distributions."""

    def __init__(
        self,
        policy: InvestigatorPolicy,
        seed: Optional[int] = 42,
        ground_truth: Optional[str] = None,
    ) -> None:
        self.policy = policy
        self.rng = random.Random(seed)
        self.ground_truth = ground_truth

    def run_probe(self, probe_name: str, context: Dict[str, Any]) -> str:
        probe_def = self.policy.probes.get(probe_name)
        if not probe_def:
            return "normal"

        outcomes = list(probe_def.outcomes.keys())
        default_b = {"ordinary": 0.33, "technical": 0.33, "deliberate": 0.34}
        current_belief = context.get("current_belief", default_b)

        weights = []
        for o in outcomes:
            h_probs = probe_def.outcomes[o]
            if self.ground_truth and self.ground_truth in h_probs:
                p_o = h_probs[self.ground_truth]
            else:
                p_o = sum(h_probs.get(h, 0.0) * current_belief.get(h, 0.0) for h in current_belief)
            weights.append(max(0.0, p_o))

        total_w = sum(weights)
        if total_w <= 0:
            return outcomes[0]

        return self.rng.choices(outcomes, weights=weights, k=1)[0]


# Mathematical Utilities
def bayes_update(
    prior: Dict[str, float],
    likelihoods: Dict[str, float],
) -> Dict[str, float]:
    """Exact, normalized, division-by-zero protected Bayesian posterior update."""
    unnormalized: Dict[str, float] = {}
    for h, p_h in prior.items():
        p_e_given_h = likelihoods.get(h, 0.0)
        unnormalized[h] = p_e_given_h * p_h

    normalizer = sum(unnormalized.values())
    if normalizer <= 1e-12:
        return dict(prior)

    posterior = {h: round(val / normalizer, 6) for h, val in unnormalized.items()}
    # Clean rounding discrepancy so sum is exactly 1.0
    err = 1.0 - sum(posterior.values())
    first_key = next(iter(posterior))
    posterior[first_key] = round(posterior[first_key] + err, 6)
    return posterior


def kl_divergence(p: Dict[str, float], q: Dict[str, float]) -> float:
    """Calculate KL divergence D_KL(P || Q) = sum_h P(h) * ln(P(h) / Q(h))."""
    divergence = 0.0
    for h, p_val in p.items():
        if p_val <= 1e-12:
            continue
        q_val = max(1e-12, q.get(h, 1e-12))
        divergence += p_val * math.log(p_val / q_val)
    return max(0.0, divergence)


def calculate_expected_information_gain(
    prior: Dict[str, float],
    probe_def: ProbeConfig,
) -> float:
    """Calculate Expected Information Gain: sum_o P(o) * KL(P(H|o) || P(H))."""
    outcomes = probe_def.outcomes
    expected_ig = 0.0

    for _o_name, likelihood_map in outcomes.items():
        # Marginal probability P(o) = sum_h P(o|h) * P(h)
        p_o = sum(likelihood_map.get(h, 0.0) * prior.get(h, 0.0) for h in prior)
        if p_o <= 1e-12:
            continue

        # Posterior given outcome o: P(H|o)
        posterior_o = bayes_update(prior, likelihood_map)
        divergence = kl_divergence(posterior_o, prior)
        expected_ig += p_o * divergence

    return max(0.0, expected_ig)


# Investigation Agent
class InvestigatorAgent:
    """Orchestrates case lifecycle, probe selection, and resolution."""

    def __init__(
        self,
        policy: Optional[InvestigatorPolicy] = None,
        probe_runner: Optional[ProbeRunner] = None,
    ) -> None:
        self.policy = policy or load_investigator_policy()
        self.probe_runner = probe_runner or ScriptedProbeRunner()
        self.active_cases: Dict[str, InvestigationCase] = {}
        self.resolved_cases: List[InvestigationCase] = []
        self._case_counter = 0

    def should_open_case(
        self,
        observation: Observation,
        predicted_raw_weight: float,
        current_risk_state: RiskState,
        repetition_count: int,
    ) -> Tuple[bool, str]:
        """Evaluate the three triggers for opening an investigation case."""
        # Rule 1: Low detector confidence
        if observation.confidence < self.policy.confidence_threshold:
            return (
                True,
                f"Low detector confidence ({observation.confidence:.2f} < "
                f"{self.policy.confidence_threshold:.2f})",
            )

        # Rule 2: Escalation risk (applying this observation would raise candidate tier)
        simulated_total = current_risk_state.current_score + predicted_raw_weight

        # Check if simulated score crosses next tier threshold
        if (
            simulated_total >= 45.0
            and current_risk_state.current_tier.value in ("CLEAR", "WATCHING")
        ):
            return True, f"Escalation risk: observation would push score to {simulated_total:.1f}"

        # Rule 3: Behavior recurring
        if repetition_count > 1:
            return True, f"Recurring anomaly: occurrence #{repetition_count} within 5 minutes"

        return False, ""

    def open_case(
        self,
        observation: Observation,
        channel: str,
        held_raw_weight: float,
        reason: str,
        now: float,
    ) -> InvestigationCase:
        """Open a new case and initialize prior beliefs."""
        self._case_counter += 1
        case_id = f"CASE-{uuid.uuid4().hex[:6]}-{self._case_counter:04d}"

        # Get priors for this signal type, fallback to balanced prior
        priors = self.policy.signal_priors.get(
            observation.signal,
            {"ordinary": 0.40, "technical": 0.30, "deliberate": 0.30},
        )

        case = InvestigationCase(
            case_id=case_id,
            session_id=observation.session_id,
            observation=observation,
            channel=channel,
            held_raw_weight=held_raw_weight,
            open_reason=reason,
            opened_at=now,
            is_open=True,
            current_belief=dict(priors),
            probe_history=[],
            resolution=None,
        )

        self.active_cases[case_id] = case
        return case

    def select_best_probe(self, case: InvestigationCase) -> Optional[str]:
        """Select next probe maximizing E[KL] / (1 + cost) among unexecuted probes."""
        executed_names = {p.probe_name for p in case.probe_history}
        available = [name for name in self.policy.probes if name not in executed_names]

        if not available:
            return None

        best_probe: Optional[str] = None
        best_efficiency = -1.0
        best_cost = float("inf")

        for name in available:
            probe_def = self.policy.probes[name]
            eig = calculate_expected_information_gain(case.current_belief, probe_def)
            efficiency = eig / (1.0 + probe_def.cost)

            # Maximize efficiency; on tie, prefer lower cost (quieter)
            if efficiency > best_efficiency + 1e-9:
                best_efficiency = efficiency
                best_cost = probe_def.cost
                best_probe = name
            elif abs(efficiency - best_efficiency) <= 1e-9 and probe_def.cost < best_cost:
                best_cost = probe_def.cost
                best_probe = name

        return best_probe

    def execute_next_probe(self, case_id: str, now: float) -> Optional[ProbeRecord]:
        """Select and run the next most informative probe for the case."""
        case = self.active_cases.get(case_id)
        if not case or not case.is_open:
            return None

        probe_name = self.select_best_probe(case)
        if not probe_name:
            return None

        probe_def = self.policy.probes[probe_name]
        context = {
            "current_belief": case.current_belief,
            "session_id": case.session_id,
            "signal": case.observation.signal,
            "default_outcome": next(iter(probe_def.outcomes.keys())),
        }

        outcome = self.probe_runner.run_probe(probe_name, context)
        likelihood_map = probe_def.outcomes.get(outcome, {})
        prior_belief = dict(case.current_belief)
        posterior_belief = bayes_update(prior_belief, likelihood_map)

        record = ProbeRecord(
            probe_name=probe_name,
            cost=probe_def.cost,
            outcome=outcome,
            prior_belief=prior_belief,
            posterior_belief=posterior_belief,
            executed_at=now,
        )

        case.probe_history.append(record)
        case.current_belief = dict(posterior_belief)

        # Check closing conditions
        self.check_and_close_case(case_id, now)
        return record

    def check_and_close_case(self, case_id: str, now: float) -> Optional[CaseResolution]:
        """Check if case meets closing criteria: P(h) >= 0.70 or max probes reached."""
        case = self.active_cases.get(case_id)
        if not case or not case.is_open:
            return case.resolution if case else None

        threshold = self.policy.closing_threshold
        max_probes = self.policy.max_probes

        leading_h: Optional[Hypothesis] = None
        for h_str, prob in case.current_belief.items():
            if prob >= threshold:
                leading_h = Hypothesis(h_str)
                break

        # Check if resolved by high confidence
        if leading_h is not None:
            status = ResolutionStatus(leading_h.value)
            mult = self.policy.resolution_multipliers.get(status.value, 0.0)
            pct = case.current_belief[leading_h.value] * 100
            reason = (
                f"Resolved as {status.value.upper()} with confidence {pct:.1f}% "
                f"(exceeds {threshold:.0%}) after {len(case.probe_history)} probe(s)."
            )
            resolution = CaseResolution(
                status=status,
                multiplier=mult,
                final_posterior=dict(case.current_belief),
                probes_used=list(case.probe_history),
                reason=reason,
                resolved_at=now,
            )
            case.is_open = False
            case.resolution = resolution
            del self.active_cases[case_id]
            self.resolved_cases.append(case)
            return resolution

        # Check if closed by probe exhaustion
        if len(case.probe_history) >= max_probes:
            status = ResolutionStatus.INCONCLUSIVE
            mult = self.policy.resolution_multipliers.get("inconclusive", 0.40)
            reason = (
                f"Resolved as INCONCLUSIVE after reaching probe limit ({max_probes}). "
                f"Student given benefit of doubt (multiplier x{mult})."
            )
            resolution = CaseResolution(
                status=status,
                multiplier=mult,
                final_posterior=dict(case.current_belief),
                probes_used=list(case.probe_history),
                reason=reason,
                resolved_at=now,
            )
            case.is_open = False
            case.resolution = resolution
            del self.active_cases[case_id]
            self.resolved_cases.append(case)
            return resolution

        return None

    def run_full_investigation(
        self,
        case_id: str,
        start_time: float,
    ) -> CaseResolution:
        """Run probes until the case closes, advancing clock per probe."""
        current_time = start_time
        while case_id in self.active_cases:
            self.execute_next_probe(case_id, current_time)
            current_time += 1.0  # 1s per probe step in simulation

        # Case must be in resolved list
        for c in self.resolved_cases:
            if c.case_id == case_id:
                return c.resolution
        raise RuntimeError(f"Case {case_id} failed to resolve")

    def apply_case_resolution_to_engine(
        self,
        case: InvestigationCase,
        engine: RiskEngine,
        now: float,
    ) -> Tuple[ProcessedObservation, RiskState]:
        """Apply the resolved weight to the risk engine."""
        if case.is_open or not case.resolution:
            raise ValueError(f"Cannot apply unresolved case {case.case_id}")

        mult = case.resolution.multiplier
        adjusted_weight = case.held_raw_weight * mult

        # Modify observation to inject final adjusted weight
        processed, state = engine.process_observation(case.observation, now=now)

        # Override raw weight in history with resolved weight
        if state.observation_history:
            latest = state.observation_history[-1]
            latest.raw_weight = adjusted_weight
            engine._recalculate_state(state, now)
            engine.state_store.set_state(case.session_id, state)

        return processed, state

    def get_case(self, case_id: str) -> Optional[InvestigationCase]:
        """Fetch an active or resolved case by ID."""
        if case_id in self.active_cases:
            return self.active_cases[case_id]
        for c in self.resolved_cases:
            if c.case_id == case_id:
                return c
        return None

    def get_session_cases(self, session_id: str) -> List[InvestigationCase]:
        """Fetch all active and resolved cases for a session."""
        cases = [c for c in self.active_cases.values() if c.session_id == session_id]
        cases.extend([c for c in self.resolved_cases if c.session_id == session_id])
        return sorted(cases, key=lambda c: c.opened_at)

    def select_next_probe(self, case: InvestigationCase) -> Optional[ProbeConfig]:
        """Select next probe definition for case."""
        p_name = self.select_best_probe(case)
        if p_name:
            return self.policy.probes.get(p_name)
        return None

    def evaluate_observation(
        self,
        observation: Observation,
        current_risk_state: Optional[RiskState] = None,
        predicted_raw_weight: float = 10.0,
        repetition_count: int = 1,
        now: Optional[float] = None,
    ) -> Optional[InvestigationCase]:
        """Evaluate if an observation opens an investigation case and open it if needed."""
        ts = now if now is not None else observation.timestamp
        channel = observation.metadata.get("channel", "camera")

        if current_risk_state is None:
            from core.models import Tier

            current_risk_state = RiskState(
                session_id=observation.session_id,
                current_score=0.0,
                current_tier=Tier.CLEAR,
                candidate_tier=Tier.CLEAR,
                candidate_tier_since=ts,
            )

        should_open, reason = self.should_open_case(
            observation=observation,
            predicted_raw_weight=predicted_raw_weight,
            current_risk_state=current_risk_state,
            repetition_count=repetition_count,
        )

        if should_open:
            return self.open_case(
                observation=observation,
                channel=channel,
                held_raw_weight=predicted_raw_weight,
                reason=reason,
                now=ts,
            )
        return None

    def run_investigation(
        self, case_id: str, now: Optional[float] = None
    ) -> CaseResolution:
        """Run investigation to resolution."""
        ts = now if now is not None else time.time()
        return self.run_full_investigation(case_id, start_time=ts)

    def apply_probe_outcome(
        self,
        case: InvestigationCase,
        probe_name: str,
        outcome: str,
        timestamp: float,
    ) -> Optional[CaseResolution]:
        """Apply outcome of an interactive probe executed by the client."""
        probe_def = self.policy.probes.get(probe_name)
        if not probe_def:
            return None

        likelihood_map = probe_def.outcomes.get(outcome, {})
        prior_belief = dict(case.current_belief)
        posterior_belief = bayes_update(prior_belief, likelihood_map)

        record = ProbeRecord(
            probe_name=probe_name,
            cost=probe_def.cost,
            outcome=outcome,
            prior_belief=prior_belief,
            posterior_belief=posterior_belief,
            executed_at=timestamp,
        )

        case.probe_history.append(record)
        case.current_belief = dict(posterior_belief)

        return self.check_and_close_case(case.case_id, timestamp)

