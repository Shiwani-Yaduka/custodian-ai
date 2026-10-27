# AGENTS.md — Custodian AI (Adaptive AI Exam Proctor)

> READ THIS FILE FIRST in every session, every task, every prompt.
> If anything in a prompt conflicts with this file, stop and ask me before continuing.

---

## 0. Who I am and how you must work with me

I am **Shiwani**, a BTech CSE student at Lovely Professional University. This is my final-year style project and I must be able to explain and defend every part of it to my guide. I know some Kubernetes and DevOps basics but I am a **beginner at AWS DevSecOps, CloudFormation and GitHub Actions**.

### Standing rules (apply to EVERY task)

**RULE 1: TEACH ME while you build.**
Before writing code or config for any task, give me a short "Learn first" note (max ~10 lines):
- what this piece is and why the project needs it
- the 2-3 key concepts, in plain words, with one analogy
- how it connects to the other services
After finishing, give a "What you just built" recap and 2-3 viva-style questions I should be able to answer. Do not skip this even if I seem busy.

**RULE 2: ASK ME when you need something from me. Never guess, never invent.**
You cannot do these things for me, so stop and ask:
- AWS account actions (creating the account, console clicks, enabling services, billing alerts)
- creating or copying secrets, tokens, access keys, Docker Hub tokens, GitHub repo settings
- anything that costs money
- any choice between two reasonable options
When you ask, use this format:
```
ACTION NEEDED FROM YOU
Why: <one line>
Steps:
1. ...
2. ...
How to check it worked: <one line>
Reply "done" or paste the output/error.
```
Then **wait**. Do not continue past a step that depends on me.

**RULE 3: Small steps, always runnable.**
Work in small increments. After each increment tell me the exact command to run and what I should see. Never leave the repo in a broken state.

**RULE 4: Explain every command and config block the first time it appears.** Use short inline comments in YAML/CloudFormation/Dockerfiles.

**RULE 5: Cost safety first.** Before any command that creates AWS resources, state the approximate hourly/daily cost and the exact command to delete it. Never leave resources running. Remind me to tear down at the end of every AWS session.

**RULE 6: Security basics are not optional.** No secrets in code, images, logs or commits. No long-lived AWS keys. If I ask for something insecure, warn me and offer the safe alternative.

**RULE 7: Keep a running log.** After each task update `docs/PROGRESS.md` (what is done, what is next, open questions, decisions made) and add any new term to `docs/GLOSSARY.md`. Use `docs/PROGRESS.md` to resume if a session is lost.

**RULE 8: Be honest.** If something is uncertain, version-dependent, or you could not test it, say so. Do not claim a test passed unless you ran it.

---

## 1. Project in one paragraph

Custodian AI is an adaptive exam proctor. Instead of flagging suspicious behaviour as a verdict, it treats unexplained observations as **evidence under uncertainty**. Sensors report observations with a confidence value. A **risk engine** turns them into a decaying, capped, corroborated score. An **investigation agent** holds ambiguous weight back, opens a case, runs low-intrusion probes, and decides whether the behaviour is ordinary, a technical fault, or deliberate. **No automatic failing ever happens.** The most severe outcome is pausing the exam and sending a **hold to a human teacher** with evidence attached. Every decision is written to an evidence ledger the student can read.

**Priorities:** fairness to students > privacy > explainability > scale > cost.

---

## 2. FINAL technology decisions (do not change without asking me)

| Area | Decision |
|---|---|
| Source control + CI/CD | **GitHub + GitHub Actions** (NOT Jenkins) |
| Infrastructure as code | **AWS CloudFormation only** (NOT Terraform) |
| Container packaging | **Docker**, one slim Python base image shared by all services |
| Image registry | **Docker Hub** |
| Orchestration | **Amazon EKS (Kubernetes)**, demo-only, deleted after use |
| Local development | **kind or Minikube** + Docker Compose. AWS is NOT used for daily work |
| Backend | Python 3.11, FastAPI, OpenCV, MediaPipe |
| Frontend | TypeScript + React (browser capture, student view, faculty portal) |
| Live session state | **Redis running as a container in the cluster** (not ElastiCache, to save money) |
| Evidence ledger | PostgreSQL 16. Local container in dev; **RDS db.t3.micro** only during demos |
| Evidence clips | Amazon S3 + KMS encryption, auto-delete lifecycle rule |
| Secrets | AWS Secrets Manager (cloud), `.env` files that are git-ignored (local) |
| Monitoring | Prometheus + Grafana (lightweight Helm install in cluster) |
| Image scanning | Trivy |
| AWS auth from GitHub | **GitHub OIDC to an IAM role** (no stored access keys) |
| Process | Scrum, six two-week sprints, fairness regression suite is part of "definition of done" |

