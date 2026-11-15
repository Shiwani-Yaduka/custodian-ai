"""Risk Policy definitions, validation, and loader for Custodian AI.

Implements the configurable parameters specified in Section 5 of AGENTS.md.
Validates that single sensors can never push a student to WARNED threshold.
"""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field, model_validator


class SignalDefinition(BaseModel):
    """Configuration for an individual signal detector."""

    channel: str
    b_s: float = Field(..., gt=0, description="Base weight of the signal")
    g_s: float = Field(..., ge=0, description="Grace duration in seconds")
    f_s: float = Field(..., gt=0, description="Full-weight duration in seconds")

    @model_validator(mode="after")
    def validate_duration_ordering(self) -> "SignalDefinition":
        if self.f_s <= self.g_s:
            raise ValueError(
                f"Full-weight duration f_s ({self.f_s}s) must be strictly greater than "
                f"grace duration g_s ({self.g_s}s) for channel '{self.channel}'"
            )
        return self


class RepetitionConfig(BaseModel):
    """Configuration for repeated signal escalation."""

    step: float = Field(default=0.35, ge=0.0, description="Weight increment per repeat")
    max_steps: int = Field(default=4, ge=0, description="Maximum repetition escalation steps")
    window_seconds: float = Field(default=300.0, gt=0.0, description="Rolling time window")


class RiskPolicy(BaseModel):
    """Complete, validated risk policy configuration."""

    version: str = "1.0"
    channel_caps: Dict[str, float] = Field(
        default_factory=lambda: {
            "camera": 40.0,
            "microphone": 40.0,
            "exam_window": 40.0,
            "device": 40.0,
        }
    )
    half_life_seconds: float = Field(default=240.0, gt=0.0)
    corroboration_lambda: float = Field(default=0.20, ge=0.0)
    contributing_epsilon: float = Field(default=2.0, ge=0.0)
    repetition: RepetitionConfig = Field(default_factory=RepetitionConfig)
    hysteresis_seconds: float = Field(default=6.0, ge=0.0)
    tier_thresholds: Dict[str, float] = Field(
        default_factory=lambda: {
            "CLEAR": 0.0,
            "WATCHING": 25.0,
            "WARNED": 45.0,
            "ELEVATED": 65.0,
            "HELD": 80.0,
        }
    )
    signals: Dict[str, SignalDefinition] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_safety_and_fairness_constraints(self) -> "RiskPolicy":
        """Enforce Section 5 fairness rules and single-channel isolation."""
        warned_threshold = self.tier_thresholds.get("WARNED", 45.0)

        # Non-negotiable fairness rule: Every channel cap must be strictly below WARNED threshold
        for channel, cap in self.channel_caps.items():
            if cap >= warned_threshold:
                raise ValueError(
                    f"Safety Violation in Policy: Channel cap K_{channel} ({cap}) must be "
                    f"strictly less than the WARNED threshold ({warned_threshold}). "
                    f"A single sensor must never be capable of triggering a warning alone."
                )

        # Validate that all signals map to a known capped channel
        for signal_name, signal_def in self.signals.items():
            if signal_def.channel not in self.channel_caps:
                raise ValueError(
                    f"Signal '{signal_name}' references channel '{signal_def.channel}', "
                    f"which has no defined channel cap in channel_caps."
                )

        return self


DEFAULT_POLICY_PATH = Path(__file__).resolve().parent / "default_policy.yaml"


def load_policy(source: Optional[Any] = None) -> RiskPolicy:
    """Load and validate a RiskPolicy from a YAML file, dict, or the default policy file."""
    if source is None:
        source = DEFAULT_POLICY_PATH

    if isinstance(source, (str, Path)):
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Risk policy file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f)
    elif isinstance(source, dict):
        raw_data = source
    else:
        raise TypeError(f"Expected file path or dict for policy, got {type(source).__name__}")

    return RiskPolicy.model_validate(raw_data)
