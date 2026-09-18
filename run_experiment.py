"""
ArogyaTwin Full Experiment Runner
==================================
- 3-trial validation (seeds 8000-8002)
- 30-trial full experiment (seeds 8000-8029)
- All 7 configurations x scenario: long_outage (primary) + all scenarios
- Results saved to results_trials.json, results.json, experiment_manifest.json
"""
import json
import math
import traceback
from datetime import datetime
from math import sqrt

import numpy as np
import scipy.stats

from sim.engine import run_trial, CONFIGS
from sim.metrics import compute_metrics, ci95
from sim.core import (
    SCENARIOS, HOURS, COMPACT_SIZE_BYTES, RAW_SIZE_BYTES,
    TRUST_WEIGHTS, TTL_MIN, TTL_MAX, CANDIDATE_MIN_SOURCES,
    OUTBREAK_1, OUTBREAK_2, ADVERSARIAL_VILLAGE, ADVERSARIAL_WINDOW,
    VERIFICATION_DELAY, H_ALPHA, H_PRIOR, B_L, B_T,
)

SCENARIO_PRIMARY = "long_outage"
ALL_CONFIGS = list(CONFIGS.keys())
SEED_BASE = 8000
N_TRIALS_FULL = 30
N_TRIALS_VALIDATION = 3

CANONICAL_METRICS = [
    "n_generated", "n_delivered", "n_stale", "proactive_discards",
    "stale_rate", "bytes_per_event", "bytes_per_day", "total_bytes",
    "mean_valid_latency", "median_valid_latency",
    "mean_queue", "max_queue",
    "detect_latency_ob1", "detect_latency_ob2",
    "false_verified_adversarial", "n_false_verifs_adversarial",
    "precision", "recall", "calib_error",
    "degraded_bytes", "reliable_bytes", "degraded_share",
]


def run_one(scenario, config, seed, trial_idx):
    try:
        r = run_trial(scenario, config, seed=seed)
        m = compute_metrics(r, seed=seed)
        return dict(
            ok=True, scenario=scenario, config=config, seed=seed, trial=trial_idx,
            metrics=m,
            queue_trace_peak=int(np.max([q for (_, _, q) in r["queue_trace"]])),
        )
    except Exception as e:
        return dict(
            ok=False, scenario=scenario, config=config, seed=seed, trial=trial_idx,
            error=str(e), traceback=traceback.format_exc()
        )


def aggregate_results(trial_rows):
    """Aggregate trial-level dicts into mean/CI dict per metric."""
    out = {}
    for metric in CANONICAL_METRICS:
        vals = []
        for row in trial_rows:
            if row["ok"]:
                v = row["metrics"].get(metric)
                if v is not None and not (isinstance(v, float) and math.isnan(v)):
                    vals.append(v)
        stats = ci95(vals)
        out[metric] = {
            "mean": stats["mean"],
            "sd": stats["sd"],
            "se": stats["se"],
            "ci95": stats["ci95_margin"],
            "ci95_lo": stats["ci95_lo"],
            "ci95_hi": stats["ci95_hi"],
            "n": stats["n"],
        }
    return out


# =====================================================================
# STAGE 1: 3-trial validation
# =====================================================================
print("=" * 60)
print("STAGE 1: 3-TRIAL VALIDATION")
print("=" * 60)
validation_rows = []
failed_v = 0
for trial_idx in range(N_TRIALS_VALIDATION):
    seed = SEED_BASE + trial_idx
    for cfg in ALL_CONFIGS:
        res = run_one(SCENARIO_PRIMARY, cfg, seed, trial_idx)
        if res["ok"]:
            m = res["metrics"]
            print(f"  trial={trial_idx} seed={seed} cfg={cfg:20s} "
                  f"n_gen={m['n_generated']:5d} stale={m['stale_rate']:.3f} "
                  f"prec={m['precision']:.3f} rec={m['recall']:.3f} "
                  f"bpe={m['bytes_per_event']:.1f}B")
        else:
            print(f"  FAIL trial={trial_idx} seed={seed} cfg={cfg}: {res['error']}")
            failed_v += 1
        validation_rows.append(res)

