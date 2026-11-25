"""Investigator Microservice (Port 8003).

Manages Bayesian investigation lifecycle: opens cases under uncertainty,
holds back weight, selects probes using Expected Information Gain, coordinates
interactive client browser probes via polling, and determines resolutions.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.investigator import (
    CaseResolution,
    InvestigationCase,
    InvestigatorAgent,
    ProbeConfig,
    ScriptedProbeRunner,
    load_investigator_policy,
)
from core.ledger import SQLAlchemyLedgerRepository
from core.models import Observation
from shared.config import get_settings
from shared.logging import setup_json_logging
from shared.metrics import MetricsRegistry

settings = get_settings()
logger = setup_json_logging(service_name="investigator", log_level=settings.log_level)
metrics = MetricsRegistry(service_name="investigator")

app = FastAPI(
    title="Custodian AI — Bayesian Investigator Service",
    description="Bayesian case lifecycle, EIG probe selection, and browser probe coordination.",
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

repo = SQLAlchemyLedgerRepository(database_url=settings.database_url)
try:
    repo.init_db()
except Exception as e:
    logger.warning(f"Initial database initialization deferred: {e}")

inv_policy = load_investigator_policy()
# Default runner for automated background probes
default_runner = ScriptedProbeRunner(script={"device_telemetry_check": "hardware_normal"})
agent = InvestigatorAgent(policy=inv_policy, probe_runner=default_runner)

# Polling channel storage: session_id -> list of pending interactive probe requests
pending_client_probes: Dict[str, List[ProbeConfig]] = {}


class EvaluateObservationResponse(BaseModel):
    """Result of evaluating an observation for case opening."""

    case_opened: bool
    case: Optional[InvestigationCase] = None
    held_weight: float = 0.0


class ProbeResponsePayload(BaseModel):
    """Outcome reported by browser or client after executing a probe."""

    case_id: str
    probe_name: str
    outcome: str
    timestamp: Optional[float] = None


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
    return {"status": "ok", "service": "investigator", "port": settings.investigator_port}


@app.get("/metrics")
def get_metrics():
    return Response(content=metrics.to_prometheus_text(), media_type="text/plain")


@app.post("/evaluate", response_model=EvaluateObservationResponse)
def evaluate_observation(obs: Observation):
    """Evaluate whether an observation requires opening an investigation case."""
    case = agent.evaluate_observation(obs)
    if case:
        metrics.inc("cases_opened_total")

        # Record case opening in ledger
        repo.append_case(
            case_id=case.case_id,
            session_id=case.session_id,
            observation_id=None,
            open_reason=case.open_reason,
            opened_at=case.opened_at,
        )

        # Check next probe
        next_probe = agent.select_next_probe(case)
        if next_probe and next_probe.cost >= 0.7:  # Client interactive probe
            pending_client_probes.setdefault(obs.session_id, []).append(next_probe)

        return EvaluateObservationResponse(
            case_opened=True,
            case=case,
            held_weight=case.held_raw_weight,
        )
    return EvaluateObservationResponse(case_opened=False, case=None, held_weight=0.0)


@app.get("/probes/pending/{session_id}", response_model=List[ProbeConfig])
def poll_pending_probes(session_id: str):
    """Polling channel for client browser to retrieve interactive probes."""
    probes = pending_client_probes.pop(session_id, [])
    return probes


@app.post("/probes/respond", response_model=Dict[str, Optional[CaseResolution]])
def respond_probe(payload: ProbeResponsePayload):
    """Client delivers probe outcome, triggers Bayesian update, and evaluates resolution."""
    case = agent.get_case(payload.case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    ts = payload.timestamp if payload.timestamp is not None else time.time()
    resolution = agent.apply_probe_outcome(
        case=case,
        probe_name=payload.probe_name,
        outcome=payload.outcome,
        timestamp=ts,
    )

    probe_def = inv_policy.probes.get(payload.probe_name)
    probe_cost = probe_def.cost if probe_def else 0.5
    repo.append_probe(
        case_id=case.case_id,
        probe_name=payload.probe_name,
        cost=probe_cost,
        outcome=payload.outcome,
        prior_json=str(case.current_belief),
        posterior_json=str(case.current_belief),
        executed_at=ts,
    )

    if resolution:
        repo.resolve_case(
            case_id=case.case_id,
            resolution=resolution.status.value,
            multiplier=resolution.multiplier,
            resolved_at=resolution.resolved_at,
        )

    metrics.inc("probes_executed_total")
    return {"resolution": resolution}


@app.post("/cases/{case_id}/run", response_model=CaseResolution)
def run_case_automated(case_id: str):
    """Execute all investigative probes automatically until resolution."""
    resolution = agent.run_investigation(case_id)
    case = agent.get_case(case_id)
    if case:
        for p_rec in case.probe_history:
            repo.append_probe(
                case_id=case.case_id,
                probe_name=p_rec.probe_name,
                cost=p_rec.cost,
                outcome=p_rec.outcome,
                prior_json=str(p_rec.prior_belief),
                posterior_json=str(p_rec.posterior_belief),
                executed_at=p_rec.executed_at,
            )
        repo.resolve_case(
            case_id=case.case_id,
            resolution=resolution.status.value,
            multiplier=resolution.multiplier,
            resolved_at=resolution.resolved_at,
        )
    metrics.inc("cases_resolved_total")
    return resolution


@app.get("/cases/{session_id}", response_model=List[InvestigationCase])
def list_session_cases(session_id: str):
    """Retrieve all open and resolved cases for a session."""
    return agent.get_session_cases(session_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=settings.investigator_port, log_config=None)
