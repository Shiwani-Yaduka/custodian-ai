# Custodian AI — Progress Log

This file tracks project momentum, active sprints, recent completions, next actions, and design decisions. It serves as the primary session resume point.

---

## Current Sprint & Status

- **Active Sprint:** Sprint 1 — Foundation (Repo, Dockerfiles, CloudFormation baseline, EKS stack, basic GitHub Actions pipeline)
- **Current Task:** Task 1 — Project Skeleton & Local Environment Setup
- **Date:** 2026-10-27
- **Status:** In Progress (Toolchain verification & Git initialization)

---

## 1. What Is Done

- [x] Reviewed and memorized `AGENTS.md` standing rules and architectural constraints.
- [x] Initialized complete project skeleton according to Section 12 of `AGENTS.md`:
  - 5 microservices in `services/` (`capture-detect`, `risk-engine`, `investigator`, `warn-escalate`, `review-report`)
  - `web/` frontend folder
  - `shared/` core library folder
  - `infra/cloudformation/` baseline and cluster IaC templates
  - `k8s/`, `fairness/`, `simulator/`, and `.github/workflows/` directories
- [x] Created root developer assets:
  - `README.md`: High-level system overview and quickstart guide.
  - `.gitignore`: Comprehensive ignore rules for Python, Node.js, secrets, IDEs, and OS artifacts.
  - `Makefile`: Standard commands (`up`, `down`, `test`, `fairness`, `scan`, `clean`).
  - `docker-compose.yml`: Local Redis and PostgreSQL 16 configurations.
- [x] Set up documentation framework in `docs/`:
  - `PROGRESS.md`: Continuous sprint tracking log.
  - `GLOSSARY.md`: Key architectural and DevSecOps definitions.
  - `LEARNING_NOTES.md`: Educational explanations accompanying each code/infra increment.
  - `VIVA_QUESTIONS.md`: Viva and guide defense questions with detailed answers.
- [x] Audited local development environment for required tooling.

---

## 2. What Is Next

- [ ] Confirm Shiwani's development OS setup (native Windows vs WSL2 Ubuntu).
- [ ] Align Python environment to Python 3.11 (system currently reports Python 3.14).
- [ ] Install missing local validation tools (`cfn-lint` for CloudFormation; optional `kind`).
- [ ] Initialize local Git repository, create initial commit, and connect to remote GitHub repository.

---

## 3. Decisions Made

| Date | Decision | Rationale |
|---|---|---|
| 2026-10-27 | Monorepo layout with shared package | Keeps contracts and schemas synchronized across all 5 services without multi-repo overhead. |
| 2026-10-27 | Minikube for local k8s (fallback to kind) | Minikube is already installed on the host machine, satisfying the "kind or Minikube" requirement without extra downloads. |
| 2026-10-27 | CloudFormation over Terraform | Explicit decision in `AGENTS.md` (no external state management costs or complexities). |

---

## 4. Open Questions

1. Does Shiwani prefer running Python/Docker development directly in Windows PowerShell or inside WSL2 (Ubuntu)?
2. What is the target GitHub username/organization and repository name for remote push?