v_ok = sum(1 for r in validation_rows if r["ok"])
v_total = len(validation_rows)
print(f"\n3-TRIAL VALIDATION: {v_ok}/{v_total} passed, {failed_v} failed")
if failed_v > 0:
    print("STOPPING: 3-trial validation had failures.")
    for r in validation_rows:
        if not r["ok"]:
            print(f"  FAILED: {r}")
    exit(1)
print("3-TRIAL VALIDATION PASS\n")


# =====================================================================
# STAGE 2: Full 30-trial experiment
# =====================================================================
print("=" * 60)
print("STAGE 2: FULL 30-TRIAL EXPERIMENT")
print("=" * 60)

all_trial_rows = []
failed_full = 0

for trial_idx in range(N_TRIALS_FULL):
    seed = SEED_BASE + trial_idx
    for cfg in ALL_CONFIGS:
        res = run_one(SCENARIO_PRIMARY, cfg, seed, trial_idx)
        if res["ok"]:
            m = res["metrics"]
            print(f"  trial={trial_idx:02d} seed={seed} cfg={cfg:20s} "
                  f"n_gen={m['n_generated']:5d} bpe={m['bytes_per_event']:6.1f}B "
                  f"stale={m['stale_rate']:.3f} prec={m['precision']:.3f} "
                  f"rec={m['recall']:.3f} lat1={m['detect_latency_ob1']} max_q={m['max_queue']}")
        else:
            print(f"  FAIL trial={trial_idx:02d} seed={seed} cfg={cfg}: {res['error']}")
            failed_full += 1
        all_trial_rows.append(res)

n_ok = sum(1 for r in all_trial_rows if r["ok"])
n_total = len(all_trial_rows)
print(f"\nFull experiment: {n_ok}/{n_total} succeeded, {failed_full} failed")


# =====================================================================
# Save results_trials.json (raw trial-level data)
# =====================================================================
def make_serializable(obj):
    if isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [make_serializable(v) for v in obj]
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    elif isinstance(obj, float) and math.isnan(obj):
        return None
    return obj


trials_export = []
for row in all_trial_rows:
    export = dict(
        scenario=row["scenario"],
        trial=row["trial"],
        seed=row["seed"],
        config=row["config"],
        ok=row["ok"],
    )
    if row["ok"]:
        export["metrics"] = make_serializable(row["metrics"])
    else:
        export["error"] = row["error"]
    trials_export.append(export)

with open("results_trials.json", "w") as f:
    json.dump(trials_export, f, indent=2)
print("\nWrote results_trials.json")


# =====================================================================
# Build aggregated results.json (make_figures.py compatible)
# =====================================================================
# Group by config
by_config = {cfg: [] for cfg in ALL_CONFIGS}
for row in all_trial_rows:
    if row["ok"]:
        by_config[row["config"]].append(row)

aggregated_by_config = {}
for cfg in ALL_CONFIGS:
    aggregated_by_config[cfg] = aggregate_results(by_config[cfg])

# Also compute queue peak-of-mean-trace (Figure 10 metric) separately
# For figure 10 we only use 10 seeds (8000-8009) as per fig10 in make_figures.py
fig10_peak_of_mean = {}
for cfg in ["centralized_raw", "fixed_ttl", "full"]:
    traces_all = []
    for row in all_trial_rows:
        if row["ok"] and row["config"] == cfg and row["trial"] < 10:
            # We need the queue_trace from run_trial directly — already captured as peak
            # We need the full trace for mean computation; re-run those 10
            pass
    # We'll compute this properly below

