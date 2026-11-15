"""Domain Models for Custodian AI Core Risk Engine.

Pydantic models for Observations, Channels, Risk States, and Tiers.
"""

from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class Tier(str, Enum):
    """Proctoring risk tiers in ascending severity."""

    CLEAR = "CLEAR"          # Normal exam state, score 0 - 24
    WATCHING = "WATCHING"    # Internal review only, score 25 - 44
    WARNED = "WARNED"        # First warning shown to student, score 45 - 64
    ELEVATED = "ELEVATED"    # Second warning + 10 mins added, score 65 - 79
    HELD = "HELD"            # Paused, submitted to human faculty, score 80 - 100


class Observation(BaseModel):
    """Raw observation report from browser sensors or device telemetry."""

    session_id: str
    signal: str
    timestamp: float = Field(..., description="Timestamp in seconds when observation occurred")
    duration: float = Field(default=0.0, ge=0.0, description="Duration in seconds (tau_i)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detector confidence (c_i)")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProcessedObservation(BaseModel):
    """Observation annotated with calculated weights and escalation factors."""

    observation: Observation
    channel: str
    duration_factor: float
    repetition_multiplier: float
    raw_weight: float
    calculated_at: float


class ChannelState(BaseModel):
    """Current state of a single sensor accumulator channel."""

    channel: str
    accumulator: float = Field(default=0.0, ge=0.0, description="Decayed accumulated risk A_c(t)")
    cap: float = Field(default=40.0, gt=0.0, description="Maximum allowable value K_c")
    is_contributing: bool = Field(default=False, description="True if accumulator > epsilon")
    last_updated: float = Field(default=0.0, description="Timestamp of latest recalculation")


class RiskState(BaseModel):
    """Complete live risk posture for an active exam session."""

    session_id: str
    current_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Total risk score")
    current_tier: Tier = Field(default=Tier.CLEAR, description="Active tier after hysteresis")
    candidate_tier: Tier = Field(default=Tier.CLEAR, description="Instantaneous raw tier")
    candidate_tier_since: float = Field(default=0.0, description="Timestamp candidate began")
    channels: Dict[str, ChannelState] = Field(default_factory=dict)
    contributing_channels: List[str] = Field(default_factory=list)
    corroboration_multiplier: float = Field(default=1.0, ge=1.0)
    last_updated: float = Field(default=0.0)
    observation_history: List[ProcessedObservation] = Field(default_factory=list)
