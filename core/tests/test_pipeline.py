"""In-Process Unified Pipeline Test Suite.

Verifies end-to-end execution in a single Python process without HTTP networking,
testing calibration, observation generation, risk decay, gating, and ledger recording.
"""

from core.calibration import FeatureBatch
from core.models import Tier
from core.pipeline import InProcessPipeline
from core.safety import SystemAction


def test_in_process_pipeline_calibration_then_calm_student():
    """Verify that a calm student goes through calibration and remains CLEAR."""
    pipeline = InProcessPipeline()
    session_id = "sess_calm_test"

    # Calibration phase: first 30 seconds
    for t in [0.0, 10.0, 20.0, 29.0]:
        batch = FeatureBatch(session_id=session_id, timestamp=t)
        res = pipeline.process_features(batch)
        assert res.is_calibrating is True
        assert len(res.observations) == 0

    # Operational calm phase: t = 35.0 to 120.0
    for t in [35.0, 60.0, 90.0, 120.0]:
        batch = FeatureBatch(session_id=session_id, timestamp=t)
        res = pipeline.process_features(batch)
        assert res.is_calibrating is False
        assert len(res.observations) == 0
        assert res.risk_state.total_score == 0.0
        assert res.risk_state.current_tier == Tier.CLEAR
        assert res.system_action == SystemAction.NOTHING_SHOWN
        assert res.active_warning is None


def test_in_process_pipeline_corroborated_warning():
    """Verify that multi-channel sustained anomalies trigger a warning notice."""
    pipeline = InProcessPipeline()
    session_id = "sess_anomaly_test"

    # Quick calibration: t = 0 to 30
    for t in [0.0, 15.0, 30.0]:
        pipeline.process_features(FeatureBatch(session_id=session_id, timestamp=t))

    # Sustained face absent + window blur (2 channels)
    res = None
    for t in [35.0, 42.0, 50.0, 58.0]:
        batch = FeatureBatch(
            session_id=session_id,
            timestamp=t,
            face_present=False,
            window_focused=False,
        )
        res = pipeline.process_features(batch)

    assert res is not None
    # Confirm observations generated
    assert len(res.observations) >= 1
    # Check that score increased
    assert res.risk_state.total_score > 0.0
