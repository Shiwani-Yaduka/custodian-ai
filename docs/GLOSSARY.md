# Custodian AI — Glossary of Key Concepts & Terms

This document defines core architectural, mathematical, and DevSecOps terms used across Custodian AI.

---

### Architectural & Proctoring Terms

- **Evidence Under Uncertainty:** The fundamental design philosophy that sensor readings (e.g., face not detected, background sound) are noisy, probabilistic indicators rather than definitive proof of cheating.
- **Microservices Architecture:** Decomposing an application into small, independently deployable services that communicate via lightweight protocols (HTTP/REST, Redis, message queues).
- **Grace Window ($g_s$):** A duration threshold below which transient sensor signals contribute exactly zero to the risk score (e.g., briefly blinking or looking down for 2 seconds).
- **Half-Life Decay ($H = 240\text{ s}$):** An exponential decay formula applied to accumulated risk points. If no further anomalies occur, the contribution of past events halves every 4 minutes.
- **Corroboration Multiplier ($\lambda = 0.20$):** A mathematical bonus applied only when multiple independent observation channels (e.g., audio and camera) fire simultaneously.
- **Channel Cap ($K_c$):** The maximum risk score any single channel can contribute (set to 40, strictly below the WARNED threshold of 45). Ensures a student can never be penalized by one sensor alone.
- **Hysteresis:** A mandatory 6-second stabilization requirement before any tier change (e.g., CLEAR $\to$ WATCHING $\to$ WARNED) to prevent rapid flapping or oscillating alerts.
- **Bayesian Investigation Agent:** An autonomous decision-making component that evaluates hypotheses ($H \in \{\text{ordinary}, \text{technical}, \text{deliberate}\}$) using Bayes' rule and selects diagnostic probes that maximize Information Gain (KL-divergence).

---

### DevSecOps & Cloud Terms

- **DevSecOps:** The philosophy and practice of embedding security gates (SAST, secret scanning, container vulnerability scanning, policy checks) directly into every stage of the CI/CD pipeline.
- **Infrastructure as Code (IaC):** Defining and provisioning cloud infrastructure using declarative configuration files (AWS CloudFormation) rather than manual AWS Console clicks.
- **OIDC (OpenID Connect):** An identity federation standard that allows GitHub Actions to obtain short-lived, temporary AWS credentials to execute deployments without storing permanent access keys in GitHub Secrets.
- **Shift-Left Security:** Discovering and resolving vulnerabilities and configuration errors early in the development lifecycle (on the developer's laptop and during PR checks) rather than in production.
- **Trivy:** A comprehensive, lightweight security scanner used in CI/CD to detect known CVE vulnerabilities in container images, file systems, and configuration files.
- **gitleaks:** A fast, automated SAST tool that scans git repositories for hardcoded secrets, API tokens, and private keys.
- **EKS (Elastic Kubernetes Service):** AWS managed Kubernetes control plane. In Custodian AI, it is disposable and created only during active sprint review demos to minimize cost.