**Removed from the original plan:** Jenkins, Terraform, ElastiCache, 3x t3.large nodes, CloudFront+WAF (mention as "future work" only).

---

## 3. Low-budget rules (hard constraints)

- Target AWS spend: **as close to zero as possible**; absolute cap about INR 1,500-2,000 total. Check the AWS Free Tier and student credits before suggesting anything.
- **Day-to-day development is 100% local** (Docker Compose, kind). AWS only for: sprint-review demos, testing the pipeline, and final demo.
- EKS control plane costs about USD 0.10/hour while it exists. So the cluster stack is **created for a session and deleted at the end**.
- Worker nodes: **2x t3.medium (Spot where possible)**, minimum 1 for light tests.
- **Avoid NAT Gateways** (about USD 32/month each). Use public subnets with tight security groups for the demo cluster, and explain the trade-off to me.
- Redis in-cluster, Postgres in-cluster for most tests, RDS only for the final demo.
- Create an **AWS Budget with email alerts** in the very first AWS step (guide me through it).
- S3 lifecycle rule deletes evidence clips after the appeal window (configurable, default 14 days).
- Every AWS-touching task ends with a **teardown checklist**.

---

## 4. CloudFormation layout (two stacks, separate jobs)

**Why two stacks:** deleting or rebuilding the cluster must never be able to destroy stored evidence.

1. `infra/cloudformation/01-baseline.yaml` — created once, **long-lived**:
   - VPC and subnets
   - S3 evidence bucket (KMS-encrypted, versioning, public access blocked, lifecycle expiry)
   - KMS key
   - GitHub OIDC provider + IAM role for GitHub Actions (least privilege)
   - IAM roles for services
   - Secrets Manager placeholders
   - CloudTrail
   - Budget alarm (if not created by hand)
   - Deletion protection / `DeletionPolicy: Retain` on the bucket and KMS key
2. `infra/cloudformation/02-cluster.yaml` — **disposable**, created per demo:
   - EKS cluster and managed node group (Spot)
   - RDS db.t3.micro (optional parameter)
   - Security groups
   - Outputs used by the deploy workflow

Use parameters, outputs and `Export`/`ImportValue` between stacks. Validate with `cfn-lint` and `aws cloudformation validate-template`. Prefer `aws cloudformation deploy` for repeatability. Kubernetes manifests/Helm charts live in `k8s/` and are applied by the workflow with `kubectl`/`helm`.

---

## 5. Services (five containers, mirror the five DFD processes)

| # | Service | Job |
|---|---|---|
| 1 | `capture-detect` | Receives browser **features** (never raw video): face present, gaze direction, head pose, window-focus loss, audio level. Attaches a confidence value. |
| 2 | `risk-engine` | Applies grace windows, repetition, caps, decay, corroboration. Produces the risk score and tier. |
| 3 | `investigator` | Opens cases for ambiguous items, maintains posterior over 3 hypotheses, chooses probes, returns a resolution multiplier. |
| 4 | `warn-escalate` | Tier transitions with hysteresis and gating. Sends warnings with reasons. Creates holds. |
| 5 | `review-report` | Evidence ledger API, student-visible record, explanation channel, faculty portal, decision report. |

Data stores: **D1 Session State (Redis)**, **D2 Evidence Ledger (Postgres + S3 clips)**, **D3 Rules and Limits (config, per-exam policy)**.

All services: FastAPI, `/health` and `/metrics` endpoints, CPU/memory limits, non-root user, structured JSON logs, config via environment variables.

---

## 6. Risk model (implement exactly; make parameters configurable in D3)

