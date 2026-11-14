# Custodian AI — Adaptive AI Exam Proctor

> **Adaptive, Evidence-Based Exam Proctoring under Uncertainty.**
> Priorities: **Fairness to Students > Privacy > Explainability > Simplicity > Scale.**

---

## Overview

Custodian AI treats candidate observations not as an automatic guilty verdict, but as **evidence under uncertainty**.
- Observations carry confidence scores and undergo temporal decay.
- Single channels are strictly capped below the warning threshold to avoid false accusations from sensor glitches.
- An autonomous investigation agent opens quiet cases and runs non-intrusive probes to differentiate between technical glitches, ordinary student movement, and deliberate actions.
- **No student is ever automatically failed.** The highest automated escalation is a temporary pause and referral to a human educator with corroborated evidence attached.

---

## Development Setup (Phase A — Docker-Free & Laptop-Light)

### Prerequisites
- Python 3.11+
- Node.js 20+
- Git

### Quickstart

1. **Activate Environment & Install:**
   ```powershell
   python scripts/dev.py setup
   ```

2. **Run Tests:**
   ```powershell
   python scripts/dev.py test
   ```
   *(or `make test` on Unix/Git Bash)*

3. **Run Linter:**
   ```powershell
   python scripts/dev.py lint
   ```

4. **Run Fairness Checks:**
   ```powershell
   python scripts/dev.py fairness
   ```

---

## Repository Structure

```
custodian-ai/
├── AGENTS.md                 # Project constitution & single source of truth
├── README.md                 # Project documentation
├── Makefile                  # Unix task runner
├── pyproject.toml            # Python package & tool configs
├── requirements.txt          # Python dependencies
├── .env.example              # Environment configuration template
├── .gitignore                # Source control exclusions
├── core/                     # Pure Python business logic (risk decay, Bayesian logic)
├── services/                 # Lightweight FastAPI service wrappers
│   ├── capture_detect/       # Signal ingest (:8001)
│   ├── risk_engine/          # Decaying capped accumulator (:8002)
│   ├── investigator/         # Bayesian probe manager (:8003)
│   ├── warn_escalate/        # Tier transition gates (:8004)
│   └── review_report/        # Auth, ledger API, faculty portal API (:8005)
├── shared/                   # Config module, logging, common models
├── web/                      # React + Vite frontend (Phase A5)
├── fairness/                 # Scenario test suites & fairness validator
├── simulator/                # What-if risk threshold simulator
└── scripts/                  # Development scripts and CLI runner
```
