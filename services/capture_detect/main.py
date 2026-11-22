"""Capture-Detect Microservice (Port 8001).

Accepts sensory feature batches from client browsers (MediaPipe WASM + Web Audio),
maintains per-session calibration baselines, and generates calibrated Observation objects.
"""

from __future__ import annotations

import time
from typing import List

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.calibration import CalibrationDetector, FeatureBatch
from core.ledger import SQLAlchemyLedgerRepository
from core.models import Observation
from shared.config import get_settings
from shared.logging import setup_json_logging
from shared.metrics import MetricsRegistry

settings = get_settings()
logger = setup_json_logging(service_name="capture-detect", log_level=settings.log_level)
metrics = MetricsRegistry(service_name="capture-detect")

app = FastAPI(
    title="Custodian AI — Capture & Detect Service",
    description="Sensory feature ingestion, baseline calibration, and observation generation.",
    version="0.1.0",
)

# CORS configuration for Vite React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

detector = CalibrationDetector()
repo = SQLAlchemyLedgerRepository(database_url=settings.database_url)
repo.init_db()
http_client = httpx.Client(timeout=0.6)


class ProcessFeaturesResponse(BaseModel):
    """Result of sensory feature processing and calibration check."""

    session_id: str
    timestamp: float
    is_calibrating: bool = Field(..., description="True if within initial 30s calibration window")
    calibration_progress: float = Field(..., description="Progress from 0.0 to 1.0")
    observations: List[Observation] = Field(default_factory=list)


class CalibrationPayload(BaseModel):
    """Client-computed 30-second baseline statistics."""

    session_id: str
    mean_gaze_offset: float = 0.15
    std_gaze_offset: float = 0.05
    mean_head_yaw: float = 0.0
    std_head_yaw: float = 0.08
    mean_head_pitch: float = 0.0
    std_head_pitch: float = 0.08
    mean_face_size: float = 0.35
    std_face_size: float = 0.05
    sample_count: int = 150


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    metrics.inc("http_requests_total", label_key="status", label_val=str(response.status_code))
    logger.info(
        f"{request.method} {request.url.path} -> {response.status_code} ({duration:.4f}s)"
    )
    return response


@app.get("/health")
def health_check():
    """Liveness and readiness health probe."""
    return {"status": "ok", "service": "capture-detect", "port": settings.capture_detect_port}


@app.get("/metrics")
def get_metrics():
    """Prometheus exposition telemetry."""
    return Response(content=metrics.to_prometheus_text(), media_type="text/plain")


@app.post("/calibration")
def register_calibration(payload: CalibrationPayload):
    """Accept client-computed 30-second baseline and activate operational detection immediately."""
    baseline = detector.get_or_create_baseline(payload.session_id, time.time())
    baseline.is_calibrated = True
    baseline.start_time = time.time() - 35.0  # Window elapsed
    baseline.gaze_threshold = max(0.25, payload.mean_gaze_offset + 0.20)
    baseline.yaw_threshold = max(18.0, payload.mean_head_yaw + 15.0)
    baseline.pitch_threshold = max(15.0, payload.mean_head_pitch + 12.0)
    detector.save_baseline(payload.session_id, baseline)
    logger.info(f"Registered personal calibration baseline for session: {payload.session_id}")
    return {"status": "calibrated", "session_id": payload.session_id}


@app.post("/features", response_model=ProcessFeaturesResponse)
def ingest_features(batch: FeatureBatch):
    """Process a sensory feature batch, record observations to ledger, and forward."""
    is_calibrating, progress, observations = detector.process_features(batch)
    metrics.inc("observations_generated_total", amount=float(len(observations)))

    if observations:
        # 1. Append observations to append-only ledger
        for obs in observations:
            try:
                repo.append_observation(
                    session_id=obs.session_id,
                    signal=obs.signal,
                    confidence=obs.confidence,
                    duration=obs.duration,
                    timestamp=obs.timestamp,
                )
            except Exception as e:
                logger.debug(f"Failed to record observation to ledger: {e}")

        # 2. Forward to investigator and risk-engine
        for obs in observations:
            case_opened = False
            try:
                inv_res = http_client.post(
                    f"{settings.investigator_url}/evaluate",
                    json=obs.model_dump(),
                )
                if inv_res.status_code == 200 and inv_res.json().get("case_opened"):
                    case_opened = True
            except Exception as e:
                logger.debug(f"Investigator evaluate call skipped: {e}")

            if not case_opened:
                try:
                    http_client.post(
                        f"{settings.risk_engine_url}/observe",
                        json=obs.model_dump(),
                    )
                except Exception as e:
                    logger.debug(f"Risk engine observe call skipped: {e}")

        # 3. Check updated score and evaluate tier gating
        try:
            state_res = http_client.get(
                f"{settings.risk_engine_url}/state/{batch.session_id}"
            )
            if state_res.status_code == 200:
                risk_state = state_res.json()
                http_client.post(
                    f"{settings.warn_escalate_url}/evaluate",
                    json={
                        "session_id": batch.session_id,
                        "score": risk_state["total_score"],
                        "current_tier": risk_state["current_tier"],
                        "candidate_tier": risk_state["candidate_tier"],
                        "contributing_channels": risk_state["contributing_channels"],
                        "recent_signal": observations[-1].signal,
                        "recent_duration": observations[-1].duration,
                        "timestamp": batch.timestamp,
                    },
                )
        except Exception as e:
            logger.debug(f"Tier gating evaluate call skipped: {e}")

    return ProcessFeaturesResponse(
        session_id=batch.session_id,
        timestamp=batch.timestamp,
        is_calibrating=is_calibrating,
        calibration_progress=progress,
        observations=observations,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=settings.capture_detect_port, log_config=None)
