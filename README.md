# ArogyaTwin

**An Adaptive Expiry-Aware Edge Surveillance Architecture for Intermittently Connected Rural Health Networks**

ArogyaTwin is an edge-native disease outbreak surveillance framework designed for resource-constrained, intermittently connected rural health networks. Operating on digital-twin-inspired state representations at village health posts and edge gateways, ArogyaTwin couples adaptive multidimensional trust calibration with dynamic, uncertainty-aware packet lifetime (TTL) determination and proactive stale-packet suppression. This design ensures timely outbreak verification at regional monitoring hubs while mitigating buffer overflow and bandwidth wastage over delayed, disruption-tolerant network (DTN) channels.

---

## Research Paper

This repository contains the authoritative simulation source code, experimental runners, manifests, trial-level results, and figure-generation scripts associated with the research paper:

> **ArogyaTwin: An Adaptive Expiry-Aware Edge Surveillance Architecture for Intermittently Connected Rural Health Networks**

*Note: This repository provides artifacts for peer review and replication. Publication details and citations will be updated upon final appearance.*

---

## Architecture and Key Design Principles

- **Digital-Twin-Inspired State Representation:** Rather than maintaining high-overhead full physical digital twins, ArogyaTwin maintains localized, compact state vectors at village edge gateways, tracking signal confidence, inter-source consensus, environmental drift, and historical reporting fidelity.
- **Packet Structure & Communication Overhead:**
  - **Raw Packet Size:** 512 B (uncompressed sensor/telemetry payloads).
  - **Compact Signature Packet Size:** 64 B (87.5% packet-level payload reduction).
  - **Amortized Communication Metric:** 53.67 B/event transmitted per candidate outbreak event in the full ArogyaTwin configuration (a communication cost metric amortized over the 30-day evaluation horizon, distinct from wire packet size).
- **Adaptive Trust Model:** Village reporting integrity is governed by a multi-factor trust metric combining historical reporting fidelity, mean reporter confidence, inter-source spatial consensus, and environmental sensor drift tracking. Parameter weights represent a calibrated operating baseline for the simulation environment, strictly preventing ground-truth leakage during real-time forwarding.
- **Adaptive Expiry & Proactive Suppression:** Dynamic TTL bounding based on spatial consensus and current trust, enabling intermediate relay nodes and edge gateways to discard stale packets before occupying constrained DTN storage buffers.

---

## Repository Structure

```text
arogyatwin/
├── sim/
│   ├── __init__.py                 # Simulation package initialization
│   ├── core.py                     # Constants, scenario definitions, ground-truth generation, trust/TTL models
│   ├── engine.py                   # Discrete-time simulation engine, 7 ablation configurations, network outage logic
│   └── metrics.py                  # Evaluation metrics, delay-degraded precision/recall, 95% CI calculation
├── dtn.py                          # Opportunistic DTN routing implementations (Epidemic, Spray-and-Wait, PRoPHET)
├── run_experiment.py               # Main 30-trial experiment runner across 7 configurations (seeds 8000–8029)
├── run_dtn_experiment.py           # DTN sub-experiment runner across 3 protocols and 2 modes (seeds 7000–7014)
├── make_figures.py                 # Figure generator for paper Figures 7–12 (including Figure 10 queue experiment)
├── experiment_manifest.json        # Detailed execution manifest and metadata for the main experiment & Figure 10
├── dtn_experiment_manifest.json    # Execution manifest and configuration metadata for the DTN sub-experiment
├── results.json                    # Aggregated statistics and 95% confidence intervals for the main experiment
├── results_trials.json             # Full 210-trial raw output rows for the main experiment
├── dtn_results.json                # Aggregated summary and 95% confidence intervals for the DTN sub-experiment
├── dtn_results_trials.json         # Full 90-trial raw output rows for the DTN sub-experiment
├── fig7_latency_cdf.png            # Valid-alert delivery latency CDF
├── fig8_stale_handling.png         # Stale-packet transmission vs. proactive suppression
├── fig9_bandwidth.png              # Communication overhead by configuration (log scale)
├── fig10_queue_occupancy.png       # Queue occupancy over 30-day horizon (mean of 10 trials)
├── fig11_ablation_precision.png    # Ablation comparison of regional verification precision and recall
├── fig12_trust_calibration.png     # Adaptive trust calibration under chronically degraded node
├── requirements.txt                # Pinned dependency requirements
├── README.md                       # Repository overview and reproduction documentation
└── docs/
    ├── REPRODUCIBILITY_STATUS.md   # Complete verification audit and ground-truth metrics
    └── PUBLICATION_SCOPE.md        # Conceptual boundaries, terminology, and limitations
```

---

## Executed Experiments

The paper reports findings from three distinct, strictly separated experimental setups:

### 1. Main ArogyaTwin Experiment
- **Configurations Evaluated (7):**
  1. `centralized_raw` (Baseline: 512 B raw packets, no expiry, no trust)
  2. `fixed_ttl` (64 B compact, fixed 48h TTL, no adaptive trust)
  3. `fixed_trust` (64 B compact, static trust $T=0.5$, adaptive TTL)
  4. `no_signature` (512 B raw packets, adaptive TTL and trust)
  5. `no_expiry` (64 B compact, no TTL suppression)
  6. `no_diversity` (64 B compact, candidate threshold requires only 1 reporter)
  7. `full` (Full ArogyaTwin: 64 B compact, multi-source consensus, adaptive trust, dynamic TTL)
- **Trials & Seeds:** 30 trials per configuration (seeds 8000–8029).
- **Execution Volume:** 210 / 210 configuration-trial runs completed successfully.
- **Key Artifacts:** `results.json`, `results_trials.json`, `experiment_manifest.json`.

