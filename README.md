# Custodian AI — Adaptive AI Exam Proctor

> **Adaptive, Evidence-Based Exam Proctoring under Uncertainty.**  
> Priorities: **Fairness to Students > Privacy > Explainability > Simplicity > Scale.**  
> Built for: BTech CSE Final Year Project by **Shiwani** (Lovely Professional University).

---

## 1. What is Custodian AI?

Traditional commercial proctoring tools treat minor anomalies as instant guilt: a student looking away for 3 seconds, a flickering webcam, or a cough triggers an accusation and can terminate an exam.

**Custodian AI** is fundamentally different. It treats anomalies as **probabilistic evidence under uncertainty**:
- **Continuous Decay:** Anomalies naturally decay over time via an exponential half-life ($H = 240$s). Good behavior restores a student's record to clean.
- **Sensor Isolation:** Every sensory channel is strictly capped ($K_c = 40.0$) below the first warning threshold ($45.0$). A faulty webcam or microphone can **never** trigger a warning alone.
- **Bayesian Investigation:** An autonomous investigation agent opens cases upon ambiguous evidence, tests hypotheses (`ordinary`, `technical`, `deliberate`), and runs quiet, non-intrusive probes before applying penalties.
- **Human-in-the-Loop:** **No student is ever automatically failed or disqualified.** The highest system action is pausing the exam and referring the case to a human faculty educator with corroborated evidence.
- **Edge Privacy:** Computer vision runs in the student's browser via WebAssembly (WASM). **Zero video frames and zero speech recordings are ever transmitted or stored.**

---

## 2. Quickstart: Run Phase A in 5 Commands

Run directly on your laptop with standard Python 3.11+ and Node 20+ (No Docker or cloud needed):

```powershell
# 1. Set up Python virtual environment and dependencies
python scripts/dev.py setup

# 2. Seed demo accounts (student1, student2, faculty1) and Demo Exam
python scripts/dev.py seed

# 3. Run all unit and regression tests (66 passed: 59 backend + 7 frontend)
python scripts/dev.py test

# 4. Run the 34-scenario fairness benchmark suite
python scripts/dev.py fairness

# 5. Start all 5 microservices and the React web app
python scripts/dev.py run
```
*Tip: On Unix/macOS or with Windows `make.cmd`, you can also type `make setup`, `make seed`, `make test`, `make fairness`, and `make run`.*

Open your browser to: **`http://127.0.0.1:5173/`**

To stop all services cleanly:
```powershell
python scripts/dev.py stop
```

---

## 3. How to Run the 10-Minute Live Demo

