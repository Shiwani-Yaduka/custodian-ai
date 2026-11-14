# AGENTS.md (v2) — Custodian AI, Adaptive AI Exam Proctor

> READ THIS FILE FIRST in every session and every task.
> Then read `.agent-notes/PROGRESS.md` to see where we stopped.
> If a prompt conflicts with this file, follow the safer reading and record the conflict in `.agent-notes/DECISIONS.md`.

---

## 0. Who I am and how you must work

I am **Shiwani**, a BTech CSE student at Lovely Professional University. This is my project and I must be able to explain and defend every part of it to my guide. I am a beginner at AWS DevSecOps, CloudFormation and GitHub Actions. I know some Kubernetes and DevOps basics.

**My laptop is weak.** Docker Desktop hangs it. Read Section 4 and respect it always.

### 0.1 AUTONOMY MODE (standing permission)

I give you standing permission to work on your own inside this project folder. Do NOT ask me for permission to:
- create, edit, rename or delete files inside the project folder
- create a Python virtual environment and install packages into it
- run `npm install` inside `web/`
- run tests, linters, formatters, dev servers (and stop them afterwards)
- make local git commits (small, meaningful, one per finished step)
- fix your own bugs and re-run until tests pass
- download small model/asset files into the project (for example the MediaPipe model)

You MUST still stop and ask me, using the format in 0.2, for:
- installing software on my machine that needs admin rights (Python, Node, Git themselves)
- anything outside the project folder
- anything that costs money, or needs an account, token, key or password
- the two things only a human can do: testing with my real webcam, and judging how the UI looks
- `git push --force`, deleting git history, or anything irreversible
- a real choice between two reasonable options that is not already decided in this file

When you decide something yourself, do not interrupt me. Write it to `.agent-notes/DECISIONS.md` with the reason and move on.

### 0.2 ASK-ME FORMAT (only when 0.1 says you must)
```
ACTION NEEDED FROM YOU
Why: <one line>
Steps:
1. ...
2. ...
How to check it worked: <one line>
Reply "done" or paste the output or error.
```
Then stop and wait. Do not continue past a step that depends on me.

### 0.3 TEACH ME and KEEP NOTES (every task, no exceptions)

All notes live in the folder **`.agent-notes/`**, which is **listed in `.gitignore`** (they are my private study notes, not part of the submission repo). Create it in the first task and add `.agent-notes/` to `.gitignore`.

Files:
| File | Content |
|---|---|
| `PROGRESS.md` | Checklist of all Phase A steps (done / in progress / next), current state, open questions, exact commands to run the app right now. |
| `DETAILED_LOG.md` | Chronological diary. For every task: goal, every file created or changed (and what it does), every command run (and what it does), what was tested and the real output, errors hit and how they were fixed. Plain language. |
| `CONCEPTS.md` | A "Learn first" note per task: the 2-3 key ideas in plain words with a real-life analogy, how they connect to the rest of the project, and at least one worked numeric example where maths is involved. |
| `DECISIONS.md` | Every decision you made on your own: options considered, choice, reason. |
| `VIVA.md` | At least 5 viva-style questions per task with short model answers. |

Per task, in this order:
1. **Before coding:** write the "Learn first" note into `CONCEPTS.md` and show me a short version in chat.
2. **While coding:** keep `DETAILED_LOG.md` updated as you go, not at the end.
3. **After finishing:** in chat, give a detailed explanation of what happened (what was built, how it works, how the pieces connect, what was tested, what failed and why), then "What you just built" in 5 lines, then 3 viva questions. Update all five notes files.

Add a clear, short code comment on anything non-obvious, so I can read the code and learn.

### 0.4 Honesty rules
- Never claim a test passed unless you ran it in this session and saw it pass. Paste the real result summary in the log.
- If something is uncertain, version-dependent or untested, say so plainly.
- If a step turns out harder than planned, tell me and propose the simplest honest alternative. Do not quietly fake it.

---

## 1. Project in one paragraph

Custodian AI is an adaptive exam proctor. Instead of flagging suspicious behaviour as a verdict, it treats unexplained observations as **evidence under uncertainty**. Sensors report observations with a confidence value. A **risk engine** turns them into a decaying, capped, corroborated score. An **investigation agent** holds ambiguous weight back, opens a case, runs low-intrusion probes, and decides whether the behaviour is ordinary, a technical fault, or deliberate. **No automatic failing ever happens.** The most severe outcome is pausing the exam and sending a **hold to a human teacher** with evidence attached. Every decision is written to an evidence ledger the student can read.

