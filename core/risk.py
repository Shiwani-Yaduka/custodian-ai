"""Core Risk Engine for Custodian AI.

Pure Python implementation of the risk model from Section 5 of AGENTS.md:
- Observation weight with grace duration, linear ramp, and repetition scaling
- Decaying capped accumulators per sensor channel
- Corroboration multiplier across contributing channels
- Continuous score recalculation and 6-second tier transition hysteresis
- Time-injectable and framework-agnostic (zero web/HTTP dependencies)
"""

import time
from typing import Callable, Dict, List, Optional, Tuple

from core.models import (
    ChannelState,
    Observation,
    ProcessedObservation,
    RiskState,
    Tier,
)
from core.policy import RiskPolicy, load_policy
from core.state import InMemoryStateStore, StateStore


class RiskEngine:
    """Calculates, accumulates, decays, and tracks proctoring risk."""

    def __init__(
        self,
        policy: Optional[RiskPolicy] = None,
        state_store: Optional[StateStore] = None,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        self.policy = policy or load_policy()
        self.state_store = state_store or InMemoryStateStore()
        self.clock = clock or time.time

    def get_current_time(self, override: Optional[float] = None) -> float:
        """Return the injected time or current clock time."""
        if override is not None:
            return float(override)
        return float(self.clock())

    def calculate_duration_factor(self, signal_name: str, duration: float) -> float:
        """Calculate duration factor d_i in [0, 1].

        d_i = clamp((tau_i - g_s) / (f_s - g_s), 0, 1)
        """
        signal_def = self.policy.signals.get(signal_name)
        if not signal_def:
            # If an unregistered signal is provided, treat duration factor as 1.0 if duration > 0
            return 1.0 if duration > 0 else 0.0

        if duration <= signal_def.g_s:
            return 0.0
        if duration >= signal_def.f_s:
            return 1.0

        span = signal_def.f_s - signal_def.g_s
        if span <= 0:
            return 1.0
        return (duration - signal_def.g_s) / span

    def calculate_repetition_multiplier(
        self,
        signal_name: str,
        timestamp: float,
        history: List[ProcessedObservation],
    ) -> float:
        """Calculate repetition multiplier r_i.

        r_i = 1 + step * min(n - 1, max_steps)
        where n is the n-th occurrence of this signal within window_seconds.
        """
        cfg = self.policy.repetition
        window_start = timestamp - cfg.window_seconds

        # Count prior occurrences of the same signal within the rolling window
        prior_count = 0
        for p in history:
            if p.observation.signal == signal_name and (
                window_start <= p.observation.timestamp <= timestamp
            ):
                prior_count += 1

        n = prior_count + 1  # Including the current occurrence
        multiplier = 1.0 + cfg.step * min(n - 1, cfg.max_steps)
        return multiplier

    def process_observation(
        self,
        observation: Observation,
        now: Optional[float] = None,
    ) -> Tuple[ProcessedObservation, RiskState]:
        """Ingest a new observation, calculate its weight, and update session risk state."""
        current_time = self.get_current_time(now if now is not None else observation.timestamp)

        state = self.state_store.get_state(observation.session_id)
        if state is None:
            state = self._initialize_session_state(observation.session_id, current_time)

        signal_def = self.policy.signals.get(observation.signal)
        if signal_def:
            channel = signal_def.channel
            base_weight = signal_def.b_s
        else:
            channel = observation.metadata.get("channel", "device")
            base_weight = 10.0

        d_i = self.calculate_duration_factor(observation.signal, observation.duration)
        r_i = self.calculate_repetition_multiplier(
            observation.signal,
            observation.timestamp,
            state.observation_history,
        )

        raw_weight = base_weight * observation.confidence * d_i * r_i

        processed = ProcessedObservation(
            observation=observation,
            channel=channel,
            duration_factor=d_i,
            repetition_multiplier=r_i,
            raw_weight=raw_weight,
            calculated_at=current_time,
        )

        state.observation_history.append(processed)

        # Recalculate accumulators, score, and tier at current_time
        self._recalculate_state(state, current_time)
        self.state_store.set_state(observation.session_id, state)
        return processed, state

    def evaluate_session(
        self,
        session_id: str,
        now: Optional[float] = None,
    ) -> Optional[RiskState]:
        """Recalculate risk decay and tier hysteresis for a session at a specific time."""
        current_time = self.get_current_time(now)
        state = self.state_store.get_state(session_id)
        if state is None:
            return None

        self._recalculate_state(state, current_time)
        self.state_store.set_state(session_id, state)
        return state

    def apply_observation(
        self,
        observation: Observation,
        now: Optional[float] = None,
    ) -> ProcessedObservation:
        """Convenience method to ingest observation and return ProcessedObservation."""
        processed, _ = self.process_observation(observation, now)
        return processed

    def get_state(
        self,
        session_id: str,
        now: Optional[float] = None,
    ) -> RiskState:
        """Fetch or initialize risk state for a session, updating decay to now."""
        current_time = self.get_current_time(now)
        state = self.state_store.get_state(session_id)
        if state is None:
            state = self._initialize_session_state(session_id, current_time)
            self.state_store.set_state(session_id, state)
            return state

        self._recalculate_state(state, current_time)
        self.state_store.set_state(session_id, state)
        return state

    def _initialize_session_state(self, session_id: str, created_at: float) -> RiskState:
        """Create a blank RiskState with all channels initialized to 0."""
        channels: Dict[str, ChannelState] = {}
        for ch_name, ch_cap in self.policy.channel_caps.items():
            channels[ch_name] = ChannelState(
                channel=ch_name,
                accumulator=0.0,
                cap=ch_cap,
                is_contributing=False,
                last_updated=created_at,
            )

        return RiskState(
            session_id=session_id,
            current_score=0.0,
            current_tier=Tier.CLEAR,
            candidate_tier=Tier.CLEAR,
            candidate_tier_since=created_at,
            channels=channels,
            contributing_channels=[],
            corroboration_multiplier=1.0,
            last_updated=created_at,
            observation_history=[],
        )

    def _recalculate_state(self, state: RiskState, current_time: float) -> None:
        """Recalculate decayed channel accumulators, score, and tier hysteresis in place."""
        half_life = self.policy.half_life_seconds
        epsilon = self.policy.contributing_epsilon

        # Prune ancient observations (> 10 half-lives old = decayed by 99.9%)
        cutoff_time = current_time - (10 * half_life)
        state.observation_history = [
            p for p in state.observation_history if p.observation.timestamp >= cutoff_time
        ]

        # 1. Calculate decayed channel accumulators: A_c(t) = min(K_c, sum_i w_i * 2^(-dt/H))
        contributing_channels: List[str] = []
        total_channel_sum = 0.0

        for ch_name, ch_cap in self.policy.channel_caps.items():
            uncapped_sum = 0.0
            for p in state.observation_history:
                if p.channel == ch_name:
                    dt = current_time - p.observation.timestamp
                    if dt >= 0:
                        decay_factor = 2.0 ** (-dt / half_life)
                        uncapped_sum += p.raw_weight * decay_factor

            # Apply channel cap
            capped_val = min(ch_cap, uncapped_sum)
            is_active = capped_val > epsilon

            if ch_name not in state.channels:
                state.channels[ch_name] = ChannelState(
                    channel=ch_name,
                    accumulator=capped_val,
                    cap=ch_cap,
                    is_contributing=is_active,
                    last_updated=current_time,
                )
            else:
                ch_state = state.channels[ch_name]
                ch_state.accumulator = capped_val
                ch_state.is_contributing = is_active
                ch_state.last_updated = current_time

            total_channel_sum += capped_val
            if is_active:
                contributing_channels.append(ch_name)

        state.contributing_channels = contributing_channels
        m = len(contributing_channels)

        # 2. Corroboration multiplier: 1 + lambda * (m - 1) for m >= 1
        if m >= 1:
            multiplier = 1.0 + self.policy.corroboration_lambda * (m - 1)
        else:
            multiplier = 1.0

        state.corroboration_multiplier = multiplier

        # 3. Total Risk Score R(t) = min(100, (sum_c A_c) * multiplier)
        raw_score = total_channel_sum * multiplier
        final_score = min(100.0, max(0.0, raw_score))
        state.current_score = round(final_score, 4)
        state.last_updated = current_time

        # 4. Instantaneous Candidate Tier from Score
        raw_candidate = self._score_to_tier(state.current_score)

        # 5. Apply 6-Second Hysteresis Hold
        self._apply_hysteresis(state, raw_candidate, current_time)

    def _score_to_tier(self, score: float) -> Tier:
        """Map raw score to candidate Tier based on policy thresholds."""
        thresholds = self.policy.tier_thresholds
        if score >= thresholds.get("HELD", 80.0):
            return Tier.HELD
        if score >= thresholds.get("ELEVATED", 65.0):
            return Tier.ELEVATED
        if score >= thresholds.get("WARNED", 45.0):
            return Tier.WARNED
        if score >= thresholds.get("WATCHING", 25.0):
            return Tier.WATCHING
        return Tier.CLEAR

    def _apply_hysteresis(
        self,
        state: RiskState,
        raw_candidate: Tier,
        current_time: float,
    ) -> None:
        """Enforce the hysteresis hold rule before committing a tier transition."""
        hold_required = self.policy.hysteresis_seconds

        if raw_candidate == state.current_tier:
            # Score matches currently active tier; stable state
            state.candidate_tier = raw_candidate
            state.candidate_tier_since = current_time
            return

        # Candidate tier differs from currently active tier
        if raw_candidate != state.candidate_tier:
            # A new candidate has emerged; reset the holding clock
            state.candidate_tier = raw_candidate
            state.candidate_tier_since = current_time
        else:
            # Same candidate tier is holding steady; check if held >= hysteresis_seconds
            elapsed = current_time - state.candidate_tier_since
            if elapsed >= hold_required:
                state.current_tier = raw_candidate
                state.candidate_tier_since = current_time
