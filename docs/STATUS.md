# Custodian AI — Implementation Status & Architecture Gap Analysis

> **Academic Submission Safe Document**  
> **Phase:** Phase A Completion & Verification  
> **Date:** November 2026  
> **Author:** Shiwani (BTech CSE, Lovely Professional University)

---

## 1. Executive Summary

Phase A of **Custodian AI** is 100% complete, fully tested, and verified on a single developer machine without Docker or cloud infrastructure. All core mathematical models, Bayesian reasoning algorithms, procedural gating invariants, microservice wrappers, and client-side privacy-preserving WebAssembly detection loops are operational.

---

## 2. Implementation Matrix (Phase A vs Synopsis vs AGENTS.md)

| Component | Status | Phase A Implementation Details | Phase B Evolution Plan |
|---|---|---|---|
| **Risk Decay & Accumulation** | **Complete** | Full pure Python implementation in `core/risk.py`: grace window ($g_s$), duration factor ($d_i$), repetition multiplier ($r_i$), exponential decay ($H = 240$s), channel caps ($K_c = 40.0$), corroboration multiplier ($1 + \lambda(m-1)$), and 6s hysteresis hold. | Distributed execution with clustered state stores. |
| **Bayesian Investigator** | **Complete** | Pure Python implementation in `core/investigator.py`: 3 hypotheses (ordinary, technical, deliberate), exact Bayes update with zero-division guard, Expected Information Gain probe selection, held weight escrow, and resolution multipliers. | Enhanced with historical student cohort prior distributions. |
| **Escalation Gating & Invariants** | **Complete** | Closed set of 5 sanctioned outcomes in `core/safety.py`. Strict procedural gates: 2 channels for `WARNED`, prior warning for `ELEVATED`, deliberate posterior $\ge 0.85$ + 2 warnings for `HELD`. Non-accusing warning texts with blacklist checks. | Formal model checking proofs in CI pipeline. |
| **Evidence Ledger** | **Complete** | Append-only database via SQLAlchemy 2.0 with 12 relational tables. In Phase A, runs on local **SQLite** (`custodian.db`). Includes student diary reader, faculty audit reader, explanation logger, and human determination forms. | Swap repository database URL from SQLite to **PostgreSQL**. |
| **Live Session State** | **Complete** | Decoupled `StateStore` interface implemented via thread-safe `InMemoryStateStore` in `core/state.py`. | Swap implementation class from in-memory to **Redis**. |
| **Microservice Architecture** | **Complete** | 5 FastAPI microservices (`capture-detect` :8001, `risk-engine` :8002, `investigator` :8003, `warn-escalate` :8004, `review-report` :8005). Expose `GET /health`, `GET /metrics` (Prometheus text), structured JSON logs, and CORS. | Containerize via Docker; deploy to AWS EKS via CloudFormation. |
| **In-Browser Edge Detection** | **Complete** | Google MediaPipe Face Landmarker running in client browser via WebAssembly (WASM) at 5 fps using offline model (3.75 MB). Extracts abstract facial geometry only (gaze, yaw, pitch, roll, face size). Web Audio RMS volume. **Zero video streaming.** | Enhanced with dynamic client-side frame-rate throttling. |
| **Personal Calibration** | **Complete** | 30-second initial baseline calculating student's neutral mean ($\mu$) and standard deviation ($\sigma$). Anomaly thresholds are strictly relative to individual anatomy. | Dynamic recalibration upon significant lighting transitions. |
| **Faculty Review Portal** | **Complete** | Web dashboard in `web/src/screens/FacultyPortal.tsx`: HELD-only queue, pure SVG risk progression chart, Bayesian reasoning breakdown, student explanation view, human adjudication form, and 1-click printable HTML audit report. | Export PDF reports directly to institutional cloud archives. |
| **Scenario Simulator** | **Complete** | 7 interactive demo scenarios running through the real `InProcessPipeline` with fast-forwarded virtual timestamps. Live score gauge, 4-channel capped accumulator bars, gate checklist, and mass-flag relaxation. | Synthetic cohort stress generator testing 1,000 concurrent sessions. |
| **Fairness Regression Suite** | **Complete** | 34 benchmark scenarios in `fairness/scenarios.yaml`. Evaluator in `fairness/run.py` enforces 0% false flags on innocent students and 0% misses on violations. Benchmarked against a naive commercial fixed-threshold baseline detector. | Automated nightly fairness regression check in GitHub Actions CI. |
| **Policy What-If Simulator** | **Complete** | Interactive CLI tool (`python scripts/dev.py simulate` / `make simulate`) allowing administrators to test parameter adjustments with side-by-side delta tables and automated regression detection. | Web-based policy simulation dashboard in faculty admin portal. |

---

## 3. Honest Disclosure of Phase A Gaps & Approximations

In strict accordance with Section 0.3 (Honesty Rules) of `AGENTS.md`, the following elements are intentionally simplified in Phase A:

1. **Evidence Video Clips (Stub Records):**
   - *Phase A Reality:* Video clips are represented by **stub metadata records** (`stub-clip-sess-...`) containing timestamp, duration, and reference ID. No physical video media files are recorded or stored on disk.
   - *Justification:* Satisfies GDPR data minimization and laptop-light constraints during development.
   - *Phase B Plan:* Client-side 10-second encrypted WebM capture uploaded to Amazon S3 with KMS envelope encryption upon confirmed HELD events.

2. **Interactive Browser Probes in Scenarios:**
   - *Phase A Reality:* In live exam mode, soft reminders and explanation prompts are fetched via HTTP polling. In the Scenario Simulator and Fairness Suite, probe responses are scripted deterministically via `ScriptedProbeRunner`.
   - *Justification:* Ensures deterministic, reproducible regression testing without human intervention.

3. **Database & Cache Technologies:**
   - *Phase A Reality:* Local SQLite database and in-memory session dictionaries.
   - *Phase B Plan:* CloudFormation deploys containerized Redis and PostgreSQL in the AWS EKS cluster.

---

## 4. Phase B Readiness Gate

Phase A code is 100% prepared for Phase B adoption without architectural refactoring:
- All configuration is sourced from environment variables via `shared/config.py`.
- `StateStore` and `LedgerRepository` design patterns permit single-line backend swaps.
- Every microservice provides production-ready `/health` and `/metrics` endpoints.
- All 66 tests (59 backend pytest, 7 frontend vitest) pass with 0 failures and 100% ruff compliance.