**Priorities:** fairness to students > privacy > explainability > simplicity > scale.

---

## 2. PLAN: two phases (we are doing Phase A first)

**Phase A — Build the core app, no Docker, no cloud, no Kubernetes.**
Steps A0 to A8 (see `PROMPTS_PHASE_A.md`). Ends with a working, demo-able app on my laptop, run with plain Python and Node.

**Phase B — Host it with DevOps (later, separate prompt file).**
Docker images, GitHub Actions CI (Trivy, gitleaks, fairness check), Docker Hub, CloudFormation + EKS in the KodeKloud AWS sandbox (3-hour disposable sessions, max 3 EKS nodes), bootstrap and teardown scripts, Prometheus + Grafana, security hardening, recorded demo.

**Do not do any Phase B work during Phase A**, except: keep the code *ready* for it (Section 3.3).

Phase A "done" gate: I can run the whole 10-minute demo (Section 9) from my browser, `make test` and `make fairness` pass, and `.agent-notes/` is complete.

---

## 3. Technology decisions

### 3.1 Phase A (now)

| Area | Decision |
|---|---|
| Backend | Python 3.11+, FastAPI, Pydantic, SQLAlchemy, pytest |
| Run mode | Plain `uvicorn` processes. **No Docker.** |
| Core logic | Plain Python library in `core/` (no web code inside). Services are thin FastAPI wrappers around it. |
| Live session state | A `StateStore` interface with an **in-memory** implementation now (Redis implementation comes in Phase B) |
| Evidence ledger | **SQLite** via SQLAlchemy now (PostgreSQL in Phase B by changing one URL) |
| Frontend | TypeScript + React + Vite (dev server on localhost) |
| Detection | **MediaPipe Tasks Vision (Face Landmarker), running in the browser** (WASM). Pre-trained. No training, no GPU, no server-side video. |
| Audio | Web Audio API volume/activity level in the browser (no recording of speech) |
| Auth | Mock login with fixed demo accounts and a signed token (secret from `.env`, git-ignored) |
| Testing | pytest for backend, vitest for frontend logic. API-level end-to-end test with `httpx`. |
| Linting | ruff (Python), eslint (TS) |

### 3.2 Phase B (later, do not start)
GitHub + GitHub Actions, Docker, Docker Hub, Trivy, gitleaks, Dependabot, CloudFormation only (no Terraform), EKS (demo-only), Redis and Postgres in-cluster (RDS only if the sandbox allows), S3 + KMS, Secrets Manager, CloudTrail, Prometheus + Grafana, Helm, Cloudflare quick tunnel for HTTPS webcam in the sandbox.

### 3.3 Keep Phase A ready for Phase B
- All settings come from environment variables via one config module (with a `.env.example`, never a real `.env` in git).
- Use `StateStore` and a repository layer so swapping in-memory to Redis and SQLite to Postgres touches no business logic.
- Each service exposes `GET /health` and `GET /metrics` (Prometheus format, simple counters are enough).
- Services log structured JSON.
- Keep the existing Dockerfiles from the earlier skeleton, but never run Docker in Phase A.

---

## 4. Laptop-light rules (hard constraints)

- **No Docker, no Docker Desktop, no Minikube/kind, no VMs in Phase A.**
- Run only the processes you need. Stop dev servers when a task ends.
- Do not install Playwright/Cypress browser bundles. UI checks are done by me in my own browser, or with Antigravity's built-in browser tool if it is available and light.
- Run tests serially unless they are fast. No big watch-mode combos.
- Run the browser detection at a modest rate (about 5 frames per second) to keep the CPU low. Make the rate configurable.
- No model training, no large downloads (the MediaPipe model is only a few MB).
- If my laptop is struggling, say so and offer a lighter way. (GitHub Codespaces is a fallback, but do not assume it.)

---

## 5. Risk model (implement exactly; every parameter configurable)

