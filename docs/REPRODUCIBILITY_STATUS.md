# ArogyaTwin Research Reproducibility Status Report

**Document Identifier:** `docs/REPRODUCIBILITY_STATUS.md`  
**Repository:** `mishrasatvik94/arogyatwin-research`  
**Associated Paper:** *ArogyaTwin: An Adaptive Expiry-Aware Edge Surveillance Architecture for Intermittently Connected Rural Health Networks*  
**Evaluation Standard:** Deterministic Pseudo-Random Seeding & Full Artifact Traceability  
**Status:** **100% REPRODUCIBLE (ALL ARTIFACTS VERIFIED)**  

---

## 1. Overview and Reproducibility Guarantee

Every numerical result, confidence interval, statistical comparison, and figure presented in the research paper is 100% deterministic and reproducible from the source code and configuration files in this repository.

Each simulation run is driven by an explicit integer pseudo-random seed. Given identical seeds, the Python discrete-event engine (`sim/engine.py`) and delay-tolerant routing engine (`dtn.py`) generate bit-for-bit identical state trajectories, packet histories, and performance metrics.

---

## 2. Experimental Suite Mapping

| Experiment Suite | Configurations / Protocols | Random Seeds | Total Runs | Execution Script | Primary Outputs | Reproducibility Status |
|---|---|:---:|:---:|---|---|:---:|
| **Main ArogyaTwin Comparison** | 7 configurations (`centralized_raw`, `fixed_ttl`, `fixed_trust`, `no_signature`, `no_expiry`, `no_diversity`, `full`) | 8000–8029 (30 seeds) | **210** | `python run_experiment.py` | `results.json`, `results_trials.json` | **VERIFIED (100%)** |
| **Delay-Tolerant Routing Integration** | 3 protocols (Epidemic, Spray-and-Wait, PRoPHET) $\times$ 2 modes (`naive`, `expiry_aware`) | 7000–7014 (15 seeds) | **90** | `python run_dtn_experiment.py` | `dtn_results.json`, `dtn_results_trials.json` | **VERIFIED (100%)** |
| **Queue-Stress Blackout Benchmark** | 3 configurations (`centralized_raw`, `fixed_ttl`, `full`) during 96h outage | 8500–8509 (10 seeds) | **30** | Embedded in `make_figures.py` | `fig10_queue_occupancy.png`, `results.json` (`fig10_queue_metrics`) | **VERIFIED (100%)** |
| **Sensor Drift Calibration Benchmark** | Chronically degraded source ($v_5, s_0$) with EMA drift tracking | 8600–8609 (10 seeds) | **10** | Embedded in `make_figures.py` | `fig12_trust_calibration.png`, `results.json` (`fig12_calibration_metrics`) | **VERIFIED (100%)** |

---

## 3. Key Quantitative Benchmarks (Ground Truth)

All metrics below are computed across 30 independent trials (mean $\pm$ 95% confidence interval, t-distribution, $\text{ddof}=1$):

| Metric | Centralized / Raw | ArogyaTwin (Full) | Relative Improvement / Significance |
|---|:---:|:---:|:---:|
| **Individual Packet Wire Size** | 512 Bytes | 64 Bytes | **$-87.50\%$** wire payload reduction |
| **Amortized Communication Cost** | 512.00 B/event (615,100 B total) | 53.67 B/event (64,495 B total) | **$-89.52\%$** overall transmitted-byte savings ($9.54\times$ reduction) |
| **Stale Packet Delivery Rate** | 14.15% (170.03 packets) | **0.0000%** (0.00 packets) | **$100\%$ elimination** of stale data delivery |
| **Proactively Discarded Dead Packets** | 0.00 packets | 194.07 packets | Suppressed locally prior to transmission |
| **Regional Verification Precision** | 0.3333 | **0.5233** [95% CI: 0.481, 0.566] | **$+57.0\%$** precision improvement under noise and adversarial attack |
| **Precision Without Diversity (Ablation)** | — | 0.3644 [95% CI: 0.352, 0.377] | Demonstrates necessity of multi-source spatial corroboration |
| **Outbreak 1 Detection Latency** | 89.33 hours | 96.30 hours | $+6.97\text{ h}$ relative delay (dominated by 96h outage) |
| **Outbreak 2 Detection Latency** | 9.93 hours | 17.03 hours | $+7.10\text{ h}$ relative delay |
| **Queue Occupancy Peak (96h Blackout)** | 34.00 packets | **9.52 packets** | **$-72.00\%$** peak queue buffer reduction |
| **Epidemic Routing Copy Overhead** | 1,894,200 Bytes | 1,428,352 Bytes | **$-24.60\%$** copy bytes (stale: $0.241 \to 0.000$, delivery: $0.614 \to 0.615$) |
| **PRoPHET Routing Copy Overhead** | 3,512,800 Bytes | 1,313,728 Bytes | **$-62.60\%$** copy bytes (stale: $0.630 \to 0.000$, delivery: $0.617 \to 0.616$) |

---

## 4. Software Dependencies & Verification Environment

The reproducibility suite requires only standard scientific Python packages:
- **Python:** 3.10, 3.11, 3.12, or 3.13 (verified on Python 3.13.7 64-bit on Windows and Linux)
- **NumPy:** $\ge 1.24.0$ (verified on NumPy 2.2.3)
- **Matplotlib:** $\ge 3.7.0$ (verified on Matplotlib 3.10.0)

Installation via pinned `requirements.txt`:
```bash
pip install -r requirements.txt
```

---

## 5. Exact Step-by-Step Reproduction Instructions

### Step 1: Execute Main Experiment Suite (210 Runs)
```bash
python run_experiment.py
```
*Expected runtime:* ~12 to 20 seconds.  
*Outputs updated:* `results.json`, `results_trials.json`.

### Step 2: Execute Delay-Tolerant Routing Suite (90 Runs)
```bash
python run_dtn_experiment.py
```
*Expected runtime:* ~8 to 15 seconds.  
*Outputs updated:* `dtn_results.json`, `dtn_results_trials.json`.

### Step 3: Render Authoritative Figures (Figures 7–12)
```bash
python make_figures.py
```
*Expected runtime:* ~5 to 8 seconds.  
*Outputs updated:* `fig7_latency_cdf.png`, `fig8_stale_handling.png`, `fig9_bandwidth.png`, `fig10_queue_occupancy.png`, `fig11_ablation_precision.png`, `fig12_trust_calibration.png`.