Per observation `i` of signal type `s`:

```
w_i = b_s * c_i * d_i * r_i
d_i = clamp( (tau_i - g_s) / (f_s - g_s), 0, 1 )
r_i = 1 + 0.35 * min(n - 1, 4)        # n-th occurrence within a 5-minute window
```
- `b_s` base weight, `c_i` detector confidence (0-1), `tau_i` observed duration (s), `g_s` grace window (below it, contribution is exactly 0), `f_s` duration at which the signal carries full weight.

Per channel `c` (camera, microphone, exam-window, device telemetry), decaying capped accumulator, half-life `H = 240 s`:
```
A_c(t) = min( K_c, sum_i_in_c  w_i * 2^(-(t - t_i)/H) )
```
**Every `K_c` must be below the WARNED threshold (45).** Default `K_c = 40`. This guarantees one sensor alone can never push a student past a first warning.

Total risk, corroboration multiplier over `m` channels currently contributing, `lambda = 0.20`:
```
R(t) = min( 100, [ sum_c A_c(t) ] * ( 1 + lambda * (m - 1) ) )
```

### Tiers
| Tier | Score | Effect |
|---|---|---|
| CLEAR | 0-24 | Nothing shown |
| WATCHING | 25-44 | Noted internally only |
| WARNED | 45-64 | First warning with the reason. **Needs 2 different channels contributing.** |
| ELEVATED | 65-79 | Second warning and 10 minutes off the clock. **Needs 2 channels + strong evidence + 2 earlier warnings.** (follow the synopsis wording; ask me if ambiguous) |
| HELD | 80-100 | Exam paused and sent to a teacher. **Needs an observation resolved as DELIBERATE at high confidence AND two warnings the student already saw.** Never an automatic fail. |

- A tier change requires the score to hold for **6 seconds** (hysteresis, prevents flapping).
- Score falls on its own through decay. Good behaviour brings the student back down.
- **Calibration:** first minutes of a session learn the student's personal baseline (posture, gaze range). Later behaviour is compared with that baseline, not an average.

---

## 7. Investigation agent

- Trigger an investigation when: detector confidence is low, OR applying the observation at face value would raise the tier, OR the same behaviour recurs.
- While a case is open, **hold the weight back** (do not apply it to the score yet).
- Hypotheses `H = {ordinary, technical, deliberate}`, prior set per signal type.
- Bayes update after each probe outcome `e`: `P(h|e) = P(e|h)P(h) / sum_h' P(e|h')P(h')`
- Pick next probe: `p* = argmax_p [ sum_o P(o) * KL( P(H|o) || P(H) ) / (1 + cost(p)) ]`
- Probe library (6 types), quietest first: device telemetry check, network/heartbeat check, high-res frame burst, secondary-detector cross-check, soft on-screen reminder (behavioural probe), short explanation prompt to student.
- Close the case when the leading hypothesis > 0.70 or after 3 probes.
- Resolution multipliers applied to the held weight: **deliberate 1.0, inconclusive 0.4, ordinary 0.15, technical 0** (technical also discounts that channel until the fault clears).
- Everything the agent does is written to the ledger with a human-readable reason.

---

## 8. Privacy rules (non-negotiable)

- Browser sends **measurements, not pictures**. No raw video streaming, no whole-session recording.
- A short clip (about 10 s) is kept **only** around an observation that actually raised the score.
- Never collect screen contents, keystrokes inside answers, or anything outside the exam window.
- Clips are encrypted (KMS) and deleted when the appeal window closes.
- The student can see their own evidence ledger and submit an explanation during the exam.
- The system produces evidence and a recommendation only; the institution decides.

---

## 9. CI/CD with GitHub Actions

Workflows in `.github/workflows/`:

1. `ci.yml` (on every push/PR): lint, unit tests, **policy/fairness regression suite**, secret scanning (gitleaks), dependency check, build Docker images, **Trivy scan (fail on HIGH/CRITICAL)**.
2. `publish.yml` (on merge to main): push images to Docker Hub with commit-SHA tags.
3. `deploy-demo.yml` (manual `workflow_dispatch`): assume AWS role via OIDC, deploy cluster stack, deploy services, run smoke tests + fairness check against the deployed build, **rollback on failure**.
4. `teardown.yml` (manual): delete the cluster stack so nothing keeps costing money. Optionally also scheduled as a safety net.