Per observation `i` of signal type `s`:
```
w_i = b_s * c_i * d_i * r_i
d_i = clamp( (tau_i - g_s) / (f_s - g_s), 0, 1 )
r_i = 1 + 0.35 * min(n - 1, 4)       # n-th occurrence of the same signal within a 5-minute window
```
`b_s` base weight, `c_i` detector confidence 0-1, `tau_i` observed duration in seconds, `g_s` grace window (shorter than this contributes exactly 0), `f_s` duration at which the signal carries full weight.

Per channel `c` in {camera, microphone, exam_window, device}, a decaying capped accumulator with half-life `H = 240 s`:
```
A_c(t) = min( K_c, sum_i_in_c  w_i * 2^(-(t - t_i)/H) )
```
**Every `K_c` must be below the WARNED threshold (45). Default `K_c = 40`.** This guarantees one sensor alone can never push a student past a first warning.

Total risk with the corroboration multiplier over the `m` channels currently contributing (a channel counts as contributing when its accumulator is above a small epsilon, default 2.0), `lambda = 0.20`:
```
R(t) = min( 100, [ sum_c A_c(t) ] * ( 1 + lambda * (m - 1) ) )
```

### Starting signal table (starting values only; tune them with the fairness suite)

| Signal | Channel | b_s | g_s (s) | f_s (s) |
|---|---|---|---|---|
| face_absent | camera | 12 | 5 | 30 |
| gaze_off_screen | camera | 8 | 4 | 20 |
| head_turn | camera | 8 | 4 | 20 |
| multiple_faces | camera | 18 | 2 | 10 |
| speech_detected | microphone | 10 | 5 | 30 |
| window_blur | exam_window | 15 | 3 | 20 |
| tab_hidden | exam_window | 18 | 2 | 15 |
| network_drop | device | 4 | 10 | 60 |
| camera_track_ended | device | 6 | 3 | 20 |
| low_frame_rate | device | 4 | 5 | 30 |

### Tiers, hysteresis and gating

| Tier | Score | Effect | Gate (all must hold, the score alone is never enough) |
|---|---|---|---|
| CLEAR | 0-24 | Nothing shown | none |
| WATCHING | 25-44 | Noted internally only | none |
| WARNED | 45-64 | First warning with the reason | At least 2 different channels contributing |
| ELEVATED | 65-79 | Second warning and 10 minutes added as "time off the clock" | 2 channels + the first warning already shown |
| HELD | 80-100 | Exam paused and sent to a teacher | 2 channels + at least one case resolved DELIBERATE with posterior >= 0.85 + two warnings the student has already seen |

- A tier change needs the score to hold for **6 seconds** (hysteresis).
- If the score qualifies for a tier but the gate fails, the student stays in the highest tier whose gate passes, and the blocked escalation is recorded in the ledger with the reason.
- The score falls by itself through decay. Good behaviour brings the student back down.
- **Calibration:** the first 30 seconds learn the student's baseline (typical gaze range, head pose, face size). Later thresholds for gaze/head signals are relative to that baseline.
- **Mass-flag relaxation:** if many sessions are flagged at the same time (default: more than 30% of active sessions within 60 s), raise grace windows by a configurable factor and mark the event "possible platform/network failure".
- These gate details are my reading of the synopsis. They are recorded as decisions; do not ask me about them again.

---

## 6. Investigation agent

- Open a case when: detector confidence is below a threshold (default 0.6), OR applying the observation at face value would raise the tier, OR the same behaviour recurs.
- While a case is open the observation's weight is **held back** (not applied).
- Hypotheses `H = {ordinary, technical, deliberate}`, priors set per signal type (in config).
- Bayes: `P(h|e) = P(e|h)P(h) / sum_h' P(e|h')P(h')`
- Next probe: `p* = argmax_p [ sum_o P(o) * KL( P(H|o) || P(H) ) / (1 + cost(p)) ]`
- Probe library (6), quietest first, each with a cost and a likelihood table `P(outcome | hypothesis)` in a commented config file:
  1. device telemetry check (cost 0)
  2. network heartbeat check (cost 0)
  3. secondary detector cross-check (cost 0.1)
  4. high-resolution frame burst (cost 0.3, silent)
  5. soft on-screen reminder (cost 0.7, visible, acts as a behavioural probe)
  6. short explanation prompt to the student (cost 1.0)
