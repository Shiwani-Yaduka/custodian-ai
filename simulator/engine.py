"""Policy Simulator Engine for Custodian AI.

Enables what-if policy analysis by replaying fairness benchmark scenarios against
modified RiskPolicy configurations and computing empirical impact metrics.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field

from core.models import Tier
from core.policy import RiskPolicy, load_policy
from fairness.run import replay_scenario_adaptive


class ScenarioDiff(BaseModel):
    """Comparison result for a single scenario under base vs candidate policy."""

    scenario_id: str
    title: str
    label: str  # "must_not_flag" or "must_catch"
    scenario_class: str
    base_score: float
    candidate_score: float
    score_delta: float
    base_tier: str
    candidate_tier: str
    base_is_held: bool
    candidate_is_held: bool
    base_passed: bool
    candidate_passed: bool
    status_change: str  # "UNCHANGED", "REGRESSION", "IMPROVEMENT"
    notes: str = ""


class SimulationReport(BaseModel):
    """Overall outcome of policy what-if simulation."""

    parameter_overrides: Dict[str, Any]
    total_scenarios: int
    base_false_flags: int
    base_false_flag_rate: float
    candidate_false_flags: int
    candidate_false_flag_rate: float
    base_misses: int
    base_miss_rate: float
    candidate_misses: int
    candidate_miss_rate: float
    regressions_count: int
    improvements_count: int
    unchanged_count: int
    verdict: str  # "SAFE", "REGRESSION", "IMPROVEMENT"
    diffs: List[ScenarioDiff] = Field(default_factory=list)


def build_modified_policy(
    base_policy: Optional[RiskPolicy] = None,
    overrides: Optional[Dict[str, Any]] = None,
) -> RiskPolicy:
    """Build a new RiskPolicy by cloning base_policy and applying overrides.

    Supported shorthand overrides:
    - grace_gaze / g_s_gaze: float -> signals["gaze_off_screen"].g_s
    - grace_face / g_s_face: float -> signals["face_absent"].g_s
    - grace_head / g_s_head: float -> signals["head_turn"].g_s
    - grace_speech / g_s_speech: float -> signals["speech_detected"].g_s
    - cap_camera / K_camera: float -> channel_caps["camera"]
    - cap_mic / K_mic: float -> channel_caps["microphone"]
    - cap_window / K_window: float -> channel_caps["exam_window"]
    - cap_device / K_device: float -> channel_caps["device"]
    - corroboration_lambda / lambda: float -> corroboration_lambda
    - half_life / half_life_seconds: float -> half_life_seconds
    - hysteresis / hysteresis_seconds: float -> hysteresis_seconds
    - Generic dot-notation: e.g. "signals.gaze_off_screen.b_s": 15.0
    """
    if base_policy is None:
        base_policy = load_policy()

    policy_dict = base_policy.model_dump()
    if not overrides:
        return RiskPolicy.model_validate(policy_dict)

    # Shorthand mapping
    shorthands: Dict[str, str] = {
        "grace_gaze": "signals.gaze_off_screen.g_s",
        "g_s_gaze": "signals.gaze_off_screen.g_s",
        "grace_face": "signals.face_absent.g_s",
        "g_s_face": "signals.face_absent.g_s",
        "grace_head": "signals.head_turn.g_s",
        "g_s_head": "signals.head_turn.g_s",
        "grace_speech": "signals.speech_detected.g_s",
        "g_s_speech": "signals.speech_detected.g_s",
        "cap_camera": "channel_caps.camera",
        "K_camera": "channel_caps.camera",
        "cap_mic": "channel_caps.microphone",
        "K_mic": "channel_caps.microphone",
        "cap_window": "channel_caps.exam_window",
        "K_window": "channel_caps.exam_window",
        "cap_device": "channel_caps.device",
        "K_device": "channel_caps.device",
        "corroboration_lambda": "corroboration_lambda",
        "lambda": "corroboration_lambda",
        "half_life": "half_life_seconds",
        "half_life_seconds": "half_life_seconds",
        "hysteresis": "hysteresis_seconds",
        "hysteresis_seconds": "hysteresis_seconds",
    }

    for key, val in overrides.items():
        target_path = shorthands.get(key, key)
        parts = target_path.split(".")
        d = policy_dict
        for p in parts[:-1]:
            if p not in d:
                d[p] = {}
            d = d[p]
        d[parts[-1]] = val

    return RiskPolicy.model_validate(policy_dict)


def run_simulation(
    scenarios_path: Path,
    modified_policy: RiskPolicy,
    base_policy: Optional[RiskPolicy] = None,
    target_scenario: Optional[str] = None,
) -> SimulationReport:
    """Compare candidate policy against base policy across benchmark scenarios."""
    if base_policy is None:
        base_policy = load_policy()

    with open(scenarios_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    scenarios = data.get("scenarios", [])
    if target_scenario:
        scenarios = [s for s in scenarios if s.get("id") == target_scenario]
        if not scenarios:
            raise ValueError(f"Scenario '{target_scenario}' not found in {scenarios_path}")

    base_false_flags = 0
    candidate_false_flags = 0
    base_misses = 0
    candidate_misses = 0
    regressions = 0
    improvements = 0
    unchanged = 0

    diffs: List[ScenarioDiff] = []

    for sc in scenarios:
        sc_id = sc["id"]
        title = sc.get("title", sc_id)
        label = sc.get("label", "must_not_flag")
        sc_class = sc.get("class", "general")

        # 1. Evaluate on base policy
        b_res = replay_scenario_adaptive(sc, policy=base_policy)
        b_score = b_res["max_score"]
        b_tier = b_res["max_tier"]
        b_held = b_res["is_held"]

        # 2. Evaluate on candidate policy
        c_res = replay_scenario_adaptive(sc, policy=modified_policy)
        c_score = c_res["max_score"]
        c_tier = c_res["max_tier"]
        c_held = c_res["is_held"]

        # Determine pass/fail
        if label == "must_not_flag":
            b_passed = b_tier in ("CLEAR", "WATCHING") and not b_held
            c_passed = c_tier in ("CLEAR", "WATCHING") and not c_held
            if not b_passed:
                base_false_flags += 1
            if not c_passed:
                candidate_false_flags += 1
        else:  # must_catch
            b_passed = b_held or b_tier == Tier.HELD.value
            c_passed = c_held or c_tier == Tier.HELD.value
            if not b_passed:
                base_misses += 1
            if not c_passed:
                candidate_misses += 1

        # Classify change
        if b_passed and not c_passed:
            status_change = "REGRESSION"
            regressions += 1
        elif not b_passed and c_passed:
            status_change = "IMPROVEMENT"
            improvements += 1
        else:
            status_change = "UNCHANGED"
            unchanged += 1

        delta = round(c_score - b_score, 2)
        diffs.append(
            ScenarioDiff(
                scenario_id=sc_id,
                title=title,
                label=label,
                scenario_class=sc_class,
                base_score=b_score,
                candidate_score=c_score,
                score_delta=delta,
                base_tier=b_tier,
                candidate_tier=c_tier,
                base_is_held=b_held,
                candidate_is_held=c_held,
                base_passed=b_passed,
                candidate_passed=c_passed,
                status_change=status_change,
            )
        )

    tot = len(scenarios)
    innocent_tot = sum(1 for s in scenarios if s.get("label") == "must_not_flag")
    violation_tot = tot - innocent_tot

    base_ff_rate = (base_false_flags / innocent_tot) if innocent_tot > 0 else 0.0
    cand_ff_rate = (candidate_false_flags / innocent_tot) if innocent_tot > 0 else 0.0
    base_m_rate = (base_misses / violation_tot) if violation_tot > 0 else 0.0
    cand_m_rate = (candidate_misses / violation_tot) if violation_tot > 0 else 0.0

    if regressions > 0 or cand_ff_rate > base_ff_rate or cand_m_rate > base_m_rate:
        verdict = "REGRESSION"
    elif improvements > 0 and regressions == 0:
        verdict = "IMPROVEMENT"
    else:
        verdict = "SAFE"

    return SimulationReport(
        parameter_overrides={},
        total_scenarios=tot,
        base_false_flags=base_false_flags,
        base_false_flag_rate=base_ff_rate,
        candidate_false_flags=candidate_false_flags,
        candidate_false_flag_rate=cand_ff_rate,
        base_misses=base_misses,
        base_miss_rate=base_m_rate,
        candidate_misses=candidate_misses,
        candidate_miss_rate=cand_m_rate,
        regressions_count=regressions,
        improvements_count=improvements,
        unchanged_count=unchanged,
        verdict=verdict,
        diffs=diffs,
    )
