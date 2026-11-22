"""Risk Engine Microservice (Port 8002).

Applies sensory observations to decaying capped channel accumulators, maintains
session state in StateStore, and returns risk scores, candidate tiers, and channel breakdowns.
"""

from __future__ import annotations

import time
from typing import Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.models import Observation, RiskState
from core.policy import load_policy
from core.risk import RiskEngine
from core.state import InMemoryStateStore, RedisStateStore
from shared.config import get_settings
from shared.logging import setup_json_logging
from shared.metrics import MetricsRegistry

settings = get_settings()
logger = setup_json_logging(service_name="risk-engine", log_level=settings.log_level)
metrics = MetricsRegistry(service_name="risk-engine")

app = FastAPI(
    title="Custodian AI — Risk Engine Service",
    description="Decaying capped sensory accumulation, corroboration, and score tracking.",
    version="0.1.0",
)

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

policy = load_policy()
state_store = (
    RedisStateStore(redis_url=settings.redis_url)
    if settings.state_store == "redis"
    else InMemoryStateStore()
)
engine = RiskEngine(policy=policy, state_store=state_store)


class ApplyResolutionPayload(BaseModel):
    """Payload to apply an observation weight released from an investigation."""

    session_id: str
    signal: str
    effective_weight: float = Field(
        ...,
        description="Held weight multiplied by resolution multiplier",
    )
    timestamp: float


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
    return {"status": "ok", "service": "risk-engine", "port": settings.risk_engine_port}


@app.get("/metrics")
def get_metrics():
    return Response(content=metrics.to_prometheus_text(), media_type="text/plain")


@app.post("/observe", response_model=RiskState)
def ingest_observation(obs: Observation):
    """Apply an observation directly to the decaying risk accumulators."""
    engine.apply_observation(obs)
    state = engine.get_state(obs.session_id, now=obs.timestamp)
    metrics.inc("observations_applied_total")
    return state


@app.get("/state/{session_id}", response_model=RiskState)
def get_session_state(session_id: str, now: Optional[float] = None):
    """Query current risk state, score, candidate tier, and channel breakdown."""
    ts = now if now is not None else time.time()
    return engine.get_state(session_id, now=ts)


@app.post("/apply_resolution", response_model=RiskState)
def apply_case_resolution(payload: ApplyResolutionPayload):
    """Apply weight released from a closed investigation case."""
    if payload.effective_weight > 0.0:
        obs = Observation(
            session_id=payload.session_id,
            signal=payload.signal,
            confidence=1.0,
            duration=1.0,
            timestamp=payload.timestamp,
        )
        engine.apply_observation(obs)
    return engine.get_state(payload.session_id, now=payload.timestamp)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=settings.risk_engine_port, log_config=None)
