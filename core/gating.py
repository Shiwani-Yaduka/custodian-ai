"""Escalation Gating Module for Custodian AI.

Enforces Section 5 of AGENTS.md:
The risk score alone is NEVER enough to escalate a student. Every tier transition
above WATCHING requires passing qualitative procedural gates.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from core.models import Tier

TupleCheckResult = Tuple[bool, str, Dict[str, bool]]


class GatingDecision(BaseModel):
    """Result of evaluating procedural gates for a candidate tier transition."""

    approved: bool = Field(..., description="Whether the transition to candidate tier is granted")
    target_tier: Tier = Field(
        ...,
        description="The tier assigned (candidate if approved, or highest passed gate)",
    )
    candidate_tier: Tier = Field(..., description="The tier indicated by the raw score")
    current_tier: Tier = Field(..., description="The student's active tier prior to evaluation")
    score: float = Field(..., description="Current total risk score R(t)")
    reason: str = Field(..., description="Plain-language justification for the decision")
    blocked_reason: Optional[str] = Field(
        default=None,
        description="Detailed explanation of which procedural prerequisite failed if blocked",
    )
    gate_checklist: Dict[str, bool] = Field(
        default_factory=dict,
        description="Pass/fail audit of all evaluated criteria",
    )


def check_tier_gate(
    tier: Tier,
    contributing_channels: List[str],
    warnings_shown_count: int,
    deliberate_cases_p85_count: int,
) -> TupleCheckResult:
    """Evaluate whether all required preconditions hold for a specific target tier."""
    num_channels = len(contributing_channels)

    if tier in (Tier.CLEAR, Tier.WATCHING):
        return True, "No procedural gate required.", {}

    if tier == Tier.WARNED:
        passed = num_channels >= 2
        checklist = {"at_least_2_channels": passed}
        if passed:
            return (
                True,
                f"Gate passed: {num_channels} independent channels contributing.",
                checklist,
            )
        return (
            False,
            f"Gate blocked: First warning requires at least 2 independent sensory channels "
            f"contributing risk (currently {num_channels}: {contributing_channels}).",
            checklist,
        )

    if tier == Tier.ELEVATED:
        c1 = num_channels >= 2
        c2 = warnings_shown_count >= 1
        checklist = {
            "at_least_2_channels": c1,
            "first_warning_already_shown": c2,
        }
        if c1 and c2:
            return (
                True,
                "Gate passed: Multiple channels corroborated and first warning was shown.",
                checklist,
            )
        missing = []
        if not c1:
            missing.append(f"requires >= 2 channels (currently {num_channels})")
        if not c2:
            missing.append("requires first warning to have been shown to the student")
        return (
            False,
            f"Gate blocked: Escalated warning requires all preconditions ({', '.join(missing)}).",
            checklist,
        )

    if tier == Tier.HELD:
        c1 = num_channels >= 2
        c2 = deliberate_cases_p85_count >= 1
        c3 = warnings_shown_count >= 2
        checklist = {
            "at_least_2_channels": c1,
            "case_resolved_deliberate_p85": c2,
            "two_warnings_already_shown": c3,
        }
        if c1 and c2 and c3:
            return (
                True,
                "Gate passed: 2+ corroborated channels, verified deliberate investigation "
                "(P>=0.85), and candidate was previously shown both warnings.",
                checklist,
            )
        missing = []
        if not c1:
            missing.append(f"requires >= 2 channels (currently {num_channels})")
        if not c2:
            missing.append(
                f"requires at least one case resolved DELIBERATE with posterior >= 0.85 "
                f"(currently {deliberate_cases_p85_count})"
            )
        if not c3:
            missing.append(
                f"requires two prior warnings shown to student (currently {warnings_shown_count})"
            )
        return (
            False,
            f"Gate blocked: Faculty hold requires all prerequisites ({'; '.join(missing)}).",
            checklist,
        )

    return False, f"Unknown tier {tier}", {}


def evaluate_escalation_gate(
    candidate_tier: Tier,
    current_tier: Tier,
    score: float,
    contributing_channels: List[str],
    warnings_shown_count: int,
    deliberate_cases_p85_count: int,
) -> GatingDecision:
    """Evaluate candidate tier against procedural gates and return final GatingDecision.

    If candidate tier's gate passes, escalation is approved.
    If it fails, candidate stays in the highest allowed tier whose gate passes,
    and a BLOCKED ESCALATION record is generated with the plain-language reason.
    """
    tier_order = [Tier.CLEAR, Tier.WATCHING, Tier.WARNED, Tier.ELEVATED, Tier.HELD]
    cand_idx = tier_order.index(candidate_tier)
    curr_idx = tier_order.index(current_tier)

    # De-escalation or stable tier is always allowed (natural score decay)
    if cand_idx <= curr_idx:
        return GatingDecision(
            approved=True,
            target_tier=candidate_tier,
            candidate_tier=candidate_tier,
            current_tier=current_tier,
            score=score,
            reason=(
                f"Tier transitioned or maintained naturally from {current_tier.value} "
                f"to {candidate_tier.value}."
            ),
            blocked_reason=None,
            gate_checklist={"de_escalation_or_stable": True},
        )

    # Escalation requested: evaluate gate for candidate_tier
    passed, explanation, checklist = check_tier_gate(
        candidate_tier,
        contributing_channels,
        warnings_shown_count,
        deliberate_cases_p85_count,
    )

    if passed:
        return GatingDecision(
            approved=True,
            target_tier=candidate_tier,
            candidate_tier=candidate_tier,
            current_tier=current_tier,
            score=score,
            reason=f"Escalation to {candidate_tier.value} approved. {explanation}",
            blocked_reason=None,
            gate_checklist=checklist,
        )

    # Candidate gate failed: find the highest allowed tier <= candidate_tier whose gate passes
    highest_allowed = Tier.CLEAR
    for t in tier_order:
        if tier_order.index(t) > cand_idx:
            break
        t_passed, _, _ = check_tier_gate(
            t, contributing_channels, warnings_shown_count, deliberate_cases_p85_count
        )
        if t_passed:
            highest_allowed = t

    return GatingDecision(
        approved=False,
        target_tier=highest_allowed,
        candidate_tier=candidate_tier,
        current_tier=current_tier,
        score=score,
        reason=(
            f"Escalation to {candidate_tier.value} was BLOCKED. "
            f"Candidate held at {highest_allowed.value}."
        ),
        blocked_reason=explanation,
        gate_checklist=checklist,
    )
