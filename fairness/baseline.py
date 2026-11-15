"""Naive Fixed-Threshold Baseline Detector for Proctoring Evaluation.

Represents conventional / legacy commercial proctoring software:
- Static threshold triggers without grace windows
- No exponential decay (past actions never forgiven)
- No per-channel accumulator caps (single faulty sensor easily breaches limit)
- No multi-channel corroboration requirement (single sensor flags student)
- No Bayesian investigation for uncertainty (low confidence blips treated as violations)
"""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class BaselineThresholds:
    """Fixed static duration thresholds (in seconds) used by legacy proctors."""

    gaze_off_screen: float = 2.0
    head_turn: float = 2.0
    face_absent: float = 3.0
    multiple_faces: float = 1.0
    speech_detected: float = 2.0
    window_blur: float = 1.5
    tab_hidden: float = 1.0
    network_drop: float = 5.0
    camera_track_ended: float = 2.0
    low_frame_rate: float = 5.0


class BaselineResult(BaseModel):
    """Result of running a scenario through the naive fixed-threshold detector."""

    scenario_id: str
    flagged: bool
    final_tier: str  # "FLAGGED" or "CLEARED"
    trigger_count: int
    reasons: List[str] = Field(default_factory=list)


class FixedThresholdBaseline:
    """Evaluates raw sensory observations against naive static thresholds."""

    def __init__(self, thresholds: BaselineThresholds | None = None):
        self.thresholds = thresholds or BaselineThresholds()

    def evaluate_scenario(self, scenario: Dict[str, Any]) -> BaselineResult:
        """Evaluate a scenario timeline through naive fixed thresholds."""
        timeline = scenario.get("timeline", [])
        reasons: List[str] = []
        flagged = False

        for ev in timeline:
            signal = ev.get("signal", "")
            duration = ev.get("duration", 0.0)
            threshold = getattr(self.thresholds, signal, 2.0)

            # In legacy proctoring, ANY observation exceeding fixed threshold triggers a flag
            if duration >= threshold:
                flagged = True
                reasons.append(
                    f"Fixed threshold breached for {signal}: {duration:.1f}s >= {threshold:.1f}s"
                )

        return BaselineResult(
            scenario_id=scenario.get("id", ""),
            flagged=flagged,
            final_tier="FLAGGED" if flagged else "CLEARED",
            trigger_count=len(reasons),
            reasons=reasons,
        )