### 2. DTN Sub-Experiment
- **Relay Protocols Evaluated:**
  - Epidemic Routing
  - Binary Spray-and-Wait ($L = 8$)
  - PRoPHET ($P_{\text{init}} = 0.75, \beta = 0.25, \gamma = 0.98$)
- **Operating Modes:**
  - `naive` (standard DTN forwarding without expiration checks)
  - `expiry_aware` (ArogyaTwin dynamic TTL evaluation prior to custody transfer)
- **Trials & Seeds:** 15 trials per protocol/mode combination (seeds 7000–7014).
- **Execution Volume:** 90 / 90 protocol-mode-trial runs completed successfully.
- **Key Artifacts:** `dtn_results.json`, `dtn_results_trials.json`, `dtn_experiment_manifest.json`.

### 3. Figure 10 Queue-Occupancy Experiment
- **Setup:** A dedicated 10-trial time-series queue-trace experiment evaluating buffer accumulation across 6 village gateways during a 96-hour network outage.
- **Seeds:** 8500–8509 (10 trials per configuration: `centralized_raw`, `fixed_ttl`, `full`).
- **Distinction:** Figure 10 presents the temporal mean of these 10 distinct trace trials to visualize buffer pressure under acute isolation. This queue experiment is kept strictly separate from the 30-trial main aggregated sample.

---

## Summary of Results

All reported values are derived from reproducible simulation runs with 95% confidence intervals (t-distribution, $\text{ddof}=1$):

| Configuration | Bytes / Event (B) | Stale Rate (%) | Suppression (%) | Verification Precision | Outbreak Recall | Max Queue / Village |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Centralized / Raw** | $512.00 \pm 0.00$ | $14.15 \pm 0.82$ | $0.00 \pm 0.00$ | $0.333 \pm 0.000$ | $1.000 \pm 0.000$ | $82.87 \pm 2.14$ |
| **No Compact Signature** | $429.35 \pm 7.74$ | $0.00 \pm 0.00$ | $16.15 \pm 0.81$ | $0.523 \pm 0.043$ | $1.000 \pm 0.000$ | $31.93 \pm 1.65$ |
| **Fixed-TTL (48h)** | $54.94 \pm 0.97$ | $0.00 \pm 0.00$ | $14.16 \pm 0.87$ | $0.520 \pm 0.038$ | $1.000 \pm 0.000$ | $24.60 \pm 1.42$ |
| **Fixed-Trust ($T=0.5$)** | $55.03 \pm 0.83$ | $0.00 \pm 0.00$ | $14.02 \pm 0.82$ | $0.434 \pm 0.039$ | $1.000 \pm 0.000$ | $32.87 \pm 1.70$ |
| **No Expiry Suppression** | $64.00 \pm 0.00$ | $16.09 \pm 0.86$ | $0.00 \pm 0.00$ | $0.523 \pm 0.043$ | $1.000 \pm 0.000$ | $82.87 \pm 2.14$ |
| **No Diversity Check** | $53.67 \pm 0.31$ | $0.00 \pm 0.00$ | $16.15 \pm 0.81$ | $0.364 \pm 0.012$ | $1.000 \pm 0.000$ | $31.93 \pm 1.65$ |
| **Full ArogyaTwin** | $\mathbf{53.67 \pm 0.31}$ | $\mathbf{0.00 \pm 0.00}$ | $\mathbf{16.15 \pm 0.81}$ | $\mathbf{0.523 \pm 0.043}$ | $\mathbf{1.000 \pm 0.000}$ | $\mathbf{31.93 \pm 1.65}$ |

> **Note on Verification Precision:** The 95% confidence interval for Full ArogyaTwin is **[0.481, 0.566]** (mean 0.5233). Removing the multi-source diversity requirement causes precision to collapse to 0.3644 [95% CI: 0.352, 0.377], establishing the necessity of cross-source corroboration.

> **Note on Packet Envelope:** The baseline evaluated packet size is **64 bytes** ($32\text{ B payload} + 32\text{ B HMAC-SHA256}$ authentication tag, RFC 2104). For untrusted relays requiring asymmetric public-key verification without symmetric keys, appending a standard 64-byte Ed25519 signature (RFC 8032) expands the packet to **96 bytes** ($32\text{ B} + 64\text{ B}$), which still delivers an 81.25% bandwidth reduction over raw 512-byte telemetry. See [`docs/PUBLICATION_SCOPE.md`](docs/PUBLICATION_SCOPE.md) for full details.

---

## Reproduction Guide

### Prerequisites

- Python 3.10+ (tested on Python 3.13.7)
- Standard packages specified in `requirements.txt`:
  ```bash
  pip install -r requirements.txt
  ```

### Step 1: Run the Main ArogyaTwin Experiment (30 Trials)
To execute all 210 trial-configuration runs (seeds 8000–8029 across 7 configurations) and regenerate `results.json` and `results_trials.json`:
```bash
python run_experiment.py
```

### Step 2: Run the DTN Sub-Experiment (90 Runs)
To execute the opportunistic routing comparison (Epidemic, Spray-and-Wait, PRoPHET in naive and expiry-aware modes; seeds 7000–7014) and regenerate `dtn_results.json` and `dtn_results_trials.json`:
```bash
python run_dtn_experiment.py
```

### Step 3: Generate Publication Figures (Figures 7–12)
To generate all paper figures from the experimental data:
```bash
python make_figures.py
```
This script reads `results.json` for Figures 8, 9, and 11, runs the separate 10-trial queue-trace experiment (seeds 8500–8509) for Figure 10, runs latency CDF sampling (seeds 8000–8009) for Figure 7, and generates the trust calibration trajectory (seeds 8600–8609) for Figure 12.
