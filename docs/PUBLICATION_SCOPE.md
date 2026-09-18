# ArogyaTwin Publication Scope, Conceptual Boundaries & Limitations

**Document Identifier:** `docs/PUBLICATION_SCOPE.md`  
**Repository:** `mishrasatvik94/arogyatwin-research`  
**Associated Paper:** *ArogyaTwin: An Adaptive Expiry-Aware Edge Surveillance Architecture for Intermittently Connected Rural Health Networks*  
**Date:** September 18, 2026  
**Standard:** Rigorous Scientific Positioning, CIRP Engineering Taxonomy, and Evidentiary Discipline  

---

## 1. System Definition & Approved Scientific Terminology

ArogyaTwin is strictly defined as:
> **"A digital-twin-inspired edge state representation for rural health surveillance"**  
> or, where formally distinguishing data integration flow:  
> **"A digital-shadow-inspired cyber-physical surveillance state model."**

### Grounding in CIRP Engineering Taxonomy
In accordance with the foundational engineering taxonomy established by Jones et al. (2020) and Fuller et al. (2020):
- **Digital Model:** Manual bidirectional data flow between physical asset and digital representation.
- **Digital Shadow:** Automated one-way data flow from the physical entity to the digital model; subsequent real-world interventions remain manual or advisory.
- **Digital Twin:** Fully automated, closed-loop bidirectional coupling, where digital state changes directly actuate physical mechanisms without human mediation.

Under this formal standard, ArogyaTwin operates strictly as a **Digital Shadow**. Edge gateways at rural clinics automatically ingest heterogeneous observation streams to maintain a cyber-physical state representation. However, all subsequent epidemiological alerts and containment interventions are delivered as decision-support artifacts to human public health officials.

---

## 2. Categorical Scope Exclusions (What ArogyaTwin Is NOT)

To maintain absolute scientific and clinical integrity, the following components are explicitly outside the scope of ArogyaTwin:
- **No Patient-Specific Physiological Modeling:** ArogyaTwin does not model cardiac electrophysiology, pulmonary airflow, pharmacokinetic metabolism, or cellular biophysics.
- **No EHR or Personal Health Avatars:** ArogyaTwin processes zero electronic health records (EHRs) and constructs no individual patient avatars.
- **No Autonomous Clinical Diagnosis:** The system evaluates syndromic anomaly signals; it does not diagnose patient diseases or prescribe therapeutics.
- **No Hardware-in-the-Loop Clinical Sensing:** The evaluation does not attach physical biomedical transducers to human subjects.
- **No Prospective Clinical Validation:** The system has not been evaluated in prospective clinical patient trials.

---

## 3. Scientific Scope & Systems Architecture

ArogyaTwin investigates an integrated cross-layer systems architecture:
$$\text{Multi-Source Evidence Trust } (T_i) + \text{Spatial Corroboration } (C_k) + \text{Observed Contact Dynamics } (\bar{R}_i) \longrightarrow \text{Dynamic Lifetime } (\text{TTL}_p) \longrightarrow \text{Pre-Relay Queue Pruning}$$
evaluated across intermittently connected delay-tolerant networks to eliminate stale data flooding without compromising valid outbreak alert delivery. The research focuses on the systems-level interaction between application-layer evidence semantics and store-and-forward queue management.

---

## 4. Cryptographic Budgeting & Envelope Specification

1. **Baseline 64-Byte Envelope (Symmetric HMAC-SHA256):**
   - Surveillance Metadata: 32 Bytes
   - Cryptographic Authentication: 32-Byte HMAC-SHA256 Authentication Tag (RFC 2104 / FIPS 198-1)
   - Total Size: **64 Bytes** (yielding an **87.5% packet reduction** vs. 512-byte raw telemetry).
   - Designed for rural clinics with pre-shared gateway-to-hub secret keys.
2. **Asymmetric 96-Byte Envelope (Ed25519 Extension):**
   - Under RFC 8032, a standard Ed25519 digital signature is strictly **64 bytes** (512 bits: 32-byte point $R$ + 32-byte scalar $S$).
   - When intermediate DTN ferries require independent public-key verification without symmetric keys, appending a 64-byte Ed25519 signature to the 32-byte metadata expands the packet to **96 bytes** (still an **81.25% reduction** vs. 512-byte raw JSON).

---

## 5. Transparent Disclosure of Core Study Limitations

The research paper openly discloses fundamental operational and methodological limitations:

1. **Synthetic Simulation Environment:** Evaluated using discrete-event simulation in Python/NumPy rather than an in-situ rural field deployment.
2. **Simplified Contact & Outage Dynamics:** Inter-village contact opportunities and link outages follow stationary Bernoulli/Poisson trials rather than empirical GPS mobility traces.
3. **Absence of Clinical Patient Validation:** The architecture processes aggregated syndromic counts; clinical diagnostic accuracy on human patients is not evaluated.
4. **Lack of Physical Hardware-in-the-Loop Profiling:** While ESP32 microbenchmarks confirm feasibility (0.11 ms HMAC, 17.8 ms Ed25519), extensive physical hardware bench testing remains future work.
5. **Calibrated Operational Baseline:** Trust model weights and TTL scaling coefficients were determined through engineering calibration as an operational baseline, rather than through an automated parameter optimization procedure.
6. **Adversarial Resilience Scope:** Evaluates resilience against false reporting bursts from compromised observation sources; advanced persistent multi-village collusion scenarios remain an open area for future distributed defense mechanisms.
