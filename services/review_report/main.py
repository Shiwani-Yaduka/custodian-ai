"""Review-Report Microservice (Port 8005).

Provides:
- Authentication & JWT token issuing (student1, student2, faculty1 demo accounts)
- Exam management & session initialization
- Student-facing transparent evidence record reader & explanation submission
- Faculty review portal for held sessions, audit timelines, determinations, and reports
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from core.ledger import (
    FacultyTimeline,
    SQLAlchemyLedgerRepository,
    StudentRecord,
    build_faculty_timeline,
    build_student_record,
)
from core.ledger.report import generate_faculty_html_report
from core.scenarios import SCENARIOS_META, ScenarioResult, ScenarioRunner
from shared.auth import create_access_token, decode_access_token, hash_password, verify_password
from shared.config import get_settings
from shared.logging import setup_json_logging
from shared.metrics import MetricsRegistry

settings = get_settings()
logger = setup_json_logging(service_name="review-report", log_level=settings.log_level)
metrics = MetricsRegistry(service_name="review-report")

app = FastAPI(
    title="Custodian AI — Review & Report Service",
    description="Authentication, student record ledger, and faculty decision review portal.",
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

security = HTTPBearer(auto_error=False)


# --- Schemas ---


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class StartSessionRequest(BaseModel):
    exam_id: int
    session_id: Optional[str] = None


class ExplanationRequest(BaseModel):
    session_id: str
    explanation_text: str = Field(..., min_length=2)


class FacultyDecisionRequest(BaseModel):
    session_id: str
    verdict: str = Field(..., description="'cleared', 'warning_stands', or 'refer_onward'")
    notes: str = ""


# --- Auth Dependency ---


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, Any]:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required",
        )
    try:
        payload = decode_access_token(credentials.credentials)
        return payload
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        ) from e


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
    return {"status": "ok", "service": "review-report", "port": settings.review_report_port}


@app.get("/metrics")
def get_metrics():
    return Response(content=metrics.to_prometheus_text(), media_type="text/plain")


# --- Authentication ---


@app.post("/auth/login", response_model=LoginResponse)
def login(req: LoginRequest):
    """Authenticate user with demo credentials or database record and return JWT."""
    user = repo.get_user(req.username)

    # If user doesn't exist, check against default demo credentials and auto-seed if matched
    if not user:
        demo_map = {
            settings.demo_student1_username: (settings.demo_student1_password, "student"),
            settings.demo_student2_username: (settings.demo_student2_password, "student"),
            settings.demo_faculty1_username: (settings.demo_faculty1_password, "faculty"),
        }
        if req.username in demo_map:
            expected_pwd, role = demo_map[req.username]
            if req.password == expected_pwd:
                hashed = hash_password(expected_pwd)
                user = repo.create_user(req.username, hashed, role=role)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password")

    valid = verify_password(req.password, user.password_hash)
    if not valid:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "role": user.role}
    )
    metrics.inc("logins_total", label_key="role", label_val=user.role)
    return LoginResponse(access_token=token, role=user.role, username=user.username)


# --- Exams & Sessions ---


@app.get("/exams")
def list_exams():
    """List all available exams with questions."""
    exam = repo.get_exam(1)
    if not exam:
        return [
            {
                "id": 1,
                "title": "Demo Exam",
                "description": "Adaptive proctoring demo exam (10 MCQs + 2 Written)",
                "duration_minutes": 30,
                "questions": [],
            }
        ]

    questions = []
    clean_description = "Adaptive proctoring demo exam (10 MCQs + 2 Written Questions)"
    if exam.description:
        try:
            raw = json.loads(exam.description)
            if isinstance(raw, dict):
                for mcq in raw.get("multiple_choice", []):
                    questions.append({
                        "id": f"q{mcq.get('id', len(questions) + 1)}",
                        "type": "mcq",
                        "prompt": mcq.get("question", ""),
                        "options": mcq.get("options", []),
                    })
                for w in raw.get("written_questions", raw.get("written", [])):
                    questions.append({
                        "id": f"q_w{w.get('id', len(questions) + 1)}",
                        "type": "written",
                        "prompt": w.get("question", w.get("prompt", "")),
                    })
            elif isinstance(raw, list):
                questions = raw
        except (json.JSONDecodeError, TypeError) as e:
            logger.debug(f"Description is plain text, not JSON: {e}")
            clean_description = exam.description

    return [
        {
            "id": exam.id,
            "title": exam.title,
            "description": clean_description,
            "duration_minutes": exam.duration_minutes,
            "questions": questions,
        }
    ]


@app.post("/sessions/start")
def start_session(
    req: StartSessionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Start an exam session for the authenticated student."""
    user = repo.get_user(current_user["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    session_id = req.session_id or f"sess-{uuid.uuid4().hex[:8]}"
    existing = repo.get_session(session_id)
    if existing:
        return {"session_id": existing.id, "exam_id": existing.exam_id, "status": existing.status}

    exam = repo.get_exam(req.exam_id)
    if not exam:
        exam = repo.create_exam("Demo Exam", duration_minutes=30)

    sess = repo.create_session(
        session_id=session_id,
        student_id=user.id,
        exam_id=exam.id,
        start_time=time.time(),
    )
    metrics.inc("sessions_started_total")
    return {"session_id": sess.id, "exam_id": exam.id, "status": sess.status}


# --- Student Ledger APIs ---


@app.get("/student/record/{session_id}", response_model=StudentRecord)
def get_student_record(session_id: str):
    """Retrieve transparent, non-accusing student timeline."""
    return build_student_record(session_id, repo)


@app.post("/student/explain")
def submit_explanation(req: ExplanationRequest):
    """Record candidate explanation in the append-only ledger."""
    exp = repo.append_explanation(
        session_id=req.session_id,
        explanation_text=req.explanation_text,
    )
    metrics.inc("student_explanations_total")
    return {"status": "recorded", "explanation_id": exp.id}


# --- Faculty Portal APIs ---


@app.get("/faculty/sessions/held")
def list_held_sessions(current_user: Dict[str, Any] = Depends(get_current_user)):
    """List only sessions currently on hold awaiting human faculty review."""
    if current_user.get("role") != "faculty":
        raise HTTPException(status_code=403, detail="Faculty authorization required")

    holds = repo.get_holds()
    held_sessions = []
    seen = set()
    for h in holds:
        if h.session_id not in seen:
            seen.add(h.session_id)
            sess = repo.get_session(h.session_id)
            held_sessions.append(
                {
                    "session_id": h.session_id,
                    "paused_at": h.paused_at,
                    "evidence_summary": h.evidence_summary,
                    "status": sess.status if sess else "held",
                }
            )
    return held_sessions


@app.get("/faculty/session/{session_id}", response_model=FacultyTimeline)
def get_faculty_session_detail(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Comprehensive technical audit timeline with Bayesian probe logs and stub clip markers."""
    if current_user.get("role") != "faculty":
        raise HTTPException(status_code=403, detail="Faculty authorization required")
    return build_faculty_timeline(session_id, repo)


@app.post("/faculty/decision")
def record_faculty_decision(
    req: FacultyDecisionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Record official human faculty determination in the append-only ledger."""
    if current_user.get("role") != "faculty":
        raise HTTPException(status_code=403, detail="Faculty authorization required")

    user = repo.get_user(current_user["sub"])
    faculty_id = user.id if user else 1

    fdec = repo.append_faculty_decision(
        session_id=req.session_id,
        faculty_id=faculty_id,
        verdict=req.verdict,
        notes=req.notes,
    )

    # If student is cleared, mark session active or completed
    if req.verdict == "cleared":
        repo.update_session_status(session_id=req.session_id, status="active")

    metrics.inc("faculty_decisions_total", label_key="verdict", label_val=req.verdict)
    return {"status": "recorded", "verdict_id": fdec.id}


@app.get("/faculty/report/{session_id}")
def get_faculty_report(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Generate human-readable decision report for faculty download."""
    if current_user.get("role") != "faculty":
        raise HTTPException(status_code=403, detail="Faculty authorization required")

    timeline = build_faculty_timeline(session_id, repo)
    return {
        "report_title": f"Custodian AI Proctoring Audit Report — {session_id}",
        "session_id": session_id,
        "status": timeline.status,
        "peak_risk_score": timeline.peak_risk_score,
        "recommendation": timeline.recommendation,
        "warnings_count": len(timeline.warnings_issued),
        "cases_count": len(timeline.investigation_cases),
        "explanations_count": len(timeline.student_explanations),
        "faculty_decisions": timeline.faculty_decisions,
        "timeline": timeline,
    }


@app.get("/faculty/report/{session_id}/html", response_class=Response)
def get_faculty_report_html(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Generate printable HTML audit report."""
    if current_user.get("role") != "faculty":
        raise HTTPException(status_code=403, detail="Faculty authorization required")

    timeline = build_faculty_timeline(session_id, repo)
    sess = repo.get_session(session_id)
    student_name = "Candidate"
    if sess and sess.student_id:
        user = repo.get_user_by_id(sess.student_id)
        if user:
            student_name = user.username

    html_content = generate_faculty_html_report(
        session_id=session_id,
        student_username=student_name,
        timeline=timeline,
    )
    return Response(content=html_content, media_type="text/html")


# --- Demonstration & Scenario Simulator APIs ---

_mass_flag_state = {
    "triggered": False,
    "notice": "possible platform/network failure, staff alerted",
    "relaxation_factor": 1.5,
    "affected_ratio": 0.40,
    "updated_at": time.time(),
}


@app.get("/system/mass_flag")
def get_mass_flag_status():
    """Retrieve global platform mass-flag relaxation status."""
    return _mass_flag_state


@app.post("/system/mass_flag/toggle")
def toggle_mass_flag(triggered: bool = True):
    """Toggle mass-flag state for demonstration."""
    _mass_flag_state["triggered"] = triggered
    _mass_flag_state["updated_at"] = time.time()
    return _mass_flag_state


@app.get("/scenarios")
def list_scenarios():
    """List all available scripted demonstration scenarios from AGENTS.md Section 9."""
    return SCENARIOS_META


@app.post("/scenarios/run/{scenario_id}", response_model=ScenarioResult)
def run_demo_scenario(scenario_id: str, session_id: Optional[str] = None):
    """Execute a scripted scenario sequence through the real proctoring pipeline."""
    runner = ScenarioRunner(repo=repo)
    try:
        result = runner.run_scenario(scenario_id, session_id=session_id)
        if scenario_id == "mass_flag":
            _mass_flag_state["triggered"] = True
            _mass_flag_state["updated_at"] = time.time()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error executing scenario {scenario_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Scenario execution failed: {e}") from e


@app.post("/scenarios/reset/{session_id}")
def reset_demo_session(session_id: str):
    """Reset a demo session in the database."""
    repo.update_session_status(session_id, "active")
    _mass_flag_state["triggered"] = False
    _mass_flag_state["updated_at"] = time.time()
    return {"status": "reset", "session_id": session_id}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=settings.review_report_port, log_config=None)