Also enable: Dependabot, GitHub secret scanning, branch protection on `main`, and GitHub Environments with required approval for the deploy job.

**Fairness check:** replay several hundred recorded + synthetic sessions through the new build, compare warnings/deductions/holds to expected results. If the **false-flag rate** exceeds the agreed limit, the pipeline fails exactly like a failing unit test. Include scenarios: glance away, brief network drop, sibling walking by, failing webcam (must stay harmless), neurodivergent movement patterns, low light, and real violations that must NOT be missed.

---

## 10. Beginner DevSecOps controls (keep it simple and real)

| Area | What to implement |
|---|---|
| AWS access | GitHub OIDC role, no access keys; least-privilege IAM per service; CloudTrail on |
| Containers | Trivy in CI; non-root user; slim base image; pinned versions |
| Secrets | AWS Secrets Manager; never in code or images; gitleaks in CI |
| Data | S3 + KMS encryption, public access blocked, lifecycle deletion; encryption at rest on RDS |
| Pipeline | Dependabot; protected main branch; only the GitHub Actions deploy role can touch the cluster |
| Cluster | Separate namespaces (dev/test/prod), resource limits, health probes, NetworkPolicy basics |
| Cost | AWS Budget alarm, teardown workflow |

---

## 11. Observability

- Every service exposes Prometheus metrics: request latency, error rate, detection time.
- **Decision metrics:** warnings per 100 sessions, investigation outcomes (ordinary/technical/deliberate/inconclusive), false-flag rate, per-class flag rate.
- Grafana "exam day" dashboard + **mass-flag alert**: many students flagged at the same time almost always means network or platform failure, not mass cheating. The system then relaxes thresholds and notifies staff.

---

## 12. Repository structure (create this, keep it consistent)

```
custodian-ai/
├── AGENTS.md                      <- this file
├── README.md
├── docs/
│   ├── PROGRESS.md                <- running log (Rule 7)
│   ├── GLOSSARY.md
│   ├── LEARNING_NOTES.md          <- your "Learn first" notes saved for me
│   └── VIVA_QUESTIONS.md          <- viva questions collected per task
├── services/
│   ├── capture-detect/
│   ├── risk-engine/
│   ├── investigator/
│   ├── warn-escalate/
│   └── review-report/
├── web/                           <- React app (exam browser + faculty portal)
├── shared/                        <- shared Python package (models, config)
├── infra/cloudformation/
│   ├── 01-baseline.yaml
│   └── 02-cluster.yaml
├── k8s/                           <- manifests / Helm values
├── fairness/                      <- recorded + synthetic sessions, expected results, runner
├── simulator/                     <- threshold what-if simulator
├── docker-compose.yml             <- local dev
├── Makefile                       <- make up, make test, make fairness, make scan
└── .github/workflows/
```

---

## 13. Sprint map (six two-week sprints)

1. Foundation: repo, Dockerfiles, CloudFormation baseline, EKS stack, basic GitHub Actions pipeline
2. Capture and detect: browser capture, gaze/face/window-focus detectors with confidence
3. Risk engine: weighting, decay, caps, corroboration, repetition, tier ladder with hysteresis
4. Investigation agent: Bayesian posterior, probe library, information-gain selection, resolution multipliers
5. Ledger and portals: evidence ledger, student explanation channel, faculty review portal, decision report
6. Hardening and release: security controls, Grafana dashboards, fairness check in pipeline, load testing

Definition of done for every story: tests pass, **fairness regression suite passes**, Trivy clean, docs/PROGRESS.md updated, learning notes written.

---

## 14. Things you must NEVER do

- Never add automatic failing, disqualification or punishment without human review.
- Never apply a penalty on single-channel or low-confidence evidence.
- Never store or stream raw video of the whole session.
- Never hard-code secrets or AWS keys; never commit `.env`.
- Never create AWS resources without telling me the cost and the delete command first.
- Never swap a technology from Section 2 without asking me.
- Never say something works unless you ran it.
