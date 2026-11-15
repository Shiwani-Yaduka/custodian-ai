# Custodian AI — 10-Minute Live Demonstration Script

> **Target Audience:** Project Guide, External Evaluator, Academic Viva Committee  
> **Presenter:** Shiwani (BTech CSE, Lovely Professional University)  
> **System Requirements:** Plain Python 3.11+, Node 20+, Chrome/Edge browser. Zero Docker, zero cloud, zero GPU.

---

## Quick Reference / Demo Cheat Sheet

| Time | Segment | Role & URL | Primary Action | Key Visual / Outcome |
|---|---|---|---|---|
| **00:00 - 01:30** | The Core Philosophy & Student Privacy | Student (`student1`)<br>`http://127.0.0.1:5173/` | Login -> Consent Screen | Plain-language privacy contract; zero video streaming |
| **01:30 - 03:00** | Edge Detection & 30s Calibration | Student (`student1`) | Hardware check -> Calibration | In-browser MediaPipe WASM; personal $\mu, \sigma$ baseline |
| **03:00 - 05:00** | Active Exam & Live Telemetry | Student (`student1`) | 12-question Demo Exam | Status badge (5 fps), live mirror, explanation ledger |
| **05:00 - 07:30** | Scenario Panel: Proving Fairness Under Noise | Demo Mode (`D` key) | 6 Buttons (Glance, Network, Webcam, etc.) | Grace windows filter glances; webcam capped at 40 (no warning!) |
| **07:30 - 08:30** | The Cheating Attempt: Corroboration & Hold | Demo Mode (`D` key) | Click "Phone + Notes Corroborated" | 2 channels + deliberate posterior -> 1st warn -> 2nd warn (+10m) -> HELD |
| **08:30 - 10:00** | Faculty Adjudication & Audit Report | Faculty (`faculty1`)<br>`http://127.0.0.1:5173/` | Review held queue -> Adjudicate | SVG risk chart, Bayesian case breakdown, 1-click printable HTML report |

---

## Detailed 10-Minute Walkthrough

### Part 1: Philosophy & Student Consent (00:00 - 01:30)

1. **Open the browser:** Navigate to `http://127.0.0.1:5173/`.
2. **Audience sees:** Clean, calm Login screen with role selector tabs `[ 🎓 Student ]` and `[ 👩‍🏫 Faculty ]`. Quick-fill demo account buttons (`student1`, `student2`, `faculty1`) are visible in demo mode.
3. **Action:** Click the `[ student1 ]` button, then click **"Sign In to Exam Portal"**.
4. **Audience sees:** The **Privacy & Consent Screen**.
5. **Talking Points:**
   - *"Most commercial proctoring tools treat students as suspects, streaming their private bedrooms to cloud servers and issuing automated verdicts."*
   - *"Custodian AI is built on a different thesis: evidence under uncertainty. We never record whole video sessions, never record speech, and never issue automated failing verdicts."*
   - *"Look at this privacy contract: it explicitly tells the student in plain language what is measured (abstract facial geometry, volume level) and what is NEVER collected (video streams, keystrokes inside answers, screen capture)."*
6. **Action:** Click **"I Understand & Agree to Proceed"**.

---

### Part 2: Edge WASM Detection & Personal Baseline Calibration (01:30 - 03:00)

1. **Audience sees:** Camera & Microphone Permission screen with live hardware check and clear troubleshooting instructions.
2. **Action:** Click **"Grant Camera & Audio Access"**. Browser prompts for webcam/mic permissions; click **Allow**.
3. **Audience sees:** Live webcam mirror appears with green connection pills: `Webcam Connected (640x480)` and `Microphone Active`.
4. **Action:** Click **"Start 30-Second Calibration"**.
5. **Audience sees:** 30-second countdown circle with live telemetry bars showing Gaze Deviation, Head Yaw/Pitch, and Face Dimensions.
6. **Talking Points:**
   - *"All computer vision runs entirely on the student's laptop via MediaPipe Face Landmarker compiled to WebAssembly (WASM). No video pixels are ever transmitted over the network."*
   - *"Why do we calibrate for 30 seconds? Because static thresholds are inherently unfair. A student with an external monitor looks higher; a low desk forces a downward gaze. During calibration, we calculate this specific student's neutral mean ($\mu$) and standard deviation ($\sigma$). All later thresholds are relative to this baseline."*

