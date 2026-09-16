"""
DTN Sub-Experiment Runner
=========================
Executes dtn.py's run_dtn_comparison() with extended trial-level output.
- n_trials = 15 (as implemented in dtn.py)
- seed_offset = 7000 (as implemented)
- protocols: epidemic, spray, prophet
- modes: naive (no expiry), expiry_aware (ArogyaTwin TTL check)

Produces:
  dtn_results_trials.json  -- raw trial-level data
  dtn_results.json         -- summary (matching dtn.py's own output)
  dtn_experiment_manifest.json
"""
import json, math, sys, traceback
from datetime import datetime
import numpy as np
import scipy.stats

# Add repo root to path so sim.core is resolvable
sys.path.insert(0, ".")

from sim.core import (
    N_VILLAGES, SOURCES_PER_VILLAGE, HOURS, COMPACT_SIZE_BYTES,
    CANDIDATE_MIN_SOURCES, CANDIDATE_MIN_CONF, generate_ground_truth,
)

# Import DTN functions from dtn.py at root (dtn.py itself uses 'from sim.core import ...')
import importlib.util, os
spec = importlib.util.spec_from_file_location("dtn", os.path.join(".", "dtn.py"))
dtn_mod = importlib.util.load_from_spec = None

# Use direct import
from dtn import build_packets, run_protocol, run_dtn_comparison, summarize_dtn

N_TRIALS = 15
SEED_OFFSET = 7000
PROTOCOLS = ["epidemic", "spray", "prophet"]
MODES = ["naive", "expiry_aware"]
METRIC_KEYS = ["n_copies", "n_stale_copies", "stale_copy_rate",
                "total_bytes", "stale_bytes",
                "n_delivered", "n_generated", "delivery_ratio",
                "mean_valid_latency"]

print("=" * 60)
print("DTN SUB-EXPERIMENT")
print(f"n_trials={N_TRIALS}, seed_offset={SEED_OFFSET}")
print(f"protocols: {PROTOCOLS}")
print(f"modes: {MODES}")
print("=" * 60)

# Run with trial-level capture (extend run_dtn_comparison to preserve rows)
trial_rows = []
results_raw = {proto: {mode: [] for mode in MODES} for proto in PROTOCOLS}
failed = 0

for i in range(N_TRIALS):
    seed = SEED_OFFSET + i
    rng = np.random.default_rng(seed)
    packets = build_packets(rng)
    print(f"\n  trial {i:02d} seed={seed}  n_packets={len(packets)}")

    for proto in PROTOCOLS:
        for mode in MODES:
            aware = (mode == "expiry_aware")
            try:
                rng2 = np.random.default_rng(seed * 100 + hash(proto + mode) % 1000)
                r = run_protocol(rng2, packets, proto, aware)
                results_raw[proto][mode].append(r)
                trial_rows.append(dict(
                    trial=i, seed=seed, protocol=proto, mode=mode, ok=True, metrics=r
                ))
                lat_str = f"{r['mean_valid_latency']:.1f}h" if not math.isnan(r["mean_valid_latency"]) else "nan"
                print(f"    {proto:10s} {mode:14s}: copies={r['n_copies']:5d} "
                      f"stale_rate={r['stale_copy_rate']:.3f} "
                      f"deliv={r['delivery_ratio']:.3f} lat={lat_str}")
            except Exception as e:
                failed += 1
                trial_rows.append(dict(
                    trial=i, seed=seed, protocol=proto, mode=mode, ok=False,
                    error=str(e), traceback=traceback.format_exc()
                ))
                print(f"    {proto:10s} {mode:14s}: FAILED: {e}")

n_ok = sum(1 for r in trial_rows if r["ok"])
n_total = len(trial_rows)
print(f"\nDTN experiment: {n_ok}/{n_total} succeeded, {failed} failed")


# =====================================================================
# Aggregate statistics
# =====================================================================
def ci95(values):
    vals = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    n = len(vals)
    if n == 0:
        return dict(n=0, mean=float("nan"), sd=float("nan"), se=float("nan"),
                    ci95_margin=float("nan"), ci95_lo=float("nan"), ci95_hi=float("nan"))
    from math import sqrt
    arr = np.array(vals, dtype=float)
    mean = float(np.mean(arr))
    if n == 1:
        sd, se, tcrit = 0.0, 0.0, 0.0
    else:
        sd = float(np.std(arr, ddof=1))
        se = sd / sqrt(n)
        tcrit = float(scipy.stats.t.ppf(0.975, n - 1))
    margin = tcrit * se
    return dict(n=n, mean=mean, sd=sd, se=se,
                ci95_margin=margin, ci95_lo=mean - margin, ci95_hi=mean + margin)


