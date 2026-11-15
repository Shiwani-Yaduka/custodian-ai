"""In-Process Pipeline Runner for Custodian AI.

Executes the entire end-to-end proctoring workflow (sensory detection, calibration,
Bayesian investigation, risk decay accumulation, procedural gating, and ledger recording)
in a single Python process with zero HTTP overhead.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from core.calibration import CalibrationDetector, FeatureBatch
from core.gating import GatingDecision, evaluate_escalation_gate
from core.investigator import (
    CaseResolution,
    InvestigatorAgent,
    ProbeRunner,
    SimulatedProbeRunner,
    load_investigator_policy,
)
from core.ledger import (
    LedgerRepository,
    SQLAlchemyLedgerRepository,
)
from core.models import Observation, RiskState, Tier
from core.policy import RiskPolicy, load_policy
from core.risk import RiskEngine
from core.safety import SystemAction, determine_system_action
from core.state import InMemoryStateStore, StateStore
from core.warnings import format_warning_message


class PipelineResult(BaseModel):
    """Aggregate output from processing a feature batch through the pipeline."""

    session_id: str
    timestamp: float
    is_calibrating: bool
    calibration_progress: float
    observations: List[Observation] = Field(default_factory=list)
    risk_state: RiskState
    gating_decision: GatingDecision
    system_action: SystemAction
    active_warning: Optional[str] = None
    case_resolutions: List[CaseResolution] = Field(default_factory=list)


class InProcessPipeline:
    """Unified in-memory execution pipeline for tests, fairness runner, and services."""

    def __init__(
        self,
        risk_policy: Optional[RiskPolicy] = None,
        state_store: Optional[StateStore] = None,
        ledger_repo: Optional[LedgerRepository] = None,
        probe_runner: Optional[ProbeRunner] = None,
    ):
        self.risk_policy = risk_policy or load_policy()
        self.state_store = state_store or InMemoryStateStore()

        if ledger_repo is None:
            self.ledger_repo = SQLAlchemyLedgerRepository(database_url="sqlite:///:memory:")
            self.ledger_repo.init_db()
        else:
            self.ledger_repo = ledger_repo

        self.risk_engine = RiskEngine(policy=self.risk_policy, state_store=self.state_store)
        self.detector = CalibrationDetector()

        inv_policy = load_investigator_policy()
        runner = probe_runner or SimulatedProbeRunner(policy=inv_policy, seed=42)
        self.investigator = InvestigatorAgent(
            policy=inv_policy,
            probe_runner=runner,
        )

    def process_features(self, batch: FeatureBatch) -> PipelineResult:
        """Process a raw feature batch through all phases of the proctoring pipeline."""
        # 1. Feature detection and calibration
        is_calibrating, progress, observations = self.detector.process_features(batch)

        if is_calibrating:
            risk_state = self.risk_engine.get_state(batch.session_id, now=batch.timestamp)
            gating_decision = GatingDecision(
                approved=True,
                target_tier=Tier.CLEAR,
                candidate_tier=Tier.CLEAR,
                current_tier=Tier.CLEAR,
                score=0.0,
                reason="Calibration phase active",
            )
            return PipelineResult(
                session_id=batch.session_id,
                timestamp=batch.timestamp,
                is_calibrating=True,
                calibration_progress=progress,
                observations=[],
                risk_state=risk_state,
                gating_decision=gating_decision,
                system_action=SystemAction.NOTHING_SHOWN,
                active_warning=None,
                case_resolutions=[],
            )

        res = self.process_observations(
            session_id=batch.session_id,
            observations=observations,
            timestamp=batch.timestamp,
        )
        res.is_calibrating = False
        res.calibration_progress = progress
        return res

    def process_observations(
        self,
        session_id: str,
        observations: List[Observation],
        timestamp: float,
    ) -> PipelineResult:
        """Process high-level sensory observations through investigator, risk engine, and gating."""
        case_resolutions: List[CaseResolution] = []

        # 2. Ingest observations through investigator and risk engine
        for obs in observations:
            # Append raw observation to ledger
            ledger_obs = self.ledger_repo.append_observation(
                session_id=obs.session_id,
                signal=obs.signal,
                confidence=obs.confidence,
                duration=obs.duration,
                timestamp=obs.timestamp,
            )

            # Evaluate whether an investigation case should open using current state and repetition
            current_state = self.risk_engine.get_state(obs.session_id, now=obs.timestamp)
            recent_obs = [
                o
                for o in current_state.observation_history
                if o.observation.signal == obs.signal and (obs.timestamp - o.calculated_at) <= 300.0
            ]
            repetition_count = len(recent_obs) + 1
            d_i = self.risk_engine.calculate_duration_factor(obs.signal, obs.duration)
            r_i = self.risk_engine.calculate_repetition_multiplier(
                obs.signal, obs.timestamp, current_state.observation_history
            )
            sig_def = self.risk_policy.signals.get(obs.signal)
            base_w = sig_def.b_s if sig_def else 10.0
            pred_weight = base_w * obs.confidence * d_i * r_i

            case = self.investigator.evaluate_observation(
                observation=obs,
                current_risk_state=current_state,
                predicted_raw_weight=pred_weight,
                repetition_count=repetition_count,
                now=obs.timestamp,
            )

            if case is not None:
                # Case opened: record in ledger
                self.ledger_repo.append_case(
                    case_id=case.case_id,
                    session_id=case.session_id,
                    observation_id=ledger_obs.id,
                    open_reason=case.open_reason,
                    opened_at=case.opened_at,
                )

                # Execute investigation probes
                resolution = self.investigator.run_investigation(case.case_id, now=timestamp)
                case_resolutions.append(resolution)

                # Record executed probes in ledger
                for p_rec in case.probe_history:
                    self.ledger_repo.append_probe(
                        case_id=case.case_id,
                        probe_name=p_rec.probe_name,
                        cost=p_rec.cost,
                        outcome=p_rec.outcome,
                        prior_json=str(p_rec.prior_belief),
                        posterior_json=str(p_rec.posterior_belief),
                        executed_at=p_rec.executed_at,
                    )

                # Record case resolution in ledger
                self.ledger_repo.resolve_case(
                    case_id=case.case_id,
                    resolution=resolution.status.value,
                    multiplier=resolution.multiplier,
                    resolved_at=resolution.resolved_at,
                )

                # Apply released observation to risk engine scaled by resolution multiplier
                self.risk_engine.apply_resolved_observation(
                    obs, multiplier=resolution.multiplier, now=obs.timestamp
                )

                # Record contribution in ledger
                self.ledger_repo.append_contribution(
                    session_id=obs.session_id,
                    observation_id=ledger_obs.id,
                    channel=self.risk_policy.signals[obs.signal].channel,
                    raw_weight=case.held_raw_weight,
                    held=False,
                    released=True,
                    resolution_multiplier=resolution.multiplier,
                    final_weight=case.held_raw_weight * resolution.multiplier,
                    timestamp=obs.timestamp,
                )
            else:
                # No case needed: apply directly to risk engine
                processed = self.risk_engine.apply_observation(obs)
                self.ledger_repo.append_contribution(
                    session_id=obs.session_id,
                    observation_id=ledger_obs.id,
                    channel=processed.channel,
                    raw_weight=processed.raw_weight,
                    held=False,
                    released=True,
                    resolution_multiplier=1.0,
                    final_weight=processed.raw_weight,
                    timestamp=obs.timestamp,
                )

        # 3. Query updated risk state
        risk_state = self.risk_engine.get_state(session_id, now=timestamp)

        # 4. Gating evaluation
        contributing_channels = risk_state.contributing_channels

        warnings_shown = self.ledger_repo.get_warnings(session_id)
        warnings_count = len(warnings_shown)

        cases = self.ledger_repo.get_cases(session_id)
        deliberate_cases_count = sum(
            1 for c in cases
            if c.resolution == "deliberate"
        )

        gating_decision = evaluate_escalation_gate(
            candidate_tier=risk_state.candidate_tier,
            current_tier=risk_state.current_tier,
            score=risk_state.total_score,
            contributing_channels=contributing_channels,
            warnings_shown_count=warnings_count,
            deliberate_cases_p85_count=deliberate_cases_count,
        )

        # 5. Handle approved transitions or blocked escalations
        active_warning: Optional[str] = None
        if gating_decision.approved and gating_decision.target_tier != risk_state.current_tier:
            new_tier = gating_decision.target_tier
            # Update engine tier
            risk_state.current_tier = new_tier

            # Generate warnings if entering WARNED or ELEVATED
            if new_tier == Tier.WARNED:
                msg = format_warning_message(
                    signal_name=observations[0].signal if observations else "face_absent",
                    duration=observations[0].duration if observations else 20.0,
                    warning_number=1,
                )
                self.ledger_repo.append_warning(
                    session_id=session_id,
                    warning_number=1,
                    message=msg,
                    timestamp=timestamp,
                )
                active_warning = msg
            elif new_tier == Tier.ELEVATED:
                msg = format_warning_message(
                    signal_name=observations[0].signal if observations else "tab_hidden",
                    duration=observations[0].duration if observations else 15.0,
                    warning_number=2,
                )
                self.ledger_repo.append_warning(
                    session_id=session_id,
                    warning_number=2,
                    message=msg,
                    timestamp=timestamp,
                )
                active_warning = msg
            elif new_tier == Tier.HELD:
                self.ledger_repo.append_hold(
                    session_id=session_id,
                    evidence_summary=gating_decision.reason,
                    paused_at=timestamp,
                )
                self.ledger_repo.update_session_status(
                    session_id=session_id,
                    status="held",
                )

            # Record approved decision in ledger
            self.ledger_repo.append_decision(
                session_id=session_id,
                decision_type="TIER_TRANSITION",
                score=risk_state.total_score,
                from_tier=risk_state.current_tier.value,
                to_tier=new_tier.value,
                candidate_tier=risk_state.candidate_tier.value,
                gate_passed=True,
                reason=gating_decision.reason,
                blocked_reason=None,
                timestamp=timestamp,
            )
        elif not gating_decision.approved:
            # Record blocked escalation in ledger
            self.ledger_repo.append_decision(
                session_id=session_id,
                decision_type="BLOCKED_ESCALATION",
                score=risk_state.total_score,
                from_tier=risk_state.current_tier.value,
                to_tier=gating_decision.target_tier.value,
                candidate_tier=gating_decision.candidate_tier.value,
                gate_passed=False,
                reason=gating_decision.reason,
                blocked_reason=gating_decision.blocked_reason,
                timestamp=timestamp,
            )

        system_action = determine_system_action(gating_decision.target_tier)

        return PipelineResult(
            session_id=session_id,
            timestamp=timestamp,
            is_calibrating=False,
            calibration_progress=1.0,
            observations=observations,
            risk_state=risk_state,
            gating_decision=gating_decision,
            system_action=system_action,
            active_warning=active_warning,
            case_resolutions=case_resolutions,
        )


def run_in_process_pipeline(
    batches: List[FeatureBatch],
    repo: Optional[LedgerRepository] = None,
) -> List[PipelineResult]:
    """Execute a chronological sequence of feature batches in a single process."""
    pipeline = InProcessPipeline(ledger_repo=repo)
    results = []
    for b in batches:
        res = pipeline.process_features(b)
        results.append(res)
    return results
