"""Capture-Detect Microservice (Port 8001).

Accepts sensory feature batches from client browsers (MediaPipe WASM + Web Audio),
maintains per-session calibration baselines, and generates calibrated Observation objects.
"""

from __future__ import annotations

import time
from typing import List

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.calibration import CalibrationDetector, FeatureBatch
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


class ProcessFeaturesResponse(BaseModel):
    """Result of sensory feature processing and calibration check."""

    session_id: str
    timestamp: float
    is_calibrating: bool = Field(..., description="True if within initial 30s calibration window")
    calibration_progress: float = Field(..., description="Progress from 0.0 to 1.0")
    observations: List[Observation] = Field(default_factory=list)


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


@app.post("/features", response_model=ProcessFeaturesResponse)
def ingest_features(batch: FeatureBatch):
    """Process a sensory feature batch and return any detected observations."""
    is_calibrating, progress, observations = detector.process_features(batch)
    metrics.inc("observations_generated_total", amount=float(len(observations)))
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
