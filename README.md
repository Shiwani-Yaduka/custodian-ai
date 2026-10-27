# Custodian AI — Adaptive AI Exam Proctor

> **Evidence Under Uncertainty** | **Fairness First** | **Privacy by Design**

Custodian AI is an adaptive, privacy-preserving AI exam proctoring system. Instead of labeling student actions with instant cheating verdicts, it treats sensor detections as probabilistic evidence under uncertainty. Observations are evaluated by a continuous risk engine with half-life decay, grace periods, channel caps, and corroboration requirements.

An automated investigation agent probes ambiguous scenarios, holds score impact in escrow, and categorizes observations into ordinary behavior, technical faults, or deliberate actions. **No automatic disqualifications or failing ever occurs**; the highest escalation is a temporary pause and human faculty hold.

---

## Key Principles

- **Fairness & Explainability:** Multi-sensor corroboration prevents single-camera false positives. Every observation is logged to an immutable evidence ledger accessible to the student.
- **Privacy First:** Only lightweight browser features (head pose, gaze angle, audio energy levels) are transmitted—never continuous raw webcam video streams.
- **Human-in-the-Loop:** High-risk cases are escalated to proctors with attached 10-second contextual evidence clips and audit trails.

---

## Architecture Overview

1. `services/capture-detect`: Receives client-side feature telemetry with confidence metrics.
2. `services/risk-engine`: Calculates decaying, capped, corroborated risk scores.
3. `services/investigator`: Bayesian agent running low-intrusion diagnostic probes on ambiguous signals.
4. `services/warn-escalate`: Manages state tiers (CLEAR, WATCHING, WARNED, ELEVATED, HELD) with hysteresis gating.
5. `services/review-report`: Student evidence ledger, explanation portal, and faculty review dashboards.
6. `shared/`: Common domain models, validation schemas, and utilities.
7. `web/`: Student examination client and proctor/faculty interface.

---

## Quickstart (Local Development)

```bash
# View available commands
make help

# Start local infrastructure (Redis, PostgreSQL)
make up

# Run unit tests
make test

# Run the fairness regression suite
make fairness

# Run security and secret scanning
make scan
```

Refer to [AGENTS.md](file:///c:/Users/shiwa/Documents/custodian-ai/AGENTS.md) for full architecture specifications, risk formulas, and sprint plans.
