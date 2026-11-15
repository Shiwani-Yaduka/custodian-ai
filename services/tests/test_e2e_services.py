"""End-to-End API Test Suite for Custodian AI Microservices.

Validates the full multi-service proctoring pipeline:
1. Health and telemetry metrics across all 5 services.
2. Student authentication (mock login) and exam session initiation.
3. Feature batch ingestion, calibration, and observation generation on :8001.
4. Risk accumulation, decay, and channel tracking on :8002.
5. Bayesian probe polling and investigation case resolution on :8003.
6. Procedural gating, accusation-free warning generation, and hold referrals on :8004.
7. Transparent student timeline, explanation submission, and faculty portal on :8005.
8. Calm student control test verifying zero false alarms and clean audit record.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from core.models import Tier
from core.safety import SystemAction
from scripts.seed import seed_demo_data
from services.capture_detect.main import app as app_capture
from services.investigator.main import app as app_investigator
from services.review_report.main import app as app_review
from services.risk_engine.main import app as app_risk
from services.warn_escalate.main import app as app_warn
from shared.config import get_settings

settings = get_settings()


@pytest.fixture(scope="module", autouse=True)
def init_db():
    """Ensure database has demo accounts and exam seeded."""
    seed_demo_data()


@pytest.fixture
def client_capture():
    return TestClient(app_capture)


@pytest.fixture
def client_risk():
    return TestClient(app_risk)


@pytest.fixture
def client_investigator():
    return TestClient(app_investigator)


@pytest.fixture
def client_warn():
    return TestClient(app_warn)


@pytest.fixture
def client_review():
    return TestClient(app_review)


def test_all_services_health_and_metrics(
    client_capture, client_risk, client_investigator, client_warn, client_review
):
    """Verify that all 5 microservices respond to /health and expose /metrics."""
    services = [
        (client_capture, "capture-detect", 8001),
        (client_risk, "risk-engine", 8002),
        (client_investigator, "investigator", 8003),
        (client_warn, "warn-escalate", 8004),
        (client_review, "review-report", 8005),
    ]

    for client, name, port in services:
        # /health
        h_resp = client.get("/health")
        assert h_resp.status_code == 200
        h_data = h_resp.json()
        assert h_data["status"] == "ok"
        assert h_data["service"] == name
        assert h_data["port"] == port

        # /metrics
        m_resp = client.get("/metrics")
        assert m_resp.status_code == 200
        assert "custodian_service_info" in m_resp.text
        assert f'service="{name}"' in m_resp.text


def test_student_flow_with_warning_and_explanation(
    client_review, client_capture, client_risk, client_warn
):
    """Test student login, calibration, anomaly detection, warning notice, and explanation."""
    # 1. Student Login
    login_resp = client_review.post(
        "/auth/login",
        json={
            "username": settings.demo_student1_username,
            "password": settings.demo_student1_password,
        },
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    assert token is not None
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Start Exam Session
    session_id = f"e2e_st1_{uuid.uuid4().hex[:6]}"
    session_resp = client_review.post(
        "/sessions/start",
        json={"exam_id": 1, "session_id": session_id},
        headers=headers,
    )
    assert session_resp.status_code == 200
    session_id = session_resp.json()["session_id"]
    assert session_id is not None

    # 3. Calibration Phase on :8001 (t = 0 to 25s)
    cal_resp = client_capture.post(
        "/features",
        json={
            "session_id": session_id,
            "timestamp": 0.0,
            "face_present": True,
            "gaze_offset_x": 0.05,
        },
    )
    assert cal_resp.status_code == 200
    cal_data = cal_resp.json()
    assert cal_data["is_calibrating"] is True
    assert len(cal_data["observations"]) == 0

    # Advance time to finalize calibration (30s window)
    client_capture.post(
        "/features",
        json={"session_id": session_id, "timestamp": 30.5, "face_present": True},
    )

    # 4. Sustained Anomaly Phase (t = 35 to 55s): Face absent + Window blur
    # Start anomaly at t = 35s
    client_capture.post(
        "/features",
        json={
            "session_id": session_id,
            "timestamp": 35.0,
            "face_present": False,
            "window_focused": False,
        },
    )

    # Re-sample at t = 55s (elapsed 20s > grace windows of 5s and 3s)
    feat_resp = client_capture.post(
        "/features",
        json={
            "session_id": session_id,
            "timestamp": 55.0,
            "face_present": False,
            "window_focused": False,
        },
    )
    assert feat_resp.status_code == 200
    feat_data = feat_resp.json()
    assert feat_data["is_calibrating"] is False
    observations = feat_data["observations"]
    assert len(observations) >= 2
    signals = {obs["signal"] for obs in observations}
    assert "face_absent" in signals
    assert "window_blur" in signals

    # 5. Apply observations to Risk Engine (:8002)
    last_risk_state = None
    for obs in observations:
        r_resp = client_risk.post("/observe", json=obs)
        assert r_resp.status_code == 200
        last_risk_state = r_resp.json()

    assert last_risk_state is not None
    assert last_risk_state["current_score"] > 0.0

    # 6. Evaluate Tier Gating on :8004
    eval_resp = client_warn.post(
        "/evaluate",
        json={
            "session_id": session_id,
            "score": 52.0,  # Simulated escalated score into WARNED tier
            "current_tier": Tier.WATCHING.value,
            "candidate_tier": Tier.WARNED.value,
            "contributing_channels": ["camera", "exam_window"],
            "recent_signal": "face_absent",
            "recent_duration": 25.0,
            "timestamp": 60.0,
        },
    )
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()
    assert eval_data["approved"] is True
    assert eval_data["target_tier"] == Tier.WARNED.value
    assert eval_data["system_action"] == SystemAction.FIRST_WARNING.value
    assert eval_data["active_warning"] is not None
    assert "Notice 1: Your face was not visible" in eval_data["active_warning"]
    assert "cheat" not in eval_data["active_warning"].lower()

    # 7. Check Student Record on :8005
    rec_resp = client_review.get(f"/student/record/{session_id}")
    assert rec_resp.status_code == 200
    rec_data = rec_resp.json()
    assert len(rec_data["events"]) >= 1
    assert "Notice 1: Your face was not visible" in rec_data["events"][0]["description"]

    # 8. Student Submits Explanation
    exp_resp = client_review.post(
        "/student/explain",
        json={
            "session_id": session_id,
            "explanation_text": "A family member entered the room and I looked away.",
        },
    )
    assert exp_resp.status_code == 200
    assert exp_resp.json()["status"] == "recorded"

    # Verify explanation appears in student record
    rec_resp2 = client_review.get(f"/student/record/{session_id}")
    rec_data2 = rec_resp2.json()
    exp_events = [e for e in rec_data2["events"] if e["event_type"] == "explanation"]
    assert len(exp_events) == 1
    assert "family member entered" in exp_events[0]["description"]


def test_faculty_portal_and_held_session_workflow(
    client_review, client_warn, client_investigator
):
    """Test faculty authorization, listing held sessions, audit timeline, and verdict."""
    session_id = f"e2e_held_{uuid.uuid4().hex[:6]}"

    # Start session
    student_login = client_review.post(
        "/auth/login",
        json={
            "username": settings.demo_student1_username,
            "password": settings.demo_student1_password,
        },
    )
    st_token = student_login.json()["access_token"]
    client_review.post(
        "/sessions/start",
        json={"exam_id": 1, "session_id": session_id},
        headers={"Authorization": f"Bearer {st_token}"},
    )

    # Student cannot access faculty portal
    forbidden_resp = client_review.get(
        "/faculty/sessions/held",
        headers={"Authorization": f"Bearer {st_token}"},
    )
    assert forbidden_resp.status_code == 403

    # Open case in investigator (:8003) and resolve DELIBERATE
    case_resp = client_investigator.post(
        "/evaluate",
        json={
            "session_id": session_id,
            "signal": "multiple_faces",
            "confidence": 0.55,
            "duration": 15.0,
            "timestamp": 100.0,
        },
    )
    assert case_resp.status_code == 200
    case_id = case_resp.json()["case"]["case_id"]

    # Client polls pending interactive probes
    probes = client_investigator.get(f"/probes/pending/{session_id}").json()
    assert isinstance(probes, list)

    # Close case with high-confidence deliberate finding (P >= 0.85)
    resp = client_investigator.post(
        "/probes/respond",
        json={
            "case_id": case_id,
            "probe_name": "high_res_frame_burst",
            "outcome": "clear_secondary_actor",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["resolution"]["status"] == "deliberate"

    # Escalate through WARNED and ELEVATED first
    client_warn.post(
        "/evaluate",
        json={
            "session_id": session_id,
            "score": 50.0,
            "current_tier": Tier.CLEAR.value,
            "candidate_tier": Tier.WARNED.value,
            "contributing_channels": ["camera", "microphone"],
            "timestamp": 120.0,
        },
    )
    client_warn.post(
        "/evaluate",
        json={
            "session_id": session_id,
            "score": 70.0,
            "current_tier": Tier.WARNED.value,
            "candidate_tier": Tier.ELEVATED.value,
            "contributing_channels": ["camera", "microphone"],
            "timestamp": 140.0,
        },
    )

    # Now escalate to HELD
    held_eval = client_warn.post(
        "/evaluate",
        json={
            "session_id": session_id,
            "score": 88.0,
            "current_tier": Tier.ELEVATED.value,
            "candidate_tier": Tier.HELD.value,
            "contributing_channels": ["camera", "microphone"],
            "timestamp": 160.0,
        },
    )
    assert held_eval.status_code == 200
    assert held_eval.json()["target_tier"] == Tier.HELD.value
    assert held_eval.json()["system_action"] == SystemAction.PAUSE_AND_HOLD_FOR_HUMAN.value

    # Faculty Login (:8005)
    fac_login = client_review.post(
        "/auth/login",
        json={
            "username": settings.demo_faculty1_username,
            "password": settings.demo_faculty1_password,
        },
    )
    assert fac_login.status_code == 200
    fac_token = fac_login.json()["access_token"]
    fac_headers = {"Authorization": f"Bearer {fac_token}"}

    # Faculty queries held sessions list
    held_list = client_review.get("/faculty/sessions/held", headers=fac_headers).json()
    assert len(held_list) >= 1
    session_ids = [h["session_id"] for h in held_list]
    assert session_id in session_ids

    # Faculty queries detailed session audit timeline
    tl_resp = client_review.get(f"/faculty/session/{session_id}", headers=fac_headers)
    assert tl_resp.status_code == 200
    tl_data = tl_resp.json()
    assert tl_data["session_id"] == session_id
    assert tl_data["hold_summary"] is not None
    assert len(tl_data["risk_points"]) >= 3
    # Verify stub clip marker was attached to score-raising events
    clip_markers = [
        rp["stub_clip_marker"] for rp in tl_data["risk_points"] if rp["stub_clip_marker"]
    ]
    assert len(clip_markers) >= 1

    # Faculty records decision
    dec_resp = client_review.post(
        "/faculty/decision",
        json={
            "session_id": session_id,
            "verdict": "warning_stands",
            "notes": "Reviewed camera audio logs; warning confirmed, candidate allowed to submit.",
        },
        headers=fac_headers,
    )
    assert dec_resp.status_code == 200

    # Faculty downloads decision report
    rep_resp = client_review.get(f"/faculty/report/{session_id}", headers=fac_headers)
    assert rep_resp.status_code == 200
    rep_data = rep_resp.json()
    assert rep_data["session_id"] == session_id
    assert "Audit Report" in rep_data["report_title"]


def test_calm_student_scenario(client_review, client_capture, client_risk):
    """Confirm a calm student remains CLEAR with zero warnings and an empty record."""
    session_id = f"e2e_calm_{uuid.uuid4().hex[:6]}"

    # Start session for student2
    s_login = client_review.post(
        "/auth/login",
        json={
            "username": settings.demo_student2_username,
            "password": settings.demo_student2_password,
        },
    )
    token = s_login.json()["access_token"]
    client_review.post(
        "/sessions/start",
        json={"exam_id": 1, "session_id": session_id},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Calibration phase
    for t in [0.0, 15.0, 29.0]:
        client_capture.post(
            "/features",
            json={"session_id": session_id, "timestamp": t, "face_present": True},
        )

    # Calm exam session for 2 minutes: centered gaze, window active, quiet audio
    for t in [35.0, 60.0, 90.0, 120.0]:
        feat = client_capture.post(
            "/features",
            json={
                "session_id": session_id,
                "timestamp": t,
                "face_present": True,
                "face_count": 1,
                "gaze_offset_x": 0.02,
                "gaze_offset_y": -0.01,
                "head_yaw": 2.0,
                "head_pitch": 1.0,
                "window_focused": True,
                "tab_visible": True,
                "audio_level": 0.05,
            },
        ).json()
        assert feat["is_calibrating"] is False
        assert len(feat["observations"]) == 0

    # Check risk state
    state = client_risk.get(f"/state/{session_id}?now=120.0").json()
    assert state["current_score"] == 0.0
    assert state["current_tier"] == Tier.CLEAR.value

    # Check Student Record
    rec = client_review.get(f"/student/record/{session_id}").json()
    # No notices or warnings
    assert len(rec["events"]) == 0
    assert "No notices or interventions occurred during your exam session." in rec["summary"]