---

### Part 3: Live Exam Experience & Explanation Box (03:00 - 05:00)

1. **Audience sees:** The 12-question **Demo Exam** (10 MCQs + 2 Written Questions) with an active 30-minute countdown timer.
2. **Audience sees:** At the top right: a small, calm status badge `🟢 Monitoring Active · 5.0 fps` and a picture-in-picture student mirror with live pose readouts.
3. **Action (Physical Check):**
   - Turn your head to the side for 2-3 seconds -> observe badge changes to `🟡 Head Turned (+28°)`, but risk stays at 0.0 because of the 4-second grace window.
   - Look at Question 1 ("What is the primary architectural purpose of the Investigation Agent?") and click option B.
4. **Action (Explanation Submission):**
   - Scroll down to the **"Submit an Explanation"** card.
   - Type: *"Testing natural head movement during exam reading"* and click **"Save Explanation to Ledger"**.
   - Notice the green confirmation: *"Explanation logged to append-only evidence ledger."*
5. **Action (Student Evidence Diary):**
   - Click **"📜 My Evidence Record"** in the top navigation bar.
   - Audience sees the chronological student diary: each observation noted under uncertainty, alongside the student's own explanation.
   - Click **"Back to Exam"**.

---

### Part 4: The Scenario Panel — Proving Fairness Under Noise (05:00 - 07:30)

1. **Action:** Press the keyboard key **`D`** (or click **"⚡ Scenario Panel (DEMO MODE)"** at the top right).
2. **Audience sees:** The interactive **Scenario Panel (Demo Mode)** modal overlay.
   - Live telemetry: Risk gauge ($0 - 100$), Tier badge (`CLEAR`), 4-channel accumulator bars (Camera, Microphone, Exam Window, Device) with the $40.0$ safety cap line marked, the 3-item Gate Checklist, and Bayesian Posterior probabilities ($P(H|E)$).
3. **Talking Points:**
   - *"These buttons do not display hardcoded animations or fake responses. Each button injects synthetic sensory batches into the REAL InProcessPipeline running the exact same risk engine, investigator, and SQLite ledger."*
4. **Action & Visuals — Run Scenario Buttons:**
   - **Click "Glance away 3s":**
     - *Audience sees:* Gaze fires for 3.0s. Risk remains **0.0 (CLEAR)**.
     - *Talking point:* *"Grace window ($g_s = 4.0$s) filters out innocent glances. Zero penalty."*
   - **Click "Brief network drop":**
     - *Audience sees:* Network packet loss detected. Investigator opens Case #1, runs device telemetry probes, and resolves `TECHNICAL` ($P = 0.92$). Risk remains **0.0 (CLEAR)**.
     - *Talking point:* *"Hardware/network faults are discounted to 0 weight."*
   - **Click "Sibling walks by":**
     - *Audience sees:* Secondary face detected for 2.5s. Investigator runs soft reminder probe and resolves `ORDINARY`. Risk blips to 2.7 and naturally decays away.
   - **Click "Failing webcam, repeated (15x)":**
     - *Audience sees:* Camera drops out 15 consecutive times. The Camera accumulator climbs and clamps exactly at **40.0**. Total score stays at 40.0 in `WATCHING`.
     - *Talking point:* *"Notice the gate checklist: 'At least 2 channels contributing: NO'. A broken camera can NEVER breach the 45.0 WARNED threshold alone. Single-channel isolation is mathematically proven."*

---

### Part 5: The Coordinated Cheating Attempt — Corroboration & Escalation (07:30 - 08:30)

