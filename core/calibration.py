"""Calibration and Sensory Feature Processing Module.

Processes raw sensory feature batches from client browser (MediaPipe WASM + Web Audio),
manages the 30-second initial student baseline calibration, and converts normalized
features into calibrated Observation objects with confidence estimation.
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

from pydantic import BaseModel, Field

from core.models import Observation


class FeatureBatch(BaseModel):
    """Raw sensory measurements emitted by client browser."""

    session_id: str
    timestamp: float
    face_present: bool = True
    face_count: int = 1
    gaze_offset_x: float = 0.0  # Normalized deviation from screen center (-1.0 to 1.0)
    gaze_offset_y: float = 0.0
    head_pitch: float = 0.0  # Degrees (-90 to +90)
    head_yaw: float = 0.0
    head_roll: float = 0.0
    window_focused: bool = True
    tab_visible: bool = True
    audio_level: float = 0.0  # RMS audio volume level (0.0 to 1.0)
    network_heartbeat_ok: bool = True
    camera_track_active: bool = True
    fps: float = 30.0
    ambient_light: float = 0.8  # Estimated illumination (0.0 dark to 1.0 bright)


class CalibrationBaseline(BaseModel):
    """Learned student baseline measurements during the initial 30 seconds."""

    session_id: str
    start_time: float
    is_calibrated: bool = False
    samples_count: int = 0
    gaze_samples: List[float] = Field(default_factory=list)
    yaw_samples: List[float] = Field(default_factory=list)
    pitch_samples: List[float] = Field(default_factory=list)

    # Dynamic thresholds learned from student
    gaze_threshold: float = 0.35  # Max radial deviation before gaze_off_screen
    yaw_threshold: float = 25.0  # Degrees head turn
    pitch_threshold: float = 20.0


class CalibrationDetector:
    """Manages session calibration baselines and feature-to-observation conversion."""

    def __init__(self, calibration_window_seconds: float = 30.0):
        self.calibration_window_seconds = calibration_window_seconds
        self._baselines: Dict[str, CalibrationBaseline] = {}
        # Track persistent signal durations per session: (session_id, signal_name) -> start_time
        self._active_signals: Dict[Tuple[str, str], float] = {}

    def get_or_create_baseline(self, session_id: str, timestamp: float) -> CalibrationBaseline:
        if session_id not in self._baselines:
            self._baselines[session_id] = CalibrationBaseline(
                session_id=session_id,
                start_time=timestamp,
            )
        return self._baselines[session_id]

    def process_features(
        self, batch: FeatureBatch
    ) -> Tuple[bool, float, List[Observation]]:
        """Ingest raw sensory features.

        Returns:
            (is_calibrating, calibration_progress, generated_observations)
        """
        baseline = self.get_or_create_baseline(batch.session_id, batch.timestamp)
        elapsed = batch.timestamp - baseline.start_time

        # 1. Calibration Phase (First 30 seconds)
        if elapsed < self.calibration_window_seconds:
            radial_gaze = math.sqrt(batch.gaze_offset_x**2 + batch.gaze_offset_y**2)
            baseline.gaze_samples.append(radial_gaze)
            baseline.yaw_samples.append(abs(batch.head_yaw))
            baseline.pitch_samples.append(abs(batch.head_pitch))
            baseline.samples_count += 1

            progress = min(1.0, elapsed / self.calibration_window_seconds)
            return True, progress, []

        # Finalize calibration once window expires
        if not baseline.is_calibrated:
            baseline.is_calibrated = True
            if baseline.gaze_samples:
                mean_gaze = sum(baseline.gaze_samples) / len(baseline.gaze_samples)
                baseline.gaze_threshold = max(0.25, mean_gaze + 0.20)
            if baseline.yaw_samples:
                mean_yaw = sum(baseline.yaw_samples) / len(baseline.yaw_samples)
                baseline.yaw_threshold = max(18.0, mean_yaw + 15.0)
            if baseline.pitch_samples:
                mean_pitch = sum(baseline.pitch_samples) / len(baseline.pitch_samples)
                baseline.pitch_threshold = max(15.0, mean_pitch + 12.0)

        # 2. Operational Detection Phase
        observations: List[Observation] = []

        # Confidence modifiers based on environmental factors
        base_confidence = 1.0
        if batch.ambient_light < 0.30:
            base_confidence *= 0.65  # Poor lighting lowers confidence
        if batch.fps < 2.5:
            base_confidence *= 0.70  # Low frame rate introduces jitter uncertainty

        def track_duration(signal: str, is_active: bool) -> float:
            key = (batch.session_id, signal)
            if is_active:
                if key not in self._active_signals:
                    self._active_signals[key] = batch.timestamp
                return max(1.0, batch.timestamp - self._active_signals[key])
            else:
                self._active_signals.pop(key, None)
                return 0.0

        # Check: Face Absent
        dur_face_absent = track_duration("face_absent", not batch.face_present)
        if not batch.face_present:
            observations.append(
                Observation(
                    session_id=batch.session_id,
                    signal="face_absent",
                    confidence=max(0.40, base_confidence * 0.95),
                    duration=dur_face_absent,
                    timestamp=batch.timestamp,
                )
            )

        # Check: Multiple Faces
        dur_multi = track_duration("multiple_faces", batch.face_count > 1)
        if batch.face_count > 1:
            observations.append(
                Observation(
                    session_id=batch.session_id,
                    signal="multiple_faces",
                    confidence=max(0.45, base_confidence * 0.90),
                    duration=dur_multi,
                    timestamp=batch.timestamp,
                )
            )

        # Check: Gaze Off-Screen (relative to calibrated baseline)
        radial_gaze = math.sqrt(batch.gaze_offset_x**2 + batch.gaze_offset_y**2)
        is_gaze_off = batch.face_present and (radial_gaze > baseline.gaze_threshold)
        dur_gaze = track_duration("gaze_off_screen", is_gaze_off)
        if is_gaze_off:
            observations.append(
                Observation(
                    session_id=batch.session_id,
                    signal="gaze_off_screen",
                    confidence=max(0.40, base_confidence * 0.85),
                    duration=dur_gaze,
                    timestamp=batch.timestamp,
                )
            )

        # Check: Head Turn (relative to calibrated baseline)
        is_head_turned = batch.face_present and (
            abs(batch.head_yaw) > baseline.yaw_threshold
            or abs(batch.head_pitch) > baseline.pitch_threshold
        )
        dur_head = track_duration("head_turn", is_head_turned)
        if is_head_turned:
            observations.append(
                Observation(
                    session_id=batch.session_id,
                    signal="head_turn",
                    confidence=max(0.40, base_confidence * 0.85),
                    duration=dur_head,
                    timestamp=batch.timestamp,
                )
            )

        # Check: Speech Detected
        is_speech = batch.audio_level > 0.45
        dur_speech = track_duration("speech_detected", is_speech)
        if is_speech:
            observations.append(
                Observation(
                    session_id=batch.session_id,
                    signal="speech_detected",
                    confidence=0.88,
                    duration=dur_speech,
                    timestamp=batch.timestamp,
                )
            )

        # Check: Window Blur (Exam Window)
        dur_blur = track_duration("window_blur", not batch.window_focused)
        if not batch.window_focused:
            observations.append(
                Observation(
                    session_id=batch.session_id,
                    signal="window_blur",
                    confidence=1.0,  # OS window events are deterministic
                    duration=dur_blur,
                    timestamp=batch.timestamp,
                )
            )

        # Check: Tab Hidden
        dur_tab = track_duration("tab_hidden", not batch.tab_visible)
        if not batch.tab_visible:
            observations.append(
                Observation(
                    session_id=batch.session_id,
                    signal="tab_hidden",
                    confidence=1.0,
                    duration=dur_tab,
                    timestamp=batch.timestamp,
                )
            )

        # Check: Network Drop
        dur_net = track_duration("network_drop", not batch.network_heartbeat_ok)
        if not batch.network_heartbeat_ok:
            observations.append(
                Observation(
                    session_id=batch.session_id,
                    signal="network_drop",
                    confidence=0.92,
                    duration=dur_net,
                    timestamp=batch.timestamp,
                )
            )

        # Check: Camera Track Ended
        dur_cam = track_duration("camera_track_ended", not batch.camera_track_active)
        if not batch.camera_track_active:
            observations.append(
                Observation(
                    session_id=batch.session_id,
                    signal="camera_track_ended",
                    confidence=0.95,
                    duration=dur_cam,
                    timestamp=batch.timestamp,
                )
            )

        # Check: Low Frame Rate (threshold tuned for laptop-light 5 fps proctoring)
        dur_fps = track_duration("low_frame_rate", batch.fps < 2.5)
        if batch.fps < 2.5:
            observations.append(
                Observation(
                    session_id=batch.session_id,
                    signal="low_frame_rate",
                    confidence=0.90,
                    duration=dur_fps,
                    timestamp=batch.timestamp,
                )
            )

        return False, 1.0, observations