aggregated = {}
for proto in PROTOCOLS:
    aggregated[proto] = {}
    for mode in MODES:
        rows = results_raw[proto][mode]
        aggregated[proto][mode] = {}
        for k in METRIC_KEYS:
            vals = [r[k] for r in rows]
            aggregated[proto][mode][k] = ci95(vals)

# =====================================================================
# Print summary table
# =====================================================================
print("\n" + "=" * 80)
print("DTN SUMMARY TABLE")
print("=" * 80)
print(f"{'Protocol':10s} {'Mode':14s} {'n_copies':>8s} {'stale_rate':>10s} "
      f"{'deliv_ratio':>11s} {'valid_lat(h)':>12s}")
print("-" * 80)
for proto in PROTOCOLS:
    for mode in MODES:
        a = aggregated[proto][mode]
        lat = a["mean_valid_latency"]
        lat_str = f"{lat['mean']:.2f}" if lat["n"] > 0 and not math.isnan(lat["mean"]) else "nan"
        print(f"{proto:10s} {mode:14s} {a['n_copies']['mean']:8.1f} "
              f"{a['stale_copy_rate']['mean']:10.4f} "
              f"{a['delivery_ratio']['mean']:11.4f} {lat_str:>12s}")
print()

# =====================================================================
# Save outputs
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

# Raw trial-level
trials_export = []
for row in trial_rows:
    export = dict(trial=row["trial"], seed=row["seed"],
                  protocol=row["protocol"], mode=row["mode"], ok=row["ok"])
    if row["ok"]:
        export["metrics"] = make_serializable(row["metrics"])
    else:
        export["error"] = row["error"]
    trials_export.append(export)

with open("dtn_results_trials.json", "w") as f:
    json.dump(trials_export, f, indent=2)
print("Wrote dtn_results_trials.json")

# Summary (matching dtn.py's own output format + CI extension)
summary_simple = summarize_dtn(results_raw)
dtn_results_full = {
    "summary": make_serializable(summary_simple),
    "aggregated_with_ci": make_serializable(aggregated),
    "experiment_info": {
        "n_trials": N_TRIALS,
        "seed_range": f"{SEED_OFFSET}-{SEED_OFFSET + N_TRIALS - 1}",
        "seed_formula": f"seed = {SEED_OFFSET} + trial_index",
        "protocols": PROTOCOLS,
        "modes": MODES,
        "rng_per_trial": f"rng = default_rng(seed), packets = build_packets(rng), "
                         f"rng2 = default_rng(seed*100 + hash(proto+mode)%1000)",
        "dtn_params": {
            "N_RELAYS": 6, "BUFFER_CAP": 40,
            "P_G2R": 0.15, "P_R2H": 0.10, "P_R2R": 0.05,
            "SPRAY_L": 8,
            "TTL_ROUTINE": 18, "TTL_CANDIDATE": 30,
            "P_INIT": 0.75, "BETA": 0.25, "GAMMA": 0.98,
        },
        "n_successful": n_ok,
        "n_failed": failed,
        "timestamp": datetime.now().isoformat(),
    }
}

with open("dtn_results.json", "w") as f:
    json.dump(dtn_results_full, f, indent=2)
print("Wrote dtn_results.json")

# Manifest
manifest = {
    "experiment_name": "ArogyaTwin DTN Relay Sub-Experiment",
    "description": (
        "Sensitivity of ArogyaTwin's expiry/trust layer to underlying opportunistic relay strategy. "
        "Compares three DTN routing protocols (Epidemic, binary Spray-and-Wait, PRoPHET) "
        "with and without ArogyaTwin per-packet expiry check. Separate from the main 30-trial experiment."
    ),
    "n_trials": N_TRIALS,
    "seed_offset": SEED_OFFSET,
    "seed_range": f"{SEED_OFFSET}-{SEED_OFFSET + N_TRIALS - 1}",
    "protocols": PROTOCOLS,
    "modes": {"naive": "no expiry check", "expiry_aware": "ArogyaTwin TTL expiry applied before relay"},
    "source_file": "dtn.py",
    "canonical_imports": "from sim.core import ...",
    "packet_size_bytes": COMPACT_SIZE_BYTES,
    "ttl_routine_h": 18,
    "ttl_candidate_h": 30,
    "statistical_method": "t-distribution 95% CI, ddof=1",
    "n_successful": n_ok,
    "n_failed": failed,
    "execution_timestamp": datetime.now().isoformat(),
    "relationship_to_main_experiment": (
        "SEPARATE. Main experiment: 30 trials, seeds 8000-8029, run_trial() in engine.py. "
        "DTN experiment: 15 trials, seeds 7000-7014, run_protocol() in dtn.py."
    )
}
with open("dtn_experiment_manifest.json", "w") as f:
    json.dump(make_serializable(manifest), f, indent=2)
print("Wrote dtn_experiment_manifest.json")

print("\nDTN SUB-EXPERIMENT COMPLETE")