1. **Action:** Click **"Reset Session"** to return to clean state.
2. **Action:** Click **"Phone + Notes, Corroborated"**.
3. **Audience sees:**
   - Step 1: Prolonged off-screen gaze down at notes (camera channel climbs).
   - Step 2: Whispered voice detected (microphone channel climbs). Corroboration multiplier activates ($1 + 0.20 \times 1 = 1.20\times$).
   - Step 3: Investigator opens Case, runs quiet probes, and resolves `DELIBERATE` ($P(\text{deliberate}) = 0.94$).
   - Step 4: Gates pass: Score crosses 45.0 with 2 channels -> **First Warning Issued** (*"Please ensure your attention remains directed at the screen..."*).
   - Step 5: Violation continues -> Score crosses 65.0 -> **Second Warning Issued** with **10 minutes added to clock**.
   - Step 6: Score crosses 80.0 with 2 warnings shown and $P(\text{deliberate}) \ge 0.85$ -> **HELD**.
   - *Final Status:* Badge turns red `HELD`. Exam pauses. Notice displays: *"Exam paused. Evidence submitted to human faculty reviewer."*
4. **Talking Points:**
   - *"Notice what happened: Custodian AI never disqualified the student. The most severe outcome the algorithm can trigger is pausing the exam and referring the case to a human faculty member with the complete evidence ledger."*

---

### Part 6: Faculty Adjudication & Decision Report (08:30 - 10:00)

1. **Action:** Click **"Close Demo Panel"**. Click **"Sign Out"** at top right.
2. **Action:** On the Login screen, click the **`[ 👩‍🏫 Faculty ]`** tab, click **`[ faculty1 ]`**, and click **"Sign In as Faculty"**.
3. **Audience sees:** The **Faculty Review Portal**.
   - Queue lists the HELD session: `Candidate: student1`, `Exam: Demo Exam`, `Reason: 2 channels corroborated; deliberate posterior 0.94`.
4. **Action:** Click on the session row to inspect details.
5. **Audience sees:**
   - **Risk-Over-Time Chart:** Zero-dependency pure SVG timeline showing exact score progression crossing the 45, 65, and 80 threshold lines.
   - **Bayesian Investigator Card:** Explains in plain language why the case was classified deliberate ($P = 0.94$).
   - **Student Explanation & Stub Marker:** The student's explanation displayed directly alongside the video stub clip reference (`stub-clip-sess-...`).
6. **Action (Adjudication):**
   - In the Human Determination form, select **"Warning Stands (Allow Exam Submission)"**.
   - In Faculty Review Comments, type: *"Reviewed audio and gaze telemetry. Clear notes look-down; warning issued appropriately. Candidate allowed to complete remaining time."*
   - Click **"Record Human Determination"**.
7. **Action (Downloadable Audit Report):**
   - Click **"🖨️ View & Print Official Audit Report (HTML)"**.
   - Audience sees the self-contained, printable HTML decision report with institutional header, complete sensory timeline, and human faculty signature block.
8. **Conclusion Talking Point:**
   - *"This completes the full cycle: from edge detection and calibration, through adaptive risk accumulation and Bayesian investigation, to transparent human faculty adjudication. That is Custodian AI."*

---

## Contingency: "What If the Webcam Fails During the Live Demo?"

If the physical webcam fails, permissions are blocked by the browser, or lighting in the evaluation room is poor:
1. **Calmly state to the evaluator:**
   > *"In commercial proctoring, a camera driver glitch crashes the exam and fails the student. In Custodian AI, edge hardware faults are handled gracefully. I will now switch to our built-in Scenario Simulator to demonstrate the exact same real proctoring pipeline with controlled sensory feeds."*
2. **Press `D` on the keyboard.**
3. **Run Scenario 4 ("Failing webcam, repeated")** to show the committee that the risk engine explicitly absorbs webcam disconnects, capping the accumulator at 40.0 without issuing an unfair warning.
4. Continue with Scenario 5 ("Phone + Notes Corroborated") to show the rest of the pipeline.
