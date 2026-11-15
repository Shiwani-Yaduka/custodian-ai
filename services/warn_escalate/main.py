"""Warn-Escalate Microservice (Port 8004).

Enforces procedural escalation gates and 6-second hysteresis hold, generates
polite accusation-free student notices, and records all approved/blocked transitions
in the append-only evidence ledger.
"""

from __future__ import annotations

import time
from typing import List, Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.gating import evaluate_escalation_gate
from core.ledger import SQLAlchemyLedgerRepository
from core.models import Tier
from core.safety import SystemAction, determine_system_action
from core.warnings import format_warning_message
from shared.config import get_settings
from shared.logging import setup_json_logging
from shared.metrics import MetricsRegistry

settings = get_settings()
logger = setup_json_logging(service_name="warn-escalate", log_level=settings.log_level)
metrics = MetricsRegistry(service_name="warn-escalate")

app = FastAPI(
    title="Custodian AI — Warn & Escalate Service",
    description="Procedural gating, hysteresis, student warning notices, and hold referrals.",
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
repo.init_db()


class EvaluateTierRequest(BaseModel):
    """Payload to evaluate a candidate tier against procedural gates."""

    session_id: str
    score: float
    current_tier: Tier
    candidate_tier: Tier
    contributing_channels: List[str] = Field(default_factory=list)
    recent_signal: str = "face_absent"
    recent_duration: float = 20.0
    timestamp: Optional[float] = None


class EvaluateTierResponse(BaseModel):
    """Result of gating evaluation and escalation determination."""

    session_id: str
    approved: bool
    target_tier: Tier
    current_tier: Tier
    candidate_tier: Tier
    score: float
    system_action: SystemAction
    active_warning: Optional[str] = None
    reason: str
    blocked_reason: Optional[str] = None


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
    return {"status": "ok", "service": "warn-escalate", "port": settings.warn_escalate_port}


@app.get("/metrics")
def get_metrics():
    return Response(content=metrics.to_prometheus_text(), media_type="text/plain")


@app.post("/evaluate", response_model=EvaluateTierResponse)
def evaluate_tier(req: EvaluateTierRequest):
    """Evaluate candidate tier against qualitative gates and record decisions in ledger."""
    ts = req.timestamp if req.timestamp is not None else time.time()

    # Query ledger for session history
    warnings_shown = repo.get_warnings(req.session_id)
    warnings_count = len(warnings_shown)

    cases = repo.get_cases(req.session_id)
    deliberate_cases_count = sum(1 for c in cases if c.resolution == "deliberate")

    # Evaluate procedural gate
    gating = evaluate_escalation_gate(
        candidate_tier=req.candidate_tier,
        current_tier=req.current_tier,
        score=req.score,
        contributing_channels=req.contributing_channels,
        warnings_shown_count=warnings_count,
        deliberate_cases_p85_count=deliberate_cases_count,
    )

    active_warning: Optional[str] = None

    if gating.approved and gating.target_tier != req.current_tier:
        new_tier = gating.target_tier

        # Generate polite notice if entering WARNED or ELEVATED
        if new_tier == Tier.WARNED:
            msg = format_warning_message(
                signal_name=req.recent_signal,
                duration=req.recent_duration,
                warning_number=1,
            )
            repo.append_warning(
                session_id=req.session_id,
                warning_number=1,
                message=msg,
                timestamp=ts,
            )
            active_warning = msg
            metrics.inc("warnings_issued_total")
        elif new_tier == Tier.ELEVATED:
            msg = format_warning_message(
                signal_name=req.recent_signal,
                duration=req.recent_duration,
                warning_number=2,
            )
            repo.append_warning(
                session_id=req.session_id,
                warning_number=2,
                message=msg,
                timestamp=ts,
            )
            active_warning = msg
            metrics.inc("warnings_issued_total")
        elif new_tier == Tier.HELD:
            repo.append_hold(
                session_id=req.session_id,
                evidence_summary=gating.reason,
                paused_at=ts,
            )
            repo.update_session_status(session_id=req.session_id, status="held")
            metrics.inc("holds_initiated_total")

        # Record approved escalation decision in ledger
        repo.append_decision(
            session_id=req.session_id,
            decision_type="TIER_TRANSITION",
            score=req.score,
            from_tier=req.current_tier.value,
            to_tier=new_tier.value,
            candidate_tier=req.candidate_tier.value,
            gate_passed=True,
            reason=gating.reason,
            blocked_reason=None,
            timestamp=ts,
        )
    elif not gating.approved:
        # Record blocked escalation in ledger
        repo.append_decision(
            session_id=req.session_id,
            decision_type="BLOCKED_ESCALATION",
            score=req.score,
            from_tier=req.current_tier.value,
            to_tier=gating.target_tier.value,
            candidate_tier=gating.candidate_tier.value,
            gate_passed=False,
            reason=gating.reason,
            blocked_reason=gating.blocked_reason,
            timestamp=ts,
        )
        metrics.inc("escalations_blocked_total")

    action = determine_system_action(gating.target_tier)

    return EvaluateTierResponse(
        session_id=req.session_id,
        approved=gating.approved,
        target_tier=gating.target_tier,
        current_tier=req.current_tier,
        candidate_tier=req.candidate_tier,
        score=req.score,
        system_action=action,
        active_warning=active_warning,
        reason=gating.reason,
        blocked_reason=gating.blocked_reason,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=settings.warn_escalate_port, log_config=None)