A complete step-by-step walkthrough script with exact click paths and talking points is provided in [docs/DEMO_SCRIPT.md](file:///C:/Users/shiwa/Desktop/custodian-ai/docs/DEMO_SCRIPT.md).

### Student Experience
1. Navigate to `http://127.0.0.1:5173/`. Click **`[ student1 ]`** -> **Sign In**.
2. Read the transparent **Privacy Consent Screen** -> Click **Agree**.
3. Allow Camera & Microphone permissions -> View hardware status.
4. Complete the **30-second personal baseline calibration** (learns student's neutral head pose $\mu, \sigma$).
5. Enter the **12-question Demo Exam**. Observe the top status badge (`🟢 Monitoring Active · 5.0 fps`).
6. Type a note in **"Submit an Explanation"** and check **"📜 My Evidence Record"** to see your transparent student diary.

### Interactive Scenario Simulator (DEMO MODE)
1. On any exam screen, press the **`D`** key (or click **"⚡ Scenario Panel (DEMO MODE)"**).
2. Click scenario buttons to feed scripted events into the **real proctoring pipeline** in fast-forwarded virtual time:
   - **Glance away 3s:** Risk remains 0.0 (grace window filters brief movement).
   - **Brief network drop:** Investigator resolves `TECHNICAL` (0 penalty).
   - **Sibling walks by:** Secondary face resolves `ORDINARY` (weight decays to 0).
   - **Failing webcam (15x):** Camera clamps at 40.0; gate checklist blocks warning because only 1 channel contributed.
   - **Phone + Notes Corroborated:** 2 channels cross into `WARNED`, then `ELEVATED` (+10 mins added), then `HELD` for human review.

### Faculty Portal & Adjudication
1. Sign out and sign in with the **`[ 👩‍🏫 Faculty ]`** tab (`faculty1`).
2. Open the held session in the queue to inspect:
   - Zero-dependency **pure SVG risk progression chart** with 45, 65, 80 threshold markers.
   - **Bayesian Investigator reasoning audit** card.
   - Student's own explanation alongside the video stub marker (`stub-clip-sess-...`).
3. Select an adjudication determination (`Cleared`, `Warning Stands`, `Refer Onward`) and record comments.
4. Click **"🖨️ View & Print Official Audit Report (HTML)"** to preview the printable, institutional decision document.

---

## 4. Architecture Diagram

```mermaid
flowchart TD
    subgraph Browser ["Student Browser (web/) — Pure Client Edge"]
        Camera["Webcam Feed"] --> MP["MediaPipe Face Landmarker (WASM)"]
        Audio["Microphone"] --> WebAudio["Web Audio API (Volume RMS)"]
        WindowEvents["Exam Window (Focus/Blur/Visibility)"]
        
        MP -->|Extracts 3D Pose & Gaze| Features["Feature Batcher (5 fps)\n{gaze, yaw, pitch, rms, blur}"]
        WebAudio --> Features
        WindowEvents --> Features
        
        Features -->|HTTP POST JSON (No Video!)| CaptureService
    end

    subgraph Backend ["Backend Microservices (services/) & Core Logic (core/)"]
        CaptureService["1. capture-detect (:8001)\nBaseline Calibration & Anomaly Extraction"] -->|Observations| RiskService
        
        RiskService["2. risk-engine (:8002)\nExponential Decay Accumulator\nHalf-Life H=240s & Channel Caps K=40"]
        
        RiskService <-->|Escrow Suspicious Weight| InvestService["3. investigator (:8003)\nBayesian Agent (Ordinary/Tech/Deliberate)\nExpected Information Gain Probe Selection"]
        
        RiskService -->|Score & Contributing Channels| WarnService["4. warn-escalate (:8004)\nProcedural Gates (>=2 Channels)\n6s Hysteresis & Accusation-Free Notices"]
        
        WarnService -->|Record Decisions & Referrals| ReviewService["5. review-report (:8005)\nJWT Mock Auth, Exams API,\nFaculty Portal & HTML Reports"]
    end

    subgraph Ledger ["Append-Only Evidence Ledger (SQLite / PostgreSQL)"]
        ReviewService <--> DB[("SQLite Database\n(custodian.db)\n12 Relational Tables")]
        WarnService --> DB
    end

    subgraph Faculty ["Faculty Review Portal"]
        ReviewService -->|Live Held Queue & SVG Risk Chart| FacultyUI["Faculty Portal (faculty1)\nAdjudication & 1-Click Printable Audit Report"]
    end
```

---

## 5. Privacy-by-Design Architecture

Custodian AI adheres strictly to **GDPR Article 5 Data Minimisation** and student privacy rights:

1. **Edge-Only Computer Vision:** MediaPipe runs in client RAM via WebAssembly. Video frames are analyzed inside the browser and instantly discarded. Raw webcam video is **never streamed across the network**.
2. **Audio Level Only:** Room sound is analyzed via the Web Audio API using root-mean-square (RMS) energy. Volume levels are transmitted as a scalar percentage ($0.0 - 1.0$). **Spoken words are never recorded, transcribed, or stored.**
3. **No Keylogging or Screen Snooping:** The system monitors window focus and tab visibility only. It never reads student answers, keystroke cadences, clipboard contents, or background applications.
4. **Evidence Stub Markers:** In Phase A, video segments are represented by lightweight metadata stub records (`stub-clip-sess-...`), avoiding continuous surveillance storage while maintaining human-in-the-loop reviewability.
5. **Student Right-to-Explanation:** Students can inspect their own transparent event diary during the exam and append explanations directly into the append-only ledger.

---

## 6. Fairness Regression Suite & Policy Simulator

To mathematically prove fairness over legacy proctoring, Custodian AI includes an automated benchmark suite:

```powershell
# Run the 34-scenario fairness benchmark
python scripts/dev.py fairness

# Run the What-If Policy Simulator
python scripts/dev.py simulate --grace-gaze 2.0
python scripts/dev.py simulate --corroboration-lambda 0.35
```

### Empirical Results (Custodian AI vs Legacy Baseline)

| Proctoring System | Innocent False Alarms (28 Scenarios) | Violations Caught (6 Scenarios) | Miss Rate |
|---|---|---|---|
| **Legacy Fixed-Threshold Baseline** | **25 / 28 (89.3%)** | 6 / 6 (100.0%) | 0.0% |
| **Custodian AI Adaptive Engine** | **0 / 28 (0.0%)** | 6 / 6 (100.0%) | 0.0% |
| **Empirical Improvement** | **-89.3 percentage points false alarms** | **100% security maintained** | **0% misses** |

---

## 7. Project Documentation

- [docs/DEMO_SCRIPT.md](file:///C:/Users/shiwa/Desktop/custodian-ai/docs/DEMO_SCRIPT.md): Complete 10-minute live demonstration rehearsal script.
- [docs/STATUS.md](file:///C:/Users/shiwa/Desktop/custodian-ai/docs/STATUS.md): Submission-safe architecture status and gap analysis.
- [AGENTS.md](file:///C:/Users/shiwa/Desktop/custodian-ai/AGENTS.md): Project constitution, mathematical formulas, and Phase B transition requirements.
- [.agent-notes/](file:///C:/Users/shiwa/Desktop/custodian-ai/.agent-notes/): Complete study notes, viva questions, decisions, and conceptual analogies (git-ignored).
