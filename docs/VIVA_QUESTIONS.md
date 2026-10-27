# Custodian AI — Viva & Guide Defense Questions

This document prepares you for technical viva sessions and project defense with your university guide.

---

## Sprint 1 — Task 1: Architecture & Project Skeleton

### Question 1: Why did you organize Custodian AI as a monorepo instead of five separate repositories for the five microservices?
**Answer:**
A monorepo layout is optimal for this project because:
1. **Atomic Commits & Contract Versioning:** The risk engine, investigator, and capture services share strict Pydantic data contracts located in `shared/`. When an event schema changes, both producer and consumer can be updated and tested in a single atomic commit without multi-repo dependency version mismatch.
2. **Simplified CI/CD & Fairness Testing:** The fairness regression suite evaluates the entire system end-to-end. In a monorepo, a pull request can run integration tests across all five services and the fairness runner simultaneously.
3. **Low Operational Overhead:** Managing five repositories, five sets of permissions, and cross-repo CI triggers introduces unnecessary complexity for our small team and academic timeline. Each service still maintains independent Dockerfiles and Kubernetes deployment boundaries.

---

### Question 2: Why are your AWS CloudFormation templates divided into two separate stacks (`01-baseline.yaml` and `02-cluster.yaml`)?
**Answer:**
CloudFormation templates are decoupled into two distinct lifecycles to guarantee data protection and minimize AWS costs:
1. **Lifecycle Independence:** `01-baseline.yaml` provisions long-lived foundational assets: the VPC, KMS keys, IAM OIDC deploy roles, and the S3 evidence bucket containing student audit trails with `DeletionPolicy: Retain`.
2. **Cost-Optimized Disposable Compute:** `02-cluster.yaml` provisions Amazon EKS worker nodes and the Kubernetes control plane (which costs ~$0.10/hour). Because the cluster is disposable, we spin it up only for live evaluations/demos and tear it down immediately afterward (`make teardown`).
3. **Data Loss Prevention:** If the cluster stack is deleted or encounters a deployment rollback, stored evidence clips and KMS encryption keys in the baseline stack remain 100% safe and intact.

---

### Question 3: Why is there a top-level `fairness/` directory, and why is the fairness suite part of your definition of done?
**Answer:**
In an automated proctoring system, standard unit and integration tests only verify that code runs without crashing; they do not verify that the algorithmic decisions are ethical, unbiased, or fair to students.
1. **Algorithmic Accountability:** The `fairness/` suite replays hundreds of synthetic and recorded sessions representing edge cases: poor lighting, transient WiFi drops, sudden sneezing or looking down, neurodivergent movement patterns, or siblings walking in the background.
2. **Automated Quality Gate:** If an algorithm tweak causes the false-flag rate to exceed our tolerance threshold, the CI pipeline fails immediately—just like a broken unit test. This enforces our primary project priority: *fairness to students > privacy > explainability > scale > cost*.
