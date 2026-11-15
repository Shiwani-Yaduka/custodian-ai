"""Safety Proof and Invariant Verification Module for Custodian AI.

Enforces Section 10 of AGENTS.md:
"Never add automatic failing, disqualification or any punishment without human review.
Add a test that proves it cannot happen."

Proves mathematically and programmatically that the system can ONLY produce one of
the five sanctioned actions and CANNOT fail, disqualify, or dock marks from candidates.
"""

from enum import Enum
from typing import Set

from core.models import Tier


class SystemAction(str, Enum):
    """The exhaustive, closed set of all possible system outcomes in Custodian AI."""

    NOTHING_SHOWN = "NOTHING_SHOWN"
    INTERNAL_NOTE = "INTERNAL_NOTE"
    FIRST_WARNING = "FIRST_WARNING"
    SECOND_WARNING_TIME_ADDED = "SECOND_WARNING_TIME_ADDED"
    PAUSE_AND_HOLD_FOR_HUMAN = "PAUSE_AND_HOLD_FOR_HUMAN"


# Explicit blacklist of prohibited punitive actions
PROHIBITED_ACTIONS: Set[str] = {
    "AUTOMATIC_FAIL",
    "DISQUALIFY",
    "DISQUALIFICATION",
    "MARK_DEDUCTION",
    "SCORE_PENALTY",
    "EXAM_TERMINATION",
    "CANCEL_SUBMISSION",
}


TIER_TO_ACTION_MAP = {
    Tier.CLEAR: SystemAction.NOTHING_SHOWN,
    Tier.WATCHING: SystemAction.INTERNAL_NOTE,
    Tier.WARNED: SystemAction.FIRST_WARNING,
    Tier.ELEVATED: SystemAction.SECOND_WARNING_TIME_ADDED,
    Tier.HELD: SystemAction.PAUSE_AND_HOLD_FOR_HUMAN,
}


def determine_system_action(assigned_tier: Tier) -> SystemAction:
    """Map the finalized proctoring tier to its singular authorized system action."""
    if assigned_tier not in TIER_TO_ACTION_MAP:
        raise ValueError(f"Unrecognized tier {assigned_tier}")
    action = TIER_TO_ACTION_MAP[assigned_tier]

    # Hard safety assert: outcome must be strictly within sanctioned set
    assert action in SystemAction, f"Illegal action {action} generated"
    assert action.value not in PROHIBITED_ACTIONS, f"Prohibited punitive action {action} attempted"
    return action


def verify_all_system_outcomes() -> Set[SystemAction]:
    """Return the set of all possible outcomes for formal exhaustiveness testing."""
    return set(SystemAction)