# Re-run 10 trials for queue traces (fig10 needs full traces, not just peak)
print("\nRecomputing 10 queue traces for Figure 10 peak-of-mean metric...")
fig10_configs = ["centralized_raw", "fixed_ttl", "full"]
fig10_data = {cfg: {"peak_of_mean": None, "mean_of_peaks": None} for cfg in fig10_configs}

for cfg in fig10_configs:
    traces_arr = []
    peaks = []
    for trial_idx in range(10):
        seed = SEED_BASE + trial_idx  # seeds 8000-8009
        r = run_trial(SCENARIO_PRIMARY, cfg, seed=seed)
        qt = np.zeros(HOURS)
        for (t, v, q) in r["queue_trace"]:
            qt[t] += q
        qt = qt / 6.0  # mean across villages
        traces_arr.append(qt)
        peaks.append(float(np.max(qt)))
    mean_trace = np.mean(traces_arr, axis=0)
    fig10_data[cfg]["peak_of_mean"] = float(np.max(mean_trace))
    fig10_data[cfg]["mean_of_peaks"] = float(np.mean(peaks))
    print(f"  {cfg}: peak_of_mean={fig10_data[cfg]['peak_of_mean']:.2f}, mean_of_peaks={fig10_data[cfg]['mean_of_peaks']:.2f}")

# Build results.json in the format make_figures.py expects
# make_figures.py reads: d["exp1_main_comparison"][scen][config][metric]["mean"] / "ci95"
results_json = {
    "exp1_main_comparison": {
        SCENARIO_PRIMARY: {}
    },
    "fig10_queue_metrics": fig10_data,
    "experiment_info": {
        "scenario": SCENARIO_PRIMARY,
        "n_trials": N_TRIALS_FULL,
        "seed_range": f"{SEED_BASE}-{SEED_BASE + N_TRIALS_FULL - 1}",
        "configs": ALL_CONFIGS,
        "timestamp": datetime.now().isoformat(),
    }
}

for cfg in ALL_CONFIGS:
    results_json["exp1_main_comparison"][SCENARIO_PRIMARY][cfg] = aggregated_by_config[cfg]

with open("results.json", "w") as f:
    json.dump(make_serializable(results_json), f, indent=2)
print("Wrote results.json")


# =====================================================================
# Validate results.json
# =====================================================================
print("\n=== VALIDATING results.json ===")
with open("results.json") as f:
    d = json.load(f)

scen_data = d["exp1_main_comparison"][SCENARIO_PRIMARY]
for cfg in ALL_CONFIGS:
    assert cfg in scen_data, f"Missing config: {cfg}"
    for metric in ["stale_rate", "bytes_per_event", "precision", "recall", "max_queue",
                   "detect_latency_ob1", "n_generated", "proactive_discards"]:
        assert metric in scen_data[cfg], f"Missing metric {metric} in {cfg}"
        assert "mean" in scen_data[cfg][metric], f"Missing mean for {metric} in {cfg}"
        assert "ci95" in scen_data[cfg][metric], f"Missing ci95 for {metric} in {cfg}"
print("results.json validation PASSED")


# =====================================================================
# Print summary table
# =====================================================================
print("\n" + "=" * 80)
print("SUMMARY TABLE (long_outage, N=30 trials, mean [95% CI])")
print("=" * 80)
hdr = f"{'Config':22s}  {'bpe(B)':>10s}  {'stale%':>8s}  {'disc%':>8s}  {'prec':>6s}  {'rec':>6s}  {'lat_ob1':>8s}  {'max_q':>6s}"
print(hdr)
print("-" * 80)
for cfg in ALL_CONFIGS:
    agg = aggregated_by_config[cfg]
    bpe = agg["bytes_per_event"]
    sr = agg["stale_rate"]
    disc_n = agg["proactive_discards"]
    n_gen = agg["n_generated"]
    # disc% = proactive_discards / n_generated * 100
    disc_pct = (disc_n["mean"] / n_gen["mean"] * 100) if n_gen["mean"] else float("nan")
    prec = agg["precision"]
    rec = agg["recall"]
    lat = agg["detect_latency_ob1"]
    mq = agg["max_queue"]
    lat_str = f"{lat['mean']:.1f}" if not math.isnan(lat["mean"]) else "nan"
    print(f"{cfg:22s}  {bpe['mean']:8.1f}B  {sr['mean']*100:6.2f}%  {disc_pct:6.2f}%  "
          f"{prec['mean']:6.3f}  {rec['mean']:6.3f}  {lat_str:>8s}h  {mq['mean']:6.1f}")
