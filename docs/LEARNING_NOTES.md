# Custodian AI — Learning Notes

These notes explain the "why" and "how" behind every component built in Custodian AI, serving as your study guide.

---

## Sprint 1 — Task 1: Project Skeleton & Directory Organization

### What this piece is and why the project needs it
The project skeleton is the foundational blueprint of Custodian AI. It creates the physical and logical boundaries for all five microservices, the shared data contracts, frontend web clients, infrastructure templates, and automated verification suites before writing business logic. Without this structure, services become tightly coupled, configurations leak between layers, and automated pipelines have no consistent targets.

### Key concepts
1. **Monorepo with Explicit Domain Boundaries:** All code resides in one Git repository, but each microservice (`services/*`) is isolated with its own Dockerfile and dependencies. Shared contracts live in `shared/` so all services speak identical data models without copy-pasting code.
2. **Infrastructure Separation of Concerns:** Application logic (`services/`, `web/`) is separated from infrastructure declarations (`infra/cloudformation/`, `k8s/`). Baseline resources (VPC, S3 evidence bucket) live in `01-baseline.yaml` and are never destroyed, while cluster resources live in `02-cluster.yaml` and are disposable to minimize AWS spend.
3. **Shift-Left Automation via Makefile:** Standardized developer shortcuts (`make up`, `make test`, `make scan`, `make fairness`) ensure that every team member and the CI runner execute identical commands.
- **Analogy:** Think of building a multi-specialty hospital. Before patient beds or medical machines arrive, civil engineers lay the foundation, build separate wings (ICU, triage, pathology, records room), mark fire exits, and route plumbing and electrical conduits.

### How it connects to other services
- `services/capture-detect` receives sensor measurements and writes to Redis (`D1`).
- `services/risk-engine` reads events, computes decaying risk, and informs `warn-escalate`.
- `services/investigator` runs diagnostic probes on ambiguous flags before score escalation.
- `services/review-report` surfaces the immutable PostgreSQL ledger (`D2`) and S3 clips to students and faculty.
- `web/` connects student exam takers and faculty proctors to these backends.