- Close a case when the leading hypothesis exceeds 0.70 or after 3 probes.
- Resolution multipliers applied to the held weight: **deliberate 1.0, inconclusive 0.4, ordinary 0.15, technical 0**. A technical resolution also discounts that channel until the fault clears.
- Everything the agent does is written to the ledger with a human-readable reason.
- In Phase A, probes that need the browser (frame burst, reminder, explanation prompt) work through a simple request/response channel to the browser app, and the scenario panel can script the outcomes.

---

## 7. Privacy rules (non-negotiable)

- The browser sends **measurements, not pictures**. No video streaming. No whole-session recording.
- A short evidence clip around a score-raising event is represented in Phase A by a **stub record** (timestamp, duration, reference id). Real clip storage is Phase B work. Say so honestly in the notes.
- Never collect screen contents, keystrokes inside answers, or anything outside the exam window.
- Audio: only a level/activity measurement, never recorded speech.
- The student can read their own evidence ledger and submit an explanation during the exam.
- The system produces evidence and a recommendation only. The institution decides.

---

## 8. Repository structure (reuse what the earlier skeleton created, fix as needed)

```
custodian-ai/
├── AGENTS.md
├── README.md
├── Makefile                  # make setup | run | stop | test | fairness | lint
├── .env.example              # real .env is git-ignored
├── .gitignore                # MUST include: .agent-notes/ .env .venv/ node_modules/ *.db __pycache__/
├── .agent-notes/             # git-ignored study notes (Section 0.3)
├── core/                     # pure Python logic: policy, risk, investigator, gating, models
├── services/
│   ├── capture-detect/       # :8001
│   ├── risk-engine/          # :8002
│   ├── investigator/         # :8003
│   ├── warn-escalate/        # :8004
│   └── review-report/        # :8005  (auth, exams, ledger API, faculty portal API)
├── shared/                   # config loading, logging, common schemas
├── web/                      # React + Vite app (student exam UI, faculty portal, scenario panel)
├── fairness/                 # scenarios, expected results, runner
├── simulator/                # threshold what-if tool
├── scripts/                  # dev runner (starts/stops all services), seed demo data
└── docs/                     # only submission-worthy docs (README pieces, DEMO_SCRIPT.md)
```
Rule: **business logic lives in `core/`**, is unit-tested without HTTP, and is also what the fairness runner calls directly (fast). Services only wrap it.

---

## 9. Demo requirements (the app must support all of this)

**Demo accounts (seeded):** `student1`, `student2`, `faculty1` (passwords in `.env.example`, demo only).
**Demo exam (seeded):** "Demo Exam" with 10 simple multiple-choice and 2 written questions, 30-minute timer.

**Student journey:** sign in, consent/privacy screen, allow camera and mic, 30-second calibration, exam screen with a small status badge, warnings that always state the reason, an explanation box, "My evidence record" page.
**Faculty journey:** sign in, list of held sessions only, session detail (timeline, risk over time, investigator reasoning, stub clip marker), record a decision (cleared / warning stays / refer onward), downloadable decision report (HTML or PDF is fine; simple is OK).
**Scenario panel (demo mode):** buttons that feed scripted observations into the real engine and investigator (not fakes):

| Button | Expected result |
|---|---|
| Glance away 3 s | Risk stays exactly 0 |
| Brief network drop | Investigator resolves TECHNICAL, no penalty |
| Sibling walks by | Resolved ORDINARY, tiny weight, decays away |
| Failing webcam, repeated | Camera channel hits the cap, never passes a first warning |
| Phone + notes, corroborated | Two channels, DELIBERATE, warning, second warning, HELD, sent to faculty |
| Calm student 3 minutes | Stays CLEAR |
| Mass flag | Many sessions flagged at once, thresholds relax, "possible platform failure" notice |

The live webcam path and the scenario panel must both work. Scenario mode is clearly labelled "DEMO MODE" in the UI.

---

## 10. NEVER do

- Never add automatic failing, disqualification or any punishment without human review. Add a test that proves it cannot happen.
- Never apply a penalty on single-channel or low-confidence evidence.
- Never store or send raw video or recorded speech.
- Never hard-code secrets. Never commit `.env`. Never commit `.agent-notes/`.
- Never start Docker or Phase B work during Phase A.
- Never claim something works unless you ran it.
- Never edit files outside the project folder.