print()


# =====================================================================
# Experiment manifest
# =====================================================================
manifest = {
    "experiment_name": "ArogyaTwin Evaluation Experiment",
    "scenario": SCENARIO_PRIMARY,
    "trial_count": N_TRIALS_FULL,
    "seed_formula": f"seed = {SEED_BASE} + trial_index  (trial 0..{N_TRIALS_FULL-1})",
    "seed_range": f"{SEED_BASE}..{SEED_BASE + N_TRIALS_FULL - 1}",
    "crn_note": (
        "Each trial uses a single integer seed passed to numpy.random.default_rng(seed). "
        "All configurations within a trial receive the SAME seed value (CRN pairing). "
        "However, each config draws from that RNG independently, so the actual "
        "sequence of random numbers diverges after each config's generate_ground_truth() call."
    ),
    "configuration_list": ALL_CONFIGS,
    "simulation_horizon_hours": HOURS,
    "simulation_horizon_days": HOURS // 24,
    "packet_sizes": {
        "compact_bytes": COMPACT_SIZE_BYTES,
        "raw_bytes": RAW_SIZE_BYTES,
        "reduction_pct": (RAW_SIZE_BYTES - COMPACT_SIZE_BYTES) / RAW_SIZE_BYTES * 100,
    },
    "trust_weights": TRUST_WEIGHTS,
    "ttl_bounds": {"min": TTL_MIN, "max": TTL_MAX},
    "ttl_calibration": {"B_L": B_L, "B_T": B_T},
    "diversity_threshold_sources": CANDIDATE_MIN_SOURCES,
    "outbreak_1": OUTBREAK_1,
    "outbreak_2": OUTBREAK_2,
    "adversarial_village": ADVERSARIAL_VILLAGE,
    "adversarial_window": ADVERSARIAL_WINDOW,
    "verification_delay_hours": VERIFICATION_DELAY,
    "h_alpha": H_ALPHA,
    "h_prior": H_PRIOR,
    "statistical_method": "t-distribution 95% CI, ddof=1, scipy.stats.t.ppf(0.975, n-1)",
    "execution_timestamp": datetime.now().isoformat(),
    "successful_trial_configs": n_ok,
    "failed_trial_configs": failed_full,
    "python_version": "3.13.7",
    "numpy_version": "2.5.2",
    "scipy_version": "1.18.1",
    "dtn_status": "Implemented in dtn.py (Epidemic, Spray-and-Wait, PRoPHET)",
    "source_files": {
        "sim/core.py": "simulation configuration and ground-truth generation",
        "sim/engine.py": "run_trial() main simulation loop",
        "sim/metrics.py": "compute_metrics() post-processing",
        "make_figures.py": "figure generation (reads results.json)",
        "dtn.py": "DTN relay protocol comparison (separate sub-experiment)",
    }
}

with open("experiment_manifest.json", "w") as f:
    json.dump(make_serializable(manifest), f, indent=2)
print("Wrote experiment_manifest.json")

print("\n=== FULL EXPERIMENT COMPLETE ===")
print(f"Successful: {n_ok}/{n_total}  Failed: {failed_full}")
print(f"Seed range: {SEED_BASE}..{SEED_BASE + N_TRIALS_FULL - 1}")
